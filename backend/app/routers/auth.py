from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import cache
from app.core.audit import log as audit_log
from app.core.database import get_db
from app.core.ratelimit import (
    rate_limit,
    is_account_locked,
    record_failed_login,
    reset_failed_logins,
    AccountLocked,
)
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    blacklist_token,
    is_token_blacklisted,
)
from app.dependencies.auth import get_current_user
from app.models.user import User, UserRole
from app.schemas.auth import RegisterRequest, LoginRequest, RefreshRequest, TokenResponse, AccessTokenResponse
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])

AUTH_RATE_LIMIT = 20
AUTH_RATE_WINDOW = 60
FAILED_LOGIN_THRESHOLD = 5


def _ip_of(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=201,
    dependencies=[Depends(rate_limit("auth_register", AUTH_RATE_LIMIT, AUTH_RATE_WINDOW))],
)
async def register(data: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(
        select(User).where((User.email == data.email) | (User.username == data.username))
    )
    if exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already registered",
        )

    user = User(
        email=data.email,
        username=data.username,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    audit_log("auth.register", user_id=user.id, email=user.email, ip=_ip_of(request))

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth_login", AUTH_RATE_LIMIT, AUTH_RATE_WINDOW))],
)
async def login(
    data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    ip = _ip_of(request)

    remaining = await is_account_locked(data.email)
    if remaining > 0:
        audit_log("auth.login_locked", email=data.email, ip=ip, retry_after=remaining)
        raise AccountLocked(retry_after=remaining)

    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        audit_log("auth.login_failed", email=data.email, ip=ip)
        if cache.redis_client is not None:
            try:
                fail_key = f"auth:failed:{ip}"
                counter = await cache.redis_client.incr(fail_key)
                if counter == 1:
                    await cache.redis_client.expire(fail_key, 300)
                if counter >= FAILED_LOGIN_THRESHOLD:
                    audit_log(
                        "suspicious_login_activity",
                        ip=ip,
                        email=data.email,
                        failures=int(counter),
                    )
            except Exception:
                pass
        await record_failed_login(data.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is blocked",
        )

    await reset_failed_logins(user.email)
    audit_log("auth.login", user_id=user.id, email=user.email, ip=ip)

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(data.refresh_token, expected_type="refresh")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    if await is_token_blacklisted(payload.get("jti", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or blocked",
        )

    return AccessTokenResponse(access_token=create_access_token(user.id))


@router.post("/logout", status_code=204)
async def logout(data: RefreshRequest):
    payload = decode_token(data.refresh_token, expected_type="refresh")
    if payload is not None:
        await blacklist_token(payload.get("jti", ""))


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
