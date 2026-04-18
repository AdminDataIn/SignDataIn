# Guia de Integracion - DataIn Sign

Esta guia describe el uso de `signature_service` como servicio independiente de DataIn.

## Modo recomendado

Ejecutar el proyecto standalone de este repositorio.

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

## URLs principales

- UI: `/signatures/`
- API: `/api/signatures/`
- webhook: `/api/webhooks/signatures/`
- health: `/health/`

## Variables minimas

```env
DJANGO_SECRET_KEY=change-this-secret
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=sign.datain.pro
DJANGO_CSRF_TRUSTED_ORIGINS=https://sign.datain.pro
APP_DOMAIN=sign.datain.pro
APP_USE_HTTPS=True
DATABASE_URL=postgresql://signature_user:strong-password@127.0.0.1:5432/signature_service
ZAPSIGN_API_TOKEN=your-token
ZAPSIGN_ENVIRONMENT=sandbox
ZAPSIGN_WEBHOOK_SECRET=your-secret
ZAPSIGN_WEBHOOK_HEADER=X-ZapSign-Secret
```

## Integracion operativa

### UI

- crear solicitud en `/signatures/create/`
- enviar a firma desde el detalle
- descargar documento firmado cuando quede en `SIGNED`

### API

- `POST /api/signatures/`
- `GET /api/signatures/`
- `GET /api/signatures/<uuid>/`
- `POST /api/signatures/<uuid>/send/`
- `GET /api/signatures/<uuid>/download/`
- `POST /api/webhooks/signatures/`

## Notas

- el foco principal es DataIn como producto independiente
- cualquier adaptador legado se conserva solo como referencia tecnica
- para despliegue usar `DEPLOYMENT.md`
- para pruebas manuales usar `MANUAL_TESTING.md`
