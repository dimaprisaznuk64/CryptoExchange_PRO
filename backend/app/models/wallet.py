import uuid
import enum
from datetime import datetime, UTC

import sqlalchemy as sa
from sqlalchemy import String, Numeric, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class WalletType(str, enum.Enum):
    spot = "spot"
    funding = "funding"


class Wallet(Base):
    __tablename__ = "wallets"
    __table_args__ = (
        UniqueConstraint("user_id", "asset_id", "type", name="uq_wallet_user_asset_type"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("assets.id"), index=True)
    type: Mapped[WalletType] = mapped_column(
        Enum(WalletType), default=WalletType.spot
    )
    balance: Mapped[float] = mapped_column(Numeric(40, 12), default=0)
    available: Mapped[float] = mapped_column(Numeric(40, 12), default=0)
    frozen: Mapped[float] = mapped_column(Numeric(40, 12), default=0)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    asset = relationship("Asset")
