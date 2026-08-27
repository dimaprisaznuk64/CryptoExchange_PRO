import pytest
from sqlalchemy import insert

from app.models.user import User
from app.models.asset import Asset
from app.core.security import create_access_token, hash_password


async def _seed_assets(db_session):
    await db_session.execute(insert(Asset).values(
        id="a-usd", symbol="USD", name="US Dollar", decimals=2, is_fiat=True,
    ))
    await db_session.execute(insert(Asset).values(
        id="a-btc", symbol="BTC", name="Bitcoin", decimals=8, is_fiat=False,
    ))
    await db_session.commit()


async def _user_and_headers(db_session, uid="w-user"):
    await db_session.execute(insert(User).values(
        id=uid, email=f"{uid}@test.com", username=f"{uid}name",
        hashed_password=hash_password("secret123"), role="user", is_active=True,
    ))
    await db_session.commit()
    return {"Authorization": f"Bearer {create_access_token(uid)}"}


@pytest.mark.asyncio
async def test_deposit_credits_balance(client, db_session):
    await _seed_assets(db_session)
    headers = await _user_and_headers(db_session)

    resp = await client.post("/api/v1/wallets/deposit", json={
        "asset_symbol": "USD", "amount": 10000,
    }, headers=headers)
    assert resp.status_code == 200
    usd = next(i for i in resp.json()["items"] if i["asset_symbol"] == "USD")
    assert float(usd["balance"]) == 10000.0
    assert float(usd["available"]) == 10000.0


@pytest.mark.asyncio
async def test_withdraw_debits_balance(client, db_session):
    await _seed_assets(db_session)
    headers = await _user_and_headers(db_session)
    await client.post("/api/v1/wallets/deposit", json={
        "asset_symbol": "USD", "amount": 10000,
    }, headers=headers)

    resp = await client.post("/api/v1/wallets/withdraw", json={
        "asset_symbol": "USD", "amount": 4000,
    }, headers=headers)
    assert resp.status_code == 200
    usd = next(i for i in resp.json()["items"] if i["asset_symbol"] == "USD")
    assert float(usd["balance"]) == 6000.0


@pytest.mark.asyncio
async def test_withdraw_insufficient_400(client, db_session):
    await _seed_assets(db_session)
    headers = await _user_and_headers(db_session)
    await client.post("/api/v1/wallets/deposit", json={
        "asset_symbol": "USD", "amount": 100,
    }, headers=headers)

    resp = await client.post("/api/v1/wallets/withdraw", json={
        "asset_symbol": "USD", "amount": 999,
    }, headers=headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_negative_amount_400(client, db_session):
    await _seed_assets(db_session)
    headers = await _user_and_headers(db_session)
    resp = await client.post("/api/v1/wallets/deposit", json={
        "asset_symbol": "USD", "amount": -5,
    }, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_unknown_asset_404(client, db_session):
    await _seed_assets(db_session)
    headers = await _user_and_headers(db_session)
    resp = await client.post("/api/v1/wallets/deposit", json={
        "asset_symbol": "DOGE", "amount": 5,
    }, headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_balances_require_auth(client, db_session):
    await _seed_assets(db_session)
    resp = await client.get("/api/v1/wallets/balances")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_transactions_history(client, db_session):
    await _seed_assets(db_session)
    headers = await _user_and_headers(db_session)
    await client.post("/api/v1/wallets/deposit", json={
        "asset_symbol": "USD", "amount": 500,
    }, headers=headers)
    await client.post("/api/v1/wallets/deposit", json={
        "asset_symbol": "BTC", "amount": 0.5,
    }, headers=headers)

    resp = await client.get("/api/v1/wallets/transactions", headers=headers)
    assert resp.status_code == 200
    txs = resp.json()
    assert len(txs) == 2
    types = {t["type"] for t in txs}
    assert types == {"deposit"}
