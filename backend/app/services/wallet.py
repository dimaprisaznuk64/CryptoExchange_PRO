import logging
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.wallet import Wallet, WalletType
from app.models.transaction import Transaction, TransactionType, TransactionStatus

logger = logging.getLogger(__name__)


def _to_dec(v) -> Decimal:
    return Decimal(str(v))


async def get_or_create_asset(db: AsyncSession, symbol: str) -> Asset:
    result = await db.execute(select(Asset).where(Asset.symbol == symbol))
    asset = result.scalar_one_or_none()
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{symbol}' not found",
        )
    return asset


async def get_or_create_wallet(
    db: AsyncSession, user_id: str, asset_id: str, wallet_type: WalletType = WalletType.spot
) -> Wallet:
    result = await db.execute(
        select(Wallet).where(
            Wallet.user_id == user_id,
            Wallet.asset_id == asset_id,
            Wallet.type == wallet_type,
        )
    )
    wallet = result.scalar_one_or_none()
    if wallet is None:
        wallet = Wallet(user_id=user_id, asset_id=asset_id, type=wallet_type)
        db.add(wallet)
        await db.flush()
        await db.refresh(wallet)
    return wallet


async def credit(
    db: AsyncSession,
    user_id: str,
    symbol: str,
    amount: float,
    tx_type: TransactionType = TransactionType.deposit,
    ref_id: Optional[str] = None,
    note: Optional[str] = None,
) -> Wallet:
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    asset = await get_or_create_asset(db, symbol)
    # Row lock to keep balance updates atomic and avoid lost updates.
    wallet = await get_or_create_wallet(db, user_id, asset.id)
    await _lock_wallet(db, wallet.id)

    delta = _to_dec(amount)
    wallet.balance = _to_dec(wallet.balance) + delta
    wallet.available = _to_dec(wallet.available) + delta
    await db.flush()

    db.add(
        Transaction(
            user_id=user_id,
            wallet_id=wallet.id,
            asset_id=asset.id,
            type=tx_type,
            status=TransactionStatus.completed,
            amount=delta,
            delta=delta,
            ref_id=ref_id,
            note=note,
        )
    )
    await db.flush()
    await db.refresh(wallet)
    return wallet


async def debit(
    db: AsyncSession,
    user_id: str,
    symbol: str,
    amount: float,
    tx_type: TransactionType = TransactionType.withdrawal,
    ref_id: Optional[str] = None,
    note: Optional[str] = None,
) -> Wallet:
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    asset = await get_or_create_asset(db, symbol)
    wallet = await get_or_create_wallet(db, user_id, asset.id)
    await _lock_wallet(db, wallet.id)

    delta = _to_dec(amount)
    if _to_dec(wallet.available) < delta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient available balance",
        )

    wallet.balance = _to_dec(wallet.balance) - delta
    wallet.available = _to_dec(wallet.available) - delta
    await db.flush()

    db.add(
        Transaction(
            user_id=user_id,
            wallet_id=wallet.id,
            asset_id=asset.id,
            type=tx_type,
            status=TransactionStatus.completed,
            amount=delta,
            delta=-delta,
            ref_id=ref_id,
            note=note,
        )
    )
    await db.flush()
    await db.refresh(wallet)
    return wallet


async def transfer(
    db: AsyncSession,
    user_id: str,
    symbol: str,
    from_type: WalletType,
    to_type: WalletType,
    amount: float,
    note: Optional[str] = None,
) -> Wallet:
    """Move funds from one wallet type to another for the same user.

    Atomically debits the source wallet's available balance and credits the
    target wallet, recording a `transfer` transaction on each side linked by a
    shared `ref_id`.
    """
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if from_type == to_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and target wallet types must differ",
        )
    if from_type not in (WalletType.spot, WalletType.funding) or to_type not in (
        WalletType.spot,
        WalletType.funding,
    ):
        raise HTTPException(status_code=400, detail="Invalid wallet type")

    asset = await get_or_create_asset(db, symbol)
    from_wallet = await get_or_create_wallet(db, user_id, asset.id, from_type)
    to_wallet = await get_or_create_wallet(db, user_id, asset.id, to_type)
    await _lock_wallet(db, from_wallet.id)
    await _lock_wallet(db, to_wallet.id)

    delta = _to_dec(amount)
    if _to_dec(from_wallet.available) < delta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient available balance",
        )

    from_wallet.balance = _to_dec(from_wallet.balance) - delta
    from_wallet.available = _to_dec(from_wallet.available) - delta
    to_wallet.balance = _to_dec(to_wallet.balance) + delta
    to_wallet.available = _to_dec(to_wallet.available) + delta
    await db.flush()

    transfer_ref = f"{from_wallet.id}:{to_wallet.id}"
    db.add(
        Transaction(
            user_id=user_id,
            wallet_id=from_wallet.id,
            asset_id=asset.id,
            type=TransactionType.transfer,
            status=TransactionStatus.completed,
            amount=delta,
            delta=-delta,
            ref_id=transfer_ref,
            note=note or f"Transfer to {to_type.value} wallet",
        )
    )
    db.add(
        Transaction(
            user_id=user_id,
            wallet_id=to_wallet.id,
            asset_id=asset.id,
            type=TransactionType.transfer,
            status=TransactionStatus.completed,
            amount=delta,
            delta=delta,
            ref_id=transfer_ref,
            note=note or f"Transfer from {from_type.value} wallet",
        )
    )
    await db.flush()
    await db.refresh(from_wallet)
    await db.refresh(to_wallet)
    return to_wallet


async def _lock_wallet(db: AsyncSession, wallet_id: str) -> None:
    stmt = select(Wallet.id).where(Wallet.id == wallet_id).with_for_update()
    await db.execute(stmt)


async def get_balances(db: AsyncSession, user_id: str) -> list[dict]:
    result = await db.execute(
        select(Wallet, Asset.symbol)
        .join(Asset, Asset.id == Wallet.asset_id)
        .where(Wallet.user_id == user_id)
        .order_by(Asset.symbol)
    )
    rows = result.all()
    return [
        {
            "asset_symbol": symbol,
            "wallet_type": w.type.value,
            "balance": _to_dec(w.balance),
            "available": _to_dec(w.available),
            "frozen": _to_dec(w.frozen),
        }
        for w, symbol in rows
    ]


async def get_transactions(
    db: AsyncSession,
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    tx_type: str | None = None,
    status: str | None = None,
    asset_symbol: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[Transaction]:
    stmt = (
        select(Transaction)
        .join(Asset, Transaction.asset_id == Asset.id)
        .where(Transaction.user_id == user_id)
    )
    if tx_type:
        stmt = stmt.where(Transaction.type == TransactionType(tx_type))
    if status:
        stmt = stmt.where(Transaction.status == TransactionStatus(status))
    if asset_symbol:
        stmt = stmt.where(Asset.symbol == asset_symbol)
    if date_from:
        stmt = stmt.where(Transaction.created_at >= date_from)
    if date_to:
        stmt = stmt.where(Transaction.created_at <= date_to)
    stmt = stmt.order_by(Transaction.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def purge_stale_transactions(
    db: AsyncSession, days: int = 7
) -> int:
    """Soft-cleanup: delete pending/failed simulated transactions older than `days`.
    Used by the daily Celery cleanup task; returns the number removed."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    result = await db.execute(
        delete(Transaction).where(
            Transaction.status.in_(
                [TransactionStatus.pending, TransactionStatus.failed]
            ),
            Transaction.created_at < cutoff,
        )
    )
    return result.rowcount or 0
