# ── Stage: Build ─────────────────────────────────────────────────────────────
FROM python:3.10-slim

# Install GTK3/Pango/Cairo (required by WeasyPrint for PDF generation)
RUN apt-get update && apt-get install -y --no-install-recommends \
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
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create necessary directories
RUN mkdir -p /app/media/reports/monthly \
             /app/media/reports/quarterly \
             /app/static

# Collect static files
RUN python manage.py collectstatic --noinput --settings=su_analytics.settings || true

# Run migrations and create superuser on startup via entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# HF Spaces runs on port 7860
EXPOSE 7860

ENTRYPOINT ["/entrypoint.sh"]
