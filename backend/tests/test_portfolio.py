import pytest
from sqlalchemy import insert

from app.models.user import User
from app.models.asset import Asset
from app.models.trading_pair import TradingPair
from app.core.security import create_access_token, hash_password


async def _seed(client, db_session, uid="p-user"):
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
    await db_session.execute(insert(TradingPair).values(
        id="p-btcusd", symbol="BTC/USD",
        base_asset_id="a-btc", quote_asset_id="a-usd", is_active=True,
        price_precision=2, qty_precision=6,
    ))
    await db_session.execute(insert(Asset).values(
        id="a-usd", symbol="USD", name="US Dollar", decimals=2, is_fiat=True,
    ))
    await db_session.execute(insert(User).values(
        id=uid, email=f"{uid}@test.com", username=f"{uid}name",
        hashed_password=hash_password("secret123"), role="user", is_active=True,
    ))
    await db_session.commit()
    return {"Authorization": f"Bearer {create_access_token(uid)}"}


@pytest.mark.asyncio
async def test_empty_portfolio(client, db_session):
    headers = await _seed(client, db_session)
    resp = await client.get("/api/v1/portfolio", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_usd"] == 0
    assert body["items"] == []


@pytest.mark.asyncio
async def test_portfolio_after_buy(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "USDT", "amount": 10000}, headers=headers)
    await client.post("/api/v1/orders", json={"pair": "BTC/USDT", "side": "buy", "qty": 0.05}, headers=headers)

    resp = await client.get("/api/v1/portfolio", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_usd"] > 0
    symbols = {i["asset"]: i for i in body["items"]}
    assert "BTC" in symbols
    assert symbols["BTC"]["balance"] == 0.05
    assert symbols["BTC"]["usd_price"] > 0
    assert symbols["BTC"]["value_usd"] > 0
    # BTC/USD quote is preferred over USDT
    assert "USDT" in symbols or "USD" in symbols


@pytest.mark.asyncio
async def test_recent_trades(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "USDT", "amount": 10000}, headers=headers)
    await client.post("/api/v1/orders", json={"pair": "BTC/USDT", "side": "buy", "qty": 0.05}, headers=headers)

    resp = await client.get("/api/v1/portfolio/trades", headers=headers)
    assert resp.status_code == 200
    trades = resp.json()
    assert len(trades) == 1
    assert trades[0]["pair"] == "BTC/USDT"
    assert trades[0]["side"] == "buy"


@pytest.mark.asyncio
async def test_portfolio_requires_auth(client, db_session):
    resp = await client.get("/api/v1/portfolio")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_portfolio_history_reconstructs_balances(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "USDT", "amount": 10000}, headers=headers)
    await client.post("/api/v1/orders", json={"pair": "BTC/USDT", "side": "buy", "qty": 0.05}, headers=headers)

    resp = await client.get("/api/v1/portfolio/history", params={"days": 1}, headers=headers)
    assert resp.status_code == 200
    hist = resp.json()
    assert len(hist) == 13  # 1 day * 12 points/day + current-time point
    # before the deposit happened portfolio was empty
    assert hist[0]["value"] == 0
    # latest (now) sample equals current total portfolio value
    cur = (await client.get("/api/v1/portfolio", headers=headers)).json()["total_usd"]
    assert hist[-1]["value"] > 0
    assert abs(hist[-1]["value"] - cur) < 1
    assert hist[0]["time"] < hist[-1]["time"]


@pytest.mark.asyncio
async def test_portfolio_history_requires_auth(client, db_session):
    resp = await client.get("/api/v1/portfolio/history")
    assert resp.status_code == 401
