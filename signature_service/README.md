# Signature Service - DataIn Sign

Servicio de firma digital orientado a DataIn, pensado para correr como aplicacion Django independiente con UI, API y webhook productivo.

## Enfoque del producto

- operacion de firma digital profesional para DataIn
- despliegue standalone en subdominio como `sign.datain.pro`
- experiencia B2B sobria para equipos operativos
- integracion actual con ZapSign

## Alcance actual

Esta version se enfoca en cerrar muy bien el flujo de firma:

- crear solicitud de firma
- enviar a proveedor
- recibir webhook
- actualizar estado
- descargar PDF firmado

No incluye por ahora una capa de plantillas o documentos dinamicos. Esa capacidad tiene sentido como siguiente fase, pero requiere modelado, versionado, render de variables y controles de negocio propios. En esta fase el criterio correcto es consolidar la experiencia de firma, trazabilidad y despliegue.

## Origen tecnico

El modulo nacio a partir de una extraccion tecnica previa, pero hoy su narrativa y uso principal estan orientados a DataIn como servicio independiente. Cualquier referencia a integraciones historicas debe leerse solo como antecedente tecnico.

## Capa disponible

- UI en `/signatures/`
- API en `/api/signatures/`
- webhook en `/api/webhooks/signatures/`
- health check en `/health/`
- tests automatizados del flujo principal

## Endpoints principales

- `GET /signatures/`
- `GET|POST /signatures/create/`
- `GET|POST /signatures/<uuid>/`
- `GET|POST /api/signatures/`
- `GET /api/signatures/<uuid>/`
- `POST /api/signatures/<uuid>/send/`
- `GET /api/signatures/<uuid>/download/`
- `POST /api/webhooks/signatures/`

## Estructura relevante

```text
signature_service/
├── api/                  # endpoints HTTP
├── providers/            # cliente ZapSign
├── services/             # orquestacion del flujo
├── templates/            # UI Django
├── tests/                # pruebas de API, UI y proyecto
├── application.py        # capa de uso compartida
├── forms.py              # formularios
├── models.py             # SignatureRequest y SignatureEventLog
├── urls.py               # urls de la app
└── views.py              # vistas UI
```

## Ejecucion

Desde la raiz del proyecto standalone:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

## Documentacion operativa

- despliegue VPS: `DEPLOYMENT.md`
- pruebas manuales: `signature_service/MANUAL_TESTING.md`
- configuracion del proyecto host: `config/settings.py`

## Roadmap razonable

Siguiente fase con sentido practico:

- plantillas base versionadas
- variables de documento
- render de documento final antes de firma
- multiples firmantes
- panel administrativo con filtros avanzados

Licencia interna de DataIn.
