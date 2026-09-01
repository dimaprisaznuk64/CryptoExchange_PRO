# 🚀 CryptoExchange_PRO

Production-oriented симулятор криптобіржі. Функціональний демо-застосунок з
real-time ринком (Binance-ціни + симуляція), ордерами, P&L, адмін-кабінетом
і повним набором тестів.

- **Live frontend**: https://crypto-exchange-pro-two.vercel.app
- **Live backend API**: https://cryptoexchange-backend.onrender.com (docs `/docs` увімкнено лише в DEBUG)

> Демо-режим: новий акаунт отримує віртуальні **$10,000 USDT** для торгівлі.

```
                    CryptoExchange_PRO
                           │
        ┌──────────────────┼──────────────────┐
        ↓                  ↓                  ↓
     Frontend           FastAPI            WebSocket   (real-time ціни,
   React + TS          Backend             Realtime    стакан, угоди, сповіщення)
        │                  │                  │
        └──────────────────┼──────────────────┘
                           ↓
                     PostgreSQL
                           │
             ┌─────────────┼─────────────┐
             ↓             ↓             ↓
           Redis         Celery        Market Data (Binance API + fallback)
             │             │
             └─────────────┴─────────────┘
```

## Функціонал

**Користувач**
- Реєстрація / вхід / JWT (refresh + access), WS-ticket замість токена в URL, logout revokes access
- Спот-рахуночок: депозит, переказ між гаманцями (spot ↔ funding)
- Риночні та лімітні ордери, TP/SL з фоновим in-process монітором
- Портфель, історія угод, P&L, звіт за обсягом
- Real-time: ціни, стакан, лента угод, графіки (свічки)
- Сповіщення ("Order filled", ...) — в Postgres + push через `/ws/notifications`

**Адмін**
- Керування користувачами / блокування
- Перегляд ордерів і трейдів всіх користувачів
- Аудит-лог активності

**Під капотом (30 фаз розробки)**
- Live-ринок: Binance (`api.binance.com` → `data-api.binance.vision`) з автоматичним
  fallback на **Market Maker** (симульований рух ціни, живе споживання стакана, лента угод)
- WebSocket-шлюз з heartbeat (ping/pong), resume-снапшотом після конекту і live subscribe/unsubscribe
- Redis-кеш ринкових даних, rate-limiting, Celery (worker + beat)
- Error boundaries (root / `/trade` / global) — жодних «білих сторінок»
- Захист від гонок: `SELECT ... FOR UPDATE` за ордерами та гаманцями

## Стек

Python 3.13, FastAPI, SQLAlchemy (async), PostgreSQL, Redis, Celery, JWT,
React + Next.js 16 (App Router, Turbopack, Tailwind v4, TypeScript), Pytest, Docker.

## Real-time WebSocket

Протокол `/ws/prices` та `/ws/notifications` описано в [docs/WS.md](docs/WS.md):
`hello`, `price`, `book`, `trades`, `ping`/`pong`, `subscribe`/`unsubscribe`.

## Запуск (локально)

```bash
# Весь стек через Docker (Postgres + Redis + backend :8001 + worker + beat)
docker compose up --build

# Backend без Docker, тільки для тестів (SQLite + in-memory Redis mock)
cd backend && .venv\Scripts\python -m pytest -q

# Frontend
cd frontend && npm install && npm run dev
```

Конфіг frontend — `frontend/.env.local`: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_WS_URL`
(за замовчуванням `http://localhost:8001` / `ws://localhost:8001`).

## Тести

- Backend: **119 тестів** (auth, security/concurrency, trading, wallets, portfolio, market, market maker, realtime WS, notifications, admin).
  SQLite + in-memory Redis — Docker не потрібен.
- Frontend: ESLint + `next build` (13 статичних сторінок) — green.

## Деплой

| Частина  | Технології | Куди                          |
|----------|-----------|-------------------------------|
| Backend  | FastAPI + WS + Celery | Docker (VPS / Render web service) |
| Frontend | Next.js   | Vercel (Root Directory = `frontend`) |

- GitHub Actions `.github/workflows/backend-build.yml` — збирає образ backend і пушить у GHCR
- `render.yaml` — Render Blueprint (web: API; Postgres/Redis — зовнішні, через env)
- Детальна інструкція (env-змінні, TLS/wss, перевірка після деплою): [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

## Структура репо

```
backend/    FastAPI: app/{routers,services,models,core,schemas}, alembic, tests/
frontend/   Next.js 16 App Router: app/, components/, hooks/, lib/, context/
docs/       DEPLOYMENT.md, WS.md
.github/    GitHub Actions (backend-build.yml)
docker-compose.yml   render.yaml   PROGRESS.md
```

## Стан проєкту

Розвиток ведеться фазами; актуальна точка збереження та план —
[PROGRESS.md](PROGRESS.md). (Repo приватний, гілка `master`.)