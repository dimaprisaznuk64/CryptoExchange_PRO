# Деплой — CryptoExchange_PRO

Проект складається з двох частин, які деплояться окремо:

| Частина | Технології | Спосіб деплою |
|---------|------------|----------------|
| Backend | FastAPI + WebSocket + SQLAlchemy + Redis + Celery | Docker (VPS / VDS) |
| Frontend | Next.js (React) | Vercel |

> Backend **не** підходить для Vercel serverless: там WebSocket-з'єднання,
> постійний in-process фоновий монітор (TP/SL) і Celery worker/beat.
> Тому backend запускаємо в контейнері Docker, а фронтенд — на Vercel.

---

## 1. Backend через Docker

### Структура
- `backend/Dockerfile` — образ: Python 3.13-slim, ставить `requirements.txt`,
  запускає `alembic upgrade head && uvicorn app.main:app --port 8001`.
- `docker-compose.yml` — піднімає `postgres`, `redis`, `backend`, `worker`, `beat`.
- Під час старту `lifespan` FastAPI автоматично **сіє каталог пар** і запускає
  in-process монітор умовних ордерів (TP/SL) — окремо нічого робити не треба.

### Кроки (локально, весь стек)

```bash
# з кореня репо
docker compose up --build
```

- API: `http://localhost:8001` (доки `DEBUG=true`, /docs доступний)
- Postgres: `localhost:5433`, Redis: `localhost:6380`

### Кроки (продакшен, VPS)

1. Побудувати й завантажити образ у registry:

```bash
docker build -t <registry>/cryptoexchange-backend ./backend
docker push <registry>/cryptoexchange-backend
```

2. На VPS запустити compose з override-env (це можна покласти поруч у `.env` для compose):

```
POSTGRES_DB=cryptoexchange
POSTGRES_USER=exchange
POSTGRES_PASSWORD=<сильний-пароль>
SECRET_KEY=<random: python -c "import secrets; print(secrets.token_hex(32))">
DEBUG=false
CORS_ORIGINS=https://<фронтенд-домен>
ALLOWED_HOSTS=<api.example.com>
BACKEND_PORT=8001
```

```bash
docker compose up -d --build
```

### Міграції бази
- Образи самі виконують `alembic upgrade head` перед стартом API.
- Якщо потрібно вручну (напр. на наявній базі):

```bash
docker compose run --rm backend sh -c "alembic upgrade head"
```

> **Зверни увагу:** міграції `3a9f2c77d1b4` (transfer type) і
> `f0a1b2c3d4e5` (notifications) досі **не застосовані** до жодної бази, бо
> Docker був вимкнений. У продакшені вони застосуються автоматично при першому
> старті образу; для локальної Postgres запусти `docker compose up -d`,
> потім `docker compose run --rm backend sh -c "alembic upgrade head"`.

### Celery (worker + beat)
- `worker` — виконує асинхронні задачі (`app.tasks`).
- `beat` — розклад: прогрів Redis-кешу ринкових даних (кожні 60 с)
  та очищення stale-транзакцій (щодня).
- TP/SL **вже** обробляє in-process монітор в `backend`, тому task
  `run_conditional_orders` не входить у beat (щоб не було подвійного виконання).

### Змінні середовища backend

| Змінна | Опис | Приклад |
|--------|------|---------|
| `DATABASE_URL` | asyncpg DSN | `postgresql+asyncpg://user:pass@postgres:5432/cryptoexchange` |
| `REDIS_URL` | Redis для кешу/rate-limit | `redis://redis:6379/0` |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Redis для Celery | `redis://redis:6379/1` |
| `SECRET_KEY` | симетричний ключ JWT (≥16 символів) | `secrets.token_hex(32)` |
| `DEBUG` | `true` = увімкнути /docs, `false` = вимкнути | `false` |
| `CORS_ORIGINS` | список дозволених origin (через кому) | `https://app.example.com` |
| `ALLOWED_HOSTS` | дозволені Host-заголовки (`*` = всі) | `*` |
| `API_V1_PREFIX` | префікс API | `/api/v1` |

---

## 2. Frontend через Vercel

Фронтенд — стандартний Next.js (App Router). Спеціальний `vercel.json` не
потрібен; достатньо налаштувати кореневу директорію й змінні середовища.

### Кроки

1. `vercel` у корені репо → при імпорті вкажи **Root Directory = `frontend`**
   (проєкт у монорепо: білд-конфіг Next.js лежить у `frontend/`).
2. Задай змінні середовища в Vercel (Project → Settings → Environment Variables):

```
NEXT_PUBLIC_API_URL = https://<api.example.com>     # без `/api/v1`
NEXT_PUBLIC_WS_URL   = wss://<api.example.com>      # WebSocket-ендпоінт бекенду
```

   Ці змінні читаються під час білду (`lib/api.ts`).
3. Deploy. Після кожного `git push` на бранч (production/main) — автодеплой.

### Важливо для продакшену
- `NEXT_PUBLIC_*` підставляються **на етапі білду**, тож значення мають бути
  доступні в налаштуваннях Vercel до деплою.
- WebSocket має ходити на той самий домен, що піднятий на backend
  (`wss://…/ws/prices`). Для ws+https постав TLS-термінацію на рівні reverse-proxy
  (напр. Caddy/Traefik перед контейнером backend).

---

## 3. Перевірка після деплою

- `GET https://<api>/api/v1/health` → 200.
- `GET https://<api>/api/v1/market/tickers` → список пар.
- Відкрити фронтенд → `/register`, поповнити гаманець, купити на `/trade`.
- Перевірити, що через кілька секунд у дзвіночку з'явилось сповіщення
  «Order filled» (сповіщення зберігаються в Postgres + штовхаються через
  `/ws/notifications`).
