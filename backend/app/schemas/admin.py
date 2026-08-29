from datetime import datetime

from pydantic import BaseModel

from app.models.user import UserRole
from app.models.wallet import WalletType


class AdminUserListItem(BaseModel):
    id: str
    email: str
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime
    total_usd: float
    order_count: int
    trade_count: int


class AdminUserList(BaseModel):
    total: int
    users: list[AdminUserListItem]


class AdminWallet(BaseModel):
    asset: str
    type: WalletType
    balance: float
    available: float
    frozen: float


class AdminUserDetail(BaseModel):
    id: str
    email: str
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
    total_usd: float
    order_count: int
    trade_count: int
    wallets: list[AdminWallet]


class AdminUserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None
