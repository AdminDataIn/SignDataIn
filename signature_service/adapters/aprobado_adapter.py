"""
Adaptador entre el model Pagare de Aprobado y el signature_service genérico.

Este adaptador permite que Aprobado continúe usando los modelos específicos (Pagare, Credito)
mientras utiliza la integración genérica de SignatureService y ZapSign.

Patrón: Adapter/Bridge - traduce entre dos interfaces incompatibles.
"""

import logging
import hashlib
from typing import Optional
from django.utils import timezone
from django.core.files.base import ContentFile

from signature_service.models import SignatureRequest
from signature_service.services import SignatureService
from gestion_creditos.models import Pagare, Credito

logger = logging.getLogger('zapsign')


class AprobadoSignatureAdapter:
    """
    Adaptador que traduce entre:
    - Pagare (modelo específico de Aprobado)
    - SignatureRequest (modelo genérico de signature_service)
    """
    
    def __init__(self):
        """Inicializa el adaptador"""
        self.service = SignatureService(provider='zapsign')
    
    def create_signature_request_for_pagare(
        self,
        pagare: Pagare,
        document_url: str
    ) -> SignatureRequest:
        """
        Crea una SignatureRequest a partir de un Pagare.
        
        Args:
            pagare: Instancia del modelo Pagare
            document_url: URL pública del PDF
        
        Returns:
            SignatureRequest: Creada y lista para enviar
        """
        
        credito = pagare.credito
        usuario = credito.usuario
        
        # Extraer datos del firmante según el tipo de crédito
        signer_name, signer_email = self._extract_signer_info(credito)
        
        # Crear metadata con información de Aprobado
        metadata = {
            'aprobado_credito_id': credito.id,
            'aprobado_numero_credito': credito.numero_credito,
            'aprobado_linea': credito.linea,
            'aprobado_monto': str(credito.monto_aprobado or 0),
        }
        
        # Crear solicitud genérica
        signature_request = self.service.create_signature_request(
            document_name=f"Pagaré {credito.numero_credito}",
            document_url=document_url,
            document_file=pagare.archivo_pdf,
            signer_name=signer_name,
            signer_email=signer_email,
            external_id=str(pagare.id),
            metadata=metadata,
            created_by=pagare.creado_por
        )
        
        return signature_request
    
    def send_pagare_to_zapsign(
        self,
        pagare: Pagare,
        document_url: str,
        brand_name: str = "Aprobado"
    ) -> Pagare:
        """
        Envía un pagaré a ZapSign usando el servicio genérico.
        
        Actualiza Pagare con datos de ZapSign (el modelo antiguo).
        
        Args:
            pagare: Pagaré a enviar
            document_url: URL pública del PDF
            brand_name: Nombre de la marca en ZapSign
        
        Returns:
            Pagare: Actualizado con datos de ZapSign
        """
        
        # Crear solicitud genérica
        signature_request = self.create_signature_request_for_pagare(pagare, document_url)
        
        # Enviar a proveedor
        signature_request = self.service.send_for_signature(
            signature_request,
            brand_name=brand_name
        )
        
        # Copiar datos a Pagare (para mantener compatibilidad)
        pagare.zapsign_doc_token = signature_request.provider_document_id
        pagare.zapsign_sign_url = signature_request.provider_sign_url
        pagare.estado = Pagare.EstadoPagare.SENT
        pagare.fecha_envio = timezone.now()
        pagare.save()
        
        logger.info(
            f"[Adapter] Pagaré {pagare.numero_pagare} enviado a ZapSign "
            f"(signature_request={signature_request.id})"
        )
        
        return pagare
    
    def process_zapsign_webhook_for_pagare(
        self,
        payload: dict,
        headers: dict,
        ip_address: str
    ) -> Optional[Pagare]:
        """
        Procesa un webhook de ZapSign y actualiza el Pagare correspondiente.
        
        Flujo:
        1. Procesa webhook genéricamente
        2. Encuentra el Pagare por token de ZapSign
        3. Actualiza Pagare y Credito
        
        Args:
            payload: Payload del webhook
            headers: Headers del webhook
            ip_address: IP que envió el webhook
        
        Returns:
            Pagare: Actualizado, None si no se procesó
        """
        
        # Procesar genéricamente
        signature_request = self.service.process_webhook(
            payload,
            headers,
            ip_address
        )
        
        if not signature_request:
            return None
        
        # Encontrar Pagare correspondiente
        try:
            pagare = Pagare.objects.get(id=signature_request.external_id)
        except (Pagare.DoesNotExist, ValueError):
            logger.warning(
                f"[Adapter] No se encontró Pagare para signature_request {signature_request.id}"
            )
            return None
        
        # Actualizar Pagare según el estado de SignatureRequest
        if signature_request.status == SignatureRequest.SignatureStatus.SIGNED:
            pagare.estado = Pagare.EstadoPagare.SIGNED
            pagare.fecha_firma = signature_request.signed_at
            pagare.zapsign_status = signature_request.provider_status
            pagare.zapsign_signed_file_url = signature_request.provider_signed_document_url
            pagare.ip_firmante = signature_request.signer_ip
            pagare.evidencias = signature_request.provider_webhook_payload
            pagare.save()
            
            logger.info(f"[Adapter] Pagaré {pagare.numero_pagare} marcado como SIGNED")
        
        elif signature_request.status == SignatureRequest.SignatureStatus.REFUSED:
            pagare.estado = Pagare.EstadoPagare.REFUSED
            pagare.fecha_rechazo = signature_request.refused_at
            pagare.zapsign_status = signature_request.provider_status
            pagare.evidencias = signature_request.provider_webhook_payload
            pagare.save()
            
            logger.info(f"[Adapter] Pagaré {pagare.numero_pagare} marcado como REFUSED")
        
        return pagare
    
    def download_and_save_signed_pagare(self, pagare: Pagare) -> bool:
        """
        Descarga el PDF firmado de ZapSign y lo guarda en el Pagare.
        
        Args:
            pagare: Pagaré cuyo PDF descargar
        
        Returns:
            bool: True si se guardó exitosamente, False si no
        """
        
        # Buscar SignatureRequest
        try:
            signature_request = SignatureRequest.objects.get(
                external_id=str(pagare.id)
            )
        except SignatureRequest.DoesNotExist:
            logger.warning(f"[Adapter] No se encontró SignatureRequest para Pagare {pagare.numero_pagare}")
            return False
        
        try:
            # Descargar
            pdf_bytes = self.service.download_signed_document(signature_request)
            
            if not pdf_bytes:
                return False
            
            # Guardar en Pagare
            filename = f"{pagare.numero_pagare}_firmado.pdf"
            pagare.archivo_pdf_firmado.save(filename, ContentFile(pdf_bytes), save=True)
            
            logger.info(f"[Adapter] PDF firmado guardado para {pagare.numero_pagare}")
            return True
        
        except Exception as e:
            logger.error(f"[Adapter] Error descargando PDF firmado: {str(e)}")
            return False
    
    @staticmethod
    def _extract_signer_info(credito: Credito) -> tuple:
        """
        Extrae nombre y email del firmante según el tipo de crédito.
        
        Args:
            credito: Crédito del cual extraer información
        
        Returns:
            tuple: (nombre_firmante, email_firmante)
        """
        
        usuario = credito.usuario
        detalle = credito.detalle
        
        if not detalle:
            # Fallback
            nombre = f"{usuario.first_name} {usuario.last_name}".strip() or usuario.username
            email = usuario.email
            return nombre, email
        
        if credito.linea == Credito.LineaCredito.LIBRANZA:
            nombre = detalle.nombre_completo or f"{usuario.first_name} {usuario.last_name}".strip() or usuario.username
            email = detalle.correo_electronico or usuario.email
        
        elif credito.linea == Credito.LineaCredito.ADELANTO_NOMINA:
            vinculo = detalle.vinculo_laboral
            nombre = vinculo.nombre_empleado or f"{usuario.first_name} {usuario.last_name}".strip() or usuario.username
            email = vinculo.correo_empleado or usuario.email
        
        else:  # EMPRENDIMIENTO
            nombre = detalle.nombre or f"{usuario.first_name} {usuario.last_name}".strip() or usuario.username
            email = usuario.email
        
        return nombre, email
