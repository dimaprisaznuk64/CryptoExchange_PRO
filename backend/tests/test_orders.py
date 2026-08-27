import pytest
from sqlalchemy import insert

from app.models.user import User
from app.models.asset import Asset
from app.models.trading_pair import TradingPair
from app.core.security import create_access_token, hash_password


async def _seed(client, db_session, uid="o-user"):
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


async def _balance(client, headers, symbol):
    resp = await client.get("/api/v1/wallets/balances", headers=headers)
    items = {i["asset_symbol"]: i for i in resp.json()["items"]}
    return items.get(symbol)


@pytest.mark.asyncio
async def test_market_buy_exchanges_assets(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "USDT", "amount": 10000}, headers=headers)

    resp = await client.post("/api/v1/orders", json={
        "pair": "BTC/USDT", "side": "buy", "qty": 0.05,
    }, headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "filled"
    assert body["pair"] == "BTC/USDT"
    assert body["side"] == "buy"
    assert float(body["filled_qty"]) == 0.05

    usdt = await _balance(client, headers, "USDT")
    btc = await _balance(client, headers, "BTC")
    assert float(usdt["balance"]) < 10000  # spent some USDT
    assert float(btc["balance"]) == 0.05


@pytest.mark.asyncio
async def test_market_sell_exchanges_assets(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "BTC", "amount": 0.1}, headers=headers)

    resp = await client.post("/api/v1/orders", json={
        "pair": "BTC/USDT", "side": "sell", "qty": 0.04,
    }, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["status"] == "filled"

    usdt = await _balance(client, headers, "USDT")
    btc = await _balance(client, headers, "BTC")
    assert float(usdt["balance"]) > 0  # received USDT
    assert float(btc["balance"]) == 0.06


@pytest.mark.asyncio
async def test_market_buy_insufficient_400(client, db_session):
    headers = await _seed(client, db_session)
    resp = await client.post("/api/v1/orders", json={
        "pair": "BTC/USDT", "side": "buy", "qty": 0.05,
    }, headers=headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_bad_side_422(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "USDT", "amount": 10000}, headers=headers)
    resp = await client.post("/api/v1/orders", json={
        "pair": "BTC/USDT", "side": "hold", "qty": 0.05,
    }, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_unknown_pair_404(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "USDT", "amount": 10000}, headers=headers)
    resp = await client.post("/api/v1/orders", json={
        "pair": "ETH/USDT", "side": "buy", "qty": 1,
    }, headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_order_history_and_trades(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "USDT", "amount": 10000}, headers=headers)
    await client.post("/api/v1/orders", json={"pair": "BTC/USDT", "side": "buy", "qty": 0.05}, headers=headers)

    orders = await client.get("/api/v1/orders", headers=headers)
    assert orders.status_code == 200
    assert len(orders.json()) == 1

    trades = await client.get("/api/v1/orders/trades", headers=headers)
    assert trades.status_code == 200
    assert len(trades.json()) == 1
    assert trades.json()[0]["side"] == "buy"


@pytest.mark.asyncio
async def test_orders_require_auth(client, db_session):
    resp = await client.get("/api/v1/orders")
    assert resp.status_code == 401
