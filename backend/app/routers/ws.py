import asyncio
import logging
from datetime import datetime, UTC

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from app.core import cache
from app.core.database import async_session
from app.core.security import decode_token, is_token_blacklisted
from app.models.user import User
from app.services.market import get_live_price_async, recent_trades
from app.services.depth import order_book
from app.services.notifications import list_notifications, unread_count

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ws"])

# Allowed resilience window for an in-flight websocket message.
RECEIVE_TIMEOUT = 0.2
# Order book + trade tape snapshot every N price ticks (~2s).
SNAPSHOT_EVERY_TICKS = 2
# Server pushes a {"type":"ping"} every N ticks (~15s).
HEARTBEAT_EVERY_TICKS = 15
# If the client hasn't answered any heartbeat (or sent anything at all) for
# this long, the connection is considered dead and gets closed — proxies and
# free-tier hosts silently drop idle websockets, and only a client "pong"
# proves the socket is still healthy.
HEARTBEAT_TIMEOUT_SECONDS = 45.0


async def authenticate_ws(websocket: WebSocket) -> User | None:
    ticket = websocket.query_params.get("ticket")
    if ticket:
        # One-time WS ticket issued by POST /auth/ws-ticket (no JWT in the URL).
        user_id = await cache.consume_ws_ticket(ticket)
        if user_id is None:
            return None
        async with async_session() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
        return user if user is not None and user.is_active else None

    # Legacy fallback: JWT passed via ?token (kept for backward compat).
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
    subscribed: set[str] = set(
        p.strip() for p in pairs.split(",") if p.strip()
    ) or {"BTC/USDT"}

    await websocket.send_json({"type": "hello", "user": user.email, "pairs": sorted(subscribed)})

    async def push_snapshot(pair: str) -> None:
        """Full current state for a pair — sent right after connect/subscribe so
        a reconnecting client resumes instantly instead of waiting for ticks."""
        price = await get_live_price_async(pair)
        await websocket.send_json(
            {"type": "price", "pair": pair, "price": float(price), "ts": datetime.now(UTC).isoformat()}
        )

    # Resume: push the current state immediately so the client can render.
    for pair in sorted(subscribed):
        await push_snapshot(pair)
    if subscribed:
        head = next(iter(sorted(subscribed)))
        await websocket.send_json({"type": "book", **await order_book(head)})
        await websocket.send_json({"type": "trades", "pair": head, "trades": await recent_trades(head, limit=30)})

    last_seen = datetime.now(UTC)
    tick = 0
    try:
        while True:
            # Drain incoming messages (pong / subscribe / unsubscribe) without
            # blocking the send loop: a short wait_for timeout is the "no message
            # this round" path, not an error.
            try:
                msg = await asyncio.wait_for(websocket.receive_json(), timeout=RECEIVE_TIMEOUT)
            except asyncio.TimeoutError:
                msg = None
            except (ValueError, TypeError) as e:
                logger.debug("WS malformed frame from %s: %s", user.id, e)
                msg = None
            except WebSocketDisconnect:
                break

            if msg is not None:
                now = datetime.now(UTC)
                msg_type = msg.get("type")
                if msg_type == "pong":
                    last_seen = now
                elif msg_type == "subscribe":
                    before = set(subscribed)
                    for p in (msg.get("pairs") or []):
                        symbol = str(p).strip()
                        if symbol:
                            subscribed.add(symbol)
                    await websocket.send_json({"type": "subscribed", "pairs": sorted(subscribed)})
                    for pair in sorted(subscribed - before):
                        await push_snapshot(pair)
                elif msg_type == "unsubscribe":
                    for p in (msg.get("pairs") or []):
                        subscribed.discard(str(p).strip())
                    await websocket.send_json({"type": "unsubscribed", "pairs": sorted(subscribed)})

            now = datetime.now(UTC)
            # Heartbeat: prove the socket is alive (Render free / proxies kill
            # idle websockets silently — only a client pong proves otherwise).
            if tick % HEARTBEAT_EVERY_TICKS == 0:
                await websocket.send_json({"type": "ping", "ts": now.isoformat()})
            if (now - last_seen).total_seconds() > HEARTBEAT_TIMEOUT_SECONDS:
                logger.info("WS heartbeat timeout for %s", user.id)
                await websocket.close(code=status.WS_1001_GOING_AWAY)
                return

            for pair in sorted(subscribed):
                price = await get_live_price_async(pair)
                await websocket.send_json(
                    {
                        "type": "price",
                        "pair": pair,
                        "price": float(price),
                        "ts": now.isoformat(),
                    }
                )
            await asyncio.sleep(1.0)
            tick += 1
            # order book snapshot every other tick (~2s) — plenty for a depth ladder
            if tick % SNAPSHOT_EVERY_TICKS == 0:
                for pair in sorted(subscribed)[:1]:
                    book = await order_book(pair)
                    await websocket.send_json({"type": "book", **book})
                    trades = await recent_trades(pair, limit=30)
                    await websocket.send_json({"type": "trades", "pair": pair, "trades": trades})
    except WebSocketDisconnect:
        logger.info("WS disconnected for %s", user.id)


@router.websocket("/ws/notifications")
async def ws_notifications(websocket: WebSocket):
    await websocket.accept()

    user = await authenticate_ws(websocket)
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    sent_ids: set[str] = set()
    await websocket.send_json({"type": "notification_init"})
    try:
        while True:
            async with async_session() as db:
                items = await list_notifications(db, user.id, limit=30)
                count = await unread_count(db, user.id)
            for n in items:
                if n.id in sent_ids:
                    continue
                sent_ids.add(n.id)
                await websocket.send_json(
                    {
                        "type": "notification",
                        "notification": {
                            "id": n.id,
                            "kind": n.kind,
                            "title": n.title,
                            "body": n.body,
                            "is_read": n.is_read,
                            "created_at": n.created_at.isoformat(),
                        },
                    }
                )
            await websocket.send_json({"type": "unread_count", "count": count})
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        logger.info("WS notifications disconnected for %s", user.id)
