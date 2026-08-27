import asyncio
import logging
from datetime import datetime, UTC

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from app.core.database import async_session
from app.core.security import decode_token, is_token_blacklisted
from app.models.user import User
from app.services.market import _live_price
from app.services.depth import order_book

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ws"])


async def authenticate_ws(websocket: WebSocket) -> User | None:
    token = websocket.query_params.get("token")
    if not token:
        return None
    payload = decode_token(token, expected_type="access")
    if payload is None:
        return None
    if await is_token_blacklisted(payload.get("jti", "")):
        return None
    user_id = payload.get("sub")
    async with async_session() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            return None
    return user


@router.websocket("/ws/prices")
async def ws_prices(websocket: WebSocket):
    await websocket.accept()

    user = await authenticate_ws(websocket)
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    pairs = websocket.query_params.get("pairs", "")
    subscribed = [p.strip() for p in pairs.split(",") if p.strip()] or ["BTC/USDT"]

    await websocket.send_json({"type": "hello", "user": user.email, "pairs": subscribed})
    try:
        tick = 0
        while True:
            now = datetime.now(UTC)
            for pair in subscribed:
                price = _live_price(pair, now)
                await websocket.send_json(
                    {
                        "type": "price",
                        "pair": pair,
                        "price": float(price),
                        "ts": now.isoformat(),
                    }
                )
            await asyncio.sleep(0.05)
            tick += 1
            # periodic order book snapshot every ~5 iterations
            if tick % 5 == 0:
                for pair in subscribed[:1]:
                    book = order_book(pair)
                    await websocket.send_json({"type": "book", **book})
    except WebSocketDisconnect:
        logger.info("WS disconnected for %s", user.id)
