import logging
import math
import hashlib
from datetime import datetime, timedelta, UTC
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trading_pair import TradingPair
from app.core.cache import cache_get, cache_set
from app.services import binance_client
from app.services.market_maker import engine

logger = logging.getLogger(__name__)

# TTL for Redis-cached market data (fall back to in-memory compute when Redis is down)
TICKERS_CACHE_TTL = 5
PAIRS_CACHE_TTL = 60
BINANCE_24HR_TTL = 3
BINANCE_PRICE_TTL = 2
BINANCE_KLINES_TTL = 15

# Deterministic base prices (simulated market_data feed)
BASE_PRICES = {
    "BTC/USD": Decimal("61500.00"),
    "BTC/USDT": Decimal("61480.00"),
    "ETH/USD": Decimal("3350.00"),
    "ETH/USDT": Decimal("3345.00"),
}

# Max intra-day swing as a fraction for 24h stats
DAILY_VOLATILITY = 0.04


def _hash_seed(value: str) -> int:
    return int(hashlib.sha256(value.encode()).hexdigest()[:8], 16)


def _current_price(pair_symbol: str) -> Decimal:
    base = BASE_PRICES.get(pair_symbol, Decimal("100.00"))
    seed = _hash_seed(pair_symbol + ":" + str(int(datetime.now(UTC).timestamp() // 60)))
    spread = Decimal(seed % 2001 - 1000) / Decimal(10000)  # -10%..+10% deterministic per minute
    return base * (Decimal("1") + spread)


def _price_at(pair_symbol: str, ts: datetime) -> Decimal:
    base = BASE_PRICES.get(pair_symbol, Decimal("100.00"))
    seed = _hash_seed(pair_symbol + ":" + str(int(ts.timestamp() // 60)))
    spread = Decimal(seed % 2001 - 1000) / Decimal(10000)
    return base * (Decimal("1") + spread)


def _live_price(pair_symbol: str, ts: datetime) -> Decimal:
    """Smooth per-second price variation for realtime feed."""
    base = _current_price(pair_symbol)
    sec = int(ts.timestamp())
    drift = math.sin(sec / 8.0) * 0.002 + math.sin(sec / 23.0) * 0.0015
    return base * (Decimal("1") + Decimal(str(drift)))


async def _binance_24hr_cached(binance_sym: str) -> dict | None:
    """24hr ticker payload from Binance, Redis-cached for a few seconds so
    every connected client/pair doesn't trigger its own upstream call."""
    cache_key = f"market:binance:24hr:{binance_sym}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    data = await binance_client.fetch_24hr(binance_sym)
    if data is not None:
        await cache_set(cache_key, data, BINANCE_24HR_TTL)
    return data


async def get_live_price_async(pair_symbol: str) -> Decimal:
    """Best-effort real price from Binance; falls back to the deterministic
    simulated feed if Binance is unreachable (rate limit, geo-block, etc.)."""
    binance_sym = binance_client.binance_symbol(pair_symbol)
    if binance_sym:
        cache_key = f"market:binance:price:{binance_sym}"
        cached = await cache_get(cache_key)
        if cached is not None:
            return Decimal(str(cached))
        price = await binance_client.fetch_price(binance_sym)
        if price is not None:
            await cache_set(cache_key, price, BINANCE_PRICE_TTL)
            return Decimal(str(price))
    # Simulated fallback: the market maker's evolving mid instead of the static
    # per-minute anchor, so the realtime feed feels alive when Binance is down.
    return engine.price(pair_symbol)


async def recent_trades(pair_symbol: str, limit: int = 30) -> list[dict]:
    """Recent executed market trades (tape).

    Real Binance trade prints when the upstream feed is reachable, otherwise
    the market maker's simulated tape — so the trade tape never looks dead.
    Returns newest-first: [{time, price, qty, side}, ...].
    """
    binance_sym = binance_client.binance_symbol(pair_symbol)
    if binance_sym:
        n = min(limit, 100)
        cache_key = f"market:binance:trades:{binance_sym}:{n}"
        raw = await cache_get(cache_key)
        if raw is None:
            raw = await binance_client.fetch_recent_trades(binance_sym, limit=n)
            if raw is not None:
                await cache_set(cache_key, raw, BINANCE_PRICE_TTL)
        if raw:
            try:
                trades = [
                    {
                        "time": datetime.fromtimestamp(t["time"] / 1000, UTC).isoformat(),
                        "price": float(t["price"]),
                        "qty": float(t["qty"]),
                        "side": "sell" if t.get("isBuyerMaker") else "buy",
                    }
                    for t in raw
                ]
                trades.reverse()  # newest first, like the simulated tape
                return trades[:limit]
            except (KeyError, TypeError, ValueError) as e:
                logger.warning("Binance trades parse failed for %s: %s", pair_symbol, e)
    return engine.recent_trades(pair_symbol, limit)


async def list_pairs(db: AsyncSession) -> list[TradingPair]:
    result = await db.execute(
        select(TradingPair)
        .options(selectinload(TradingPair.base_asset), selectinload(TradingPair.quote_asset))
        .where(TradingPair.is_active == True)  # noqa: E712
        .order_by(TradingPair.symbol)
    )
    return list(result.scalars().all())


async def _pair_symbols(db: AsyncSession) -> list[str]:
    result = await db.execute(
        select(TradingPair.symbol).where(TradingPair.is_active == True)  # noqa: E712
    )
    return list(result.scalars().all())


def get_ticker(pair_symbol: str, base: Decimal, quote: Decimal) -> dict:
    """Deterministic simulated ticker — fallback when Binance is unreachable."""
    price = engine.price(pair_symbol)
    open_price = _price_at(pair_symbol, datetime.now(UTC) - timedelta(hours=24))
    change = (price - open_price) / open_price if open_price else Decimal("0")
    high = max(price, open_price) * (Decimal("1") + Decimal("0.01"))
    low = min(price, open_price) * (Decimal("1") - Decimal("0.01"))
    volume_quote = _hash_seed(pair_symbol + ":vol") % 4000 + 500

    return {
        "pair": pair_symbol,
        "base_asset": base,
        "quote_asset": quote,
        "last": float(price),
        "open_24h": float(open_price),
        "high_24h": float(high),
        "low_24h": float(low),
        "change_24h": float(change),
        "volume_24h": float(Decimal(volume_quote)),
    }


def get_stats_24h(pair_symbol: str, base: str, quote: str) -> dict:
    """Deterministic simulated 24h stats — fallback when Binance is unreachable."""
    now = datetime.now(UTC)
    open_price = _price_at(pair_symbol, now - timedelta(hours=24))
    close_price = engine.price(pair_symbol)
    change = (close_price - open_price) / open_price if open_price else Decimal("0")
    high = max(close_price, open_price) * (Decimal("1") + Decimal("0.012"))
    low = min(close_price, open_price) * (Decimal("1") - Decimal("0.012"))
    volume_quote = Decimal(_hash_seed(pair_symbol + ":vol") % 4000 + 500)
    avg_price = (high + low) / Decimal("2")
    volume_base = volume_quote / avg_price if avg_price else Decimal("0")
    trades = _hash_seed(pair_symbol + ":trades") % 900 + 120

    return {
        "pair": pair_symbol,
        "base_asset": base,
        "quote_asset": quote,
        "last": float(close_price),
        "open_24h": float(open_price),
        "high_24h": float(high),
        "low_24h": float(low),
        "close_24h": float(close_price),
        "change_24h": float(change),
        "volume_24h": float(volume_quote),
        "volume_base_24h": float(volume_base),
        "trades_24h": int(trades),
    }


async def _build_ticker(pair_symbol: str, base: str, quote: str) -> dict:
    binance_sym = binance_client.binance_symbol(pair_symbol)
    if binance_sym:
        data = await _binance_24hr_cached(binance_sym)
        if data is not None:
            try:
                return {
                    "pair": pair_symbol,
                    "base_asset": base,
                    "quote_asset": quote,
                    "last": float(data["lastPrice"]),
                    "open_24h": float(data["openPrice"]),
                    "high_24h": float(data["highPrice"]),
                    "low_24h": float(data["lowPrice"]),
                    "change_24h": float(data["priceChangePercent"]) / 100,
                    "volume_24h": float(data["quoteVolume"]),
                }
            except (KeyError, ValueError, TypeError) as e:
                logger.warning("Binance 24hr parse failed for %s: %s", pair_symbol, e)
    return get_ticker(pair_symbol, base, quote)


async def _build_stats_24h(pair_symbol: str, base: str, quote: str) -> dict:
    binance_sym = binance_client.binance_symbol(pair_symbol)
    if binance_sym:
        data = await _binance_24hr_cached(binance_sym)
        if data is not None:
            try:
                return {
                    "pair": pair_symbol,
                    "base_asset": base,
                    "quote_asset": quote,
                    "last": float(data["lastPrice"]),
                    "open_24h": float(data["openPrice"]),
                    "high_24h": float(data["highPrice"]),
                    "low_24h": float(data["lowPrice"]),
                    "close_24h": float(data["lastPrice"]),
                    "change_24h": float(data["priceChangePercent"]) / 100,
                    "volume_24h": float(data["quoteVolume"]),
                    "volume_base_24h": float(data["volume"]),
                    "trades_24h": int(data["count"]),
                }
            except (KeyError, ValueError, TypeError) as e:
                logger.warning("Binance 24hr parse failed for %s: %s", pair_symbol, e)
    return get_stats_24h(pair_symbol, base, quote)


async def get_stats_24h_cached(pair_symbol: str, base: str, quote: str) -> dict:
    cached = await cache_get(f"market:stats24:{pair_symbol}")
    if cached is not None:
        return cached
    stats = await _build_stats_24h(pair_symbol, base, quote)
    await cache_set(f"market:stats24:{pair_symbol}", stats, TICKERS_CACHE_TTL)
    return stats


async def get_ticker_cached(pair_symbol: str, base: str, quote: str) -> dict:
    """Ticker with Redis cache (graceful fallback when Redis is down)."""
    cached = await cache_get(f"market:ticker:{pair_symbol}")
    if cached is not None:
        return cached
    ticker = await _build_ticker(pair_symbol, base, quote)
    await cache_set(f"market:ticker:{pair_symbol}", ticker, TICKERS_CACHE_TTL)
    return ticker


async def get_all_tickers(db: AsyncSession) -> list[dict]:
    cached = await cache_get("market:tickers")
    if cached is not None:
        return cached

    symbols = await _pair_symbols(db)
    result = []
    for s in symbols:
        base, quote = s.split("/")
        pair = await db.execute(select(TradingPair).where(TradingPair.symbol == s))
        pair_obj = pair.scalar_one_or_none()
        if pair_obj is not None:
            result.append(await _build_ticker(s, base, quote))

    await cache_set("market:tickers", result, TICKERS_CACHE_TTL)
    return result


def _simulated_ohlc(pair_symbol: str, interval_minutes: int, limit: int) -> list[dict]:
    now = datetime.now(UTC)
    candles = []
    for i in range(limit - 1, -1, -1):
        candle_ts = now - timedelta(minutes=interval_minutes * i)
        price = _price_at(pair_symbol, candle_ts)
        candles.append(
            {
                "time": candle_ts.replace(microsecond=0, second=0),
                "open": price,
                "high": price * Decimal("1.005"),
                "low": price * Decimal("0.995"),
                "close": price,
                "volume": Decimal(_hash_seed(pair_symbol + str(i)) % 900 + 100),
            }
        )
    return candles


async def get_ohlc(db: AsyncSession, pair_symbol: str, interval_minutes: int = 5, limit: int = 100) -> list[dict]:
    binance_sym = binance_client.binance_symbol(pair_symbol)
    if binance_sym:
        interval_str = binance_client.INTERVAL_MAP.get(interval_minutes)
        if interval_str:
            cache_key = f"market:binance:klines:{binance_sym}:{interval_str}:{limit}"
            raw = await cache_get(cache_key)
            if raw is None:
                raw = await binance_client.fetch_klines(binance_sym, interval_str, limit)
                if raw is not None:
                    await cache_set(cache_key, raw, BINANCE_KLINES_TTL)
            if raw:
                try:
                    return [
                        {
                            "time": datetime.fromtimestamp(k[0] / 1000, UTC).replace(microsecond=0),
                            "open": Decimal(str(k[1])),
                            "high": Decimal(str(k[2])),
                            "low": Decimal(str(k[3])),
                            "close": Decimal(str(k[4])),
                            "volume": Decimal(str(k[5])),
                        }
                        for k in raw
                    ]
                except (IndexError, ValueError, TypeError) as e:
                    logger.warning("Binance klines parse failed for %s: %s", pair_symbol, e)
    return _simulated_ohlc(pair_symbol, interval_minutes, limit)
