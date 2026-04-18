# Reporte Historico de Evolucion

Este documento queda como referencia breve del cambio de modulo tecnico a producto usable.

## Resultado actual

`signature_service` ya no se presenta como una extraccion orientada a otro sistema, sino como servicio independiente de DataIn.

## Lo que hoy existe

- proyecto Django standalone
- UI operativa para solicitudes de firma
- API funcional conectada al service real
- webhook ZapSign cableado
- guia de despliegue para VPS con Nginx, Gunicorn y systemd
- documentacion de pruebas manuales

## Documentos principales

- `signature_service/README.md`
- `signature_service/ARCHITECTURE.md`
- `signature_service/MANUAL_TESTING.md`
- `DEPLOYMENT.md`

## Nota

El origen tecnico del modulo es parte de la historia del repositorio, pero no del posicionamiento actual del producto.
