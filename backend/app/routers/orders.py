from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.order import OrderSide, OrderStatus
from app.models.trading_pair import TradingPair
from app.schemas.order import PlaceMarketOrderRequest, OrderResponse, TradeResponse
from app.services import trading as trading_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderResponse, status_code=201)
async def place_market_order(
    data: PlaceMarketOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.side not in ("buy", "sell"):
        raise HTTPException(status_code=422, detail="side must be 'buy' or 'sell'")

    order = await trading_service.place_market_order(
        db, current_user.id, data.pair, OrderSide(data.side), data.qty
    )
    await db.commit()
    await db.refresh(order)
    pair = (await db.execute(select(TradingPair).where(TradingPair.id == order.pair_id))).scalar_one_or_none()
    return _to_order_response(order, pair)


@router.get("", response_model=list[OrderResponse])
async def my_orders(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    orders = await trading_service.list_orders(db, current_user.id, limit, offset)
    pairs = {}
    for o in orders:
        if o.pair_id not in pairs:
            res = await db.execute(select(TradingPair).where(TradingPair.id == o.pair_id))
            pairs[o.pair_id] = res.scalar_one_or_none()
    return [_to_order_response(o, pairs.get(o.pair_id)) for o in orders]


@router.get("/trades", response_model=list[TradeResponse])
async def my_trades(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trades = await trading_service.list_trades(db, current_user.id, limit)
    return [
        TradeResponse(
            id=t.id,
            order_id=t.order_id,
            side=t.side,
            price=float(t.price),
            qty=float(t.qty),
            notional=float(t.notional),
            created_at=t.created_at,
        )
        for t in trades
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
