# Despliegue con Traefik + Docker Compose

Estructura recomendada:

```text
docker/
├── traefik/
│   ├── docker-compose.yml
│   ├── .env.example
│   └── letsencrypt/
└── mi_app/
    ├── docker-compose.yml
    └── .env.example
```

## 1. Crear red Docker externa

```bash
docker network create web
```

## 2. Preparar certificados de Let's Encrypt

```bash
mkdir -p docker/traefik/letsencrypt
touch docker/traefik/letsencrypt/acme.json
chmod 600 docker/traefik/letsencrypt/acme.json
```

## 3. Preparar variables

```bash
cp docker/traefik/.env.example docker/traefik/.env
cp docker/mi_app/.env.example docker/mi_app/.env
```

Configura en `docker/mi_app/.env`:

- `APP_DOMAIN=midominio.com`
- `DJANGO_ALLOWED_HOSTS=midominio.com`
- `DJANGO_CSRF_TRUSTED_ORIGINS=https://midominio.com`
- `SIGNATURE_PUBLIC_BASE_URL=https://midominio.com`
- `ZAPSIGN_API_TOKEN`
- `ZAPSIGN_WEBHOOK_SECRET`

Configura en `docker/traefik/.env`:

- `TRAEFIK_ACME_EMAIL=tu-correo@dominio.com`
- opcionalmente `TRAEFIK_DASHBOARD_ENABLED=true`
- opcionalmente `TRAEFIK_DASHBOARD_HOST=traefik.midominio.com`
- opcionalmente `TRAEFIK_DASHBOARD_AUTH=...`

## 4. Levantar Traefik

```bash
cd docker/traefik
docker compose up -d
```

## 5. Levantar la aplicación

```bash
cd ../mi_app
docker compose up -d --build
```

## Resultado esperado

- `https://midominio.com` responde con SSL válido automático
- redirección HTTP -> HTTPS activa
- la app no publica puertos directamente
- Traefik enruta internamente hacia `web:8000`

## Seguridad mínima recomendada

- no usar `DJANGO_DEBUG=True` en VPS
- usar `DJANGO_SECRET_KEY` larga y única
- no exponer PostgreSQL
- mantener `TRAEFIK_DASHBOARD_ENABLED=false` si no vas a usar dashboard
- si habilitas dashboard, protegerlo con `TRAEFIK_DASHBOARD_AUTH`
- restringir DNS solo al dominio real que usarás
