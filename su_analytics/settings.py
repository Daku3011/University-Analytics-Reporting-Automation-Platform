"""
Django settings for su_analytics project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env')

# ── Security ──────────────────────────────────────────────────────────────────
# SECRET_KEY MUST be set via environment variable in production.
# The insecure fallback only works when DEBUG=True.
_default_secret = 'django-insecure-ie53i!u)+hx1u*z*%u&*pqx1djx&uw4x&6hy0w+r842)$ja2&&'
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', _default_secret)

DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

# Safety: Refuse to start in production mode with the insecure key
if not DEBUG and SECRET_KEY == _default_secret:
    raise ValueError(
        "DJANGO_SECRET_KEY must be set to a unique, unpredictable value in production. "
        "Generate one with: python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\""
    )

ALLOWED_HOSTS = os.environ.get(
    'ALLOWED_HOSTS',
    '127.0.0.1,localhost,.hf.space,.huggingface.co,.render'
).split(',')

# ── Application definition ────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',    # {% load humanize %} for intcomma, naturaltime, etc.
    'accounts',
    'colleges',
    'events',
    'analytics_app',
    'reports',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # Serve static files in production
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'accounts.middleware.SessionTimeoutMiddleware',     # Custom: auto-logout idle users
    'django.contrib.messages.middleware.MessageMiddleware',
    # XFrameOptionsMiddleware removed — HF Spaces embeds app in iframe from different origin
]

ROOT_URLCONF = 'su_analytics.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ── Auth & Login ──────────────────────────────────────────────────────────────
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# ── Session Security ──────────────────────────────────────────────────────────
# Session expires after 1 hour of inactivity
SESSION_COOKIE_AGE = 3600
# Session ends when browser closes
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True

# Cross-origin cookies: only enable SameSite=None + Secure in production (HTTPS on HF)
RUNNING_ON_HF = 'SPACE_ID' in os.environ

if RUNNING_ON_HF:
    # Required for cross-origin iframe (HF Spaces): SameSite=None + Secure
    SESSION_COOKIE_SAMESITE = 'None'
    SESSION_COOKIE_SECURE = True
elif DEBUG:
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False
else:
    # Production settings for local testing (HTTP)
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False

# ── CSRF Security ─────────────────────────────────────────────────────────────
CSRF_COOKIE_HTTPONLY = True
if RUNNING_ON_HF:
    CSRF_COOKIE_SAMESITE = 'None'
    CSRF_COOKIE_SECURE = True
elif DEBUG:
    CSRF_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SECURE = False
else:
    CSRF_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SECURE = False

# ── Security Headers ──────────────────────────────────────────────────────────
SECURE_CONTENT_TYPE_NOSNIFF = True

if RUNNING_ON_HF:
    # Tell Django it's behind a secure reverse proxy (Hugging Face Spaces load balancer)
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    if not DEBUG:
        # HTTPS enforcement in production (Hugging Face Spaces)
        SECURE_SSL_REDIRECT = True
        SECURE_HSTS_SECONDS = 31536000       # 1 year
        SECURE_HSTS_INCLUDE_SUBDOMAINS = True
        SECURE_HSTS_PRELOAD = True
elif not DEBUG:
    # Production settings for local testing (HTTP)
    SECURE_SSL_REDIRECT = False

# Trusted origins for CSRF (required for HF Spaces cross-origin requests)
CSRF_TRUSTED_ORIGINS = [
    'https://*.hf.space',
    'https://*.huggingface.co',
    'http://127.0.0.1:8000',
    'http://localhost:8000',
]

WSGI_APPLICATION = 'su_analytics.wsgi.application'

# ── File Upload Limits ────────────────────────────────────────────────────────
# Faculty upload 3 monthly PDFs, each up to 70 MB → allow 250 MB total
DATA_UPLOAD_MAX_MEMORY_SIZE = 250 * 1024 * 1024   # 250 MB total request body
FILE_UPLOAD_MAX_MEMORY_SIZE = 1 * 1024 * 1024     # >1 MB → write to temp disk file

# ── Database ──────────────────────────────────────────────────────────────────
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///' + str(BASE_DIR / 'db.sqlite3'),
        conn_max_age=600,   # Reuse DB connections for 10 minutes
    )
}

# ── Password Validation ───────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internationalization ──────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ── Static & Media Files ──────────────────────────────────────────────────────
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []
STATIC_ROOT = BASE_DIR / 'staticfiles'                # For collectstatic
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Caching (Redis-backed, shared with Celery) ───────────────────────────────
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
        'OPTIONS': {
            'db': '1',    # Use a separate Redis DB from Celery to avoid collisions
        },
    }
} if not DEBUG else {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# ── Email Configuration (email-systems skill) ─────────────────────────────────
# Development: print emails to console
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# Production (uncomment and fill in .env):
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
# EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
# EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
# DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'SU Analytics <no-reply@su-analytics.in>')

# ── Gemini AI Configuration (gemini-api-dev skill) ───────────────────────────
GEMINI_CONFIG = {
    'MODEL': os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash'),
    'COOLDOWN_SECONDS': 60,   # Wait 60s between generations per user
    'DAILY_LIMIT': 50,         # Max 50 generations per user per day
}

# ── Login Throttling ──────────────────────────────────────────────────────────
LOGIN_MAX_ATTEMPTS = 5          # Max failed attempts before lockout
LOGIN_LOCKOUT_SECONDS = 900     # 15-minute lockout

# ── Celery & Redis Background Tasks ───────────────────────────────────────────
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# ── Logging ───────────────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {module}.{funcName}:{lineno} — {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'reports': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'analytics_app': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
