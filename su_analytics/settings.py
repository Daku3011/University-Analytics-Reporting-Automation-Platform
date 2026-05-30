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
# IMPORTANT: Move SECRET_KEY to your .env file in production!
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-ie53i!u)+hx1u*z*%u&*pqx1djx&uw4x&6hy0w+r842)$ja2&&'
)

DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get(
    'ALLOWED_HOSTS',
    '127.0.0.1,localhost,.hf.space,.huggingface.co'
).split(',')

# ── Application definition ────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
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
# Required for cross-origin iframe (HF Spaces): SameSite=None + Secure
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SECURE = True   # SameSite=None requires Secure

# ── CSRF Security ─────────────────────────────────────────────────────────────
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'None'
CSRF_COOKIE_SECURE = True      # SameSite=None requires Secure

# ── Security Headers ──────────────────────────────────────────────────────────
# X-Frame-Options intentionally NOT set — HF Spaces must embed app from different origin
# (huggingface.co embedding dwarkesh3011-su-report-analytics.hf.space)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

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
        conn_max_age=0,
    )
}
# SQLite (for local dev without PostgreSQL):
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }


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
