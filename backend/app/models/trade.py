import uuid
import enum
from datetime import datetime, UTC

import sqlalchemy as sa
from sqlalchemy import String, Numeric, Enum, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("orders.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    pair_id: Mapped[str] = mapped_column(String(36), ForeignKey("trading_pairs.id"), index=True)
    side: Mapped[str] = mapped_column(String(4))  # buy / sell
    price: Mapped[float] = mapped_column(Numeric(30, 8))
    qty: Mapped[float] = mapped_column(Numeric(30, 8))
    notional: Mapped[float] = mapped_column(Numeric(38, 8))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
