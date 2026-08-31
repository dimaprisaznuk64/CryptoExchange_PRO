import secrets
import warnings

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_asyncpg_tls(url: str) -> str:
    """Convert Postgres query params asyncpg can't take into ones it can.

    asyncpg uses `ssl=require` rather than `sslmode=require` (and errors on
    `sslmode`). If the URL carries `sslmode=require`, translate it so the
    connection can be established over TLS.
    """
    if "?sslmode=require" in url and "ssl=" not in url.split("?")[-1]:
        url = url.replace("?sslmode=require", "?ssl=require", 1)
        url = url.replace("&sslmode=require", "&ssl=require", 1)
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Core
    APP_NAME: str = "CryptoExchange_PRO"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/cryptoexchange"

    # Auth
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    CELERY_TASK_ALWAYS_EAGER: bool = False

    # Conditional orders (TP/SL) background monitor
    CONDITIONAL_CHECK_INTERVAL_SECONDS: int = 5

    # Demo signup bonus (USDT credited to a brand-new account)
    DEMO_SIGNUP_BONUS_USDT: float = 10000.0
    DEMO_SIGNUP_BONUS_ASSET: str = "USDT"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"
    ALLOWED_HOSTS: str = "*"

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if v in ("change-me-in-production", "your-secret-key-change-in-production", ""):
            warnings.warn(
                "SECRET_KEY is a default/insecure value. "
                "Set a strong random key in production!",
                UserWarning,
                stacklevel=2,
            )
        if len(v) < 16:
            raise ValueError("SECRET_KEY must be at least 16 characters")
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if "postgres:postgres" in v:
            warnings.warn(
                "DATABASE_URL contains default credentials. Change them for production!",
                UserWarning,
                stacklevel=2,
            )
        if v.startswith(("postgres://", "postgresql://")) and "+asyncpg" not in v.split("://")[0]:
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1) or v.replace(
                "postgres://", "postgresql+asyncpg://", 1
            )
        v = _normalize_asyncpg_tls(v)
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def allowed_hosts_list(self) -> list[str]:
        return [h.strip() for h in self.ALLOWED_HOSTS.split(",") if h.strip()]

    @property
    def is_production(self) -> bool:
        return not self.DEBUG


def generate_secret_key() -> str:
    """Generate a cryptographically strong random secret key."""
    return secrets.token_hex(32)


@lru_cache
def get_settings() -> Settings:
    return Settings()
