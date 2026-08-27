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
