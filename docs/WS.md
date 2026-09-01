# WebSocket real-time — протокол

Backend надає два WS-ендпоінти (обидва під префіксом API, за замовчуванням `/api/v1`).

| Ендпоінт           | Призначення |
|--------------------|-------------|
| `/ws/prices`       | Ціни, стакан, лента угод |
| `/ws/notifications`| Push-сповіщення користувача |

## Авторизація

Підключення йде через **одноразовий, короткоживучий ticket**, а не JWT:

1. `POST /api/v1/auth/ws-ticket` (з Bearer access токеном) → `{ "ticket": "..." }` (TTL 60s, single-use).
2. `wss://<host>/api/v1/ws/prices?ticket=<ticket>&pairs=BTC/USDT,ETH/USDT`

Для сумісності `?token=<jwt>` теж приймається. Якщо авторизація не пройшла —
з'єднання закривається з кодом `1008`.

## `/ws/prices`

### Вхідні повідомлення (клієнт → сервер)

```jsonc
// Відповідь на серверний ping — тримає з'єднання живим
{ "type": "pong" }

// Підписатись на додаткові пари (наживо, без перепідключення)
{ "type": "subscribe",   "pairs": ["ETH/USDT", "SOL/USDT"] }

// Відписатись
{ "type": "unsubscribe", "pairs": ["SOL/USDT"] }
```

### Вихідні повідомлення (сервер → клієнт)

```jsonc
// Відразу після конекту: hello + повний снапшот поточного стану (resume).
{ "type": "hello", "user": "me@example.com", "pairs": ["BTC/USDT"] }
{ "type": "price", "pair": "BTC/USDT", "price": 78043.12, "ts": "2026-09-01T12:00:00+00:00" }

// Стакан (кожні ~2с і після конекту)
{ "type": "book",
  "pair": "BTC/USDT",
  "bids": [[78040.0, 0.412], ...],   // [price, qty], найкраща ціна перша
  "asks": [[78055.0, 0.830], ...],
  "ts": "..." }

// Лента угод (кожні ~2с, останні 30, newest-first)
{ "type": "trades", "pair": "BTC/USDT",
  "trades": [ { "time": 1788169690, "price": 78042.5, "qty": 0.031, "side": "buy" }, ... ] }

// Heartbeat: клієнт має відповісти {"type":"pong"}.
// Нема відповіді ≥45с → сервер закриває з'єднання (код 1001).
{ "type": "ping", "ts": "..." }

// Ака на підписку/відписку
{ "type": "subscribed",   "pairs": ["BTC/USDT", "ETH/USDT"] }
{ "type": "unsubscribed", "pairs": ["BTC/USDT"] }
```

### Поведінка джерел даних

- Коли Binance доступний — ціни/стакан/угоди **реальні** з `data-api.binance.vision`.
- Якщо Binance недоступний (Render free / офлайн) — працює **Market Maker**:
  детермінований рух ціни з кореляцією до свічок, живе споживання стакана, лента угод.

## `/ws/notifications`

```jsonc
{ "type": "notification",
  "notification": { "id": 42, "kind": "order_filled", "title": "Order filled",
                    "payload": { "order_id": 7, "pair": "BTC/USDT", "qty": 0.1, "price": 78042.5 },
                    "read": false, "created_at": "..." } }
```

## Клієнт

`frontend/hooks/useRealtime.ts` обробляє весь протокол:

- відповідає `pong` на `ping`;
- при `MAX_RECONNECTS=3` невдалих спробах деградує на REST-polling
  (`/market/tickers`, `/market/depth`, `/market/trades` — кожні 2с);
- staleness-сторож: 20с без жодного кадру від сервера — сокет закривається,
  щоб спрацював reconnect, а не «застиглий» UI.