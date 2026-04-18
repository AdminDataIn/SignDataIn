from pathlib import Path

from django.conf import settings
from django.urls import reverse

from signature_service import SignatureService


class SignatureApplicationError(Exception):
    """Error en la capa de uso de signature_service."""


def _build_absolute_document_url(request, signature_request):
    path = reverse(
        "signature_service:api-signature-document",
        kwargs={"signature_id": signature_request.id},
    )
    public_base_url = getattr(settings, "SIGNATURE_PUBLIC_BASE_URL", "").rstrip("/")
    if public_base_url:
        return f"{public_base_url}{path}"
    return request.build_absolute_uri(path)


def create_signature_request_from_upload(
    *,
    request,
    uploaded_file,
    signer_name,
    signer_email,
):
    service = SignatureService()
    document_name = Path(uploaded_file.name).name

    signature_request = service.create_signature_request(
        document_name=document_name,
        document_url=request.build_absolute_uri(
            reverse("signature_service:api-signature-list")
        ),
        document_file=uploaded_file,
        signer_name=signer_name,
        signer_email=signer_email,
        created_by=request.user if getattr(request, "user", None) and request.user.is_authenticated else None,
    )

    signature_request.document_url = _build_absolute_document_url(request, signature_request)
    signature_request.save(update_fields=["document_url"])
    return signature_request


def send_signature_request(*, signature_request, brand_name="DataIn"):
    service = SignatureService()
    return service.send_for_signature(signature_request, brand_name=brand_name)


def download_signed_document(*, signature_request):
    service = SignatureService()
    return service.download_signed_document(signature_request)


def process_signature_webhook(*, payload, headers, ip_address):
    service = SignatureService()
    return service.process_webhook(payload, headers, ip_address)
