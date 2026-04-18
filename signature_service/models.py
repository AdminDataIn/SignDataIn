"""
Modelos genéricos para gestión de solicitudes de firma digital.
Independientes del dominio de negocio específico.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class SignatureRequest(models.Model):
    """
    Modelo genérico para representar un documento pendiente de firma digital.
    
    Este es el equivalente reutilizable del modelo 'Pagare' específico de Aprobado.
    Puede ser usado por diferentes servicios dentro de DataIn.
    """
    
    class SignatureStatus(models.TextChoices):
        """Estados del documento durante el ciclo de vida de firma"""
        CREATED = 'CREATED', 'Creado'
        PENDING = 'PENDING', 'Pendiente de firma'
        SIGNED = 'SIGNED', 'Firmado'
        REFUSED = 'REFUSED', 'Rechazado por firmante'
        CANCELLED = 'CANCELLED', 'Cancelado'
        EXPIRED = 'EXPIRED', 'Expirado'
    
    # Identificación única
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    external_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="ID externo de referencia en el sistema cliente"
    )
    document_name = models.CharField(
        max_length=255,
        help_text="Nombre amigable del documento"
    )
    
    # Estado
    status = models.CharField(
        max_length=20,
        choices=SignatureStatus.choices,
        default=SignatureStatus.CREATED
    )
    
    # Información del documento
    document_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="Hash SHA-256 del documento (trazabilidad)"
    )
    document_url = models.URLField(
        help_text="URL pública del documento a firmar"
    )
    document_version = models.CharField(
        max_length=20,
        default='1.0',
        help_text="Versión del documento"
    )
    
    # Información del firmante
    signer_name = models.CharField(
        max_length=255,
        help_text="Nombre del firmante"
    )
    signer_email = models.EmailField(
        help_text="Email del firmante"
    )
    signer_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP del firmante al momento de firmar"
    )
    
    # Proveedor de firma (ZapSign, DocuSign, etc.)
    provider = models.CharField(
        max_length=50,
        default='zapsign',
        help_text="Proveedor de firma utilizado"
    )
    provider_document_id = models.CharField(
        max_length=200,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="ID único del documento en el proveedor"
    )
    provider_sign_url = models.URLField(
        max_length=1000,
        null=True,
        blank=True,
        help_text="URL de firma proporcionada por el proveedor"
    )
    provider_signed_document_url = models.URLField(
        max_length=1000,
        null=True,
        blank=True,
        help_text="URL del documento firmado en el proveedor"
    )
    provider_status = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Estado reportado por el proveedor"
    )
    
    # Archivos
    document_file = models.FileField(
        upload_to='signature_requests/%Y/%m/',
        help_text="Archivo original del documento"
    )
    signed_document_file = models.FileField(
        upload_to='signature_requests_signed/%Y/%m/',
        null=True,
        blank=True,
        help_text="Documento descargado después de firmar"
    )
    
    # Auditoría y trazabilidad
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='signature_requests_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Cuándo se envió para firma"
    )
    signed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Cuándo se firmó (timestamp del proveedor)"
    )
    refused_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Cuándo fue rechazado"
    )
    
    # Metadata adicional (flexible para diferentes clientes)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Datos adicionales específicos del cliente"
    )
    
    # Evidencia forense (para auditoría legal)
    provider_webhook_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Payload completo del último webhook del proveedor"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Solicitud de Firma'
        verbose_name_plural = 'Solicitudes de Firma'
        indexes = [
            models.Index(fields=['provider_document_id']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['signer_email']),
            models.Index(fields=['external_id']),
        ]
    
    def __str__(self):
        return f"{self.document_name} - {self.signer_email} ({self.get_status_display()})"


class SignatureEventLog(models.Model):
    """
    Registro de auditoría para todos los eventos de firma recibidos de proveedores.
    
    Mapeo con BDD: cada evento se registra antes de procesar para cumplir con
    requisitos legales de trazabilidad.
    """
    
    class EventType(models.TextChoices):
        """Tipos de eventos que pueden ocurrir"""
        DOCUMENT_CREATED = 'document_created', 'Documento creado'
        DOCUMENT_SENT = 'document_sent', 'Documento enviado'
        DOCUMENT_VIEWED = 'document_viewed', 'Documento visualizado'
        DOCUMENT_SIGNED = 'document_signed', 'Documento firmado'
        DOCUMENT_REFUSED = 'document_refused', 'Documento rechazado'
        DOCUMENT_EXPIRED = 'document_expired', 'Documento expirado'
        SIGNER_COMPLETED = 'signer_completed', 'Firmante completó'
        WEBHOOK_RECEIVED = 'webhook_received', 'Webhook recibido'
    
    # Identificación
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    signature_request = models.ForeignKey(
        SignatureRequest,
        on_delete=models.CASCADE,
        related_name='events',
        null=True,
        blank=True
    )
    
    # Tipo de evento
    event_type = models.CharField(
        max_length=50,
        choices=EventType.choices
    )
    provider_event_type = models.CharField(
        max_length=100,
        help_text="Tipo de evento reportado por el proveedor (ej: doc_signed)"
    )
    
    # Payload completo
    payload = models.JSONField(
        help_text="Datos completos del evento/webhook"
    )
    
    # Metadata HTTP (para webhooks)
    http_headers = models.JSONField(
        default=dict,
        help_text="Headers HTTP recibidos"
    )
    http_ip_address = models.GenericIPAddressField(
        help_text="IP desde donde vino el evento"
    )
    
    # Validación y procesamiento
    signature_valid = models.BooleanField(
        default=False,
        help_text="Si la firma/HMAC fue validada correctamente"
    )
    processed = models.BooleanField(
        default=False,
        help_text="Si el evento fue procesado exitosamente"
    )
    processing_error = models.TextField(
        null=True,
        blank=True,
        help_text="Error si el procesamiento falló"
    )
    
    # Trazabilidad
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(
        null=True,
        blank=True
    )
    
    class Meta:
        ordering = ['-received_at']
        verbose_name = 'Evento de Firma'
        verbose_name_plural = 'Eventos de Firma'
        indexes = [
            models.Index(fields=['signature_request', '-received_at']),
            models.Index(fields=['event_type', 'processed']),
            models.Index(fields=['provider_event_type']),
        ]
    
    def __str__(self):
        status = "OK" if self.processed else "ERROR"
        return f"{status} {self.get_event_type_display()} - {self.received_at.strftime('%Y-%m-%d %H:%M:%S')}"
