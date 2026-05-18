# ── Stage: Build ─────────────────────────────────────────────────────────────
FROM python:3.10-slim

# Install native libraries required by WeasyPrint for PDF generation.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgobject-2.0-0 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi8 \
    shared-mime-info \
    fonts-liberation \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Some WeasyPrint loaders look up this exact name; provide compatibility alias.
RUN ln -sf /usr/lib/x86_64-linux-gnu/libgobject-2.0.so.0 /usr/lib/x86_64-linux-gnu/libgobject-2.0-0

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
RUN apt-get update && apt-get install -y --no-install-recommends dos2unix && \
    dos2unix /entrypoint.sh && \
    chmod +x /entrypoint.sh && \
    rm -rf /var/lib/apt/lists/*

# HF Spaces runs on port 7860
EXPOSE 7860

ENTRYPOINT ["/entrypoint.sh"]
