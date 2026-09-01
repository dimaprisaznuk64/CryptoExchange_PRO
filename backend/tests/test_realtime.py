import pytest
from starlette.testclient import TestClient

import app.routers.ws as ws_module
from app.main import app


class FakeUser:
    id = "ws-user"
    email = "ws@test.com"
    is_active = True


@pytest.mark.asyncio
async def test_ws_prices_streams(monkeypatch):
    async def fake_auth(websocket):
        return FakeUser()

    monkeypatch.setattr(ws_module, "authenticate_ws", fake_auth)

    tc = TestClient(app)
    with tc.websocket_connect("/ws/prices?token=abc&pairs=BTC/USDT,ETH/USDT") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello"
        assert hello["pairs"] == ["BTC/USDT", "ETH/USDT"]

        price_msgs = []
        for _ in range(10):
            msg = ws.receive_json()
            if msg["type"] == "price":
                price_msgs.append(msg)
                if len(price_msgs) >= 2:
                    break
        assert len(price_msgs) >= 1
        assert price_msgs[0]["pair"] in ("BTC/USDT", "ETH/USDT")
        assert price_msgs[0]["price"] > 0
    tc.close()


@pytest.mark.asyncio
async def test_ws_subscribe_unsubscribe(monkeypatch):
    async def fake_auth(websocket):
        return FakeUser()

    monkeypatch.setattr(ws_module, "authenticate_ws", fake_auth)

    tc = TestClient(app)
    with tc.websocket_connect("/ws/prices?token=abc&pairs=BTC/USDT") as ws:
        assert ws.receive_json()["type"] == "hello"

        # Subscribe to a second pair live.
        ws.send_json({"type": "subscribe", "pairs": ["ETH/USDT"]})
        subscribed_ack = None
        eth_price = None
        for _ in range(20):
            msg = ws.receive_json()
            if msg["type"] == "subscribed":
                subscribed_ack = msg
                continue
            if msg["type"] == "price" and msg["pair"] == "ETH/USDT":
                eth_price = msg
            if subscribed_ack and eth_price:
                break
        assert subscribed_ack["pairs"] == ["BTC/USDT", "ETH/USDT"]
        assert eth_price is not None and eth_price["price"] > 0

        # Unsubscribe: the ack reflects only the remaining pair.
        ws.send_json({"type": "unsubscribe", "pairs": ["ETH/USDT"]})
        unsubscribed_ack = None
        for _ in range(20):
            msg = ws.receive_json()
            if msg["type"] == "unsubscribed":
                unsubscribed_ack = msg
                break
        assert unsubscribed_ack["pairs"] == ["BTC/USDT"]
    tc.close()


@pytest.mark.asyncio
async def test_ws_sends_heartbeat_ping(monkeypatch):
    async def fake_auth(websocket):
        return FakeUser()

    monkeypatch.setattr(ws_module, "authenticate_ws", fake_auth)

    tc = TestClient(app)
    with tc.websocket_connect("/ws/prices?token=abc&pairs=BTC/USDT") as ws:
        assert ws.receive_json()["type"] == "hello"
        ping = None
        for _ in range(30):
            msg = ws.receive_json()
            if msg["type"] == "ping":
                ping = msg
                break
        assert ping is not None
        assert "ts" in ping
        # A pong keeps the session healthy (no close fired).
        ws.send_json({"type": "pong"})
    tc.close()


@pytest.mark.asyncio
async def test_ws_rejects_unauthenticated(monkeypatch):
    async def fake_auth(websocket):
        return None

    monkeypatch.setattr(ws_module, "authenticate_ws", fake_auth)

    tc = TestClient(app)
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with tc.websocket_connect("/ws/prices?token=bad") as ws:
            ws.receive_json()
    tc.close()
