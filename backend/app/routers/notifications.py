from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.ratelimit import rate_limit_user
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import NotificationRead, UnreadCount
from app.services import notifications as notifications_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _out(n: Notification) -> NotificationRead:
    return NotificationRead(
        id=n.id,
        kind=n.kind,
        title=n.title,
        body=n.body,
        is_read=n.is_read,
        created_at=n.created_at,
    )


@router.get(
    "",
    response_model=list[NotificationRead],
    dependencies=[Depends(rate_limit_user("notifications_list", limit=60, window=60))],
)
async def get_notifications(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items = await notifications_service.list_notifications(
        db, current_user.id, limit=limit, offset=offset
    )
    return [_out(n) for n in items]


@router.get(
    "/unread-count",
    response_model=UnreadCount,
    dependencies=[Depends(rate_limit_user("notifications_unread", limit=60, window=60))],
)
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await notifications_service.unread_count(db, current_user.id)
    return UnreadCount(count=count)


@router.post(
    "/read-all",
    response_model=UnreadCount,
    dependencies=[Depends(rate_limit_user("notifications_read_all", limit=60, window=60))],
)
async def read_all(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await notifications_service.mark_all_read(db, current_user.id)
    return UnreadCount(count=count)


@router.post(
    "/{notification_id}/read",
    response_model=NotificationRead,
    dependencies=[Depends(rate_limit_user("notifications_read", limit=120, window=60))],
)
async def read_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    n = await notifications_service.mark_read(db, current_user.id, notification_id)
    if n is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return _out(n)
