from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.ratelimit import rate_limit
from app.models.trading_pair import TradingPair
from app.schemas.market import (
    PairResponse,
    TickerResponse,
    CandleResponse,
    MarketStatsResponse,
)
from app.services import market as market_service

router = APIRouter(prefix="/market", tags=["market"])


@router.get(
    "/pairs",
    response_model=list[PairResponse],
    dependencies=[Depends(rate_limit("market_pairs", limit=120, window=60))],
)
async def list_pairs(db: AsyncSession = Depends(get_db)):
    pairs = await market_service.list_pairs(db)
    return [
        PairResponse(
            id=p.id,
            symbol=p.symbol,
            base_asset=p.base_asset.symbol,
            quote_asset=p.quote_asset.symbol,
            price_precision=p.price_precision,
            qty_precision=p.qty_precision,
            status=p.status.value,
        )
        for p in pairs
    ]


async def _get_pair(db: AsyncSession, symbol: str) -> TradingPair:
    result = await db.execute(select(TradingPair).where(TradingPair.symbol == symbol))
    pair = result.scalar_one_or_none()
    if pair is None or not pair.is_active:
        raise HTTPException(status_code=404, detail=f"Pair '{symbol}' not found")
    return pair


@router.get(
    "/tickers",
    response_model=list[TickerResponse],
    dependencies=[Depends(rate_limit("market_tickers", limit=120, window=60))],
)
async def get_all_tickers(db: AsyncSession = Depends(get_db)):
    return await market_service.get_all_tickers(db)


@router.get(
    "/tickers/{symbol:path}",
    response_model=TickerResponse,
    dependencies=[Depends(rate_limit("market_ticker", limit=120, window=60))],
)
async def get_ticker(symbol: str, db: AsyncSession = Depends(get_db)):
    pair = await _get_pair(db, symbol)
    base, quote = symbol.split("/")
    return await market_service.get_ticker_cached(symbol, base, quote)


@router.get(
    "/stats/{symbol:path}",
    response_model=MarketStatsResponse,
    dependencies=[Depends(rate_limit("market_stats", limit=120, window=60))],
)
async def get_stats_24h(symbol: str, db: AsyncSession = Depends(get_db)):
    await _get_pair(db, symbol)
    base, quote = symbol.split("/")
    return await market_service.get_stats_24h_cached(symbol, base, quote)


@router.get(
    "/candles/{symbol:path}",
    response_model=list[CandleResponse],
    dependencies=[Depends(rate_limit("market_candles", limit=60, window=60))],
)
async def get_candles(
    symbol: str,
    interval: int = Query(5, ge=1, le=1440, description="minutes"),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    await _get_pair(db, symbol)
    candles = await market_service.get_ohlc(db, symbol, interval, limit)
    return [
        CandleResponse(**{**c, "time": c["time"]})
        for c in candles
    ]
