import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification

logger = logging.getLogger(__name__)


async def create_notification(
    db: AsyncSession,
    user_id: str,
    kind: str,
    title: str,
    body: str = "",
) -> Notification:
    """Persist a new notification for the user."""
    n = Notification(user_id=user_id, kind=kind, title=title, body=body)
    db.add(n)
    await db.flush()
    return n


async def list_notifications(
    db: AsyncSession, user_id: str, limit: int = 50, offset: int = 0
) -> list[Notification]:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def mark_read(
    db: AsyncSession, user_id: str, notification_id: str
) -> Notification | None:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    n = result.scalar_one_or_none()
    if n is None:
        return None
    if not n.is_read:
        n.is_read = True
        await db.flush()
    return n


async def mark_all_read(db: AsyncSession, user_id: str) -> int:
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
    )
    unread = list(result.scalars().all())
    for n in unread:
        n.is_read = True
    if unread:
        await db.flush()
    return len(unread)


async def unread_count(db: AsyncSession, user_id: str) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
    )
    return int(result.scalar_one())
