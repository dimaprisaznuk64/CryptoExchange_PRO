from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class PairResponse(BaseModel):
    id: str
    symbol: str
    base_asset: str
    quote_asset: str
    price_precision: int
    qty_precision: int
    status: str


class TickerResponse(BaseModel):
    pair: str
    base_asset: str
    quote_asset: str
    last: float
    open_24h: float
    high_24h: float
    low_24h: float
    change_24h: float
    volume_24h: float


class MarketStatsResponse(BaseModel):
    pair: str
    base_asset: str
    quote_asset: str
    last: float
    open_24h: float
    high_24h: float
    low_24h: float
    close_24h: float
    change_24h: float
    volume_24h: float
    volume_base_24h: float
    trades_24h: int


class CandleResponse(BaseModel):
    time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
