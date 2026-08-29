from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.ratelimit import rate_limit_user
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.order import OrderSide, OrderStatus, OrderType
from app.models.trading_pair import TradingPair
from app.schemas.order import (
    PlaceOrderRequest,
    OrderResponse,
    CancelOrderResponse,
    TradeResponse,
)
from app.services import trading as trading_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post(
    "",
    response_model=OrderResponse,
    status_code=201,
    dependencies=[Depends(rate_limit_user("orders_place", limit=20, window=60))],
)
async def place_order(
    data: PlaceOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.side not in ("buy", "sell"):
        raise HTTPException(status_code=422, detail="side must be 'buy' or 'sell'")

    order = await trading_service.place_order(
        db,
        current_user.id,
        data.pair,
        OrderSide(data.side),
        OrderType(data.type),
        data.qty,
        price=data.price,
    )
    await db.commit()
    await db.refresh(order)
    pair = (
        await db.execute(select(TradingPair).where(TradingPair.id == order.pair_id))
    ).scalar_one_or_none()
    return _to_order_response(order, pair)


@router.get(
    "",
    response_model=list[OrderResponse],
    dependencies=[Depends(rate_limit_user("orders_list", limit=60, window=60))],
)
async def my_orders(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Literal["open", "filled", "cancelled"] | None = Query(None),
    pair: str | None = Query(None, description="filter by pair symbol, e.g. BTC/USDT"),
    side: Literal["buy", "sell"] | None = Query(None),
    type: Literal["market", "limit", "take_profit", "stop_loss"] | None = Query(None),
    from_time: datetime | None = Query(None, alias="from"),
    to: datetime | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    orders = await trading_service.list_orders(
        db,
        current_user.id,
        limit,
        offset,
        order_status=status,
        pair_symbol=pair,
        side=side,
        order_type=type,
        date_from=from_time,
        date_to=to,
    )
    pairs = {}
    for o in orders:
        if o.pair_id not in pairs:
            res = await db.execute(select(TradingPair).where(TradingPair.id == o.pair_id))
            pairs[o.pair_id] = res.scalar_one_or_none()
    return [_to_order_response(o, pairs.get(o.pair_id)) for o in orders]


@router.post(
    "/{order_id}/cancel",
    response_model=CancelOrderResponse,
    dependencies=[Depends(rate_limit_user("orders_cancel", limit=20, window=60))],
)
async def cancel_my_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await trading_service.cancel_order(db, current_user.id, order_id)
    await db.commit()
    return CancelOrderResponse(id=order.id, status=order.status.value)


@router.get(
    "/trades",
    response_model=list[TradeResponse],
    dependencies=[Depends(rate_limit_user("orders_trades", limit=60, window=60))],
)
async def my_trades(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    pair: str | None = Query(None, description="filter by pair symbol, e.g. BTC/USDT"),
    side: Literal["buy", "sell"] | None = Query(None),
    from_time: datetime | None = Query(None, alias="from"),
    to: datetime | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trades = await trading_service.list_trades(
        db,
        current_user.id,
        limit,
        offset,
        pair_symbol=pair,
        side=side,
        date_from=from_time,
        date_to=to,
    )
    return [
        TradeResponse(
            id=t.id,
            order_id=t.order_id,
            pair=pair_symbol,
            side=t.side,
            price=float(t.price),
            qty=float(t.qty),
            notional=float(t.notional),
            created_at=t.created_at,
        )
        for t, pair_symbol in trades
    ]


def _to_order_response(order, pair=None):
    pair_symbol = pair.symbol if pair is not None else "?"
    return OrderResponse(
        id=order.id,
        pair=pair_symbol or "?",
        side=order.side.value,
        type=order.type.value,
        price=float(order.price) if order.price is not None else None,
        qty=float(order.qty),
        filled_qty=float(order.filled_qty),
        avg_fill_price=float(order.avg_fill_price) if order.avg_fill_price is not None else None,
        status=order.status.value,
        created_at=order.created_at,
    )