import tempfile

from config.settings import *  # noqa: F403,F401


DEBUG = True
SECRET_KEY = "signature-service-test-secret"
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
CSRF_TRUSTED_ORIGINS = []
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
MEDIA_ROOT = tempfile.mkdtemp(prefix="signature_service_media_")
STATIC_ROOT = tempfile.mkdtemp(prefix="signature_service_static_")
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
APP_DOMAIN = "testserver"
APP_USE_HTTPS = False
SITE_DOMAIN = APP_DOMAIN
SITE_HTTPS = APP_USE_HTTPS
SIGNATURE_SITE_DOMAIN = APP_DOMAIN
SIGNATURE_SITE_HTTPS = APP_USE_HTTPS
ZAPSIGN_API_TOKEN = "test-token"
ZAPSIGN_ENVIRONMENT = "sandbox"
ZAPSIGN_WEBHOOK_SECRET = "webhook-secret"
ZAPSIGN_WEBHOOK_HEADER = "X-ZapSign-Secret"
