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

Backend — **Docker** (VPS), Frontend — **Vercel**. Детальна інструкція:
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Стан проєкту

Дивись [PROGRESS.md](PROGRESS.md) — точка збереження та подальші кроки.
