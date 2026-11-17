#!/usr/bin/env bash
# start.sh — Production startup script for CodeSheriff on Render
# Runs both Celery background worker and FastAPI API in the same container to stay 100% within Render's free tier.

set -e

echo "[STARTUP] Starting Celery worker in background..."
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2 &

echo "[STARTUP] Starting Uvicorn API server on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
