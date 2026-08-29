from datetime import datetime

from pydantic import BaseModel


class NotificationRead(BaseModel):
    id: str
    kind: str
    title: str
    body: str
    is_read: bool
    created_at: datetime


class UnreadCount(BaseModel):
    count: int
