#!/bin/bash
set -e

echo "--- SU Analytics: Starting up ---"

# Apply database migrations
echo "Running migrations..."
python manage.py migrate --noinput

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

echo "Starting Gunicorn server on port 7860..."
exec gunicorn su_analytics.wsgi:application \
    --bind 0.0.0.0:7860 \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
