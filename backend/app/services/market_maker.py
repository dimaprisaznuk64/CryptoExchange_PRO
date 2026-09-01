"""Simulated market maker: an evolving in-memory order book + trade tape.

When Binance is unreachable (common on Render free tier / offline dev), the
live price, order book and market-trades feed fall back to this engine so the
UI never looks empty or dead. Each pair is lazily seeded around the
deterministic anchor price (``app.services.market._current_price``) and then,
on every background tick, the engine:

* drifts the mid price with a bounded random walk pulled slowly back to the
  anchor (keeps prices coherent with candles / 24h stats),
* prints trades that consume the best resting level,
* replenishes/prunes levels so a full ladder always straddles the mid,
* keeps a rolling tape of recent prints.

Everything is synchronous and never awaits while mutating state, so reads and
writes are atomic inside the single asyncio event loop shared with HTTP/WS
handlers (no locks needed).
"""

import hashlib
import logging
import random
import time
from collections import deque
from datetime import datetime, UTC
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)

# Grid step between adjacent book levels, as a fraction of the mid price.
GRID_STEP = Decimal("0.0005")
# Levels farther than ±1% from the mid are pruned and rebuilt around it.
MAX_DISTANCE = Decimal("0.01")
# Gap between mid and the best level that triggers insertion of a fresh one.
MAX_BEST_GAP = Decimal("0.002")
# Every REANCHOR_SECONDS the mid is pulled part of the way back to the anchor.
REANCHOR_SECONDS = 60
REANCHOR_STEP = Decimal("0.15")


def _hash_seed(value: str) -> int:
    return int(hashlib.sha256(value.encode()).hexdigest()[:8], 16)


def _round_price(value: Decimal, precision: int = 2) -> Decimal:
    quantum = Decimal("1").scaleb(-precision)
    return (value / quantum).to_integral_value(rounding=ROUND_HALF_UP) * quantum


class _PairState:
    __slots__ = ("mid", "bids", "asks", "tape", "rng", "anchor_ts")

    def __init__(self, mid: Decimal, levels: int, tape_maxlen: int, seed: int):
        self.mid = mid
        self.rng = random.Random(seed)
        self.tape: deque[dict] = deque(maxlen=tape_maxlen)
        self.anchor_ts = time.time()
        self.bids, self.asks = self.layout(mid, levels)

    @staticmethod
    def _notional(mid: Decimal, rng: random.Random) -> Decimal:
        """Notional (quote units) resting behind one level: ~0.5%..3% of mid."""
        return mid * Decimal(str(rng.uniform(0.005, 0.03)))

    @staticmethod
    def _qty(mid: Decimal, price: Decimal, rng: random.Random) -> Decimal:
        qty = _PairState._notional(mid, rng) / price
        return max(qty, Decimal("0.000001")).quantize(Decimal("0.000001"))

    def layout(self, mid: Decimal, levels: int) -> tuple[list, list]:
        """Full ladder: bids descending, asks ascending, both length `levels`."""
        bids: list = []
        asks: list = []
        for i in range(levels):
            jit_b = Decimal(str(self.rng.uniform(0.7, 1.4)))
            jit_a = Decimal(str(self.rng.uniform(0.7, 1.4)))
            bid = mid * (Decimal("1") - GRID_STEP * (i + 1) * jit_b)
            ask = mid * (Decimal("1") + GRID_STEP * (i + 1) * jit_a)
            bids.append([_round_price(bid), self._qty(mid, bid, self.rng)])
            asks.append([_round_price(ask), self._qty(mid, ask, self.rng)])
        return bids, asks


class MarketMakerEngine:
    def __init__(
        self,
        levels: int = 12,
        tape_maxlen: int = 60,
        trade_probability: float = 0.7,
    ):
        self.levels = levels
        self.tape_maxlen = tape_maxlen
        self.trade_probability = trade_probability
        self._states: dict[str, _PairState] = {}

    @staticmethod
    def _anchor(pair_symbol: str) -> Decimal:
        # Lazy import avoids a module-level cycle (market.py imports this engine).
        from app.services.market import _current_price

        return _current_price(pair_symbol)

    def _ensure(self, pair_symbol: str) -> _PairState:
        state = self._states.get(pair_symbol)
        if state is None:
            state = _PairState(
                self._anchor(pair_symbol),
                self.levels,
                self.tape_maxlen,
                _hash_seed(pair_symbol + ":mm"),
            )
            self._states[pair_symbol] = state
        return state

    def price(self, pair_symbol: str) -> Decimal:
        return self._ensure(pair_symbol).mid

    def tick(self, symbols: list[str]) -> None:
        now = time.time()
        for pair in symbols:
            self._tick_pair(pair, self._ensure(pair), now)

    def _tick_pair(self, pair_symbol: str, state: _PairState, now: float) -> None:
        mid = state.mid

        if now - state.anchor_ts >= REANCHOR_SECONDS:
            mid = mid + (self._anchor(pair_symbol) - mid) * REANCHOR_STEP
            state.anchor_ts = now

        if state.rng.random() < self.trade_probability:
            side = "buy" if state.rng.random() < 0.5 else "sell"
            book = state.asks if side == "buy" else state.bids
            if book:
                price = book[0][0]
                qty = self._trade_qty(mid, price, book[0][1], state.rng)
                self._consume(book, qty)
                drift = Decimal(str(state.rng.uniform(-0.0006, 0.0006)))
                impact = Decimal(str(state.rng.uniform(0.0001, 0.0004)))
                direction = Decimal("1") if side == "buy" else Decimal("-1")
                mid = mid * (Decimal("1") + drift + impact * direction)
                state.tape.appendleft(
                    {
                        "time": datetime.now(UTC).isoformat(),
                        "price": float(price),
                        "qty": float(qty),
                        "side": side,
                    }
                )

        mid = self._rebalance(pair_symbol, state, mid)
        state.mid = mid

    @staticmethod
    def _trade_qty(
        mid: Decimal, price: Decimal, top_qty: Decimal, rng: random.Random
    ) -> Decimal:
        """Small taker print — usually consumes only a slice of the best level."""
        notional = mid * Decimal(str(rng.uniform(0.0008, 0.006)))
        qty = notional / price
        return min(max(qty, Decimal("0.000001")), top_qty)

    @staticmethod
    def _consume(book: list, qty: Decimal) -> None:
        if not book:
            return
        top = book[0]
        remaining = top[1] - qty
        if remaining > Decimal("0"):
            top[1] = remaining
        else:
            book.pop(0)

    def _rebalance(self, pair_symbol: str, state: _PairState, mid: Decimal) -> Decimal:
        # Prune levels the mid has walked far away from.
        state.bids = [lvl for lvl in state.bids if lvl[0] >= mid * (Decimal("1") - MAX_DISTANCE)]
        state.asks = [lvl for lvl in state.asks if lvl[0] <= mid * (Decimal("1") + MAX_DISTANCE)]

        # Ensure the book still straddles the moved mid.
        if not state.bids or state.bids[0][0] < mid * (Decimal("1") - MAX_BEST_GAP):
            p = mid * (Decimal("1") - GRID_STEP)
            state.bids.insert(0, [_round_price(p), _PairState._qty(mid, p, state.rng)])
        if not state.asks or state.asks[0][0] > mid * (Decimal("1") + MAX_BEST_GAP):
            p = mid * (Decimal("1") + GRID_STEP)
            state.asks.insert(0, [_round_price(p), _PairState._qty(mid, p, state.rng)])

        # Refill the ladder back up to the requested level count.
        while len(state.bids) < self.levels:
            p = state.bids[-1][0] * (Decimal("1") - GRID_STEP)
            state.bids.append([_round_price(p), _PairState._qty(mid, p, state.rng)])
        while len(state.asks) < self.levels:
            p = state.asks[-1][0] * (Decimal("1") + GRID_STEP)
            state.asks.append([_round_price(p), _PairState._qty(mid, p, state.rng)])

        state.bids.sort(key=lambda lvl: lvl[0], reverse=True)
        state.asks.sort(key=lambda lvl: lvl[0])
        return mid

    def snapshot(self, pair_symbol: str, depth: int = 10) -> dict:
        """Order book snapshot in the same shape as the REST depth endpoint."""
        state = self._ensure(pair_symbol)
        bids = sorted(state.bids, key=lambda lvl: lvl[0], reverse=True)
        asks = sorted(state.asks, key=lambda lvl: lvl[0])

        n = min(depth, len(bids), len(asks))
        if n == 0:  # ladder was fully consumed — rebuild rather than serve an empty book
            state.bids, state.asks = state.layout(state.mid, self.levels)
            bids = sorted(state.bids, key=lambda lvl: lvl[0], reverse=True)
            asks = sorted(state.asks, key=lambda lvl: lvl[0])
            n = min(depth, len(bids), len(asks))

        levels = [
            {
                "bid": float(bids[i][0]),
                "bid_qty": float(bids[i][1]),
                "ask": float(asks[i][0]),
                "ask_qty": float(asks[i][1]),
            }
            for i in range(n)
        ]
        return {
            "pair": pair_symbol,
            "timestamp": datetime.now(UTC).isoformat(),
            "best_bid": float(bids[0][0]),
            "best_ask": float(asks[0][0]),
            "spread": float(asks[0][0] - bids[0][0]),
            "levels": levels,
        }

    def recent_trades(self, pair_symbol: str, limit: int = 30) -> list[dict]:
        """Newest-first trade prints from the tape (simulated market data)."""
        state = self._ensure(pair_symbol)
        return [
            {
                "time": t["time"],
                "price": float(t["price"]),
                "qty": float(t["qty"]),
                "side": t["side"],
            }
            for t in list(state.tape)[:limit]
        ]


engine = MarketMakerEngine()