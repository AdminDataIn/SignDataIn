"""
Configuración centralizada del módulo de firma digital.
DataIn puede sobrescribir estos valores en su settings.py.
"""

import os


# Proveedor de firma a usar
SIGNATURE_PROVIDER = os.environ.get('SIGNATURE_PROVIDER', 'zapsign')

# ============================================================
# CONFIGURACIÓN DE ZAPSIGN
# ============================================================

# API Token (REQUERIDO)
ZAPSIGN_API_TOKEN = os.environ.get('ZAPSIGN_API_TOKEN', '')

# Ambiente: sandbox o production
ZAPSIGN_ENVIRONMENT = os.environ.get('ZAPSIGN_ENVIRONMENT', 'sandbox')

# Modo de autenticación en ZapSign (assinaturaTela, etc)
ZAPSIGN_AUTH_MODE = os.environ.get('ZAPSIGN_AUTH_MODE', 'assinaturaTela')

# Enviar email automáticamente (del lado de ZapSign)
ZAPSIGN_SEND_AUTOMATIC_EMAIL = os.environ.get('ZAPSIGN_SEND_AUTOMATIC_EMAIL', 'true').lower() in ('true', '1', 'yes')

# Validación biométrica por selfie
ZAPSIGN_ENABLE_SELFIE_VALIDATION = os.environ.get('ZAPSIGN_ENABLE_SELFIE_VALIDATION', 'false').lower() in ('true', '1', 'yes')

# Tipo de validación de identidad
ZAPSIGN_SELFIE_VALIDATION_TYPE = os.environ.get('ZAPSIGN_SELFIE_VALIDATION_TYPE', 'identity-verification')

# Secret para validar webhooks (opcional)
ZAPSIGN_WEBHOOK_SECRET = os.environ.get('ZAPSIGN_WEBHOOK_SECRET', '')

# Header HTTP para el secret
ZAPSIGN_WEBHOOK_HEADER = os.environ.get('ZAPSIGN_WEBHOOK_HEADER', 'X-ZapSign-Secret')

# ============================================================
# CONFIGURACIÓN DE URLs PÚBLICAS
# ============================================================

# Dominio público del servicio
SIGNATURE_SITE_DOMAIN = os.environ.get('SIGNATURE_SITE_DOMAIN', 'localhost:8000')

# Usar HTTPS
SIGNATURE_SITE_HTTPS = os.environ.get('SIGNATURE_SITE_HTTPS', 'false').lower() in ('true', '1', 'yes')

# Validez de URLs temporales (en segundos)
SIGNATURE_URL_MAX_AGE = int(os.environ.get('SIGNATURE_URL_MAX_AGE', 86400))  # 24 horas

# ============================================================
# LOGGING
# ============================================================

SIGNATURE_LOG_LEVEL = os.environ.get('SIGNATURE_LOG_LEVEL', 'INFO')
