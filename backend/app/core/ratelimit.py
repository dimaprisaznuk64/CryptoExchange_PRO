import logging
from typing import Awaitable, Callable

from fastapi import Depends, HTTPException, Request

from app.core import cache
from app.dependencies.auth import get_current_user

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 30
DEFAULT_WINDOW_SECONDS = 60

FAILED_LOGIN_THRESHOLD = 5
LOCKOUT_SECONDS = 15 * 60


class AccountLocked(HTTPException):
    def __init__(self, retry_after: int) -> None:
        super().__init__(
            status_code=423,
            detail="Account temporarily locked due to too many failed attempts.",
            headers={"Retry-After": str(retry_after)},
        )


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


def rate_limit_user(
    scope: str,
    limit: int = DEFAULT_LIMIT,
    window: int = DEFAULT_WINDOW_SECONDS,
):
    """Per-authenticated-user rate limit (keys on user.id, plus IP as a second counter)."""
    async def dependency(
        request: Request,
        current_user=Depends(get_current_user),
    ) -> None:
        ip = request.client.host if request.client else "unknown"
        user_ok = await is_allowed(f"{scope}:user", current_user.id, limit, window)
        ip_ok = await is_allowed(f"{scope}:ip", ip, limit, window)
        if not user_ok or not ip_ok:
            raise RateLimitExceeded()

    return dependency


def _lock_key(email: str) -> str:
    return f"auth:lock:{email}"


def _fail_key(email: str) -> str:
    return f"auth:failed:{email}"


async def is_account_locked(email: str) -> int:
    """Return remaining lockout seconds (0 if not locked)."""
    if cache.redis_client is None:
        return 0
    try:
        ttl = await cache.redis_client.ttl(_lock_key(email))
        return int(ttl) if ttl is not None and ttl > 0 else 0
    except Exception:  # pragma: no cover - defensive
        return 0


async def record_failed_login(email: str) -> int:
    """Increment per-account failure counter; lock the account on threshold.

    Returns the current failure count.
    """
    if cache.redis_client is None:
        return 0
    try:
        counter = await cache.redis_client.incr(_fail_key(email))
        if counter == 1:
            await cache.redis_client.expire(_fail_key(email), LOCKOUT_SECONDS)
        if counter >= FAILED_LOGIN_THRESHOLD:
            await cache.redis_client.set(_lock_key(email), "1", ex=LOCKOUT_SECONDS)
        return int(counter)
    except Exception:  # pragma: no cover - defensive
        return 0


async def reset_failed_logins(email: str) -> None:
    if cache.redis_client is None:
        return
    try:
        await cache.redis_client.delete(_fail_key(email), _lock_key(email))
    except Exception:  # pragma: no cover - defensive
        pass