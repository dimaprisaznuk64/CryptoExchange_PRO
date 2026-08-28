from datetime import datetime
from pydantic import BaseModel, Field, model_validator


class PlaceOrderRequest(BaseModel):
    pair: str = Field(description="e.g. BTC/USDT")
    side: str = Field(description="buy | sell")
    qty: float = Field(gt=0)
    type: str = Field(default="market", description="market | limit | take_profit | stop_loss")
    price: float | None = Field(default=None, gt=0, description="required for non-market orders")

    @model_validator(mode="after")
    def _validate_price(self):
        valid = ("market", "limit", "take_profit", "stop_loss")
        if self.type not in valid:
            raise ValueError("type must be 'market', 'limit', 'take_profit' or 'stop_loss'")
        if self.type != "market" and self.price is None:
            raise ValueError("price is required for this order type")
        return self


class CancelOrderResponse(BaseModel):
    id: str
    status: str


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