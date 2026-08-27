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
