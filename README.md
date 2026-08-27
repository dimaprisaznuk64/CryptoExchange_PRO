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

Python 3.12+, FastAPI, SQLAlchemy (async), PostgreSQL, Redis, Celery, JWT, React + TS, Pytest, Docker.

## Стан проєкту

Дивись [PROGRESS.md](PROGRESS.md) — точка збереження та подальші кроки.
