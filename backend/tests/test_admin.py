import pytest
from sqlalchemy import insert

from app.models.user import User, UserRole
from app.models.asset import Asset
from app.models.trading_pair import TradingPair
from app.core.security import create_access_token, hash_password


async def _seed(client, db_session, admin_uid="adm-1", user_uid="usr-1"):
    await db_session.execute(insert(Asset).values(
        id="a-usdt", symbol="USDT", name="Tether", decimals=6, is_fiat=False,
    ))
    await db_session.execute(insert(Asset).values(
        id="a-btc", symbol="BTC", name="Bitcoin", decimals=8, is_fiat=False,
    ))
    await db_session.execute(insert(TradingPair).values(
        id="p-btcusdt", symbol="BTC/USDT",
        base_asset_id="a-btc", quote_asset_id="a-usdt", is_active=True,
        price_precision=2, qty_precision=6,
    ))
    await db_session.execute(insert(User).values(
        id=admin_uid, email=f"{admin_uid}@test.com", username=f"{admin_uid}name",
        hashed_password=hash_password("secret123"), role=UserRole.admin, is_active=True,
    ))
    await db_session.execute(insert(User).values(
        id=user_uid, email=f"{user_uid}@test.com", username=f"{user_uid}name",
        hashed_password=hash_password("secret123"), role=UserRole.user, is_active=True,
    ))
    await db_session.commit()
    return {
        "admin": {"Authorization": f"Bearer {create_access_token(admin_uid)}"},
        "user": {"Authorization": f"Bearer {create_access_token(user_uid)}"},
    }


@pytest.mark.asyncio
async def test_admin_route_requires_admin(client, db_session):
    headers = await _seed(client, db_session)
    # regular user -> 403
    resp = await client.get("/api/v1/admin/users", headers=headers["user"])
    assert resp.status_code == 403
    # no auth -> 401
    resp2 = await client.get("/api/v1/admin/users")
    assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_admin_list_users(client, db_session):
    headers = await _seed(client, db_session)
    resp = await client.get("/api/v1/admin/users", headers=headers["admin"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    usernames = {u["username"] for u in body["users"]}
    assert {"adm-1name", "usr-1name"} <= usernames
    admin_item = next(u for u in body["users"] if u["id"] == "adm-1")
    assert admin_item["role"] == "admin"
    assert admin_item["is_active"] is True


@pytest.mark.asyncio
async def test_admin_search_users(client, db_session):
    headers = await _seed(client, db_session)
    resp = await client.get("/api/v1/admin/users", params={"search": "usr"}, headers=headers["admin"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["users"][0]["id"] == "usr-1"


@pytest.mark.asyncio
async def test_admin_block_user(client, db_session):
    headers = await _seed(client, db_session)
    resp = await client.patch(
        "/api/v1/admin/users/usr-1",
        json={"is_active": False},
        headers=headers["admin"],
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # blocked user's protected calls now fail with 403
    blocked = await client.get("/api/v1/portfolio", headers=headers["user"])
    assert blocked.status_code == 403


@pytest.mark.asyncio
async def test_admin_change_role(client, db_session):
    headers = await _seed(client, db_session)
    resp = await client.patch(
        "/api/v1/admin/users/usr-1",
        json={"role": "manager"},
        headers=headers["admin"],
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "manager"


@pytest.mark.asyncio
async def test_admin_self_protection(client, db_session):
    headers = await _seed(client, db_session)
    # cannot block self
    block = await client.patch(
        "/api/v1/admin/users/adm-1",
        json={"is_active": False},
        headers=headers["admin"],
    )
    assert block.status_code == 400
    # cannot demote self
    demote = await client.patch(
        "/api/v1/admin/users/adm-1",
        json={"role": "user"},
        headers=headers["admin"],
    )
    assert demote.status_code == 400


@pytest.mark.asyncio
async def test_admin_user_detail(client, db_session):
    headers = await _seed(client, db_session)
    # give the normal user some activity
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "USDT", "amount": 10000}, headers=headers["user"])
    await client.post("/api/v1/orders", json={"pair": "BTC/USDT", "side": "buy", "qty": 0.05}, headers=headers["user"])

    resp = await client.get("/api/v1/admin/users/usr-1", headers=headers["admin"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "usr-1"
    assert body["trade_count"] == 1
    assert body["order_count"] >= 1
    assert body["total_usd"] > 0
    assert any(w["asset"] == "USDT" for w in body["wallets"])


@pytest.mark.asyncio
async def test_admin_user_detail_404(client, db_session):
    headers = await _seed(client, db_session)
    resp = await client.get("/api/v1/admin/users/no-such-id", headers=headers["admin"])
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_orders_list(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "USDT", "amount": 10000}, headers=headers["user"])
    # market order (filled)
    await client.post("/api/v1/orders", json={"pair": "BTC/USDT", "side": "buy", "qty": 0.05}, headers=headers["user"])
    # limit order (open)
    await client.post("/api/v1/orders", json={"pair": "BTC/USDT", "side": "buy", "qty": 0.01, "type": "limit", "price": 1000}, headers=headers["user"])

    resp = await client.get("/api/v1/admin/orders", headers=headers["admin"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    for o in body["orders"]:
        assert o["user_email"] == "usr-1@test.com"
        assert o["user_username"] == "usr-1name"
        assert o["pair"] == "BTC/USDT"
    statuses = {o["status"] for o in body["orders"]}
    assert {"open", "filled"} <= statuses


@pytest.mark.asyncio
async def test_admin_orders_filters(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "USDT", "amount": 10000}, headers=headers["user"])
    await client.post("/api/v1/orders", json={"pair": "BTC/USDT", "side": "buy", "qty": 0.05}, headers=headers["user"])
    await client.post("/api/v1/orders", json={"pair": "BTC/USDT", "side": "buy", "qty": 0.01, "type": "limit", "price": 1000}, headers=headers["user"])

    resp = await client.get("/api/v1/admin/orders", params={"status": "open"}, headers=headers["admin"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["orders"][0]["status"] == "open"

    # filter by user search
    resp2 = await client.get("/api/v1/admin/orders", params={"user": "adm-1"}, headers=headers["admin"])
    assert resp2.status_code == 200
    assert resp2.json()["total"] == 0


@pytest.mark.asyncio
async def test_admin_trades_list(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "USDT", "amount": 10000}, headers=headers["user"])
    await client.post("/api/v1/orders", json={"pair": "BTC/USDT", "side": "buy", "qty": 0.05}, headers=headers["user"])

    resp = await client.get("/api/v1/admin/trades", headers=headers["admin"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    t = body["trades"][0]
    assert t["user_email"] == "usr-1@test.com"
    assert t["user_username"] == "usr-1name"
    assert t["pair"] == "BTC/USDT"
    assert t["side"] == "buy"
    assert t["qty"] == 0.05

    # side filter + pair filter + user filter
    resp2 = await client.get("/api/v1/admin/trades", params={"side": "sell"}, headers=headers["admin"])
    assert resp2.status_code == 200
    assert resp2.json()["total"] == 0

    resp3 = await client.get("/api/v1/admin/trades", params={"pair": "BTC/USDT"}, headers=headers["admin"])
    assert resp3.status_code == 200
    assert resp3.json()["total"] == 1

    resp4 = await client.get("/api/v1/admin/trades", params={"user": "adm-1"}, headers=headers["admin"])
    assert resp4.status_code == 200
    assert resp4.json()["total"] == 0


@pytest.mark.asyncio
async def test_admin_stats_requires_admin(client, db_session):
    headers = await _seed(client, db_session)
    resp = await client.get("/api/v1/admin/stats", headers=headers["user"])
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_stats(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "USDT", "amount": 10000}, headers=headers["user"])
    await client.post("/api/v1/orders", json={"pair": "BTC/USDT", "side": "buy", "qty": 0.05}, headers=headers["user"])

    resp = await client.get("/api/v1/admin/stats", headers=headers["admin"])
    assert resp.status_code == 200
    body = resp.json()
    totals = body["totals"]
    assert totals["users"] == 2
    assert totals["active_users"] == 2
    assert totals["orders"] >= 1
    assert totals["trades"] >= 1
    assert totals["total_spot_usd"] > 0
    assert totals["today_trades"] >= 1
    assert totals["today_volume_usd"] > 0

    pairs = {p["pair"]: p for p in body["volume_by_pair"]}
    assert "BTC/USDT" in pairs
    assert pairs["BTC/USDT"]["volume_notional"] > 0
    assert pairs["BTC/USDT"]["trades"] >= 1
    assert body["volume_timeline"], "timeline should not be empty"
