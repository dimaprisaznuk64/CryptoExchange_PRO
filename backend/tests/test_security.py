import pytest

from app.core import cache
from tests.test_auth import _create_user


@pytest.mark.asyncio
async def test_security_headers_present(client):
    resp = await client.get("/api/v1/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "no-referrer"
    assert resp.headers["Permissions-Policy"] is not None
    assert "default-src 'self'" in resp.headers["Content-Security-Policy"]


@pytest.mark.asyncio
async def test_register_rate_limit_returns_429(client):
    limit = 20
    for i in range(limit):
        resp = await client.post("/api/v1/auth/register", json={
            "email": f"rl{i}@test.com", "username": f"rluser{i}", "password": "strongpass123",
        })
        assert resp.status_code == 201
    resp = await client.post("/api/v1/auth/register", json={
        "email": "rloverflow@test.com", "username": "rlover", "password": "strongpass123",
    })
    assert resp.status_code == 429
    assert resp.json()["detail"]
    assert "Retry-After" in resp.headers


@pytest.mark.asyncio
async def test_login_rate_limit_returns_429(client, db_session):
    await _create_user(db_session, "u-rl-login", "rllogin@test.com", "rlloginuser")
    limit = 20
    for i in range(limit):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "rllogin@test.com", "password": "secret123",
        })
        assert resp.status_code == 200
    resp = await client.post("/api/v1/auth/login", json={
        "email": "rllogin@test.com", "password": "secret123",
    })
    assert resp.status_code == 429


@pytest.mark.asyncio
async def test_failed_login_counter_reaches_threshold(client, db_session, monkeypatch):
    import app.routers.auth as auth_module

    events = []
    monkeypatch.setattr(auth_module, "audit_log", lambda event, **kw: events.append((event, kw)))

    await _create_user(db_session, "u-fail", "fail@test.com", "failuser")

    captured = []
    for i in range(5):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "fail@test.com", "password": "wrongpass",
        })
        assert resp.status_code == 401

    counter = await cache.redis_client.get("auth:failed:127.0.0.1")
    assert int(counter) >= 5

    suspicious = [e for e in events if e[0] == "suspicious_login_activity"]
    assert suspicious, "expected a suspicious_login_activity audit event after 5 failed logins"


@pytest.mark.asyncio
async def test_account_lockout_after_failed_logins(client, db_session):
    await _create_user(db_session, "u-lock", "lock@test.com", "lockuser")

    from app.core.ratelimit import FAILED_LOGIN_THRESHOLD

    for _ in range(FAILED_LOGIN_THRESHOLD):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "lock@test.com", "password": "wrongpass",
        })
        assert resp.status_code == 401

    assert int(await cache.redis_client.get("auth:lock:lock@test.com")) == 1

    resp = await client.post("/api/v1/auth/login", json={
        "email": "lock@test.com", "password": "secret123",
    })
    assert resp.status_code == 423
    assert resp.json()["detail"]
    assert "Retry-After" in resp.headers


@pytest.mark.asyncio
async def test_successful_login_resets_lockout(client, db_session):
    await _create_user(db_session, "u-reset", "reset@test.com", "resetuser")

    from app.core.ratelimit import FAILED_LOGIN_THRESHOLD

    for _ in range(FAILED_LOGIN_THRESHOLD - 1):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "reset@test.com", "password": "wrongpass",
        })
        assert resp.status_code == 401

    resp = await client.post("/api/v1/auth/login", json={
        "email": "reset@test.com", "password": "secret123",
    })
    assert resp.status_code == 200

    fail_key = await cache.redis_client.get("auth:failed:reset@test.com")
    assert fail_key is None or int(fail_key) == 0

    resp = await client.post("/api/v1/auth/login", json={
        "email": "reset@test.com", "password": "secret123",
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_per_user_rate_limit_on_place_order(client, db_session):
    from app.core.security import create_access_token

    await _create_user(db_session, "u-rl-order", "rlorder@test.com", "rlorderuser")
    token = create_access_token("u-rl-order")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"pair": "BTC/USDT", "side": "buy", "type": "market", "qty": 0.001}

    limit = 20
    for _ in range(limit):
        await client.post("/api/v1/orders", json=payload, headers=headers)

    resp = await client.post("/api/v1/orders", json=payload, headers=headers)
    assert resp.status_code == 429


@pytest.mark.asyncio
async def test_per_ip_rate_limit_on_market_read(client, db_session):
    from app.core.seed import seed_catalog

    await seed_catalog(db_session)

    limit = 60
    for _ in range(limit):
        resp = await client.get("/api/v1/market/candles/BTC/USDT?interval=5&limit=10")
        assert resp.status_code == 200
    resp = await client.get("/api/v1/market/candles/BTC/USDT?interval=5&limit=10")
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


@pytest.mark.asyncio
async def test_per_user_rate_limit_on_portfolio_read(client, db_session):
    from app.core.security import create_access_token

    await _create_user(db_session, "u-rl-port", "rlport@test.com", "rlportuser")
    token = create_access_token("u-rl-port")
    headers = {"Authorization": f"Bearer {token}"}

    limit = 60
    for _ in range(limit):
        resp = await client.get("/api/v1/portfolio", headers=headers)
        assert resp.status_code == 200
    resp = await client.get("/api/v1/portfolio", headers=headers)
    assert resp.status_code == 429
