"""
Signature Service - servicio reutilizable de firma digital para DataIn.

El modulo soporta la aplicacion standalone de DataIn y mantiene una integracion
limpia con proveedores de firma digital como ZapSign.
"""

__version__ = '0.1.0'
__author__ = 'DataIn'
__license__ = 'Proprietary'

__all__ = [
    'SignatureService',
]


def __getattr__(name):
    if name == 'SignatureService':
        from .services.signature_service import SignatureService
        return SignatureService
    raise AttributeError(f"module 'signature_service' has no attribute {name!r}")
