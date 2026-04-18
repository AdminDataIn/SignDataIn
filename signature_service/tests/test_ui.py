from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from signature_service.models import SignatureRequest


class SignatureUiTests(TestCase):
    def test_create_signature_request_from_ui(self):
        response = self.client.post(
            "/signatures/create/",
            {
                "document": SimpleUploadedFile(
                    "pagare.pdf",
                    b"%PDF-1.4 ui pdf",
                    content_type="application/pdf",
                ),
                "signer_name": "Carlos Ruiz",
                "signer_email": "carlos@example.com",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(SignatureRequest.objects.count(), 1)

    @patch("signature_service.providers.ZapSignProvider.create_document")
    def test_send_signature_request_from_ui(self, create_document_mock):
        create_document_mock.return_value = {
            "token": "doc-token-ui",
            "signers": [{"sign_url": "https://zapsign.example/sign/doc-token-ui"}],
        }
        signature_request = SignatureRequest.objects.create(
            document_name="pagare.pdf",
            document_url="http://testserver/api/signatures/fake/document/",
            document_file=SimpleUploadedFile(
                "pagare.pdf",
                b"%PDF-1.4 ui pdf",
                content_type="application/pdf",
            ),
            signer_name="Carlos Ruiz",
            signer_email="carlos@example.com",
        )

        response = self.client.post(f"/signatures/{signature_request.id}/")

        self.assertEqual(response.status_code, 302)
        signature_request.refresh_from_db()
        self.assertEqual(signature_request.status, SignatureRequest.SignatureStatus.PENDING)

    def test_signature_detail_renders(self):
        signature_request = SignatureRequest.objects.create(
            document_name="pagare.pdf",
            document_url="http://testserver/api/signatures/fake/document/",
            document_file=SimpleUploadedFile(
                "pagare.pdf",
                b"%PDF-1.4 ui pdf",
                content_type="application/pdf",
            ),
            signer_name="Carlos Ruiz",
            signer_email="carlos@example.com",
        )

        response = self.client.get(f"/signatures/{signature_request.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "pagare.pdf")

    @patch("signature_service.providers.ZapSignProvider.get_document_status")
    def test_signature_detail_syncs_pending_status(self, get_document_status_mock):
        get_document_status_mock.return_value = {
            "token": "doc-token-ui",
            "status": "signed",
            "signed_at": "2026-04-18T17:54:00Z",
            "signers": [{"ip": "203.0.113.10"}],
        }
        signature_request = SignatureRequest.objects.create(
            document_name="pagare.pdf",
            document_url="http://testserver/api/signatures/fake/document/",
            document_file=SimpleUploadedFile(
                "pagare.pdf",
                b"%PDF-1.4 ui pdf",
                content_type="application/pdf",
            ),
            signer_name="Carlos Ruiz",
            signer_email="carlos@example.com",
            status=SignatureRequest.SignatureStatus.PENDING,
            provider_document_id="doc-token-ui",
        )

        response = self.client.get(f"/signatures/{signature_request.id}/")

        self.assertEqual(response.status_code, 200)
        signature_request.refresh_from_db()
        self.assertEqual(signature_request.status, SignatureRequest.SignatureStatus.SIGNED)
