from datetime import datetime
from pydantic import BaseModel


class PortfolioItem(BaseModel):
    asset: str
    balance: float
    usd_price: float
    value_usd: float
    pnl_usd: float


class PortfolioResponse(BaseModel):
    total_usd: float
    items: list[PortfolioItem]


class RecentTrade(BaseModel):
    id: str
    pair: str
    side: str
    price: float
    qty: float
    notional: float
    created_at: datetime


class PortfolioHistoryPoint(BaseModel):
    time: datetime
    value: float


class VolumePairReport(BaseModel):
    pair: str
    buy_notional: float
    sell_notional: float
    volume_notional: float
    buy_qty: float
    sell_qty: float
    trades: int


class VolumeReport(BaseModel):
    days: int
    total_notional: float
    total_qty: float
    total_trades: int
    pairs: list[VolumePairReport]
