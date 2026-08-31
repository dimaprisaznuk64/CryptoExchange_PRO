import logging
from datetime import datetime, UTC
from decimal import Decimal

from app.core.cache import cache_get, cache_set
from app.services import binance_client
from app.services.market import _live_price, _hash_seed

logger = logging.getLogger(__name__)

BINANCE_DEPTH_TTL = 2


def _simulated_order_book(pair_symbol: str, depth: int) -> dict:
    """Synthetic order book derived from a deterministic seed per second."""
    price = _live_price(pair_symbol, datetime.now(UTC))
    seed = _hash_seed(pair_symbol + ":book:" + str(int(datetime.now(UTC).timestamp() // 2)))

    levels = []
    mid = price
    # deterministic pseudo-random walk for bid/ask offsets
    for i in range(1, depth + 1):
        component = seed + i * 7919
        delta = Decimal(component % 500) / Decimal(100000)  # 0..0.5%
        ask = mid * (Decimal("1") + delta)
        bid = mid * (Decimal("1") - delta)
        ask_qty = Decimal((seed + i * 104729) % 3000 + 100) / Decimal(1000)
        bid_qty = Decimal((seed + i * 15485863) % 3000 + 100) / Decimal(1000)
        levels.append(
            {
                "bid": float(bid),
                "bid_qty": float(bid_qty),
                "ask": float(ask),
                "ask_qty": float(ask_qty),
            }
        )

    best_bid = max(l["bid"] for l in levels)
    best_ask = min(l["ask"] for l in levels)
    return {
        "pair": pair_symbol,
        "timestamp": datetime.now(UTC).isoformat(),
        "best_bid": best_bid,
        "best_ask": best_ask,
        "spread": best_ask - best_bid,
        "levels": levels,
    }


async def order_book(pair_symbol: str, depth: int = 10) -> dict:
    """Real order book depth from Binance when available, else the
    deterministic synthetic book."""
    binance_sym = binance_client.binance_symbol(pair_symbol)
    if binance_sym:
        cache_key = f"market:binance:depth:{binance_sym}:{depth}"
        raw = await cache_get(cache_key)
        if raw is None:
            raw = await binance_client.fetch_depth(binance_sym, depth)
            if raw is not None:
                await cache_set(cache_key, raw, BINANCE_DEPTH_TTL)
        if raw:
            try:
                bids = raw["bids"][:depth]
                asks = raw["asks"][:depth]
                n = min(len(bids), len(asks))
                levels = [
                    {
                        "bid": float(bids[i][0]),
                        "bid_qty": float(bids[i][1]),
                        "ask": float(asks[i][0]),
                        "ask_qty": float(asks[i][1]),
                    }
                    for i in range(n)
                ]
                if levels:
                    best_bid = max(l["bid"] for l in levels)
                    best_ask = min(l["ask"] for l in levels)
                    return {
                        "pair": pair_symbol,
                        "timestamp": datetime.now(UTC).isoformat(),
                        "best_bid": best_bid,
                        "best_ask": best_ask,
                        "spread": best_ask - best_bid,
                        "levels": levels,
                    }
            except (KeyError, IndexError, ValueError, TypeError) as e:
                logger.warning("Binance depth parse failed for %s: %s", pair_symbol, e)
    return _simulated_order_book(pair_symbol, depth)
