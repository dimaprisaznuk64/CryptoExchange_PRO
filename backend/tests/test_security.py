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
