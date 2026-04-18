import tempfile


BASE_DIR = tempfile.gettempdir()
SECRET_KEY = "signature-service-test-secret"
DEBUG = True
USE_TZ = True
ROOT_URLCONF = "signature_service.tests.urls"
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SITE_DOMAIN = "testserver"
SITE_HTTPS = False
ZAPSIGN_API_TOKEN = "test-token"
ZAPSIGN_ENVIRONMENT = "sandbox"
ZAPSIGN_WEBHOOK_SECRET = "webhook-secret"
ZAPSIGN_WEBHOOK_HEADER = "X-ZapSign-Secret"
MEDIA_ROOT = tempfile.mkdtemp(prefix="signature_service_media_")
MEDIA_URL = "/media/"
STATIC_URL = "/static/"

INSTALLED_APPS = [
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
]

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
    }
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
