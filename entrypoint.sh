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
# Credentials controlled by environment variables
echo "Checking for superuser..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
username = '${DJANGO_SUPERUSER_USERNAME:-admin}'
password = '${DJANGO_SUPERUSER_PASSWORD:-suanalytics2026}'
email = '${DJANGO_SUPERUSER_EMAIL:-admin@su-analytics.in}'
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f'Superuser created: {username}')
else:
    print(f'Superuser already exists: {username}')
"

# ── Start Redis (required by Celery for async tasks) ────────────
echo "Starting Redis server..."
redis-server --daemonize yes
# Give Redis a moment to initialize
sleep 1

# ── Start Celery worker in background ──────────────────────────
echo "Starting Celery worker..."
celery -A su_analytics worker --loglevel=info --concurrency=1 &
# Track PID so we can check on it later
CELERY_PID=$!
echo "Celery worker started (PID: $CELERY_PID)"

# ── Start Gunicorn ─────────────────────────────────────────────
echo "Starting Gunicorn server on port 7860..."
exec gunicorn su_analytics.wsgi:application \
    --bind 0.0.0.0:7860 \
    --workers 1 \
    --timeout 600 \
    --graceful-timeout 600 \
    --access-logfile - \
    --error-logfile -
