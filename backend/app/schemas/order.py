from datetime import datetime
from pydantic import BaseModel, Field


class PlaceMarketOrderRequest(BaseModel):
    pair: str = Field(description="e.g. BTC/USDT")
    side: str = Field(description="buy | sell")
    qty: float = Field(gt=0)


class OrderResponse(BaseModel):
    id: str
    pair: str
    side: str
    type: str
    price: float | None
    qty: float
    filled_qty: float
    avg_fill_price: float | None
    status: str
    created_at: datetime


class TradeResponse(BaseModel):
    id: str
    order_id: str
    side: str
    price: float
    qty: float
    notional: float
    created_at: datetime
