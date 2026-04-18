"""
Servicio principal de firma digital.
Orquesta la interacción entre proveedores y modelos de datos.
"""

import logging
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path

from django.utils import timezone
from django.db import transaction
from django.core.files.base import ContentFile

from signature_service.models import SignatureRequest, SignatureEventLog
from signature_service.providers import ZapSignProvider, ZapSignProviderError
from signature_service.services.document_url_service import (
    generate_temporary_url,
    validate_and_extract_document_id,
    DocumentURLError
)

logger = logging.getLogger('signature_service')


class SignatureServiceError(Exception):
    """Error en el servicio de firma"""
    pass


class SignatureService:
    """
    Servicio genérico de firma digital.
    
    Proporciona:
    - Crear solicitudes de firma
    - Enviar documentos a proveedores
    - Procesar webhooks
    - Descargar documentos firmados
    - Auditoría y trazabilidad
    
    Independiente de dominio de negocio - puede ser usado en múltiples contextos.
    """
    
    def __init__(self, provider: str = 'zapsign'):
        """
        Inicializa el servicio.
        
        Args:
            provider: 'zapsign' (default), otro provider puede ser soportado en futuro
        """
        self.provider = provider
        
        if provider == 'zapsign':
            self.provider_client = ZapSignProvider()
        else:
            raise SignatureServiceError(f"Proveedor no soportado: {provider}")
    
    def create_signature_request(
        self,
        document_name: str,
        document_url: str,
        document_file,  # Django FileField
        signer_name: str,
        signer_email: str,
        external_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        created_by=None
    ) -> SignatureRequest:
        """
        Crea una nueva solicitud de firma.
        
        Args:
            document_name: Nombre del documento (ej: "Contrato")
            document_url: URL pública donde ZapSign puede descargar el PDF
            document_file: Archivo FileField del documento
            signer_name: Nombre completo del firmante
            signer_email: Email del firmante
            external_id: ID externo de referencia (ej: credito_id)
            metadata: Datos adicionales específicos del cliente
            created_by: Usuario que crea la solicitud
        
        Returns:
            SignatureRequest: Instancia creada (estado CREATED)
        """
        
        try:
            signature_request = SignatureRequest.objects.create(
                document_name=document_name,
                document_url=document_url,
                document_file=document_file,
                signer_name=signer_name,
                signer_email=signer_email,
                external_id=external_id or '',
                provider=self.provider,
                metadata=metadata or {},
                created_by=created_by,
                status=SignatureRequest.SignatureStatus.CREATED
            )
            
            logger.info(
                f"[SignatureService] Solicitud de firma creada: {signature_request.id} "
                f"({external_id or 'sin_id_externo'})"
            )
            
            return signature_request
        
        except Exception as e:
            logger.error(f"[SignatureService] Error creando solicitud: {str(e)}")
            raise SignatureServiceError(f"Error creando solicitud: {str(e)}")
    
    def send_for_signature(
        self,
        signature_request: SignatureRequest,
        brand_name: str = "DataIn Signature Service"
    ) -> SignatureRequest:
        """
        Envía una solicitud al proveedor de firma.
        
        Args:
            signature_request: Solicitud a enviar
            brand_name: Nombre de la marca/empresa que aparecerá en ZapSign
        
        Returns:
            SignatureRequest: Actualizada con datos del proveedor
        
        Raises:
            SignatureServiceError: Si hay error al enviar
        """
        
        if signature_request.status != SignatureRequest.SignatureStatus.CREATED:
            raise SignatureServiceError(
                f"Solicitud debe estar en CREATED, está en {signature_request.status}"
            )
        
        try:
            # Enviar a proveedor
            response = self.provider_client.create_document(
                document_name=signature_request.document_name,
                document_url=signature_request.document_url,
                signer_email=signature_request.signer_email,
                signer_name=signature_request.signer_name,
                brand_name=brand_name
            )
            
            # Actualizar solicitud con respuesta
            signature_request.provider_document_id = response['token']
            signature_request.provider_sign_url = response['signers'][0].get('sign_url')
            signature_request.status = SignatureRequest.SignatureStatus.PENDING
            signature_request.sent_at = timezone.now()
            signature_request.save()
            
            logger.info(
                f"[SignatureService] Enviado al proveedor: {signature_request.id} "
                f"→ {signature_request.provider_document_id}"
            )
            
            return signature_request
        
        except ZapSignProviderError as e:
            logger.error(f"[SignatureService] Error del proveedor: {str(e)}")
            raise SignatureServiceError(f"Error del proveedor: {str(e)}")
        
        except Exception as e:
            logger.error(f"[SignatureService] Error inesperado: {str(e)}")
            raise SignatureServiceError(f"Error inesperado: {str(e)}")
    
    def process_webhook(
        self,
        payload: Dict,
        headers: Dict,
        ip_address: str
    ) -> Optional[SignatureRequest]:
        """
        Procesa un webhook del proveedor de firma.
        
        Args:
            payload: Payload JSON del webhook
            headers: Headers HTTP del webhook
            ip_address: IP que envió el webhook
        
        Returns:
            SignatureRequest: Si fue procesado exitosamente, None si fue ignorado
        """
        
        doc_token = ZapSignProvider.extract_document_token(payload)
        event_type = ZapSignProvider.extract_event_type(payload)
        
        # 1. Registrar evento en auditoría ANTES de procesar (idempotencia)
        with transaction.atomic():
            event_log = SignatureEventLog.objects.create(
                provider_event_type=event_type,
                event_type=SignatureEventLog.EventType.WEBHOOK_RECEIVED,
                payload=payload,
                http_headers=dict(headers),
                http_ip_address=ip_address,
                signature_valid=False,
                processed=False
            )
            
            # 2. Validar firma del webhook
            secret = getattr(settings, 'ZAPSIGN_WEBHOOK_SECRET', '')
            header_name = getattr(settings, 'ZAPSIGN_WEBHOOK_HEADER', 'X-ZapSign-Secret')
            
            is_valid = ZapSignProvider.validate_webhook_signature(
                payload,
                headers,
                secret=secret,
                header_name=header_name
            )
            
            event_log.signature_valid = is_valid
            event_log.save(update_fields=['signature_valid'])
            
            if not is_valid:
                logger.warning(f"[Webhook] Firma inválida en webhook de {ip_address}")
                return None
            
            # 3. Encontrar solicitud
            if not doc_token:
                event_log.processing_error = "No hay document token en payload"
                event_log.save(update_fields=['processing_error'])
                logger.warning("[Webhook] No hay document token")
                return None
            
            try:
                signature_request = SignatureRequest.objects.get(
                    provider_document_id=doc_token
                )
            except SignatureRequest.DoesNotExist:
                event_log.processing_error = f"Document token no encontrado: {doc_token}"
                event_log.save(update_fields=['processing_error'])
                logger.warning(f"[Webhook] Document token desconocido: {doc_token}")
                return None
            
            # Asociar evento a solicitud
            event_log.signature_request = signature_request
            event_log.save(update_fields=['signature_request'])
            
            # 4. Procesar acción según el evento
            status = payload.get('status', '')
            action = ZapSignProvider.normalize_status_to_event(event_type, status)
            
            if action == 'signed':
                return self._handle_signed_webhook(signature_request, payload, event_log)
            
            elif action == 'refused':
                return self._handle_refused_webhook(signature_request, payload, event_log)
            
            else:
                event_log.processed = True
                event_log.processing_error = f"Evento desconocido: {action}"
                event_log.save(update_fields=['processed', 'processing_error'])
                logger.debug(f"[Webhook] Evento {action} registrado pero no procesado")
                return None
    
    def _handle_signed_webhook(
        self,
        signature_request: SignatureRequest,
        payload: Dict,
        event_log: SignatureEventLog
    ) -> SignatureRequest:
        """Procesa webhook de documento firmado"""
        
        # Verificar idempotencia
        if signature_request.status == SignatureRequest.SignatureStatus.SIGNED:
            event_log.processed = True
            event_log.save(update_fields=['processed'])
            logger.info(f"[Webhook] Solicitud {signature_request.id} ya fue firmada (idempotencia)")
            return signature_request
        
        # Actualizar solicitud
        signature_request.status = SignatureRequest.SignatureStatus.SIGNED
        signature_request.signed_at = timezone.now()
        signature_request.provider_status = payload.get('status')
        signature_request.provider_signed_document_url = (
            payload.get('signed_file_url') or payload.get('signed_file')
        )
        
        # Extraer IP del firmante si está disponible
        signers = payload.get('signers') or []
        if signers:
            signer = signers[0]
            signature_request.signer_ip = signer.get('ip') or signer.get('ip_address')
        
        # Guardar payload completo como evidencia
        signature_request.provider_webhook_payload = payload
        signature_request.save()
        
        # Marcar evento como procesado
        event_log.event_type = SignatureEventLog.EventType.DOCUMENT_SIGNED
        event_log.processed = True
        event_log.processed_at = timezone.now()
        event_log.save(update_fields=['event_type', 'processed', 'processed_at'])
        
        logger.info(
            f"[Webhook] Documento firmado: {signature_request.id} "
            f"({signature_request.signer_email})"
        )
        
        return signature_request
    
    def _handle_refused_webhook(
        self,
        signature_request: SignatureRequest,
        payload: Dict,
        event_log: SignatureEventLog
    ) -> SignatureRequest:
        """Procesa webhook de documento rechazado"""
        
        signature_request.status = SignatureRequest.SignatureStatus.REFUSED
        signature_request.refused_at = timezone.now()
        signature_request.provider_status = payload.get('status')
        signature_request.provider_webhook_payload = payload
        signature_request.save()
        
        event_log.event_type = SignatureEventLog.EventType.DOCUMENT_REFUSED
        event_log.processed = True
        event_log.processed_at = timezone.now()
        event_log.save(update_fields=['event_type', 'processed', 'processed_at'])
        
        logger.info(
            f"[Webhook] Documento rechazado: {signature_request.id} "
            f"({signature_request.signer_email})"
        )
        
        return signature_request
    
    def download_signed_document(
        self,
        signature_request: SignatureRequest
    ) -> Optional[bytes]:
        """
        Descarga el documento firmado del proveedor.
        
        Args:
            signature_request: Solicitud con documento firmado
        
        Returns:
            bytes: Contenido del PDF firmado
        """
        
        if signature_request.status != SignatureRequest.SignatureStatus.SIGNED:
            raise SignatureServiceError(
                f"Documento no está firmado (estado: {signature_request.status})"
            )
        
        if not signature_request.provider_document_id:
            raise SignatureServiceError("No hay document_id del proveedor")

        if signature_request.signed_document_file:
            try:
                with signature_request.signed_document_file.open("rb") as signed_file:
                    content = signed_file.read()
                if content:
                    logger.info(
                        f"[SignatureService] Documento firmado servido desde almacenamiento local: "
                        f"{signature_request.id}"
                    )
                    return content
            except Exception as e:
                logger.warning(
                    f"[SignatureService] No se pudo leer copia local firmada para "
                    f"{signature_request.id}: {str(e)}"
                )
        
        try:
            pdf_bytes = self.provider_client.download_signed_document(
                signature_request.provider_document_id,
                signed_file_url=signature_request.provider_signed_document_url,
            )

            filename = f"{Path(signature_request.document_name).stem}_signed.pdf"
            signature_request.signed_document_file.save(
                filename,
                ContentFile(pdf_bytes),
                save=True,
            )
            
            logger.info(
                f"[SignatureService] Documento descargado: {signature_request.id} "
                f"({len(pdf_bytes)} bytes)"
            )
            
            return pdf_bytes
        
        except ZapSignProviderError as e:
            logger.error(f"[SignatureService] Error descargando: {str(e)}")
            raise SignatureServiceError(f"Error descargando documento: {str(e)}")

    def sync_status(self, signature_request: SignatureRequest) -> SignatureRequest:
        """
        Sincroniza el estado local consultando el documento en ZapSign.

        Se usa como fallback cuando el webhook no llegó, fue rechazado o llegó tarde.
        """
        if not signature_request.provider_document_id:
            return signature_request

        if signature_request.status in {
            SignatureRequest.SignatureStatus.SIGNED,
            SignatureRequest.SignatureStatus.REFUSED,
            SignatureRequest.SignatureStatus.CANCELLED,
            SignatureRequest.SignatureStatus.EXPIRED,
        }:
            return signature_request

        try:
            payload = self.provider_client.get_document_status(signature_request.provider_document_id)
        except ZapSignProviderError as e:
            logger.warning(
                f"[SignatureService] No fue posible sincronizar {signature_request.id}: {str(e)}"
            )
            return signature_request

        provider_status = payload.get("status") or ""
        action = ZapSignProvider.normalize_status_to_event(
            payload.get("event_type", ""),
            provider_status,
        )

        update_fields = []
        if signature_request.provider_status != provider_status:
            signature_request.provider_status = provider_status
            update_fields.append("provider_status")

        if payload.get("signed_file") or payload.get("signed_file_url"):
            signed_document_url = payload.get("signed_file") or payload.get("signed_file_url")
            if signature_request.provider_signed_document_url != signed_document_url:
                signature_request.provider_signed_document_url = signed_document_url
                update_fields.append("provider_signed_document_url")

        signer_ip = self._extract_signer_ip(payload)
        if signer_ip and signature_request.signer_ip != signer_ip:
            signature_request.signer_ip = signer_ip
            update_fields.append("signer_ip")

        if action == "signed":
            if signature_request.status != SignatureRequest.SignatureStatus.SIGNED:
                signature_request.status = SignatureRequest.SignatureStatus.SIGNED
                update_fields.append("status")
            signed_at = self._parse_provider_datetime(payload.get("signed_at"))
            if signed_at and signature_request.signed_at != signed_at:
                signature_request.signed_at = signed_at
                update_fields.append("signed_at")
        elif action == "refused":
            if signature_request.status != SignatureRequest.SignatureStatus.REFUSED:
                signature_request.status = SignatureRequest.SignatureStatus.REFUSED
                update_fields.append("status")
            refused_at = self._parse_provider_datetime(
                payload.get("refused_at") or payload.get("updated_at")
            )
            if refused_at and signature_request.refused_at != refused_at:
                signature_request.refused_at = refused_at
                update_fields.append("refused_at")

        if action in {"signed", "refused"}:
            signature_request.provider_webhook_payload = payload
            update_fields.append("provider_webhook_payload")

        if update_fields:
            signature_request.save(update_fields=list(dict.fromkeys(update_fields)))
            logger.info(
                f"[SignatureService] Estado sincronizado desde ZapSign: "
                f"{signature_request.id} -> {signature_request.status}"
            )

        return signature_request

    @staticmethod
    def _extract_signer_ip(payload: Dict) -> Optional[str]:
        signers = payload.get("signers") or []
        if not signers:
            return None
        signer = signers[0] or {}
        return signer.get("ip") or signer.get("ip_address")

    @staticmethod
    def _parse_provider_datetime(value: Optional[str]):
        if not value:
            return None
        raw_value = value.strip()
        if not raw_value:
            return None
        try:
            parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        except ValueError:
            return timezone.now()
        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed


# Importar settings aquí para evitar circular imports
from django.conf import settings
