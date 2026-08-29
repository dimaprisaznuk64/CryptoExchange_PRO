import logging
from collections import defaultdict
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.wallet import Wallet, WalletType
from app.models.order import Order
from app.models.trade import Trade
from app.services.portfolio import _quote_cache
from app.services.market import _current_price

logger = logging.getLogger(__name__)

USD_QUOTES = ("USD", "USDT")


def _wallets_total_usd(wallets: list[Wallet], prices: dict) -> Decimal:
    total = Decimal("0")
    for w in wallets:
        symbol = w.asset.symbol
        bal = Decimal(str(w.balance))
        if bal == 0:
            continue
        if symbol in USD_QUOTES:
            total += bal
            continue
        candidates = prices.get(symbol, [])
        if not candidates:
            continue
        candidates.sort(key=lambda c: c[0])
        total += bal * _current_price(candidates[0][1])
    return total


async def list_users(
    db: AsyncSession, search: str | None = None, limit: int = 50, offset: int = 0
) -> dict:
    base = select(User)
    count_q = select(func.count()).select_from(User)
    if search:
        like = f"%{search}%"
        base = base.where(or_(User.email.ilike(like), User.username.ilike(like)))
        count_q = count_q.where(or_(User.email.ilike(like), User.username.ilike(like)))

    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(
        base.order_by(User.created_at.desc()).offset(offset).limit(limit)
    )
    users = list(result.scalars().all())
    user_ids = [u.id for u in users]

    if not user_ids:
        return {"total": int(total), "users": []}

    prices = await _quote_cache(db)

    wallets_res = await db.execute(
        select(Wallet)
        .options(selectinload(Wallet.asset))
        .where(Wallet.user_id.in_(user_ids), Wallet.type == WalletType.spot)
    )
    per_user_wallets: dict = defaultdict(list)
    for w in wallets_res.scalars().all():
        per_user_wallets[w.user_id].append(w)

    order_res = (
        await db.execute(
            select(Order.user_id, func.count())
            .where(Order.user_id.in_(user_ids))
            .group_by(Order.user_id)
        )
    ).all()
    trade_res = (
        await db.execute(
            select(Trade.user_id, func.count())
            .where(Trade.user_id.in_(user_ids))
            .group_by(Trade.user_id)
        )
    ).all()
    order_counts = dict(order_res)
    trade_counts = dict(trade_res)

    items = []
    for u in users:
        total_usd = _wallets_total_usd(per_user_wallets.get(u.id, []), prices)
        items.append(
            {
                "id": u.id,
                "email": u.email,
                "username": u.username,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at,
                "total_usd": float(total_usd),
                "order_count": order_counts.get(u.id, 0),
                "trade_count": trade_counts.get(u.id, 0),
            }
        )
    return {"total": int(total), "users": items}


async def get_user_detail(db: AsyncSession, user_id: str) -> dict | None:
    result = await db.execute(select(User).where(User.id == user_id))
    u = result.scalar_one_or_none()
    if u is None:
        return None

    prices = await _quote_cache(db)
    wallets_res = await db.execute(
        select(Wallet)
        .options(selectinload(Wallet.asset))
        .where(Wallet.user_id == user_id)
        .order_by(Wallet.type)
    )
    wallets = list(wallets_res.scalars().all())

    order_count = (
        await db.execute(
            select(func.count()).select_from(Order).where(Order.user_id == user_id)
        )
    ).scalar_one()
    trade_count = (
        await db.execute(
            select(func.count()).select_from(Trade).where(Trade.user_id == user_id)
        )
    ).scalar_one()
    total_usd = _wallets_total_usd(
        [w for w in wallets if w.type == WalletType.spot], prices
    )

    return {
        "id": u.id,
        "email": u.email,
        "username": u.username,
        "role": u.role,
        "is_active": u.is_active,
        "created_at": u.created_at,
        "updated_at": u.updated_at,
        "total_usd": float(total_usd),
        "order_count": int(order_count),
        "trade_count": int(trade_count),
        "wallets": [
            {
                "asset": w.asset.symbol,
                "type": w.type,
                "balance": float(w.balance),
                "available": float(w.available),
                "frozen": float(w.frozen),
            }
            for w in wallets
        ],
    }


async def update_user(
    db: AsyncSession,
    actor: User,
    target_id: str,
    role=None,
    is_active=None,
) -> User:
    result = await db.execute(select(User).where(User.id == target_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Self-protection: an admin cannot demote or block their own account.
    if target.id == actor.id and (role is not None or is_active is False):
        raise HTTPException(
            status_code=400,
            detail="You cannot change your own role or block your own account",
        )

    if role is not None:
        target.role = role
    if is_active is not None:
        target.is_active = is_active

    await db.flush()
    await db.refresh(target)
    return target
