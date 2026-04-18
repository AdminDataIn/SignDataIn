import os
from pathlib import Path
from urllib.parse import unquote, urlparse

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


BASE_DIR = Path(__file__).resolve().parent.parent

if load_dotenv:
    load_dotenv(BASE_DIR / ".env")


def env(key, default=None):
    return os.environ.get(key, default)


def env_bool(key, default=False):
    value = env(key)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def env_list(key, default=""):
    raw = env(key, default)
    return [item.strip() for item in str(raw).split(",") if item.strip()]


def env_int(key, default=0):
    value = env(key)
    if value is None or value == "":
        return default
    return int(value)


def database_config():
    database_url = env("DATABASE_URL")
    if not database_url:
        return {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": str(BASE_DIR / "db.sqlite3"),
            }
        }

    parsed = urlparse(database_url)
    scheme = parsed.scheme.lower()

    if scheme in {"postgres", "postgresql", "psql"}:
        return {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": parsed.path.lstrip("/"),
                "USER": unquote(parsed.username or ""),
                "PASSWORD": unquote(parsed.password or ""),
                "HOST": parsed.hostname or "localhost",
                "PORT": str(parsed.port or "5432"),
                "CONN_MAX_AGE": int(env("DB_CONN_MAX_AGE", "60")),
            }
        }

    if scheme == "sqlite":
        db_path = parsed.path or "/db.sqlite3"
        return {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": str(Path(unquote(db_path)).resolve()),
            }
        }

    raise ValueError(f"Unsupported DATABASE_URL scheme: {scheme}")


SECRET_KEY = env("DJANGO_SECRET_KEY", "django-insecure-change-me")
DEBUG = env_bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "signature_service",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = database_config()

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = env("DJANGO_LANGUAGE_CODE", "es-co")
TIME_ZONE = env("DJANGO_TIME_ZONE", "America/Bogota")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

APP_DOMAIN = env("APP_DOMAIN", "localhost:8000")
APP_USE_HTTPS = env_bool("APP_USE_HTTPS", default=not DEBUG)
SIGNATURE_PUBLIC_BASE_URL = env("SIGNATURE_PUBLIC_BASE_URL", "").rstrip("/")

SITE_DOMAIN = APP_DOMAIN
SITE_HTTPS = APP_USE_HTTPS
SIGNATURE_SITE_DOMAIN = APP_DOMAIN
SIGNATURE_SITE_HTTPS = APP_USE_HTTPS

SIGNATURE_PROVIDER = env("SIGNATURE_PROVIDER", "zapsign")
ZAPSIGN_API_TOKEN = env("ZAPSIGN_API_TOKEN", "")
ZAPSIGN_ENVIRONMENT = env("ZAPSIGN_ENVIRONMENT", "sandbox")
ZAPSIGN_AUTH_MODE = env("ZAPSIGN_AUTH_MODE", "assinaturaTela")
ZAPSIGN_SEND_AUTOMATIC_EMAIL = env_bool("ZAPSIGN_SEND_AUTOMATIC_EMAIL", default=True)
ZAPSIGN_ENABLE_SELFIE_VALIDATION = env_bool("ZAPSIGN_ENABLE_SELFIE_VALIDATION", default=False)
ZAPSIGN_SELFIE_VALIDATION_TYPE = env("ZAPSIGN_SELFIE_VALIDATION_TYPE", "identity-verification")
ZAPSIGN_WEBHOOK_SECRET = env("ZAPSIGN_WEBHOOK_SECRET", "")
ZAPSIGN_WEBHOOK_HEADER = env("ZAPSIGN_WEBHOOK_HEADER", "X-ZapSign-Secret")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", default=not DEBUG)
SESSION_COOKIE_SECURE = env_bool("DJANGO_SESSION_COOKIE_SECURE", default=not DEBUG)
CSRF_COOKIE_SECURE = env_bool("DJANGO_CSRF_COOKIE_SECURE", default=not DEBUG)
SECURE_HSTS_SECONDS = env_int("DJANGO_SECURE_HSTS_SECONDS", default=31536000 if not DEBUG else 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=not DEBUG,
)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", default=not DEBUG)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL", "INFO"),
        },
        "signature_service": {
            "handlers": ["console"],
            "level": env("SIGNATURE_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
    },
}
