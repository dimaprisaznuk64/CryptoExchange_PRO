import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

BLACKLIST_PREFIX = "crypto:token:blacklist:"


async def blacklist_token(jti: str, ttl: int | None = None) -> None:
    from app.core.cache import get_redis
    redis = await get_redis()
    if not redis:
        logger.warning("Redis unavailable, token %s not blacklisted", jti)
        return
    if ttl is None:
        ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    try:
        await redis.set(f"{BLACKLIST_PREFIX}{jti}", "1", ex=ttl)
    except Exception as e:
        logger.warning("Redis blacklist set failed: %s", e)


def remaining_ttl(payload) -> int:
    """Seconds until a decoded token expires (>=0)."""
    exp = payload.get("exp")
    if not exp:
        return 0
    now = datetime.now(timezone.utc).timestamp()
    return max(0, int(exp - now))


async def is_token_blacklisted(jti: str) -> bool:
    from app.core.cache import get_redis
    redis = await get_redis()
    if not redis:
        return False
    try:
        return bool(await redis.exists(f"{BLACKLIST_PREFIX}{jti}"))
    except Exception as e:
        logger.warning("Redis blacklist check failed: %s", e)
        return False


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(user_id: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "exp": now + expires_delta,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "type": token_type,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(user_id: str) -> str:
    return _create_token(
        user_id,
        "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: str) -> str:
    return _create_token(
        user_id,
        "refresh",
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str, expected_type: Optional[str] = None):
    from jose import JWTError

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as e:
        logger.debug("Token decode failed: %s", e)
        return None
    if expected_type and payload.get("type") != expected_type:
        return None
    return payload
