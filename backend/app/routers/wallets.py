from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.ratelimit import rate_limit_user
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.asset import Asset
from app.models.transaction import TransactionType, TransactionStatus
from app.schemas.wallet import (
    BalanceItem,
    BalanceResponse,
    DepositRequest,
    WithdrawRequest,
    TransactionResponse,
)
from app.services import wallet as wallet_service

router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.get(
    "/balances",
    response_model=BalanceResponse,
    dependencies=[Depends(rate_limit_user("wallets_balances", limit=60, window=60))],
)
async def get_balances(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items = await wallet_service.get_balances(db, current_user.id)
    return BalanceResponse(items=[BalanceItem(**i) for i in items])


@router.get(
    "/transactions",
    response_model=list[TransactionResponse],
    dependencies=[Depends(rate_limit_user("wallets_transactions", limit=60, window=60))],
)
async def get_transactions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    type: Literal["deposit", "withdrawal", "trade_buy", "trade_sell", "fee", "adjustment"] | None = Query(None),
    status: Literal["pending", "completed", "failed"] | None = Query(None),
    asset: str | None = Query(None, description="asset symbol filter, e.g. BTC"),
    from_time: datetime | None = Query(None, alias="from"),
    to: datetime | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    txs = await wallet_service.get_transactions(
        db,
        current_user.id,
        limit,
        offset,
        tx_type=type,
        status=status,
        asset_symbol=asset,
        date_from=from_time,
        date_to=to,
    )
    result = []
    symbols = {}
    for tx in txs:
        if tx.asset_id not in symbols:
            asset = await db.execute(select(Asset.symbol).where(Asset.id == tx.asset_id))
            symbols[tx.asset_id] = asset.scalar_one_or_none()
        result.append(
            TransactionResponse(
                id=tx.id,
                type=tx.type.value,
                status=tx.status.value,
                amount=float(tx.amount),
                delta=float(tx.delta),
                asset_symbol=symbols[tx.asset_id],
                note=tx.note,
                created_at=tx.created_at,
            )
        )
    return result


@router.post(
    "/deposit",
    response_model=BalanceResponse,
    dependencies=[Depends(rate_limit_user("wallets_deposit", limit=10, window=60))],
)
async def deposit(
    data: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await wallet_service.credit(
        db,
        current_user.id,
        data.asset_symbol,
        data.amount,
        tx_type=TransactionType.deposit,
        note="Deposit (simulated)",
    )
    await db.commit()
    items = await wallet_service.get_balances(db, current_user.id)
    return BalanceResponse(items=[BalanceItem(**i) for i in items])


@router.post(
    "/withdraw",
    response_model=BalanceResponse,
    dependencies=[Depends(rate_limit_user("wallets_withdraw", limit=10, window=60))],
)
async def withdraw(
    data: WithdrawRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await wallet_service.debit(
        db,
        current_user.id,
        data.asset_symbol,
        data.amount,
        tx_type=TransactionType.withdrawal,
        note="Withdrawal (simulated)",
    )
    await db.commit()
    items = await wallet_service.get_balances(db, current_user.id)
    return BalanceResponse(items=[BalanceItem(**i) for i in items])
