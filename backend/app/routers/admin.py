from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime
from typing import Literal
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.ratelimit import rate_limit_user
from app.dependencies.auth import get_current_user, require_admin
from app.models.user import User
from app.schemas.admin import (
    AdminOrderList,
    AdminTradeList,
    AdminUserDetail,
    AdminUserList,
    AdminUserUpdate,
)
from app.services import admin as admin_service

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get(
    "/users",
    response_model=AdminUserList,
    dependencies=[Depends(rate_limit_user("admin_users_list", limit=60, window=60))],
)
async def list_users(
    search: str | None = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    data = await admin_service.list_users(db, search=search, limit=limit, offset=offset)
    return AdminUserList(**data)


@router.get(
    "/users/{user_id}",
    response_model=AdminUserDetail,
    dependencies=[Depends(rate_limit_user("admin_users_detail", limit=120, window=60))],
)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    data = await admin_service.get_user_detail(db, user_id)
    if data is None:
        raise HTTPException(status_code=404, detail="User not found")
    return AdminUserDetail(**data)


@router.patch(
    "/users/{user_id}",
    response_model=AdminUserDetail,
    dependencies=[Depends(rate_limit_user("admin_users_update", limit=60, window=60))],
)
async def update_user(
    user_id: str,
    payload: AdminUserUpdate,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = await admin_service.update_user(
        db,
        actor=actor,
        target_id=user_id,
        role=payload.role,
        is_active=payload.is_active,
    )
    await db.commit()
    data = await admin_service.get_user_detail(db, target.id)
    return AdminUserDetail(**data)


@router.get(
    "/orders",
    response_model=AdminOrderList,
    dependencies=[Depends(rate_limit_user("admin_orders_list", limit=120, window=60))],
)
async def list_all_orders(
    user: str | None = Query(None, max_length=100, description="email or username"),
    pair: str | None = Query(None, description="pair symbol, e.g. BTC/USDT"),
    status: Literal["open", "filled", "partially_filled", "cancelled", "rejected"] | None = Query(None),
    side: Literal["buy", "sell"] | None = Query(None),
    type: Literal["market", "limit", "take_profit", "stop_loss"] | None = Query(None),
    from_time: datetime | None = Query(None, alias="from"),
    to: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    data = await admin_service.list_all_orders(
        db,
        user=user,
        pair_symbol=pair,
        status=status,
        side=side,
        order_type=type,
        date_from=from_time,
        date_to=to,
        limit=limit,
        offset=offset,
    )
    return AdminOrderList(**data)


@router.get(
    "/trades",
    response_model=AdminTradeList,
    dependencies=[Depends(rate_limit_user("admin_trades_list", limit=120, window=60))],
)
async def list_all_trades(
    user: str | None = Query(None, max_length=100, description="email or username"),
    pair: str | None = Query(None, description="pair symbol, e.g. BTC/USDT"),
    side: Literal["buy", "sell"] | None = Query(None),
    from_time: datetime | None = Query(None, alias="from"),
    to: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    data = await admin_service.list_all_trades(
        db,
        user=user,
        pair_symbol=pair,
        side=side,
        date_from=from_time,
        date_to=to,
        limit=limit,
        offset=offset,
    )
    return AdminTradeList(**data)
