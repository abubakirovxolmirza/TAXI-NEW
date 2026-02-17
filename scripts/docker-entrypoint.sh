#!/bin/sh
set -eu

echo "[entrypoint] Waiting for PostgreSQL..."
python - <<'PY'
import os
import time
from sqlalchemy import create_engine

dsn = os.getenv("DATABASE_URL")
if not dsn:
    raise SystemExit("DATABASE_URL is not set")

last_error = None
for attempt in range(1, 61):
    try:
        # DATABASE_URL may be SQLAlchemy style (e.g. postgresql+psycopg2://...)
        engine = create_engine(dsn, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        engine.dispose()
        print("[entrypoint] PostgreSQL is ready")
        break
    except Exception as exc:  # pragma: no cover
        last_error = exc
        print(f"[entrypoint] DB not ready ({attempt}/60): {exc}")
        time.sleep(2)
else:
    raise SystemExit(f"PostgreSQL is not reachable: {last_error}")
PY

echo "[entrypoint] Waiting for Redis..."
python - <<'PY'
import os
import time
import redis

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
last_error = None
for attempt in range(1, 61):
    try:
        client = redis.Redis.from_url(redis_url)
        client.ping()
        print("[entrypoint] Redis is ready")
        break
    except Exception as exc:  # pragma: no cover
        last_error = exc
        print(f"[entrypoint] Redis not ready ({attempt}/60): {exc}")
        time.sleep(2)
else:
    raise SystemExit(f"Redis is not reachable: {last_error}")
PY

echo "[entrypoint] Running migrations..."
alembic upgrade head

echo "[entrypoint] Starting API server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
