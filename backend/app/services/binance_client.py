"""Thin async client for Binance's public spot market-data REST API.

No API key required — these are all public endpoints (ticker price,
24hr stats, klines, order book depth). Every function has a short
timeout and tries each known Binance host in turn before giving up;
callers are expected to fall back to the simulated feed in
app.services.market on any failure (network error, rate limit, or the
occasional geo-block some hosts hit on api.binance.com).
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Try hosts in order. `data-api.binance.vision` is Binance's public
# market-data-only host and is generally reachable from more cloud
# providers (Render, Fly.io, etc.) than api.binance.com.
BASE_URLS = [
    "https://api.binance.com",
    "https://data-api.binance.vision",
]
REQUEST_TIMEOUT = 4.0

# App trading pairs -> Binance spot symbol. Binance has no BTC/ETH-"USD"
# spot pair, so USD legs are approximated with the USDT price (1 USDT ~ 1 USD).
PAIR_TO_BINANCE = {
    "BTC/USD": "BTCUSDT",
    "BTC/USDT": "BTCUSDT",
    "ETH/USD": "ETHUSDT",
    "ETH/USDT": "ETHUSDT",
}

# App candle interval (minutes) -> Binance kline interval string
INTERVAL_MAP = {1: "1m", 5: "5m", 15: "15m", 60: "1h"}


def binance_symbol(pair_symbol: str) -> str | None:
    return PAIR_TO_BINANCE.get(pair_symbol)


async def _request(path: str, params: dict[str, Any], what: str) -> Any | None:
    """GET from the first Binance host that answers; None if all fail."""
    last_error: Exception | None = None
    for base in BASE_URLS:
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                resp = await client.get(f"{base}{path}", params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:  # noqa: BLE001
            last_error = e
            logger.warning("Binance %s failed on %s: %s", what, base, e)
    logger.warning("Binance %s failed on all hosts: %s", what, last_error)
    return None


async def fetch_price(symbol: str) -> float | None:
    """GET /api/v3/ticker/price?symbol=BTCUSDT -> last traded price."""
    data = await _request(
        "/api/v3/ticker/price", {"symbol": symbol}, f"price {symbol}"
    )
    try:
        return float(data["price"])
    except (KeyError, TypeError, ValueError):
        return None


async def fetch_24hr(symbol: str) -> dict[str, Any] | None:
    """GET /api/v3/ticker/24hr?symbol=BTCUSDT -> open/high/low/close/volume/count."""
    data = await _request(
        "/api/v3/ticker/24hr", {"symbol": symbol}, f"24hr {symbol}"
    )
    return data if isinstance(data, dict) else None


async def fetch_klines(
    symbol: str, interval: str, limit: int = 120
) -> list[list[Any]] | None:
    """GET /api/v3/klines -> [[openTime, open, high, low, close, volume, ...], ...]."""
    data = await _request(
        "/api/v3/klines",
        {"symbol": symbol, "interval": interval, "limit": limit},
        f"klines {symbol}",
    )
    return data if isinstance(data, list) else None


async def fetch_depth(symbol: str, limit: int = 10) -> dict[str, Any] | None:
    """GET /api/v3/depth -> {"bids": [[price, qty], ...], "asks": [[price, qty], ...]}."""
    data = await _request(
        "/api/v3/depth",
        {"symbol": symbol, "limit": limit},
        f"depth {symbol}",
    )
    return data if isinstance(data, dict) else None
