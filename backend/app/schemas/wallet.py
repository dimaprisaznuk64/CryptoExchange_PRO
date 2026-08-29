from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class BalanceItem(BaseModel):
    asset_symbol: str
    wallet_type: str = "spot"
    balance: Decimal
    available: Decimal
    frozen: Decimal


class BalanceResponse(BaseModel):
    items: list[BalanceItem]


class DepositRequest(BaseModel):
    asset_symbol: str = Field(description="e.g. USD, USDT, BTC")
    amount: float = Field(gt=0, description="Positive amount to credit")


class WithdrawRequest(BaseModel):
    asset_symbol: str = Field(description="e.g. USD, USDT, BTC")
    amount: float = Field(gt=0, description="Positive amount to debit")


class TransferRequest(BaseModel):
    asset_symbol: str = Field(description="e.g. USD, USDT, BTC")
    amount: float = Field(gt=0, description="Positive amount to move")
    from_type: Literal["spot", "funding"] = Field(description="Source wallet type")
    to_type: Literal["spot", "funding"] = Field(description="Target wallet type")


class TransactionResponse(BaseModel):
    id: str
    type: str
    status: str
    amount: float
    delta: float
    asset_symbol: str | None = None
    note: str | None = None
    created_at: datetime
