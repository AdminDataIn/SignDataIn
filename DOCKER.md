# Docker de produccion

## Archivos

- `Dockerfile`
- `.dockerignore`
- `docker-compose.yml`
- `docker/entrypoint.sh`
- `docker/gunicorn.conf.py`
- `.env.production.example`

## Caracteristicas

- imagen multi-stage
- usuario no-root
- `gunicorn` como proceso principal
- `postgres` interno en Compose
- sin puertos publicados
- reinicio `unless-stopped`
- volumenes persistentes para:
  - base de datos
  - media
  - staticfiles

## Variables importantes

```env
POSTGRES_DB=signature_service
POSTGRES_USER=signature_user
POSTGRES_PASSWORD=change-me
DATABASE_URL=postgresql://signature_user:change-me@db:5432/signature_service
DJANGO_SECRET_KEY=change-this-secret
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=sign.datain.pro
DJANGO_CSRF_TRUSTED_ORIGINS=https://sign.datain.pro
APP_DOMAIN=sign.datain.pro
APP_USE_HTTPS=True
SIGNATURE_PUBLIC_BASE_URL=https://sign.datain.pro
ZAPSIGN_API_TOKEN=your-token
ZAPSIGN_WEBHOOK_SECRET=your-secret
```

## Levantar stack

```bash
cp .env.production.example .env
docker compose up -d --build
```

## Logs

```bash
docker compose logs -f web
docker compose logs -f db
```

## Reverse proxy despues

El servicio `web` queda disponible solo dentro de la red Docker en el puerto interno `8000`.

El reverse proxy posterior debe:

- conectarse a la misma red Docker
- enrutar hacia `http://web:8000`
- exponer `sign.datain.pro`
