import uuid
import enum
from datetime import datetime, UTC

import sqlalchemy as sa
from sqlalchemy import String, Boolean, Numeric, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PairStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    delisted = "delisted"


class TradingPair(Base):
    __tablename__ = "trading_pairs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    base_asset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assets.id"), index=True
    )
    quote_asset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assets.id"), index=True
    )
    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    price_precision: Mapped[int] = mapped_column(sa.Integer, default=8)
    qty_precision: Mapped[int] = mapped_column(sa.Integer, default=8)
    min_qty: Mapped[float] = mapped_column(Numeric(30, 8), default=0)
    status: Mapped[PairStatus] = mapped_column(
        Enum(PairStatus), default=PairStatus.active
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=sa.text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    base_asset = relationship("Asset", foreign_keys=[base_asset_id])
    quote_asset = relationship("Asset", foreign_keys=[quote_asset_id])
