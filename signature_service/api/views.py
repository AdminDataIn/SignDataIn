import json
from io import BytesIO
from pathlib import Path

from django.http import FileResponse, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from signature_service.application import (
    create_signature_request_from_upload,
    download_signed_document,
    process_signature_webhook,
    send_signature_request,
)
from signature_service.forms import SignatureRequestCreateForm
from signature_service.models import SignatureEventLog, SignatureRequest
from signature_service.services import SignatureServiceError


def _serialize_signature_request(signature_request):
    return {
        "id": str(signature_request.id),
        "document_name": signature_request.document_name,
        "document_url": signature_request.document_url,
        "signer_name": signature_request.signer_name,
        "signer_email": signature_request.signer_email,
        "status": signature_request.status,
        "provider": signature_request.provider,
        "provider_document_id": signature_request.provider_document_id,
        "provider_sign_url": signature_request.provider_sign_url,
        "provider_signed_document_url": signature_request.provider_signed_document_url,
        "provider_status": signature_request.provider_status,
        "created_at": signature_request.created_at.isoformat() if signature_request.created_at else None,
        "sent_at": signature_request.sent_at.isoformat() if signature_request.sent_at else None,
        "signed_at": signature_request.signed_at.isoformat() if signature_request.signed_at else None,
        "refused_at": signature_request.refused_at.isoformat() if signature_request.refused_at else None,
        "download_url": f"/api/signatures/{signature_request.id}/download/",
        "send_url": f"/api/signatures/{signature_request.id}/send/",
    }


def _json_error(message, status=400):
    return JsonResponse({"error": message}, status=status)


def _client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "127.0.0.1")


@csrf_exempt
def signature_list_create_view(request):
    if request.method == "GET":
        signatures = SignatureRequest.objects.all()
        return JsonResponse(
            {"results": [_serialize_signature_request(signature) for signature in signatures]}
        )

    if request.method != "POST":
        return HttpResponseNotAllowed(["GET", "POST"])

    form = SignatureRequestCreateForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors}, status=400)

    try:
        signature_request = create_signature_request_from_upload(
            request=request,
            uploaded_file=form.cleaned_data["document"],
            signer_name=form.cleaned_data["signer_name"],
            signer_email=form.cleaned_data["signer_email"],
        )
    except Exception as exc:
        return _json_error(str(exc), status=500)

    return JsonResponse(_serialize_signature_request(signature_request), status=201)


def signature_detail_view(request, signature_id):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    signature_request = get_object_or_404(SignatureRequest, pk=signature_id)
    payload = _serialize_signature_request(signature_request)
    payload["events"] = [
        {
            "id": str(event.id),
            "event_type": event.event_type,
            "provider_event_type": event.provider_event_type,
            "processed": event.processed,
            "signature_valid": event.signature_valid,
            "processing_error": event.processing_error,
            "received_at": event.received_at.isoformat() if event.received_at else None,
        }
        for event in signature_request.events.all()
    ]
    return JsonResponse(payload)


@csrf_exempt
def signature_send_view(request, signature_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    signature_request = get_object_or_404(SignatureRequest, pk=signature_id)
    brand_name = request.POST.get("brand_name") or "DataIn"

    if (request.content_type or "").startswith("application/json"):
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return _json_error("JSON invalido.")
        brand_name = payload.get("brand_name") or brand_name

    try:
        updated_signature = send_signature_request(
            signature_request=signature_request,
            brand_name=brand_name,
        )
    except SignatureServiceError as exc:
        return _json_error(str(exc), status=400)
    except Exception as exc:
        return _json_error(str(exc), status=500)

    return JsonResponse(_serialize_signature_request(updated_signature))


def signature_download_view(request, signature_id):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    signature_request = get_object_or_404(SignatureRequest, pk=signature_id)

    try:
        pdf_bytes = download_signed_document(signature_request=signature_request)
    except SignatureServiceError as exc:
        return _json_error(str(exc), status=400)
    except Exception as exc:
        return _json_error(str(exc), status=500)

    filename = f"{Path(signature_request.document_name).stem}_signed.pdf"
    return FileResponse(
        BytesIO(pdf_bytes),
        as_attachment=True,
        filename=filename,
        content_type="application/pdf",
    )


def signature_document_view(request, signature_id):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    signature_request = get_object_or_404(SignatureRequest, pk=signature_id)
    filename = Path(signature_request.document_file.name).name or signature_request.document_name
    return FileResponse(
        signature_request.document_file.open("rb"),
        as_attachment=False,
        filename=filename,
        content_type="application/pdf",
    )


@csrf_exempt
def signature_webhook_view(request):
    """
    Webhook publico para ZapSign.

    Endpoint esperado en ZapSign:
        POST /api/webhooks/signatures/

    Payload minimo esperado:
        {
            "event": "doc_signed",
            "token": "<document_token>",
            "status": "signed|refused",
            "signers": [{"ip": "203.0.113.10"}]
        }

    Se deja sin CSRF porque ZapSign invoca este endpoint desde fuera del navegador.
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return _json_error("JSON invalido.")

    try:
        signature_request = process_signature_webhook(
            payload=payload,
            headers=request.headers,
            ip_address=_client_ip(request),
        )
    except Exception as exc:
        return _json_error(str(exc), status=500)

    if signature_request is None:
        latest_event = SignatureEventLog.objects.order_by("-received_at").first()
        return JsonResponse(
            {
                "processed": False,
                "status": "ignored",
                "processing_error": latest_event.processing_error if latest_event else None,
            }
        )

    return JsonResponse(
        {
            "processed": True,
            "signature_request_id": str(signature_request.id),
            "status": signature_request.status,
        }
    )
