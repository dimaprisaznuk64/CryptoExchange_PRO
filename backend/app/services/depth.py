import logging
from datetime import datetime, UTC

from app.core.cache import cache_get, cache_set
from app.services import binance_client
from app.services.market_maker import engine

logger = logging.getLogger(__name__)

BINANCE_DEPTH_TTL = 2


def _simulated_order_book(pair_symbol: str, depth: int) -> dict:
    """Evolving synthetic order book from the in-process market maker engine.

    Unlike the old per-second deterministic book, this one actually changes
    level-by-level on every background tick (trades consume the best level,
    the mid drifts, and the ladder is replenished), so the UI feels alive
    rather than frozen when Binance is unreachable.
    """
    return engine.snapshot(pair_symbol, depth)


async def order_book(pair_symbol: str, depth: int = 10) -> dict:
    """Real order book depth from Binance when available, else the evolving
    synthetic book from the market maker engine."""
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
