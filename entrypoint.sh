#!/bin/bash
set -e

echo "--- SU Analytics: Starting up ---"

# Apply database migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Seed college and demo data
echo "Seeding colleges and demo data..."
python manage.py seed_data

# Create a default superuser if none exists
# Credentials MUST be set via environment variables — no hardcoded defaults
echo "Checking for superuser..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
import os
User = get_user_model()
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'suanalytics')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@su-analytics.in')
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f'Superuser created: {username}')
else:
    print(f'Superuser already exists: {username}')
"

# ── Start Redis (required by Celery for async tasks) ────────────
echo "Starting Redis server..."
redis-server --daemonize yes

# Wait for Redis to be ready before starting Celery
echo "Waiting for Redis..."
for i in $(seq 1 10); do
    if redis-cli ping | grep -q PONG; then
        echo "Redis is ready."
        break
    fi
    if [ "$i" -eq 10 ]; then
        echo "ERROR: Redis failed to start after 10 attempts."
        exit 1
    fi
    sleep 1
done

# ── Start Celery worker in background ──────────────────────────
echo "Starting Celery worker..."
celery -A su_analytics worker --loglevel=info --concurrency=1 &
CELERY_PID=$!
echo "Celery worker started (PID: $CELERY_PID)"

# Graceful shutdown: stop Celery before Gunicorn exits
trap "echo 'Shutting down...'; kill $CELERY_PID 2>/dev/null; wait $CELERY_PID 2>/dev/null; exit 0" SIGTERM SIGINT

# ── Start Gunicorn ─────────────────────────────────────────────
echo "Starting Gunicorn server on port 7860..."
exec gunicorn su_analytics.wsgi:application \
    --bind 0.0.0.0:7860 \
    --workers 1 \
    --timeout 600 \
    --graceful-timeout 600 \
    --access-logfile - \
    --error-logfile -
