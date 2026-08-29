import pytest
from sqlalchemy import insert

from app.models.user import User
from app.models.asset import Asset
from app.models.trading_pair import TradingPair
from app.core.security import create_access_token, hash_password


async def _seed(client, db_session, uid="n-user"):
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
        id=uid, email=f"{uid}@test.com", username=f"{uid}name",
        hashed_password=hash_password("secret123"), role="user", is_active=True,
    ))
    await db_session.commit()
    return {"Authorization": f"Bearer {create_access_token(uid)}"}


@pytest.mark.asyncio
async def test_order_fill_creates_notification(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "USDT", "amount": 10000}, headers=headers)
    await client.post("/api/v1/orders", json={"pair": "BTC/USDT", "side": "buy", "qty": 0.05}, headers=headers)

    resp = await client.get("/api/v1/notifications", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    n = items[0]
    assert n["kind"] == "order_filled"
    assert "filled" in n["title"]
    assert "BTC/USDT" in n["body"]
    assert n["is_read"] is False


@pytest.mark.asyncio
async def test_unread_count_and_mark_read(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "USDT", "amount": 10000}, headers=headers)
    await client.post("/api/v1/orders", json={"pair": "BTC/USDT", "side": "buy", "qty": 0.05}, headers=headers)

    count = (await client.get("/api/v1/notifications/unread-count", headers=headers)).json()
    assert count["count"] == 1

    items = (await client.get("/api/v1/notifications", headers=headers)).json()
    nid = items[0]["id"]
    read = await client.post(f"/api/v1/notifications/{nid}/read", headers=headers)
    assert read.status_code == 200
    assert read.json()["is_read"] is True

    count2 = (await client.get("/api/v1/notifications/unread-count", headers=headers)).json()
    assert count2["count"] == 0


@pytest.mark.asyncio
async def test_cancel_creates_notification(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "USDT", "amount": 10000}, headers=headers)
    # a non-marketable limit buy stays open, then gets cancelled
    placed = await client.post(
        "/api/v1/orders",
        json={"pair": "BTC/USDT", "side": "buy", "qty": 0.05, "type": "limit", "price": 1},
        headers=headers,
    )
    oid = placed.json()["id"]
    await client.post(f"/api/v1/orders/{oid}/cancel", headers=headers)

    resp = await client.get("/api/v1/notifications", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert any(n["kind"] == "order_cancelled" for n in items)


@pytest.mark.asyncio
async def test_notifications_require_auth(client, db_session):
    resp = await client.get("/api/v1/notifications")
    assert resp.status_code == 401
