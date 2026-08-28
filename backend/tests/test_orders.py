import pytest
from decimal import Decimal
from sqlalchemy import insert

from app.models.user import User
from app.models.asset import Asset
from app.models.trading_pair import TradingPair
from app.core.security import create_access_token, hash_password
from app.services import trading as trading_service


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


# --- Limit orders (BT C/USDT price is deterministic within [55332, 67628]) ---
# buy limit at 1000 is far below market  -> stays open (freeze quote)
# buy limit at 100000 is far above market -> fills immediately
# sell limit at 100000 is far above market -> stays open (freeze base)
# sell limit at 1000 is far below market -> fills immediately


@pytest.mark.asyncio
async def test_limit_buy_below_market_open_freezes_quote(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "USDT", "amount": 10000}, headers=headers)

    resp = await client.post("/api/v1/orders", json={
        "pair": "BTC/USDT", "side": "buy", "qty": 0.05, "type": "limit", "price": 1000,
    }, headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "open"
    assert body["type"] == "limit"
    assert float(body["price"]) == 1000.0
    assert float(body["filled_qty"]) == 0.0

    usdt = await _balance(client, headers, "USDT")
    assert float(usdt["balance"]) == 10000.0          # balance untouched
    assert float(usdt["frozen"]) == 50.0              # 0.05 * 1000 frozen
    assert float(usdt["available"]) == 9950.0
    assert await _balance(client, headers, "BTC") is None  # nothing received


@pytest.mark.asyncio
async def test_limit_buy_above_market_fills_immediately(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "USDT", "amount": 10000}, headers=headers)

    resp = await client.post("/api/v1/orders", json={
        "pair": "BTC/USDT", "side": "buy", "qty": 0.05, "type": "limit", "price": 100000,
    }, headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "filled"
    assert float(body["avg_fill_price"]) == 100000.0

    usdt = await _balance(client, headers, "USDT")
    btc = await _balance(client, headers, "BTC")
    assert float(usdt["balance"]) == 5000.0           # spent 0.05 * 100000
    assert float(usdt["frozen"]) == 0.0
    assert float(btc["balance"]) == 0.05
    assert float(btc["available"]) == 0.05


@pytest.mark.asyncio
async def test_limit_sell_above_market_open_freezes_base(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "BTC", "amount": 0.1}, headers=headers)

    resp = await client.post("/api/v1/orders", json={
        "pair": "BTC/USDT", "side": "sell", "qty": 0.04, "type": "limit", "price": 100000,
    }, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["status"] == "open"

    btc = await _balance(client, headers, "BTC")
    assert float(btc["balance"]) == 0.1
    assert float(btc["frozen"]) == 0.04
    assert float(btc["available"]) == 0.06
    usdt = await _balance(client, headers, "USDT")
    assert usdt is None


@pytest.mark.asyncio
async def test_limit_sell_below_market_fills_immediately(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "BTC", "amount": 0.1}, headers=headers)

    resp = await client.post("/api/v1/orders", json={
        "pair": "BTC/USDT", "side": "sell", "qty": 0.04, "type": "limit", "price": 1000,
    }, headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "filled"
    assert float(body["avg_fill_price"]) == 1000.0

    btc = await _balance(client, headers, "BTC")
    usdt = await _balance(client, headers, "USDT")
    assert float(btc["balance"]) == 0.06
    assert float(usdt["balance"]) == 40.0             # 0.04 * 1000
    assert float(usdt["available"]) == 40.0


@pytest.mark.asyncio
async def test_cancel_open_buy_unfreezes(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "USDT", "amount": 10000}, headers=headers)
    order = await client.post("/api/v1/orders", json={
        "pair": "BTC/USDT", "side": "buy", "qty": 0.05, "type": "limit", "price": 1000,
    }, headers=headers)
    order_id = order.json()["id"]

    resp = await client.post(f"/api/v1/orders/{order_id}/cancel", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

    usdt = await _balance(client, headers, "USDT")
    assert float(usdt["frozen"]) == 0.0
    assert float(usdt["available"]) == 10000.0

    again = await client.post(f"/api/v1/orders/{order_id}/cancel", headers=headers)
    assert again.status_code == 400


@pytest.mark.asyncio
async def test_cancel_open_sell_unfreezes(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "BTC", "amount": 0.1}, headers=headers)
    order = await client.post("/api/v1/orders", json={
        "pair": "BTC/USDT", "side": "sell", "qty": 0.04, "type": "limit", "price": 100000,
    }, headers=headers)
    order_id = order.json()["id"]

    resp = await client.post(f"/api/v1/orders/{order_id}/cancel", headers=headers)
    assert resp.status_code == 200

    btc = await _balance(client, headers, "BTC")
    assert float(btc["frozen"]) == 0.0
    assert float(btc["available"]) == 0.1


@pytest.mark.asyncio
async def test_cancel_unknown_404(client, db_session):
    headers = await _seed(client, db_session)
    resp = await client.post("/api/v1/orders/no-such-order/cancel", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_limit_requires_price_422(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "USDT", "amount": 10000}, headers=headers)
    resp = await client.post("/api/v1/orders", json={
        "pair": "BTC/USDT", "side": "buy", "qty": 0.05, "type": "limit",
    }, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_limit_buy_insufficient_400(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "USDT", "amount": 10000}, headers=headers)
    resp = await client.post("/api/v1/orders", json={
        "pair": "BTC/USDT", "side": "buy", "qty": 1, "type": "limit", "price": 100000,
    }, headers=headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_orders_filter_by_status(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "USDT", "amount": 10000}, headers=headers)
    await client.post("/api/v1/orders", json={
        "pair": "BTC/USDT", "side": "buy", "qty": 0.02, "type": "limit", "price": 1000,
    }, headers=headers)  # open
    await client.post("/api/v1/orders", json={
        "pair": "BTC/USDT", "side": "buy", "qty": 0.03, "type": "limit", "price": 100000,
    }, headers=headers)  # filled

    all_orders = await client.get("/api/v1/orders", headers=headers)
    assert len(all_orders.json()) == 2

    open_orders = await client.get("/api/v1/orders", params={"status": "open"}, headers=headers)
    assert len(open_orders.json()) == 1
    assert open_orders.json()[0]["status"] == "open"

    filled = await client.get("/api/v1/orders", params={"status": "filled"}, headers=headers)
    assert len(filled.json()) == 1
    assert filled.json()[0]["status"] == "filled"


# --- Conditional orders (take_profit / stop_loss) ---------------------------
# BTC/USDT live price is deterministic in ~[55138, 67865]; the extremes below
# are safely outside that range so orders either rest or fill predictably.


@pytest.mark.asyncio
async def test_take_profit_sell_above_market_open_freezes_base(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "BTC", "amount": 0.1}, headers=headers)

    resp = await client.post("/api/v1/orders", json={
        "pair": "BTC/USDT", "side": "sell", "qty": 0.04, "type": "take_profit", "price": 200000,
    }, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["status"] == "open"
    assert resp.json()["type"] == "take_profit"

    btc = await _balance(client, headers, "BTC")
    assert float(btc["frozen"]) == 0.04
    assert float(btc["available"]) == 0.06

    cancel = await client.post(f"/api/v1/orders/{resp.json()['id']}/cancel", headers=headers)
    assert cancel.status_code == 200
    btc2 = await _balance(client, headers, "BTC")
    assert float(btc2["frozen"]) == 0.0
    assert float(btc2["available"]) == 0.1


@pytest.mark.asyncio
async def test_take_profit_sell_below_market_fills_immediately(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "BTC", "amount": 0.1}, headers=headers)

    resp = await client.post("/api/v1/orders", json={
        "pair": "BTC/USDT", "side": "sell", "qty": 0.04, "type": "take_profit", "price": 1000,
    }, headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "filled"
    assert float(body["avg_fill_price"]) == 1000.0

    btc = await _balance(client, headers, "BTC")
    usdt = await _balance(client, headers, "USDT")
    assert float(btc["balance"]) == 0.06
    assert float(usdt["balance"]) == 40.0


@pytest.mark.asyncio
async def test_stop_loss_sell_rests_then_triggers_via_monitor(client, db_session, monkeypatch):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "BTC", "amount": 0.1}, headers=headers)

    resp = await client.post("/api/v1/orders", json={
        "pair": "BTC/USDT", "side": "sell", "qty": 0.04, "type": "stop_loss", "price": 50000,
    }, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["status"] == "open"
    btc = await _balance(client, headers, "BTC")
    assert float(btc["frozen"]) == 0.04

    monkeypatch.setattr(
        "app.services.trading._live_price",
        lambda symbol, ts: Decimal("49000"),
    )
    await trading_service.check_conditional_orders(db_session)

    filled = await client.get("/api/v1/orders", params={"status": "filled"}, headers=headers)
    assert len(filled.json()) == 1
    assert float(filled.json()[0]["avg_fill_price"]) == 50000.0

    btc = await _balance(client, headers, "BTC")
    usdt = await _balance(client, headers, "USDT")
    assert float(btc["balance"]) == 0.06
    assert float(btc["frozen"]) == 0.0
    assert float(usdt["balance"]) == 2000.0


@pytest.mark.asyncio
async def test_take_profit_buy_triggers_via_monitor(client, db_session, monkeypatch):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "USDT", "amount": 10000}, headers=headers)

    resp = await client.post("/api/v1/orders", json={
        "pair": "BTC/USDT", "side": "buy", "qty": 0.04, "type": "take_profit", "price": 50000,
    }, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["status"] == "open"
    usdt = await _balance(client, headers, "USDT")
    assert float(usdt["frozen"]) == 2000.0   # 0.04 * 50000

    monkeypatch.setattr(
        "app.services.trading._live_price",
        lambda symbol, ts: Decimal("49000"),
    )
    await trading_service.check_conditional_orders(db_session)

    usdt = await _balance(client, headers, "USDT")
    btc = await _balance(client, headers, "BTC")
    assert float(usdt["frozen"]) == 0.0
    assert float(usdt["balance"]) == 8000.0  # paid 0.04 * 50000
    assert float(btc["balance"]) == 0.04


@pytest.mark.asyncio
async def test_conditional_requires_price_422(client, db_session):
    headers = await _seed(client, db_session)
    await client.post("/api/v1/wallets/deposit", json={"asset_symbol": "BTC", "amount": 0.1}, headers=headers)
    resp = await client.post("/api/v1/orders", json={
        "pair": "BTC/USDT", "side": "sell", "qty": 0.04, "type": "take_profit",
    }, headers=headers)
    assert resp.status_code == 422
