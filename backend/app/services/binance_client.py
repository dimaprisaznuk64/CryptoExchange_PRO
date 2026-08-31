"""Thin async client for Binance's public spot market-data REST API.

No API key required — these are all public endpoints (ticker price,
24hr stats, klines, order book depth). Every function has a short
timeout; callers are expected to fall back to the simulated feed in
app.services.market on any failure (network error, rate limit, or the
occasional geo-block some hosts hit on api.binance.com).
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"
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


async def fetch_price(symbol: str) -> float | None:
    """GET /api/v3/ticker/price?symbol=BTCUSDT -> last traded price."""
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.get(
                f"{BASE_URL}/api/v3/ticker/price", params={"symbol": symbol}
            )
            resp.raise_for_status()
            data = resp.json()
            return float(data["price"])
    except Exception as e:
        logger.warning("Binance price fetch failed for %s: %s", symbol, e)
        return None


async def fetch_24hr(symbol: str) -> dict[str, Any] | None:
    """GET /api/v3/ticker/24hr?symbol=BTCUSDT -> open/high/low/close/volume/count."""
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.get(
                f"{BASE_URL}/api/v3/ticker/24hr", params={"symbol": symbol}
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning("Binance 24hr fetch failed for %s: %s", symbol, e)
        return None


async def fetch_klines(
    symbol: str, interval: str, limit: int = 120
) -> list[list[Any]] | None:
    """GET /api/v3/klines -> [[openTime, open, high, low, close, volume, ...], ...]."""
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.get(
                f"{BASE_URL}/api/v3/klines",
                params={"symbol": symbol, "interval": interval, "limit": limit},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning("Binance klines fetch failed for %s: %s", symbol, e)
        return None


async def fetch_depth(symbol: str, limit: int = 10) -> dict[str, Any] | None:
    """GET /api/v3/depth -> {"bids": [[price, qty], ...], "asks": [[price, qty], ...]}."""
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.get(
                f"{BASE_URL}/api/v3/depth",
                params={"symbol": symbol, "limit": limit},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning("Binance depth fetch failed for %s: %s", symbol, e)
        return None
