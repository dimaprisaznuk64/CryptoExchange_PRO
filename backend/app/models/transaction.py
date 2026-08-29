import uuid
import enum
from datetime import datetime, UTC

import sqlalchemy as sa
from sqlalchemy import String, Numeric, Enum, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TransactionType(str, enum.Enum):
    deposit = "deposit"
    withdrawal = "withdrawal"
    trade_buy = "trade_buy"
    trade_sell = "trade_sell"
    fee = "fee"
    adjustment = "adjustment"
    transfer = "transfer"


class TransactionStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    wallet_id: Mapped[str] = mapped_column(String(36), ForeignKey("wallets.id"), index=True)
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("assets.id"), index=True)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), index=True)
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus), default=TransactionStatus.completed
    )
    amount: Mapped[float] = mapped_column(Numeric(40, 12))
    # signed delta applied to wallet balance (can be negative for withdrawal/spend)
    delta: Mapped[float] = mapped_column(Numeric(40, 12))
    ref_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    asset: Mapped["Asset"] = relationship(lazy="joined")
