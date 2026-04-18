"""
Configuración de Django App para signature_service.
"""

from django.apps import AppConfig


class SignatureServiceConfig(AppConfig):
    """Configuración de la aplicación de firma digital"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'signature_service'
    verbose_name = 'Servicio de Firma Digital'
    
    def ready(self):
        """Inicialización de la aplicación"""
        # Se puede usar para setup de signals, loggers, etc.
        import logging
        logger = logging.getLogger('signature_service')
        logger.debug("Inicializando signature_service")
