"""
Servicio para generar URLs públicas temporales firmadas.
Usado para proporcionar acceso público a documentos sin exposición directa de almacenamiento.
"""

from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
from django.http import FileResponse, HttpRequest, JsonResponse
from django.conf import settings
import logging

logger = logging.getLogger('signature_service')


class DocumentURLError(Exception):
    """Error en generación o validación de URL"""
    pass


def generate_temporary_url(
    document_id: str,
    max_age: int = 86400,
    base_path: str = '/api/signatures/download/'
) -> str:
    """
    Genera una URL firmada y timestamped para acceso temporal a un documento.
    
    Args:
        document_id: ID único del documento
        max_age: Tiempo de validez en segundos (default: 24 horas)
        base_path: Ruta base del endpoint de descarga
    
    Returns:
        str: URL completa firmada
    
    Example:
        >>> url = generate_temporary_url('sig-req-123')
        >>> print(url)
        'https://example.com/api/signatures/download/MQ:1qfYnR:...'
    """
    signer = TimestampSigner()
    
    # Crear token con formato "id:max_age"
    token = signer.sign(f"{document_id}:{max_age}")
    
    # Construir URL
    domain = getattr(settings, 'SITE_DOMAIN', 'localhost:8000')
    protocol = 'https' if getattr(settings, 'SITE_HTTPS', False) else 'http'
    
    url = f"{protocol}://{domain}{base_path}{token}/"
    
    logger.debug(f"[DocumentURL] Token generado para {document_id} (válido {max_age}s)")
    
    return url


def validate_and_extract_document_id(
    token: str,
    max_age: int = 86400
) -> str:
    """
    Valida un token firmado y extrae el ID del documento.
    
    Args:
        token: Token firmado
        max_age: Tiempo máximo de validez en segundos
    
    Returns:
        str: ID del documento
    
    Raises:
        DocumentURLError: Si el token es inválido o ha expirado
    """
    signer = TimestampSigner()
    
    try:
        # Extraer y validar
        unsigned = signer.unsign(token, max_age=max_age)
        
        if ":" not in unsigned:
            raise DocumentURLError("Formato de token inválido")
        
        document_id_str, max_age_str = unsigned.split(":", 1)
        
        try:
            stored_max_age = int(max_age_str)
        except ValueError:
            raise DocumentURLError("Max age inválido en token")
        
        logger.debug(f"[DocumentURL] Token válido para documento {document_id_str}")
        return document_id_str
    
    except SignatureExpired:
        logger.warning(f"[DocumentURL] Token expirado")
        raise DocumentURLError("El enlace ha expirado. Por favor, solicite uno nuevo.")
    
    except BadSignature:
        logger.warning(f"[DocumentURL] Firma inválida")
        raise DocumentURLError("Enlace inválido o alterado")
    
    except Exception as e:
        logger.error(f"[DocumentURL] Error validando token: {str(e)}")
        raise DocumentURLError(f"Error validando enlace: {str(e)}")
