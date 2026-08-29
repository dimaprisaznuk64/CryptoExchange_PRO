import asyncio
import logging
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.cache import init_redis, close_redis
from app.core.database import async_session
from app.core.ratelimit import AccountLocked, RateLimitExceeded
from app.routers import health, auth, wallets, market, orders, portfolio, notifications, ws
from app.services import trading as trading_service

settings = get_settings()
setup_logging()
logger = logging.getLogger(__name__)

docs_enabled = settings.DEBUG


async def _conditional_monitor_loop() -> None:
    """Auto-execute take_profit/stop_loss orders when the live price crosses them."""
    while True:
        await asyncio.sleep(settings.CONDITIONAL_CHECK_INTERVAL_SECONDS)
        try:
            async with async_session() as session:
                await trading_service.check_conditional_orders(session)
                await session.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Conditional order monitor error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    async with async_session() as session:
        from app.core.seed import seed_catalog
        await seed_catalog(session)
    monitor_task = asyncio.create_task(_conditional_monitor_loop())
    yield
    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    description="Symmetric crypto exchange simulator API",
    version=settings.VERSION,
    debug=settings.DEBUG,
    docs_url="/docs" if docs_enabled else None,
    redoc_url="/redoc" if docs_enabled else None,
    openapi_url="/openapi.json" if docs_enabled else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.ALLOWED_HOSTS.strip() != "*":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts_list,
    )


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
    )
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data:; "
        "script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
    )
    return response


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": exc.detail},
        headers={"Retry-After": str(exc.headers["Retry-After"])} if exc.headers else None,
    )


@app.exception_handler(AccountLocked)
async def account_locked_handler(request: Request, exc: AccountLocked):
    return JSONResponse(
        status_code=423,
        content={"detail": exc.detail},
        headers={"Retry-After": str(exc.headers["Retry-After"])} if exc.headers else None,
    )

app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(wallets.router, prefix=settings.API_V1_PREFIX)
app.include_router(market.router, prefix=settings.API_V1_PREFIX)
app.include_router(orders.router, prefix=settings.API_V1_PREFIX)
app.include_router(portfolio.router, prefix=settings.API_V1_PREFIX)
app.include_router(notifications.router, prefix=settings.API_V1_PREFIX)
app.include_router(ws.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
