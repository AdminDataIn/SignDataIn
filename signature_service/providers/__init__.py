"""
Proveedor ZapSign para firma digital.
Mantiene compatibilidad con la API de ZapSign pero desacoplada del dominio de negocio.
"""

import requests
import logging
from typing import Dict, Optional, Tuple
from django.conf import settings

logger = logging.getLogger('signature_service')


class ZapSignProviderError(Exception):
    """Excepción base para errores del proveedor ZapSign"""
    pass


def _to_bool(value, default=False):
    """
    Convierte valores de settings a bool de forma robusta.
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "t", "yes", "y", "si", "sí", "on"}:
            return True
        if normalized in {"0", "false", "f", "no", "n", "off"}:
            return False
    return default


class ZapSignProvider:
    """
    Cliente genérico para interactuar con la API de ZapSign.
    
    Proporciona:
    - Crear documentos para firma
    - Consultar estado
    - Descargar documentos firmados
    - Validación de webhooks
    """
    
    PROVIDER_NAME = 'zapsign'
    
    def __init__(self):
        """Inicializa el cliente con credenciales de settings"""
        self.api_token = getattr(settings, 'ZAPSIGN_API_TOKEN', '')
        self.environment = getattr(settings, 'ZAPSIGN_ENVIRONMENT', 'sandbox')
        
        self.base_url = "https://api.zapsign.com.br/api/v1"
        if self.environment == 'sandbox':
            self.base_url = "https://sandbox.api.zapsign.com.br/api/v1"
        
        if not self.api_token:
            raise ZapSignProviderError("ZAPSIGN_API_TOKEN no está configurado en settings")
    
    def _get_headers(self) -> Dict[str, str]:
        """Retorna los headers necesarios para las peticiones"""
        return {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
    
    def create_document(
        self,
        document_name: str,
        document_url: str,
        signer_email: str,
        signer_name: str,
        brand_name: str = "DataIn Signature Service",
        language: str = "es"
    ) -> Dict:
        """
        Crea un documento en ZapSign para firma.
        
        Args:
            document_name: Nombre del documento (ej: "Contrato 2026")
            document_url: URL pública del PDF a firmar
            signer_email: Email del firmante
            signer_name: Nombre completo del firmante
            brand_name: Nombre de la marca/empresa
            language: Idioma (es, pt, en)
        
        Returns:
            Dict con la respuesta de ZapSign:
            {
                "token": "uuid",
                "signers": [{"sign_url": "https://..."}]
            }
        
        Raises:
            ZapSignProviderError: Si la API retorna error
        """
        endpoint = f"{self.base_url}/docs/"
        
        auth_mode = (getattr(settings, 'ZAPSIGN_AUTH_MODE', None) or 'assinaturaTela').strip()
        send_automatic_email = _to_bool(
            getattr(settings, 'ZAPSIGN_SEND_AUTOMATIC_EMAIL', True),
            default=True
        )
        enable_selfie_validation = _to_bool(
            getattr(settings, 'ZAPSIGN_ENABLE_SELFIE_VALIDATION', False),
            default=False
        )
        selfie_validation_type = getattr(
            settings,
            'ZAPSIGN_SELFIE_VALIDATION_TYPE',
            'identity-verification'
        )
        
        signer_payload = {
            "email": signer_email,
            "name": signer_name,
            "auth_mode": auth_mode,
            "send_automatic_email": send_automatic_email,
            "send_automatic_whatsapp": False,
        }
        
        if enable_selfie_validation:
            signer_payload["require_selfie_photo"] = True
            if selfie_validation_type:
                signer_payload["selfie_validation_type"] = selfie_validation_type
        
        payload = {
            "name": document_name,
            "url_pdf": document_url,
            "signers": [signer_payload],
            "brand_name": brand_name,
            "lang": language
        }
        
        try:
            logger.info(f"[ZapSign] Creando documento: {document_name}")
            
            response = requests.post(
                endpoint,
                json=payload,
                headers=self._get_headers(),
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"[ZapSign] Documento creado. Token: {data.get('token')}")
            return data
        
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.error(f"[ZapSign] Error al crear documento: {error_msg}")
            raise ZapSignProviderError(error_msg)
        
        except requests.exceptions.RequestException as e:
            error_msg = f"Error de conexión: {str(e)}"
            logger.error(f"[ZapSign] Error de conexión: {error_msg}")
            raise ZapSignProviderError(error_msg)
    
    def get_document_status(self, document_token: str) -> Dict:
        """
        Consulta el estado de un documento.
        
        Args:
            document_token: Token del documento en ZapSign
        
        Returns:
            Dict con estado:
            {
                "token": "uuid",
                "status": "pending|signed|refused",
                "signed_at": "ISO8601",
                "signers": [...]
            }
        """
        endpoint = f"{self.base_url}/docs/{document_token}/"
        
        try:
            logger.debug(f"[ZapSign] Consultando documento: {document_token}")
            
            response = requests.get(
                endpoint,
                headers=self._get_headers(),
                timeout=10
            )
            
            response.raise_for_status()
            data = response.json()
            
            logger.debug(f"[ZapSign] Estado: {data.get('status')}")
            return data
        
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.error(f"[ZapSign] Error al consultar: {error_msg}")
            raise ZapSignProviderError(error_msg)
        
        except requests.exceptions.RequestException as e:
            logger.error(f"[ZapSign] Error de conexión: {str(e)}")
            raise ZapSignProviderError(str(e))
    
    def _download_file_from_url(self, file_url: str) -> bytes:
        """
        Descarga un archivo desde una URL temporal entregada por ZapSign.
        """
        response = requests.get(file_url, timeout=30)
        response.raise_for_status()
        return response.content

    def download_signed_document(
        self,
        document_token: str,
        signed_file_url: Optional[str] = None,
    ) -> bytes:
        """
        Descarga el documento firmado.

        Args:
            document_token: Token del documento
            signed_file_url: URL temporal del archivo firmado si ya fue obtenida

        Returns:
            bytes: Contenido del PDF firmado
        """
        try:
            logger.info(f"[ZapSign] Descargando documento firmado: {document_token}")

            if signed_file_url:
                try:
                    content = self._download_file_from_url(signed_file_url)
                    logger.info(f"[ZapSign] PDF descargado desde signed_file_url ({len(content)} bytes)")
                    return content
                except requests.exceptions.RequestException as e:
                    logger.warning(
                        f"[ZapSign] signed_file_url expirado o inválido para {document_token}: {str(e)}"
                    )

            detail = self.get_document_status(document_token)
            fresh_signed_file_url = detail.get("signed_file") or detail.get("signed_file_url")
            if fresh_signed_file_url:
                content = self._download_file_from_url(fresh_signed_file_url)
                logger.info(
                    f"[ZapSign] PDF descargado desde detalle de documento ({len(content)} bytes)"
                )
                return content

            endpoint = f"{self.base_url}/docs/{document_token}/download-signed/"
            response = requests.get(
                endpoint,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()

            logger.info(f"[ZapSign] PDF descargado desde endpoint legado ({len(response.content)} bytes)")
            return response.content
        
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.error(f"[ZapSign] Error descargando: {error_msg}")
            raise ZapSignProviderError(error_msg)
        
        except requests.exceptions.RequestException as e:
            logger.error(f"[ZapSign] Error de conexión: {str(e)}")
            raise ZapSignProviderError(str(e))
    
    @staticmethod
    def validate_webhook_signature(
        payload: Dict,
        headers: Dict,
        secret: Optional[str] = None,
        header_name: str = 'X-ZapSign-Secret'
    ) -> bool:
        """
        Valida la firma del webhook.
        
        Args:
            payload: Payload del webhook
            headers: Headers HTTP del webhook
            secret: Secret configurado (si None, no valida)
            header_name: Nombre del header con la firma
        
        Returns:
            bool: True si válido, False si inválido
        """
        if not secret:
            # Si no hay secret configurado, aceptar sin validación
            logger.warning("[ZapSign] Webhook sin validación de firma (secret vacío)")
            return True
        
        received_secret = headers.get(header_name, '')
        
        # Soportar formato Bearer token
        if header_name.lower() == 'authorization' and received_secret.lower().startswith('bearer '):
            received_secret = received_secret[7:]
        
        is_valid = received_secret == secret
        
        if not is_valid:
            logger.warning(f"[ZapSign] Webhook con firma inválida")
        
        return is_valid
    
    @staticmethod
    def extract_document_token(payload: Dict) -> Optional[str]:
        """Extrae el token del documento del payload del webhook"""
        return payload.get('token') or payload.get('doc_token')
    
    @staticmethod
    def extract_event_type(payload: Dict) -> str:
        """Extrae el tipo de evento del webhook"""
        return payload.get('event') or payload.get('event_type') or ''
    
    @staticmethod
    def normalize_status_to_event(event_type: str, status: str) -> str:
        """
        Normaliza el status/evento a una acción estándar.
        
        Returns:
            'signed' | 'refused' | 'pending' | 'unknown'
        """
        event_lower = (event_type or '').strip().lower()
        status_lower = (status or '').strip().lower()
        
        refused_statuses = {'refused', 'recusado', 'rejected', 'cancelled', 'canceled'}
        signed_statuses = {'signed', 'assinado', 'completed', 'concluded', 'concluido'}
        
        if event_lower in {'doc_refused', 'doc_rejected'}:
            return 'refused'
        
        if status_lower in refused_statuses:
            return 'refused'
        
        if status_lower in signed_statuses:
            return 'signed'
        
        if event_lower == 'doc_signed':
            return 'signed'
        
        if event_lower == 'doc_pending':
            return 'pending'
        
        return 'unknown'
