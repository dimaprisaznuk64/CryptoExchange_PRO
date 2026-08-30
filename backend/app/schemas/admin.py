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


class AdminOrderItem(BaseModel):
    id: str
    user_email: str
    user_username: str
    pair: str
    side: str
    type: str
    price: float | None
    qty: float
    filled_qty: float
    avg_fill_price: float | None
    status: str
    created_at: datetime


class AdminOrderList(BaseModel):
    total: int
    orders: list[AdminOrderItem]


class AdminTradeItem(BaseModel):
    id: str
    order_id: str
    user_email: str
    user_username: str
    pair: str
    side: str
    price: float
    qty: float
    notional: float
    created_at: datetime


class AdminTradeList(BaseModel):
    total: int
    trades: list[AdminTradeItem]


class AdminDashboardTotals(BaseModel):
    users: int
    active_users: int
    orders: int
    open_orders: int
    trades: int
    total_spot_usd: float
    today_trades: int
    today_volume_usd: float


class AdminPairVolume(BaseModel):
    pair: str
    buy_notional: float
    sell_notional: float
    volume_notional: float
    trades: int


class AdminVolumeTimelinePoint(BaseModel):
    date: str
    volume_usd: float
    trades: int


class AdminStats(BaseModel):
    days: int
    totals: AdminDashboardTotals
    volume_by_pair: list[AdminPairVolume]
    volume_timeline: list[AdminVolumeTimelinePoint]
