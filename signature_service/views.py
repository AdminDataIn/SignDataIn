from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from signature_service.application import (
    create_signature_request_from_upload,
    send_signature_request,
    sync_signature_request_status,
)
from signature_service.forms import SignatureRequestCreateForm
from signature_service.models import SignatureRequest
from signature_service.services import SignatureServiceError


def signature_list_view(request):
    return render(
        request,
        "signature_service/signature_list.html",
        {"signatures": SignatureRequest.objects.all()},
    )


def signature_create_view(request):
    error_message = None

    if request.method == "POST":
        form = SignatureRequestCreateForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                signature_request = create_signature_request_from_upload(
                    request=request,
                    uploaded_file=form.cleaned_data["document"],
                    signer_name=form.cleaned_data["signer_name"],
                    signer_email=form.cleaned_data["signer_email"],
                )
            except Exception as exc:
                error_message = str(exc)
            else:
                return HttpResponseRedirect(
                    reverse(
                        "signature_service:signature-detail",
                        kwargs={"signature_id": signature_request.id},
                    )
                )
    else:
        form = SignatureRequestCreateForm()

    return render(
        request,
        "signature_service/signature_create.html",
        {"form": form, "error_message": error_message},
    )


def signature_detail_view(request, signature_id):
    signature_request = get_object_or_404(SignatureRequest, pk=signature_id)
    error_message = None

    if request.method == "POST":
        try:
            signature_request = send_signature_request(signature_request=signature_request)
        except SignatureServiceError as exc:
            error_message = str(exc)
        else:
            return HttpResponseRedirect(
                reverse(
                    "signature_service:signature-detail",
                    kwargs={"signature_id": signature_request.id},
                )
            )
    else:
        signature_request = sync_signature_request_status(signature_request=signature_request)

    return render(
        request,
        "signature_service/signature_detail.html",
        {
            "signature_request": signature_request,
            "error_message": error_message,
        },
    )
