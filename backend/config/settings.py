import os
import re
from pathlib import Path
from urllib.parse import urlparse

import dj_database_url


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-local-development-key-change-me",
)
DEBUG = os.environ.get("DEBUG", "True").lower() == "true"

def env_list(name, default):
    return [value.strip() for value in os.environ.get(name, default).split(",") if value.strip()]


def build_vercel_origin_regex(frontend_origin):
    parsed = urlparse(frontend_origin)
    if parsed.scheme != "https":
        return None

    host = parsed.hostname or ""
    if not host.endswith(".vercel.app"):
        return None

    project_slug = host[:-len(".vercel.app")]
    if not project_slug:
        return None

    return rf"^https://{re.escape(project_slug)}(?:-[a-z0-9-]+)*\.vercel\.app$"


def build_vercel_csrf_origins(frontend_origin):
    parsed = urlparse(frontend_origin)
    if parsed.scheme != "https":
        return []

    host = parsed.hostname or ""
    if not host.endswith(".vercel.app"):
        return []

    project_slug = host[:-len(".vercel.app")]
    if not project_slug:
        return []

    return [f"https://{project_slug}.vercel.app", f"https://{project_slug}-*.vercel.app"]


ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "accounts",
    "receipts",
    "expenses",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    DATABASES["default"] = dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
        conn_health_checks=True,
    )

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ja"
TIME_ZONE = "Asia/Tokyo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "accounts.authentication.CsrfSessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "https://amber-lilac.vercel.app")
DEFAULT_FRONTEND_ORIGINS = [FRONTEND_ORIGIN]
DEFAULT_CORS_ORIGIN_REGEXES = []
vercel_origin_regex = build_vercel_origin_regex(FRONTEND_ORIGIN)
if vercel_origin_regex:
    DEFAULT_CORS_ORIGIN_REGEXES.append(vercel_origin_regex)

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", ",".join(DEFAULT_FRONTEND_ORIGINS))
CORS_ALLOWED_ORIGIN_REGEXES = env_list("CORS_ALLOWED_ORIGIN_REGEXES", ",".join(DEFAULT_CORS_ORIGIN_REGEXES))
CORS_ALLOW_CREDENTIALS = True

DEFAULT_CSRF_TRUSTED_ORIGINS = DEFAULT_FRONTEND_ORIGINS + build_vercel_csrf_origins(FRONTEND_ORIGIN)
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", ",".join(DEFAULT_CSRF_TRUSTED_ORIGINS))
CSRF_COOKIE_HTTPONLY = False

SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = os.environ.get("CSRF_COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False").lower() == "true"
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "False").lower() == "true"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
