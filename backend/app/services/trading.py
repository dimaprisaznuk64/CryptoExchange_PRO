import logging
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.trading_pair import TradingPair
from app.models.wallet import Wallet, WalletType
from app.models.order import Order, OrderSide, OrderType, OrderStatus
from app.models.trade import Trade
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.services import wallet as wallet_service
from app.services.market import _current_price

logger = logging.getLogger(__name__)


async def _lock_wallet(db: AsyncSession, wallet_id: str) -> None:
    await db.execute(select(Wallet.id).where(Wallet.id == wallet_id).with_for_update())


async def place_market_order(
    db: AsyncSession,
    user_id: str,
    pair_symbol: str,
    side: OrderSide,
    qty: float,
) -> Order:
    if qty <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

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

    base: Asset = pair.base_asset
    quote: Asset = pair.quote_asset
    price = _current_price(pair_symbol)
    notional = Decimal(str(qty)) * price

    order = Order(
        user_id=user_id,
        pair_id=pair.id,
        side=side,
        type=OrderType.market,
        price=price,
        qty=qty,
    )
    db.add(order)

    try:
        if side == OrderSide.buy:
            # spend quote, receive base
            quote_wallet = await wallet_service.get_or_create_wallet(db, user_id, quote.id)
            await _lock_wallet(db, quote_wallet.id)
            if Decimal(str(quote_wallet.available)) < notional:
                raise HTTPException(status_code=400, detail="Insufficient quote balance")
            quote_wallet.balance = Decimal(str(quote_wallet.balance)) - notional
            quote_wallet.available = Decimal(str(quote_wallet.available)) - notional

            base_wallet = await wallet_service.get_or_create_wallet(db, user_id, base.id)
            await _lock_wallet(db, base_wallet.id)
            base_wallet.balance = Decimal(str(base_wallet.balance)) + Decimal(str(qty))
            base_wallet.available = Decimal(str(base_wallet.available)) + Decimal(str(qty))
            _add_ledger(db, user_id, quote_wallet.id, quote.id, notional, -notional, TransactionType.trade_buy, f"Market buy {pair_symbol}")
            _add_ledger(db, user_id, base_wallet.id, base.id, Decimal(qty), Decimal(qty), TransactionType.trade_buy, f"Market buy {pair_symbol}")
        else:
            # spend base, receive quote
            base_wallet = await wallet_service.get_or_create_wallet(db, user_id, base.id)
            await _lock_wallet(db, base_wallet.id)
            if Decimal(str(base_wallet.available)) < Decimal(str(qty)):
                raise HTTPException(status_code=400, detail="Insufficient base balance")
            base_wallet.balance = Decimal(str(base_wallet.balance)) - Decimal(str(qty))
            base_wallet.available = Decimal(str(base_wallet.available)) - Decimal(str(qty))

            quote_wallet = await wallet_service.get_or_create_wallet(db, user_id, quote.id)
            await _lock_wallet(db, quote_wallet.id)
            quote_wallet.balance = Decimal(str(quote_wallet.balance)) + notional
            quote_wallet.available = Decimal(str(quote_wallet.available)) + notional
            _add_ledger(db, user_id, base_wallet.id, base.id, Decimal(qty), -Decimal(qty), TransactionType.trade_sell, f"Market sell {pair_symbol}")
            _add_ledger(db, user_id, quote_wallet.id, quote.id, notional, notional, TransactionType.trade_sell, f"Market sell {pair_symbol}")

        order.filled_qty = Decimal(str(qty))
        order.avg_fill_price = price
        order.status = OrderStatus.filled
        db.add(
            Trade(
                order_id=order.id,
                user_id=user_id,
                pair_id=pair.id,
                side=side.value,
                price=price,
                qty=qty,
                notional=notional,
            )
        )
        await db.flush()
    except Exception:
        await db.rollback()
        raise

    await db.refresh(order)
    return order


def _add_ledger(db, user_id, wallet_id, asset_id, amount, delta, tx_type, tx_note):
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


async def list_orders(db: AsyncSession, user_id: str, limit: int = 50, offset: int = 0) -> list[Order]:
    result = await db.execute(
        select(Order)
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_trades(db: AsyncSession, user_id: str, limit: int = 50, offset: int = 0) -> list[Trade]:
    result = await db.execute(
        select(Trade)
        .where(Trade.user_id == user_id)
        .order_by(Trade.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())
