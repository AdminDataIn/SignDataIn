# Flujo real de prueba

## Requisitos

- Django con `signature_service` en `INSTALLED_APPS`
- `include(("signature_service.urls", "signature_service"), namespace="signature_service")` montado en el `urls.py` raiz
- `requests` instalado
- variables configuradas:
  - `ZAPSIGN_API_TOKEN`
  - `ZAPSIGN_ENVIRONMENT`
  - `ZAPSIGN_WEBHOOK_SECRET`
  - `ZAPSIGN_WEBHOOK_HEADER`

## Flujo end-to-end

1. Levantar el proyecto standalone.

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

2. Crear solicitud desde UI en `http://localhost:8000/signatures/create/`.

3. Revisar en `http://localhost:8000/signatures/` que la solicitud quedo en `CREATED`.

4. Enviar a firma desde el detalle `http://localhost:8000/signatures/<uuid>/`.

5. Confirmar que el estado quedo en `PENDING` y que ya existe `provider_sign_url`.

6. Abrir `provider_sign_url` o el correo enviado por ZapSign y firmar manualmente.

7. Exponer el servidor local con `ngrok` para que ZapSign pueda invocar el webhook.

```bash
ngrok http 8000
```

8. Registrar en ZapSign el webhook publico:

```text
https://<tu-subdominio>.ngrok-free.app/api/webhooks/signatures/
```

### Importante sobre PDF fuente y ngrok

Si el documento en ZapSign queda cargando indefinidamente, valida la URL publica del PDF.

En pruebas reales, la URL del documento debe salir por una base publica controlada:

```env
SIGNATURE_PUBLIC_BASE_URL=https://tu-dominio-publico
```

Con `ngrok-free` puede ocurrir que algunos clientes externos con user-agent tipo navegador reciban una pagina HTML de advertencia en vez del PDF. En ese caso:

- el endpoint local puede responder bien
- pero ZapSign termina almacenando HTML en lugar del PDF

Para evitarlo:

- usar un dominio real en VPS
- o usar un tunel sin pagina de advertencia intermedia

9. Repetir la firma si el documento ya estaba creado sin webhook configurado.

10. Validar en el detalle que el estado pase a `SIGNED`.

11. Descargar el documento firmado desde:

```text
GET /api/signatures/<uuid>/download/
```

o usando el boton `Descargar firmado` del detalle.

## Produccion

En produccion no necesitas `ngrok`. Configura directamente en ZapSign:

```text
https://sign.datain.pro/api/webhooks/signatures/
```

Antes de habilitarlo, valida:

- `DJANGO_ALLOWED_HOSTS=sign.datain.pro`
- `DJANGO_CSRF_TRUSTED_ORIGINS=https://sign.datain.pro`
- `APP_DOMAIN=sign.datain.pro`
- `APP_USE_HTTPS=True`

## Postman

Tambien tienes una coleccion lista en:

- `postman/SignatureService.postman_collection.json`

### Crear solicitud

- Metodo: `POST`
- URL: `http://localhost:8000/api/signatures/`
- Body: `form-data`
  - `document`: archivo PDF
  - `signer_name`: nombre del firmante
  - `signer_email`: correo del firmante

### Listar solicitudes

- Metodo: `GET`
- URL: `http://localhost:8000/api/signatures/`

### Detalle

- Metodo: `GET`
- URL: `http://localhost:8000/api/signatures/<uuid>/`

### Enviar a firma

- Metodo: `POST`
- URL: `http://localhost:8000/api/signatures/<uuid>/send/`

### Descargar firmado

- Metodo: `GET`
- URL: `http://localhost:8000/api/signatures/<uuid>/download/`

### Simular webhook

- Metodo: `POST`
- URL: `http://localhost:8000/api/webhooks/signatures/`
- Headers:
  - `Content-Type: application/json`
  - `X-ZapSign-Secret: <tu-secret>`
- Body:

```json
{
  "event": "doc_signed",
  "token": "TOKEN_DEL_DOCUMENTO",
  "status": "signed",
  "signers": [
    {
      "ip": "203.0.113.10"
    }
  ]
}
```

## Validacion de logs

Configura un logger para `signature_service`:

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "signature_service": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}
```

Verifica al menos estas trazas:

- `[SignatureService] Solicitud de firma creada`
- `[SignatureService] Enviado al proveedor`
- `[Webhook] Documento firmado`
- `[SignatureService] Documento descargado`

## Que validar

- El `POST /api/signatures/` crea `SignatureRequest` y deja `document_url` publico para ZapSign.
- El `POST /api/signatures/<uuid>/send/` cambia el estado a `PENDING`.
- El webhook cambia el estado a `SIGNED` o `REFUSED`.
- El `GET /api/signatures/<uuid>/download/` descarga bytes del PDF firmado.
