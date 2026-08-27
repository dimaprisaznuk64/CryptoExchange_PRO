import logging
import math
import hashlib
from datetime import datetime, timedelta, UTC
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trading_pair import TradingPair
from app.models.asset import Asset

logger = logging.getLogger(__name__)

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
    price = _current_price(pair_symbol)
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


async def get_all_tickers(db: AsyncSession) -> list[dict]:
    symbols = await _pair_symbols(db)
    result = []
    for s in symbols:
        base, quote = s.split("/")
        pair = await db.execute(select(TradingPair).where(TradingPair.symbol == s))
        pair_obj = pair.scalar_one_or_none()
        result.append(get_ticker(s, base, quote))
    return result


async def get_ohlc(db: AsyncSession, pair_symbol: str, interval_minutes: int = 5, limit: int = 100) -> list[dict]:
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
