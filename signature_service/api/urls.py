from django.urls import path

from signature_service.api import views


urlpatterns = [
    path("signatures/", views.signature_list_create_view, name="api-signature-list"),
    path("signatures/<uuid:signature_id>/", views.signature_detail_view, name="api-signature-detail"),
    path("signatures/<uuid:signature_id>/send/", views.signature_send_view, name="api-signature-send"),
    path("signatures/<uuid:signature_id>/download/", views.signature_download_view, name="api-signature-download"),
    path("signatures/<uuid:signature_id>/document/", views.signature_document_view, name="api-signature-document"),
    # Endpoint publico para configurar en ZapSign: POST /api/webhooks/signatures/
    path("webhooks/signatures/", views.signature_webhook_view, name="api-signature-webhook"),
]
