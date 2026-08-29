import sys
import asyncio
import os
import fnmatch

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Force tests to use the in-memory Redis mock (never a real connection),
# so cross-event-loop issues can't leak in from a live Redis.
os.environ["REDIS_URL"] = "redis://localhost:1/0"

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.core.database import Base, get_db
from app.core.cache import init_redis, close_redis

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_crypto.db"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


class InMemoryRedisMock:
    def __init__(self):
        self._data = {}

    async def ping(self):
        return True

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self._data:
            return 0
        self._data[key] = str(value)
        return 1

    async def get(self, key):
        return self._data.get(key)

    async def exists(self, key):
        return 1 if key in self._data else 0

    async def delete(self, *keys):
        count = 0
        for k in keys:
            if k in self._data:
                del self._data[k]
                count += 1
        return count

    def _norm(self, key):
        raw = self._data.get(key)
        try:
            return int(raw)
        except (TypeError, ValueError):
            return 0

    async def incr(self, key):
        value = int(self._norm(key)) + 1
        self._data[key] = str(value)
        return value

    async def expire(self, key, seconds, nx=False):
        self._data[key] = str(self._norm(key))
        return 1

    async def ttl(self, key):
        return -1 if key not in self._data else 60

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self._data:
            return 0
        self._data[key] = str(value)
        return 1

    def pipeline(self, transaction=True):
        import asyncio
        from types import SimpleNamespace
        pipe = SimpleNamespace(_pending=[], _parent=self)

        def incr(key):
            pipe._pending.append(("incr", (key,)))
            return pipe

        def expire(key, seconds, nx=False):
            pipe._pending.append(("expire", (key, seconds, nx)))
            return pipe

        async def execute():
            results = []
            for cmd, args in pipe._pending:
                if cmd == "incr":
                    results.append(await pipe._parent.incr(*args))
                elif cmd == "expire":
                    results.append(await pipe._parent.expire(*args))
            pipe._pending = []
            return results

        pipe.incr = incr
        pipe.expire = expire
        pipe.execute = execute
        return pipe

    async def scan_iter(self, match="*"):
        for k in list(self._data.keys()):
            if fnmatch.fnmatch(k, match):
                yield k

    async def flushdb(self):
        self._data.clear()
        return True

    async def aclose(self):
        self._data.clear()


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    import app.models  # noqa: F401
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await init_redis()
    import app.core.cache as cache_module
    if cache_module.redis_client is None:
        cache_module.redis_client = InMemoryRedisMock()
    if cache_module.redis_client:
        await cache_module.redis_client.flushdb()
    yield
    await close_redis()
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()
    if os.path.exists("./test_crypto.db"):
        os.remove("./test_crypto.db")


@pytest.fixture
async def db_session():
    async with TestSession() as session:
        yield session
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    import app.core.cache as cache_module
    if cache_module.redis_client:
        await cache_module.redis_client.flushdb()


@pytest.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
