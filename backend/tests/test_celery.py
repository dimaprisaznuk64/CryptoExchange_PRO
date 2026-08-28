import pytest
from datetime import datetime, timedelta, UTC
from sqlalchemy import insert, select

from app.models.user import User
from app.models.asset import Asset
from app.core.security import create_access_token, hash_password


async def _seed(client, db_session):
    await db_session.execute(insert(Asset).values(
        id="a-usd", symbol="USD", name="US Dollar", decimals=2, is_fiat=True,
    ))
    await db_session.execute(insert(User).values(
        id="celery-user", email="celery@test.com", username="celeryuser",
        hashed_password=hash_password("secret123"), role="user", is_active=True,
    ))
    await db_session.commit()
    return {"Authorization": f"Bearer {create_access_token('celery-user')}"}


@pytest.mark.asyncio
async def test_celery_config_and_beat(client, db_session):
    from app.core.celery_app import celery_app

    assert celery_app.main == "cryptoexchange"
    assert "redis" in celery_app.conf.broker_url
    assert "redis" in celery_app.conf.result_backend

    schedule = celery_app.conf.beat_schedule
    assert "refresh-market-stats" in schedule
    assert "cleanup-stale-transactions" in schedule
    # run_conditional_orders must NOT be auto-scheduled (in-process monitor owns it)
    assert "run-conditional-orders" not in schedule

    # tasks are discovered and registered
    from app import tasks  # noqa: F401
    for name in (
        "app.tasks.refresh_market_stats",
        "app.tasks.cleanup_stale_transactions",
        "app.tasks.run_conditional_orders",
    ):
        assert name in celery_app.tasks


@pytest.mark.asyncio
async def test_purge_stale_transactions_removes_only_old(client, db_session):
    headers = await _seed(client, db_session)
    # deposit creates a completed transaction (now)
    await client.post("/api/v1/wallets/deposit", json={
        "asset_symbol": "USD", "amount": 500,
    }, headers=headers)

    from app.models.transaction import TransactionType, TransactionStatus

    # backdate + mark the fresh transaction as failed/pending
    tx_id = (
        await db_session.execute(select(__import__("app.models.transaction", fromlist=["Transaction"]).Transaction.id).limit(1))
    ).scalar_one()
    from app.models.transaction import Transaction
    old = datetime.now(UTC) - timedelta(days=10)
    await db_session.execute(
        Transaction.__table__.update()
        .where(Transaction.id == tx_id)
        .values(status=TransactionStatus.failed, created_at=old)
    )
    await db_session.commit()

    from app.services.wallet import purge_stale_transactions
    removed = await purge_stale_transactions(db_session, days=1)
    assert removed == 1

    remaining = (
        await db_session.execute(select(Transaction))
    ).scalars().all()
    assert remaining == []