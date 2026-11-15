import os
import dj_database_url
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# --- ENVIRONMENT DETECTION ---
# Render automatically sets RENDER='true' in its environment
IS_PRODUCTION = os.environ.get('RENDER') == 'true'

# --- SECURITY ---
SECRET_KEY = config("SECRET_KEY", default="django-insecure-change-this-in-production")
DEBUG = config("DEBUG", default=True, cast=bool)

if IS_PRODUCTION:
    ALLOWED_HOSTS = ['.onrender.com']
else:
    ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1").split(",")

# --- APPLICATIONS ---
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "django_filters",
    # Local
    "tenants",
    "subscriptions",
    "core",
    "saas",
    "accounting",
    "inventory",
    "sales",
    "customers",
    "payments",
    "zra_integration",
    "returns",
    "notifications",
    "reports",
    "purchasing",
    "security",
]

# --- MIDDLEWARE ---
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise only in production (Render)
    *(['whitenoise.middleware.WhiteNoiseMiddleware'] if IS_PRODUCTION else []),
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "subscriptions.middleware.TenantLimitMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.TenantBranchMiddleware",
]

ROOT_URLCONF = "pos_backend.urls"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

WSGI_APPLICATION = "pos_backend.wsgi.application"

# --- DATABASE ---
if IS_PRODUCTION:
    # PRODUCTION (Render/Neon): Uses the DATABASE_URL injected by Render
    DATABASES = {
        'default': dj_database_url.config(conn_max_age=600, conn_health_checks=True)
    }
else:
    # LOCAL: Uses your local .env variables or defaults to localhost Postgres
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME", default="zra_pos_saas"),
            "USER": config("DB_USER", default="pos_user"),
            "PASSWORD": config("DB_PASSWORD", default="Stacy2026!"),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="5432"),
            "OPTIONS": {"connect_timeout": 10},
            "CONN_MAX_AGE": 60,
            "ATOMIC_REQUESTS": False,
        }
    }

# --- CACHES ---
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

# --- AUTHENTICATION ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "core.User"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lusaka"
USE_I18N = True
USE_TZ = True

# --- STATIC & MEDIA ---
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]  # This allows local dev to find your JS files

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# WhiteNoise Compression (Production only)
if IS_PRODUCTION:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- CORS & REST FRAMEWORK ---
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

# --- EMAIL & SMS ---
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@yourstore.com")

AFRICASTALKING_USERNAME = config("AFRICASTALKING_USERNAME", default="")
AFRICASTALKING_API_KEY = config("AFRICASTALKING_API_KEY", default="")

# Global fallbacks
COMPANY_NAME = config("COMPANY_NAME", default="Your Store")
COMPANY_ADDRESS = config("COMPANY_ADDRESS", default="Lusaka, Zambia")
COMPANY_PHONE = config("COMPANY_PHONE", default="+260211234567")

SESSION_COOKIE_AGE = 3600
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}