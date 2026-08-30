# 🚀 CryptoExchange_PRO

Симулятор криптобіржі (production-oriented портфоліо-проєкт).

```
                    CryptoExchange_PRO
                           │
        ┌──────────────────┼──────────────────┐
        ↓                  ↓                  ↓
     Frontend           FastAPI            WebSocket
   React + TS          Backend             Realtime
        │                  │                  │
        └──────────────────┼──────────────────┘
                           ↓
                     PostgreSQL
                           │
             ┌─────────────┼─────────────┐
             ↓             ↓             ↓
           Redis         Celery        Market Data
             │             │
             └─────────────┴─────────────┘
```

## Функціонал користувача

- Акаунт та авторизація
- Баланс USD / USDT / криптовалюти
- Ринок та real-time ціни
- Ордери: створення / купівля / продаж / скасування
- Історія та P&L
- Керування портфелем
- Real-time notifications
- Графіки
- WebSocket

## Функціонал адміна

- Керування користувачами / блокування
- Трейди, ордери, статистика
- Audit logs

## Стек

Python 3.13, FastAPI, SQLAlchemy (async), PostgreSQL, Redis, Celery, JWT, React + Next.js + TS, Pytest, Docker.

## Запуск (локально)

- **Backend** (без Docker, для тестів): `cd backend && python -m pytest -q`
  (SQLite + in-memory Redis mock, Docker не потрібен).
- **Весь стек через Docker**: `docker compose up --build`
  — Postgres + Redis + backend API (`:8001`) + Celery worker/beat.
- **Frontend**: `cd frontend && npm install && npm run dev` — читає
  `NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_WS_URL` (за замовчуванням `localhost:8001`).

## Деплой

Backend — **Docker** (VPS / Render), Frontend — **Vercel**. Детальна інструкція:
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

- **GitHub**: `https://github.com/dimaprisaznuk64/CryptoExchange_PRO` (приватний, гілка `master`)
- **CI/CD**: GitHub Actions (`.github/workflows/backend-build.yml`) — на push у `backend/**` збирає Docker-образ і пушить у GHCR (`ghcr.io/dimaprisaznuk64/cryptoexchange_pro-backend`). Запуск вручну: `gh workflow run backend-build.yml`.
- **Render Blueprint**: `render.yaml` — web (backend API), 2 worker (celery worker + beat), managed Postgres + Redis.
- **Vercel**: імпорт репо, Root Directory = `frontend`, env `NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_WS_URL`.

## Стан проєкту

Дивись [PROGRESS.md](PROGRESS.md) — точка збереження та подальші кроки.
