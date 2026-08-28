import pytest

from app.core.seed import seed_catalog


@pytest.mark.asyncio
async def test_seed_creates_assets_and_pairs(db_session):
    await seed_catalog(db_session)

    from sqlalchemy import select
    from app.models.asset import Asset
    from app.models.trading_pair import TradingPair

    assets = (await db_session.execute(select(Asset))).scalars().all()
    pairs = (await db_session.execute(select(TradingPair))).scalars().all()
    assert len(assets) >= 4
    symbols = {a.symbol for a in assets}
    assert {"BTC", "ETH", "USDT", "USD"} <= symbols
    assert any(p.symbol == "BTC/USDT" for p in pairs)


@pytest.mark.asyncio
async def test_list_pairs(client, db_session):
    await seed_catalog(db_session)
    resp = await client.get("/api/v1/market/pairs")
    assert resp.status_code == 200
    symbols = {p["symbol"] for p in resp.json()}
    assert "BTC/USDT" in symbols
    assert "ETH/USD" in symbols


@pytest.mark.asyncio
async def test_get_ticker(client, db_session):
    await seed_catalog(db_session)
    resp = await client.get("/api/v1/market/tickers/BTC/USDT")
    assert resp.status_code == 200
    data = resp.json()
    assert data["pair"] == "BTC/USDT"
    assert data["last"] > 0
    assert data["high_24h"] >= data["low_24h"]


@pytest.mark.asyncio
async def test_get_all_tickers(client, db_session):
    await seed_catalog(db_session)
    resp = await client.get("/api/v1/market/tickers")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 4
    assert all(t["last"] > 0 for t in items)


@pytest.mark.asyncio
async def test_get_candles(client, db_session):
    await seed_catalog(db_session)
    resp = await client.get("/api/v1/market/candles/BTC/USDT?interval=5&limit=10")
    assert resp.status_code == 200
    candles = resp.json()
    assert len(candles) == 10
    assert float(candles[0]["open"]) > 0


@pytest.mark.asyncio
async def test_unknown_pair_404(client, db_session):
    await seed_catalog(db_session)
    resp = await client.get("/api/v1/market/tickers/DOGE/BTC")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_ticker_uses_redis_cache(client, db_session):
    await seed_catalog(db_session)
    import app.core.cache as cache_module
    await cache_module.redis_client.flushdb()

    resp = await client.get("/api/v1/market/tickers/BTC/USDT")
    assert resp.status_code == 200

    cached = await cache_module.redis_client.get("market:ticker:BTC/USDT")
    assert cached is not None and "BTC/USDT" in cached

    all_resp = await client.get("/api/v1/market/tickers")
    assert all_resp.status_code == 200
    cached_all = await cache_module.redis_client.get("market:tickers")
    assert cached_all is not None
