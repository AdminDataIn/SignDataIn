# ARCHITECTURE - DataIn Sign

Documento de arquitectura del servicio de firma digital de DataIn.

## Foco actual

El producto actual se concentra en una operacion de firma digital profesional:

- recepcion de PDF final
- creacion de solicitud
- envio a proveedor
- recepcion de webhook
- trazabilidad y auditoria
- descarga de documento firmado

Las referencias a integraciones previas son solo antecedente tecnico y no definen el enfoque del producto.

## Capas

### 1. Core de firma

- `signature_service/models.py`
- `signature_service/services/signature_service.py`
- `signature_service/providers/__init__.py`

Responsabilidad:

- modelar solicitudes y eventos
- hablar con ZapSign
- orquestar creacion, envio, webhook y descarga

### 2. Capa de uso

- `signature_service/application.py`
- `signature_service/forms.py`
- `signature_service/views.py`
- `signature_service/api/views.py`

Responsabilidad:

- convertir el core en UI y API usables
- compartir flujo entre browser y API
- mantener el core sin duplicacion de logica

### 3. Proyecto host standalone

- `manage.py`
- `config/settings.py`
- `config/urls.py`
- `config/wsgi.py`
- `config/asgi.py`

Responsabilidad:

- ejecutar la app como producto independiente
- configurar static, media, base de datos y seguridad
- permitir despliegue en subdominio de DataIn

## Flujo principal

1. usuario carga un PDF final
2. se crea `SignatureRequest` en estado `CREATED`
3. el operador envia a firma
4. `SignatureService` crea documento en ZapSign
5. la solicitud pasa a `PENDING`
6. ZapSign envia webhook
7. se registra `SignatureEventLog`
8. la solicitud pasa a `SIGNED` o `REFUSED`
9. el operador descarga el PDF firmado

## Decision de producto de esta fase

No se incluyo una capa de plantillas dinamicas en esta version.

Motivo:

- abre otro producto distinto al de firma
- exige modelado de plantillas, variables y versionado
- introduce necesidades de render, validacion y previsualizacion
- aumenta el riesgo funcional antes de cerrar bien el flujo core

## Expansion natural a futuro

Si DataIn decide elevar el producto, la expansion correcta seria:

1. `DocumentTemplate`
2. `DocumentTemplateVersion`
3. `TemplateVariable`
4. `RenderedDocument`
5. integracion con `SignatureRequest`

Eso debe entrar como una fase nueva, no como complejidad mezclada dentro del flujo actual.
