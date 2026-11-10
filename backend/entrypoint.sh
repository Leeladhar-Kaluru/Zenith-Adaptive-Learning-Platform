#!/bin/sh
# ==============================================================================
# ZENITH Production Container Entrypoint Script
# 1. Runs Alembic database schema migrations on container boot
# 2. Launches Uvicorn ASGI server bound to the dynamic $PORT
# ==============================================================================
set -e

echo "[ZENITH Boot] Initializing application container..."
echo "[ZENITH Boot] Environment: ${APP_ENV:-production}"
echo "[ZENITH Boot] Active Port: ${PORT:-8000}"

# Run Alembic migrations to bring the database schema to the latest revision
echo "[ZENITH Boot] Applying database migrations (alembic upgrade head)..."
alembic upgrade head

# If custom command was passed to docker run, execute that; otherwise launch production Uvicorn
if [ "$#" -gt 0 ]; then
    echo "[ZENITH Boot] Executing custom command: $@"
    exec "$@"
else
    echo "[ZENITH Boot] Starting Uvicorn server on 0.0.0.0:${PORT:-8000}..."
    exec uvicorn app.main:app \
        --host 0.0.0.0 \
        --port "${PORT:-8000}" \
        --workers 1 \
        --proxy-headers \
        --forwarded-allow-ips='*'
fi
