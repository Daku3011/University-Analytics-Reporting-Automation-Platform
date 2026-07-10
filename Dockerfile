# ── SU Analytics Dockerfile ──────────────────────────────────────────────────
# Two-stage build: dependencies layer (cached) + application layer (fast rebuild)
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: Dependencies ────────────────────────────────────────────────────
FROM python:3.10-slim AS deps

# Install system libraries required by WeasyPrint (PDF generation),
# Redis server (Celery broker), and PostgreSQL client
RUN apt-get update && apt-get install -y --no-install-recommends \
    # WeasyPrint rendering engine
    libglib2.0-0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-xlib-2.0-0 \
    libgdk-pixbuf2.0-common \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    fonts-dejavu-core \
    # Redis (in-container broker for HF Spaces single-container deployment)
    redis-server \
    # PostgreSQL
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 2: Application ─────────────────────────────────────────────────────
FROM deps AS app

WORKDIR /app

# Copy application source
COPY . .

# Create required directories
RUN mkdir -p /app/media/reports/monthly \
             /app/media/reports/quarterly \
             /app/media/reports/uploaded \
             /app/static

# Collect static files into /app/staticfiles for WhiteNoise
# Note: this runs with DEBUG=True default, which is safe for collectstatic
RUN python manage.py collectstatic --noinput --settings=su_analytics.settings

# Entrypoint: handles migrations, seeding, Redis, Celery, and Gunicorn startup
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create a non-root user with UID 1000 (standard for Hugging Face Spaces)
RUN useradd -m -u 1000 user

# Ensure user owns all application files and directories for write access (SQLite, media uploads, etc.)
RUN chown -R user:user /app /entrypoint.sh

# Switch to the non-root user
USER user

# HF Spaces runs on port 7860
EXPOSE 7860

# Health check: verify the web server is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/accounts/login/')" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
