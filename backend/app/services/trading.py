import logging
from datetime import datetime, UTC
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.trading_pair import TradingPair
from app.models.wallet import Wallet
from app.models.order import Order, OrderSide, OrderType, OrderStatus
from app.models.trade import Trade
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.services import wallet as wallet_service
from app.services.market import _current_price, _live_price

logger = logging.getLogger(__name__)


def _to_dec(value) -> Decimal:
    return Decimal(str(value))


async def _lock_wallet(db: AsyncSession, wallet_id: str) -> None:
    await db.execute(select(Wallet.id).where(Wallet.id == wallet_id).with_for_update())


async def _get_pair(db: AsyncSession, pair_symbol: str) -> TradingPair:
    result = await db.execute(
        select(TradingPair)
        .options(
            selectinload(TradingPair.base_asset),
            selectinload(TradingPair.quote_asset),
        )
        .where(TradingPair.symbol == pair_symbol)
    )
    pair = result.scalar_one_or_none()
    if pair is None or not pair.is_active:
        raise HTTPException(status_code=404, detail=f"Pair '{pair_symbol}' not found")
    return pair


def _add_ledger(db: AsyncSession, user_id, wallet_id, asset_id, amount, delta, tx_type, tx_note):
    db.add(
        Transaction(
            user_id=user_id,
            wallet_id=wallet_id,
            asset_id=asset_id,
            type=tx_type,
            status=TransactionStatus.completed,
            amount=amount,
            delta=delta,
            note=tx_note,
        )
    )


async def _freeze_limit(db, user_id, pair, base: Asset, quote: Asset, side: OrderSide, qty: Decimal, limit_price: Decimal) -> None:
    if side == OrderSide.buy:
        notional = qty * limit_price
        quote_wallet = await wallet_service.get_or_create_wallet(db, user_id, quote.id)
        await _lock_wallet(db, quote_wallet.id)
        if _to_dec(quote_wallet.available) < notional:
            raise HTTPException(status_code=400, detail="Insufficient quote balance")
        quote_wallet.available = _to_dec(quote_wallet.available) - notional
        quote_wallet.frozen = _to_dec(quote_wallet.frozen) + notional
    else:
        base_wallet = await wallet_service.get_or_create_wallet(db, user_id, base.id)
        await _lock_wallet(db, base_wallet.id)
        if _to_dec(base_wallet.available) < qty:
            raise HTTPException(status_code=400, detail="Insufficient base balance")
        base_wallet.available = _to_dec(base_wallet.available) - qty
        base_wallet.frozen = _to_dec(base_wallet.frozen) + qty


async def _unfreeze_limit(db, user_id, pair, base: Asset, quote: Asset, side: OrderSide, qty: Decimal, limit_price: Decimal) -> None:
    if side == OrderSide.buy:
        notional = qty * limit_price
        quote_wallet = await wallet_service.get_or_create_wallet(db, user_id, quote.id)
        await _lock_wallet(db, quote_wallet.id)
        quote_wallet.frozen = _to_dec(quote_wallet.frozen) - notional
        quote_wallet.available = _to_dec(quote_wallet.available) + notional
    else:
        base_wallet = await wallet_service.get_or_create_wallet(db, user_id, base.id)
        await _lock_wallet(db, base_wallet.id)
        base_wallet.frozen = _to_dec(base_wallet.frozen) - qty
        base_wallet.available = _to_dec(base_wallet.available) + qty


def _fill_note(order: Order, pair: TradingPair) -> str:
    label = order.type.value.replace("_", " ")
    return f"{label} {order.side.value} {pair.symbol}"


async def _execute_limit_fill(db, order: Order, pair: TradingPair) -> None:
    base: Asset = pair.base_asset
    quote: Asset = pair.quote_asset
    qty = _to_dec(order.qty)
    fill_price = _to_dec(order.price)
    notional = qty * fill_price

    if order.side == OrderSide.buy:
        quote_wallet = await wallet_service.get_or_create_wallet(db, order.user_id, quote.id)
        await _lock_wallet(db, quote_wallet.id)
        base_wallet = await wallet_service.get_or_create_wallet(db, order.user_id, base.id)
        await _lock_wallet(db, base_wallet.id)
        quote_wallet.balance = _to_dec(quote_wallet.balance) - notional
        quote_wallet.frozen = _to_dec(quote_wallet.frozen) - notional
        base_wallet.balance = _to_dec(base_wallet.balance) + qty
        base_wallet.available = _to_dec(base_wallet.available) + qty
        _add_ledger(db, order.user_id, quote_wallet.id, quote.id, notional, -notional, TransactionType.trade_buy, _fill_note(order, pair))
        _add_ledger(db, order.user_id, base_wallet.id, base.id, qty, qty, TransactionType.trade_buy, _fill_note(order, pair))
    else:
        base_wallet = await wallet_service.get_or_create_wallet(db, order.user_id, base.id)
        await _lock_wallet(db, base_wallet.id)
        quote_wallet = await wallet_service.get_or_create_wallet(db, order.user_id, quote.id)
        await _lock_wallet(db, quote_wallet.id)
        base_wallet.balance = _to_dec(base_wallet.balance) - qty
        base_wallet.frozen = _to_dec(base_wallet.frozen) - qty
        quote_wallet.balance = _to_dec(quote_wallet.balance) + notional
        quote_wallet.available = _to_dec(quote_wallet.available) + notional
        _add_ledger(db, order.user_id, base_wallet.id, base.id, qty, -qty, TransactionType.trade_sell, _fill_note(order, pair))
        _add_ledger(db, order.user_id, quote_wallet.id, quote.id, notional, notional, TransactionType.trade_sell, _fill_note(order, pair))

    order.filled_qty = qty
    order.avg_fill_price = fill_price
    order.status = OrderStatus.filled
    db.add(
        Trade(
            order_id=order.id,
            user_id=order.user_id,
            pair_id=pair.id,
            side=order.side.value,
            price=fill_price,
            qty=qty,
            notional=notional,
        )
    )


async def _sweep_open_orders(db: AsyncSession, user_id: str) -> list[Order]:
    """Fill the user's open limit orders whose price is crossed by the current market price."""
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.pair).selectinload(TradingPair.base_asset),
            selectinload(Order.pair).selectinload(TradingPair.quote_asset),
        )
        .where(
            Order.user_id == user_id,
            Order.status == OrderStatus.open,
            Order.type == OrderType.limit,
        )
    )
    filled: list[Order] = []
    for order in result.scalars().all():
        pair = order.pair
        current = _current_price(pair.symbol)
        crossed = (
            (order.side == OrderSide.buy and current <= _to_dec(order.price))
            or (order.side == OrderSide.sell and current >= _to_dec(order.price))
        )
        if not crossed:
            continue
        await _execute_limit_fill(db, order, pair)
        filled.append(order)
    if filled:
        await db.flush()
    return filled


def _conditional_triggered(order: Order, live: Decimal) -> bool:
    """Take profit fires on a favourable move, stop loss on an adverse one."""
    trigger = _to_dec(order.price)
    if order.type == OrderType.take_profit:
        if order.side == OrderSide.sell:
            return live >= trigger
        return live <= trigger
    if order.type == OrderType.stop_loss:
        if order.side == OrderSide.sell:
            return live <= trigger
        return live >= trigger
    return False


async def check_conditional_orders(
    db: AsyncSession, user_id: str | None = None
) -> list[Order]:
    """Fill open take_profit/stop_loss orders triggered by the live price.

    Called after each user action and periodically by the background monitor.
    """
    now = datetime.now(UTC)
    query = (
        select(Order)
        .options(
            selectinload(Order.pair).selectinload(TradingPair.base_asset),
            selectinload(Order.pair).selectinload(TradingPair.quote_asset),
        )
        .where(
            Order.status == OrderStatus.open,
            Order.type.in_([OrderType.take_profit, OrderType.stop_loss]),
        )
    )
    if user_id is not None:
        query = query.where(Order.user_id == user_id)
    result = await db.execute(query)
    filled: list[Order] = []
    for order in result.scalars().all():
        pair = order.pair
        live = _live_price(pair.symbol, now)
        if not _conditional_triggered(order, live):
            continue
        await _execute_limit_fill(db, order, pair)
        filled.append(order)
    if filled:
        await db.flush()
    return filled


async def place_order(
    db: AsyncSession,
    user_id: str,
    pair_symbol: str,
    side: OrderSide,
    order_type: OrderType,
    qty: float,
    price: float | None = None,
) -> Order:
    if qty <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    pair = await _get_pair(db, pair_symbol)
    base: Asset = pair.base_asset
    quote: Asset = pair.quote_asset

    if order_type != OrderType.market:
        if price is None or Decimal(str(price)) <= 0:
            raise HTTPException(status_code=400, detail="Order price must be positive")
        limit_price = Decimal(str(price))

        order = Order(
            user_id=user_id,
            pair_id=pair.id,
            side=side,
            type=order_type,
            price=limit_price,
            qty=qty,
            status=OrderStatus.open,
        )
        db.add(order)
        try:
            await _freeze_limit(db, user_id, pair, base, quote, side, _to_dec(qty), limit_price)
            await db.flush()
            await _sweep_open_orders(db, user_id)
            await check_conditional_orders(db, user_id)
        except Exception:
            await db.rollback()
            raise
    else:
        try:
            order = await _place_market(db, user_id, pair, base, quote, side, qty)
            await _sweep_open_orders(db, user_id)
            await check_conditional_orders(db, user_id)
        except Exception:
            await db.rollback()
            raise

    await db.refresh(order)
    return order


async def _place_market(
    db: AsyncSession,
    user_id: str,
    pair: TradingPair,
    base: Asset,
    quote: Asset,
    side: OrderSide,
    qty: float,
) -> Order:
    price = _current_price(pair.symbol)
    qty_dec = _to_dec(qty)
    notional = qty_dec * price

    order = Order(
        user_id=user_id,
        pair_id=pair.id,
        side=side,
        type=OrderType.market,
        price=price,
        qty=qty,
    )
    db.add(order)

    if side == OrderSide.buy:
        quote_wallet = await wallet_service.get_or_create_wallet(db, user_id, quote.id)
        await _lock_wallet(db, quote_wallet.id)
        if _to_dec(quote_wallet.available) < notional:
            raise HTTPException(status_code=400, detail="Insufficient quote balance")
        quote_wallet.balance = _to_dec(quote_wallet.balance) - notional
        quote_wallet.available = _to_dec(quote_wallet.available) - notional

        base_wallet = await wallet_service.get_or_create_wallet(db, user_id, base.id)
        await _lock_wallet(db, base_wallet.id)
        base_wallet.balance = _to_dec(base_wallet.balance) + qty_dec
        base_wallet.available = _to_dec(base_wallet.available) + qty_dec
        _add_ledger(db, user_id, quote_wallet.id, quote.id, notional, -notional, TransactionType.trade_buy, f"Market buy {pair.symbol}")
        _add_ledger(db, user_id, base_wallet.id, base.id, qty_dec, qty_dec, TransactionType.trade_buy, f"Market buy {pair.symbol}")
    else:
        base_wallet = await wallet_service.get_or_create_wallet(db, user_id, base.id)
        await _lock_wallet(db, base_wallet.id)
        if _to_dec(base_wallet.available) < qty_dec:
            raise HTTPException(status_code=400, detail="Insufficient base balance")
        base_wallet.balance = _to_dec(base_wallet.balance) - qty_dec
        base_wallet.available = _to_dec(base_wallet.available) - qty_dec

        quote_wallet = await wallet_service.get_or_create_wallet(db, user_id, quote.id)
        await _lock_wallet(db, quote_wallet.id)
        quote_wallet.balance = _to_dec(quote_wallet.balance) + notional
        quote_wallet.available = _to_dec(quote_wallet.available) + notional
        _add_ledger(db, user_id, base_wallet.id, base.id, qty_dec, -qty_dec, TransactionType.trade_sell, f"Market sell {pair.symbol}")
        _add_ledger(db, user_id, quote_wallet.id, quote.id, notional, notional, TransactionType.trade_sell, f"Market sell {pair.symbol}")

    order.filled_qty = qty_dec
    order.avg_fill_price = price
    order.status = OrderStatus.filled
    db.add(
        Trade(
            order_id=order.id,
            user_id=user_id,
            pair_id=pair.id,
            side=side.value,
            price=price,
            qty=qty_dec,
            notional=notional,
        )
    )
    await db.flush()
    return order


async def cancel_order(db: AsyncSession, user_id: str, order_id: str) -> Order:
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.pair).selectinload(TradingPair.base_asset),
            selectinload(Order.pair).selectinload(TradingPair.quote_asset),
        )
        .where(Order.id == order_id, Order.user_id == user_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != OrderStatus.open:
        raise HTTPException(status_code=400, detail=f"Order is already {order.status.value}")

    pair = order.pair
    await _unfreeze_limit(
        db, user_id, pair, pair.base_asset, pair.quote_asset,
        order.side, _to_dec(order.qty), _to_dec(order.price),
    )
    order.status = OrderStatus.cancelled
    await db.flush()
    return order


async def list_orders(
    db: AsyncSession,
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    order_status: str | None = None,
    pair_symbol: str | None = None,
    side: str | None = None,
    order_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[Order]:
    query = (
        select(Order)
        .join(TradingPair, TradingPair.id == Order.pair_id)
        .where(Order.user_id == user_id)
    )
    if order_status:
        query = query.where(Order.status == OrderStatus(order_status))
    if pair_symbol:
        query = query.where(TradingPair.symbol == pair_symbol)
    if side:
        query = query.where(Order.side == OrderSide(side))
    if order_type:
        query = query.where(Order.type == OrderType(order_type))
    if date_from:
        query = query.where(Order.created_at >= date_from)
    if date_to:
        query = query.where(Order.created_at <= date_to)
    result = await db.execute(
        query.order_by(Order.created_at.desc()).offset(offset).limit(limit)
    )
    return list(result.scalars().all())


async def list_trades(
    db: AsyncSession,
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    pair_symbol: str | None = None,
    side: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[tuple[Trade, str]]:
    query = (
        select(Trade, TradingPair.symbol)
        .join(TradingPair, TradingPair.id == Trade.pair_id)
        .where(Trade.user_id == user_id)
    )
    if pair_symbol:
        query = query.where(TradingPair.symbol == pair_symbol)
    if side:
        query = query.where(Trade.side == side)
    if date_from:
        query = query.where(Trade.created_at >= date_from)
    if date_to:
        query = query.where(Trade.created_at <= date_to)
    result = await db.execute(
        query.order_by(Trade.created_at.desc()).offset(offset).limit(limit)
    )
    return list(result.all())