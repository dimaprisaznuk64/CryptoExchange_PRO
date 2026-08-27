import math
from datetime import datetime, UTC
from decimal import Decimal

from app.services.market import _live_price, _hash_seed


def order_book(pair_symbol: str, depth: int = 10) -> dict:
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
