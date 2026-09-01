import pytest

from app.core.seed import seed_catalog
from app.services import binance_client
from app.services import market as market_service
from app.services.market_maker import MarketMakerEngine, engine as mm_engine


def test_engine_price_within_band():
    price = MarketMakerEngine().price("BTC/USDT")
    assert price > 0
    # Deterministic anchor ~61.5k with ±10% per-minute spread.
    assert 30000 < price < 90000


def test_engine_snapshot_balanced():
    engine = MarketMakerEngine(levels=12)
    book = engine.snapshot("BTC/USDT", depth=10)
    assert book["pair"] == "BTC/USDT"
    assert book["best_bid"] > 0
    assert book["best_ask"] >= book["best_bid"]
    assert len(book["levels"]) == 10
    for level in book["levels"]:
        assert level["bid"] > 0 and level["ask"] > 0
        assert level["bid_qty"] > 0 and level["ask_qty"] > 0
        assert level["ask"] > level["bid"]


def test_engine_ticks_print_trades_and_move_price():
    engine = MarketMakerEngine(trade_probability=1.0)
    engine.tick(["ETH/USDT"])
    first = engine.price("ETH/USDT")
    for _ in range(5):
        engine.tick(["ETH/USDT"])
    trades = engine.recent_trades("ETH/USDT", limit=100)
    assert len(trades) >= 1
    assert all(t["side"] in ("buy", "sell") and t["price"] > 0 for t in trades)
    assert engine.price("ETH/USDT") != first


def test_engine_refills_levels_after_consumption():
    engine = MarketMakerEngine(trade_probability=1.0, levels=5)
    for _ in range(10):
        engine.tick(["BTC/USDT"])
    book = engine.snapshot("BTC/USDT", depth=5)
    assert len(book["levels"]) == 5
    assert book["best_ask"] > book["best_bid"]


def test_engine_tape_capped():
    engine = MarketMakerEngine(trade_probability=1.0, tape_maxlen=5)
    for _ in range(20):
        engine.tick(["BTC/USDT"])
    assert len(engine.recent_trades("BTC/USDT", limit=100)) <= 5


@pytest.mark.asyncio
async def test_market_trades_endpoint_simulated(client, db_session, monkeypatch):
    await seed_catalog(db_session)

    async def no_binance_trades(symbol, limit=30):
        return None

    monkeypatch.setattr(binance_client, "fetch_recent_trades", no_binance_trades)

    # Make sure the shared engine's tape has some prints to serve.
    for _ in range(8):
        mm_engine.tick(["BTC/USDT"])

    resp = await client.get("/api/v1/market/trades/BTC/USDT?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    assert all(t["side"] in ("buy", "sell") for t in data)
    assert all(t["price"] > 0 and t["qty"] > 0 for t in data)


@pytest.mark.asyncio
async def test_market_trades_unknown_pair_404(client, db_session):
    await seed_catalog(db_session)
    resp = await client.get("/api/v1/market/trades/DOGE/BTC")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_recent_trades_uses_binance_when_available(client, db_session, monkeypatch):
    await seed_catalog(db_session)

    async def fake_binance_trades(symbol, limit=30):
        return [
            {"id": 1, "time": 1700000000000, "price": "61234.5", "qty": "0.01", "isBuyerMaker": False},
            {"id": 2, "time": 1700000001000, "price": "61200.0", "qty": "0.02", "isBuyerMaker": True},
        ]

    monkeypatch.setattr(binance_client, "fetch_recent_trades", fake_binance_trades)

    resp = await client.get("/api/v1/market/trades/BTC/USDT?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    # newest first per the API contract
    assert data[0]["price"] == 61200.0 and data[0]["side"] == "sell"
    assert data[1]["price"] == 61234.5 and data[1]["side"] == "buy"