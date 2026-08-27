import uuid
from datetime import datetime, UTC

import sqlalchemy as sa
from sqlalchemy import String, Boolean, Numeric, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    decimals: Mapped[int] = mapped_column(sa.Integer, default=8)
    is_fiat: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=sa.text("false")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=sa.text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
