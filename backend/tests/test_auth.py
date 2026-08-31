import pytest
from sqlalchemy import insert

from app.models.asset import Asset
from app.models.user import User


async def _create_user(db_session, uid, email, username, role="user", is_active=True, password="secret123"):
    from app.core.security import hash_password
    await db_session.execute(insert(User).values(
        id=uid,
        email=email,
        username=username,
        hashed_password=hash_password(password),
        role=role,
        is_active=is_active,
    ))
    await db_session.commit()
    return uid


@pytest.mark.asyncio
async def test_register_returns_tokens(client):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "new@test.com", "username": "newuser", "password": "strongpass123",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_409(client):
    await client.post("/api/v1/auth/register", json={
        "email": "dup@test.com", "username": "dupuser", "password": "strongpass123",
    })
    resp = await client.post("/api/v1/auth/register", json={
        "email": "dup@test.com", "username": "other", "password": "strongpass123",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_credits_demo_usdt_bonus(client, db_session):
    await db_session.execute(insert(Asset).values(
        id="a-usdt", symbol="USDT", name="Tether", decimals=6, is_fiat=False,
    ))
    await db_session.commit()

    resp = await client.post("/api/v1/auth/register", json={
        "email": "bonus@test.com", "username": "bonususer", "password": "strongpass123",
    })
    assert resp.status_code == 201
    token = resp.json()["access_token"]

    balances = await client.get(
        "/api/v1/wallets/balances", headers={"Authorization": f"Bearer {token}"}
    )
    assert balances.status_code == 200
    usdt = next(i for i in balances.json()["items"] if i["asset_symbol"] == "USDT")
    assert float(usdt["balance"]) == 10000.0
    assert float(usdt["available"]) == 10000.0


@pytest.mark.asyncio
async def test_register_short_password_422(client):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "x@test.com", "username": "xuser", "password": "short",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client, db_session):
    await _create_user(db_session, "u-login", "login@test.com", "loginuser")
    resp = await client.post("/api/v1/auth/login", json={
        "email": "login@test.com", "password": "secret123",
    })
    assert resp.status_code == 200
    assert resp.json()["access_token"]


@pytest.mark.asyncio
async def test_login_wrong_password_401(client, db_session):
    await _create_user(db_session, "u-wrong", "wrong@test.com", "wronguser")
    resp = await client.post("/api/v1/auth/login", json={
        "email": "wrong@test.com", "password": "badpass",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_blocked_account_403(client, db_session):
    await _create_user(db_session, "u-blocked", "blocked@test.com", "blockeduser", is_active=False)
    resp = await client.post("/api/v1/auth/login", json={
        "email": "blocked@test.com", "password": "secret123",
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_me(client, db_session):
    from app.core.security import create_access_token
    await _create_user(db_session, "u-me", "me@test.com", "meuser")
    token = create_access_token("u-me")
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@test.com"


@pytest.mark.asyncio
async def test_me_without_token_401(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_blocked_user_403(client, db_session):
    from app.core.security import create_access_token
    await _create_user(db_session, "u-meb", "meb@test.com", "mebuser", is_active=False)
    token = create_access_token("u-meb")
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_me_blacklisted_token_401(client, db_session):
    from app.core.security import create_access_token, decode_token, blacklist_token
    await _create_user(db_session, "u-bl", "bl@test.com", "bluser")
    token = create_access_token("u-bl")
    payload = decode_token(token, "access")
    await blacklist_token(payload["jti"])
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_returns_new_access(client, db_session):
    from app.core.security import create_refresh_token
    await _create_user(db_session, "u-ref", "ref@test.com", "refuser")
    refresh = create_refresh_token("u-ref")
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    assert resp.json()["access_token"]
    assert resp.json()["refresh_token"]


@pytest.mark.asyncio
async def test_refresh_rotation_revokes_old_refresh(client, db_session):
    from app.core.security import create_refresh_token
    await _create_user(db_session, "u-rot", "rot@test.com", "rotuser")
    old_refresh = create_refresh_token("u-rot")

    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert first.status_code == 200
    new_refresh = first.json()["refresh_token"]
    assert new_refresh != old_refresh

    # The presented (old) refresh must now be revoked/blacklisted.
    reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse.status_code == 401

    # The rotated-in refresh keeps working.
    second = await client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert second.status_code == 200


@pytest.mark.asyncio
async def test_refresh_invalid_401(client):
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "not.a.token"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_blacklists_refresh(client, db_session):
    from app.core.security import create_refresh_token, decode_token
    await _create_user(db_session, "u-logout", "log@test.com", "logoutuser")
    refresh = create_refresh_token("u-logout")
    resp = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh})
    assert resp.status_code == 204
    payload = decode_token(refresh, "refresh")
    from app.core.security import is_token_blacklisted
    assert await is_token_blacklisted(payload["jti"]) is True


@pytest.mark.asyncio
async def test_logout_also_revokes_access_token(client, db_session):
    from app.core.security import (
        create_access_token,
        create_refresh_token,
        decode_token,
        is_token_blacklisted,
    )
    await _create_user(db_session, "u-logout2", "log2@test.com", "logoutuser2")
    access = create_access_token("u-logout2")
    refresh = create_refresh_token("u-logout2")

    resp = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh, "access_token": access},
    )
    assert resp.status_code == 204

    access_payload = decode_token(access, "access")
    assert await is_token_blacklisted(access_payload["jti"]) is True

    # The revoked access token must no longer authenticate.
    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"}
    )
    assert me.status_code == 401


@pytest.mark.asyncio
async def test_ws_ticket_single_use(client, db_session):
    from app.core.security import create_access_token
    from app.core import cache
    await _create_user(db_session, "u-wt", "wt@test.com", "wtuser")
    access = create_access_token("u-wt")

    resp = await client.post(
        "/api/v1/auth/ws-ticket",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 200
    ticket = resp.json()["access_token"]
    assert ticket

    # First consume returns the user_id.
    user_id = await cache.consume_ws_ticket(ticket)
    assert user_id == "u-wt"

    # The ticket is single-use: second consume must be None.
    reused = await cache.consume_ws_ticket(ticket)
    assert reused is None


@pytest.mark.asyncio
async def test_ws_ticket_unknown_rejected(client, db_session):
    from app.core.security import create_access_token
    from app.core import cache
    await _create_user(db_session, "u-wt2", "wt2@test.com", "wt2user")
    access = create_access_token("u-wt2")

    # An unknown/fake ticket must not resolve to a user.
    assert await cache.consume_ws_ticket("not-a-real-ticket") is None

    resp = await client.post(
        "/api/v1/auth/ws-ticket",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 200
