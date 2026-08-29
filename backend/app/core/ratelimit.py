import logging
from typing import Awaitable, Callable

from fastapi import HTTPException, Request

from app.core import cache

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 30
DEFAULT_WINDOW_SECONDS = 60


class RateLimitExceeded(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=429,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(DEFAULT_WINDOW_SECONDS)},
        )


async def is_allowed(scope: str, key: str, limit: int, window: int) -> bool:
    """Fixed-window rate check on top of the shared Redis client.

    If Redis is unavailable the check is skipped (fail-open) so the API keeps
    working during Redis outages.
    """
    if cache.redis_client is None:
        return True
    counter_key = f"rate:{scope}:{key}"
    try:
        pipe = cache.redis_client.pipeline()
        pipe.incr(counter_key)
        pipe.expire(counter_key, window, nx=True)
        count, _ = await pipe.execute()
        return int(count) <= limit
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("Rate limiter error (fail-open): %s", e)
        return True


def rate_limit(
    scope: str,
    limit: int = DEFAULT_LIMIT,
    window: int = DEFAULT_WINDOW_SECONDS,
) -> Callable[[Request], Awaitable[None]]:
    async def dependency(request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        if not await is_allowed(scope, ip, limit, window):
            raise RateLimitExceeded()

    return dependency