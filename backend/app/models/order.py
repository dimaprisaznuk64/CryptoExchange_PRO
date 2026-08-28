import uuid
import enum
from datetime import datetime, UTC

import sqlalchemy as sa
from sqlalchemy import String, Numeric, Enum, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OrderSide(str, enum.Enum):
    buy = "buy"
    sell = "sell"


class OrderType(str, enum.Enum):
    market = "market"
    limit = "limit"
    take_profit = "take_profit"
    stop_loss = "stop_loss"


class OrderStatus(str, enum.Enum):
    open = "open"
    filled = "filled"
    partially_filled = "partially_filled"
    cancelled = "cancelled"
    rejected = "rejected"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    pair_id: Mapped[str] = mapped_column(String(36), ForeignKey("trading_pairs.id"), index=True)
    side: Mapped[OrderSide] = mapped_column(Enum(OrderSide))
    type: Mapped[OrderType] = mapped_column(Enum(OrderType), default=OrderType.market)
    price: Mapped[float | None] = mapped_column(Numeric(30, 8), nullable=True)
    qty: Mapped[float] = mapped_column(Numeric(30, 8))
    filled_qty: Mapped[float] = mapped_column(Numeric(30, 8), default=0)
    avg_fill_price: Mapped[float | None] = mapped_column(Numeric(30, 8), nullable=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.open
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    pair = relationship("TradingPair")
