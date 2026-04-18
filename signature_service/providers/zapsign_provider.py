"""
Proveedores de firma digital.
"""

from .zapsign_provider import ZapSignProvider, ZapSignProviderError

__all__ = [
    'ZapSignProvider',
    'ZapSignProviderError',
]
