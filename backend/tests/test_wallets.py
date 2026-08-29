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


@pytest.mark.asyncio
async def test_transactions_filters(client, db_session):
    await _seed_assets(db_session)
    headers = await _user_and_headers(db_session)
    await client.post("/api/v1/wallets/deposit", json={
        "asset_symbol": "USD", "amount": 1000,
    }, headers=headers)
    await client.post("/api/v1/wallets/deposit", json={
        "asset_symbol": "BTC", "amount": 0.5,
    }, headers=headers)
    await client.post("/api/v1/wallets/withdraw", json={
        "asset_symbol": "USD", "amount": 100,
    }, headers=headers)

    async def q(params=None):
        r = await client.get("/api/v1/wallets/transactions", params=params, headers=headers)
        assert r.status_code == 200
        return r.json()

    assert len(await q()) == 3
    assert len(await q({"type": "deposit"})) == 2
    assert len(await q({"type": "withdrawal"})) == 1
    assert len(await q({"asset": "USD"})) == 2
    assert len(await q({"asset": "BTC"})) == 1
    assert len(await q({"type": "deposit", "asset": "BTC"})) == 1
    assert await q({"to": "2020-01-01T00:00:00"}) == []
    assert len(await q({"from": "2026-01-01T00:00:00"})) == 3
    # each tx carries asset + note
    first = (await q())[0]
    assert first["asset_symbol"] in ("USD", "BTC")
    assert first["delta"] is not None
    # invalid enum -> 422
    assert (await client.get("/api/v1/wallets/transactions", params={"type": "nope"}, headers=headers)).status_code == 422


@pytest.mark.asyncio
async def test_transfer_moves_funds_between_wallets(client, db_session):
    from app.models.wallet import Wallet, WalletType
    from sqlalchemy import select

    await _seed_assets(db_session)
    headers = await _user_and_headers(db_session, "w-tf")
    # USD in the spot wallet (the deposit default)
    await client.post("/api/v1/wallets/deposit", json={
        "asset_symbol": "USD", "amount": 1000,
    }, headers=headers)

    resp = await client.post("/api/v1/wallets/transfer", json={
        "asset_symbol": "USD", "amount": 400,
        "from_type": "spot", "to_type": "funding",
    }, headers=headers)
    assert resp.status_code == 200

    res = await db_session.execute(
        select(Wallet).where(Wallet.user_id == "w-tf", Wallet.asset_id == "a-usd")
    )
    wallets = list(res.scalars().all())
    by_type = {w.type.value: w for w in wallets}
    assert set(by_type) == {"spot", "funding"}
    assert float(by_type["spot"].balance) == 600.0
    assert float(by_type["funding"].balance) == 400.0
    assert float(by_type["funding"].available) == 400.0


@pytest.mark.asyncio
async def test_transfer_records_ledger(client, db_session):
    from app.models.transaction import Transaction, TransactionType
    from sqlalchemy import select

    await _seed_assets(db_session)
    headers = await _user_and_headers(db_session, "w-tf2")
    await client.post("/api/v1/wallets/deposit", json={
        "asset_symbol": "USD", "amount": 500,
    }, headers=headers)

    await client.post("/api/v1/wallets/transfer", json={
        "asset_symbol": "USD", "amount": 200,
        "from_type": "spot", "to_type": "funding",
    }, headers=headers)

    res = await db_session.execute(
        select(Transaction).where(Transaction.user_id == "w-tf2")
    )
    txs = list(res.scalars().all())
    transfer_txs = [t for t in txs if t.type == TransactionType.transfer]
    assert len(transfer_txs) == 2
    assert {t.delta for t in transfer_txs} == {200, -200}
    refs = {t.ref_id for t in transfer_txs}
    assert len(refs) == 1


@pytest.mark.asyncio
async def test_transfer_insufficient_400(client, db_session):
    await _seed_assets(db_session)
    headers = await _user_and_headers(db_session, "w-tf3")
    await client.post("/api/v1/wallets/deposit", json={
        "asset_symbol": "USD", "amount": 100,
    }, headers=headers)

    resp = await client.post("/api/v1/wallets/transfer", json={
        "asset_symbol": "USD", "amount": 500,
        "from_type": "spot", "to_type": "funding",
    }, headers=headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_transfer_same_wallet_400(client, db_session):
    await _seed_assets(db_session)
    headers = await _user_and_headers(db_session, "w-tf4")
    await client.post("/api/v1/wallets/deposit", json={
        "asset_symbol": "USD", "amount": 100,
    }, headers=headers)

    resp = await client.post("/api/v1/wallets/transfer", json={
        "asset_symbol": "USD", "amount": 10,
        "from_type": "spot", "to_type": "spot",
    }, headers=headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_transfer_bad_wallet_type_422(client, db_session):
    await _seed_assets(db_session)
    headers = await _user_and_headers(db_session, "w-tf5")
    resp = await client.post("/api/v1/wallets/transfer", json={
        "asset_symbol": "USD", "amount": 10,
        "from_type": "badtype", "to_type": "funding",
    }, headers=headers)
    assert resp.status_code == 422
