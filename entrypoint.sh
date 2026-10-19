#!/bin/sh
set -e

echo "================================================================"
echo "  Kodnexus Clinical AI & Hospital Management Platform"
echo "  Production Container Startup"
echo "================================================================"

# 1. Wait for PostgreSQL database if DATABASE_URL is configured
if [ -n "$DATABASE_URL" ] && [ "$DATABASE_URL" != "sqlite:///./data/clinic_dev.db" ]; then
    echo "[STARTUP] Checking PostgreSQL connectivity..."
    python - <<'EOF'
import os
import sys
import time

db_url = os.environ.get("DATABASE_URL", "").strip()
clean_url = db_url.replace("postgresql+psycopg2://", "postgresql://").replace("postgresql+psycopg://", "postgresql://")

max_retries = 30
connected = False
for attempt in range(1, max_retries + 1):
    try:
        import psycopg2
        conn = psycopg2.connect(clean_url)
        conn.close()
        print(f"[STARTUP] PostgreSQL database connection established successfully on attempt {attempt}.")
        connected = True
        break
    except Exception as err:
        print(f"[STARTUP] Waiting for database (attempt {attempt}/{max_retries}): {err}")
        time.sleep(1)

if not connected:
    print("[STARTUP] Warning: Could not connect to PostgreSQL within timeout. Continuing startup...")
sys.exit(0)
EOF

    echo "[STARTUP] Applying database schema migrations via Alembic..."
    alembic upgrade head || {
        echo "[STARTUP] Warning: Alembic migrations encountered an issue. Continuing server startup..."
    }
else
    echo "[STARTUP] Running in standalone local storage mode (no PostgreSQL DATABASE_URL detected)."
fi

# 2. Ensure data directories exist
mkdir -p /app/data/tenants /app/data/knowledge /app/data/vectorstore /app/data/prescriptions /app/data/invoices /app/logs

# 3. Start Uvicorn application server
PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"
WORKERS="${WORKERS:-2}"
LOG_LEVEL="${LOG_LEVEL:-info}"

echo "[STARTUP] Launching Uvicorn server on ${HOST}:${PORT} (workers=${WORKERS}, log_level=${LOG_LEVEL})..."
exec uvicorn app.main:app --host "${HOST}" --port "${PORT}" --workers "${WORKERS}" --log-level "${LOG_LEVEL}"

