import asyncio
import logging
import sys
from datetime import timedelta

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.services import market as market_service
from app.services import trading as trading_service
from app.services import wallet as wallet_service

logger = logging.getLogger(__name__)


def _run(coro):
    """Run an async coroutine to completion from a synchronous Celery task."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    return asyncio.run(coro)


def _session_maker():
    """Per-run engine so asyncpg connections stay bound to the task's event loop
    (Celery tasks run in sync workers; Windows asyncio.run per task is fine if
    each run owns its engine)."""
    engine = create_async_engine(get_settings().DATABASE_URL)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    return engine, maker


@celery_app.task(name="app.tasks.refresh_market_stats")
def refresh_market_stats():
    """Warm the Redis market-data cache (beat: every 60s)."""
    async def _inner() -> dict:
        engine, maker = _session_maker()
        try:
            async with maker() as session:
                tickers = await market_service.get_all_tickers(session)
                return {"pairs": len(tickers)}
        finally:
            await engine.dispose()
    return _run(_inner())


@celery_app.task(name="app.tasks.cleanup_stale_transactions")
def cleanup_stale_transactions(days: int = 7):
    """Delete pending/failed simulated transactions older than `days` (beat: daily)."""
    async def _inner() -> dict:
        engine, maker = _session_maker()
        try:
            async with maker() as session:
                removed = await wallet_service.purge_stale_transactions(session, days)
                await session.commit()
                return {"removed": removed}
        finally:
            await engine.dispose()
    return _run(_inner())


@celery_app.task(name="app.tasks.run_conditional_orders")
def run_conditional_orders():
    """Execute due take_profit/stop_loss orders.
    NOTE: not in the beat schedule — TP/SL are already handled by the in-process
    monitor (avoid double execution). Use this task for on-demand / worker use."""
    async def _inner() -> dict:
        engine, maker = _session_maker()
        try:
            async with maker() as session:
                filled = await trading_service.check_conditional_orders(session)
                await session.commit()
                return {"executed": len(filled)}
        finally:
            await engine.dispose()
    return _run(_inner())