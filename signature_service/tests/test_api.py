from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from requests.exceptions import HTTPError
from requests.models import Response

from signature_service.models import SignatureEventLog, SignatureRequest


class SignatureApiTests(TestCase):
    def test_create_and_list_signature_requests(self):
        response = self.client.post(
            "/api/signatures/",
            {
                "document": SimpleUploadedFile(
                    "contrato.pdf",
                    b"%PDF-1.4 test pdf",
                    content_type="application/pdf",
                ),
                "signer_name": "Ana Gomez",
                "signer_email": "ana@example.com",
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        signature_request = SignatureRequest.objects.get(pk=payload["id"])
        self.assertEqual(signature_request.document_name, "contrato.pdf")
        self.assertTrue(payload["document_url"].endswith(f"/api/signatures/{signature_request.id}/document/"))

        list_response = self.client.get("/api/signatures/")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()["results"]), 1)

    @patch("signature_service.providers.ZapSignProvider.create_document")
    def test_send_signature_request(self, create_document_mock):
        create_document_mock.return_value = {
            "token": "doc-token-123",
            "signers": [{"sign_url": "https://zapsign.example/sign/doc-token-123"}],
        }
        signature_request = SignatureRequest.objects.create(
            document_name="contrato.pdf",
            document_url="http://testserver/api/signatures/fake/document/",
            document_file=SimpleUploadedFile(
                "contrato.pdf",
                b"%PDF-1.4 test pdf",
                content_type="application/pdf",
            ),
            signer_name="Ana Gomez",
            signer_email="ana@example.com",
        )

        response = self.client.post(f"/api/signatures/{signature_request.id}/send/")

        self.assertEqual(response.status_code, 200)
        signature_request.refresh_from_db()
        self.assertEqual(signature_request.status, SignatureRequest.SignatureStatus.PENDING)
        self.assertEqual(signature_request.provider_document_id, "doc-token-123")

    @patch("signature_service.providers.ZapSignProvider.download_signed_document")
    def test_download_signed_document(self, download_signed_document_mock):
        download_signed_document_mock.return_value = b"%PDF-1.4 signed"
        signature_request = SignatureRequest.objects.create(
            document_name="contrato.pdf",
            document_url="http://testserver/api/signatures/fake/document/",
            document_file=SimpleUploadedFile(
                "contrato.pdf",
                b"%PDF-1.4 test pdf",
                content_type="application/pdf",
            ),
            signer_name="Ana Gomez",
            signer_email="ana@example.com",
            status=SignatureRequest.SignatureStatus.SIGNED,
            provider_document_id="doc-token-123",
        )

        response = self.client.get(f"/api/signatures/{signature_request.id}/download/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    @patch("signature_service.providers.requests.get")
    @patch("signature_service.providers.ZapSignProvider.get_document_status")
    def test_download_signed_document_uses_detail_signed_file_url(
        self,
        get_document_status_mock,
        requests_get_mock,
    ):
        expired_response = Response()
        expired_response.status_code = 404
        expired_response._content = b"not found"
        http_error = HTTPError(response=expired_response)

        signed_response = Response()
        signed_response.status_code = 200
        signed_response._content = b"%PDF-1.4 signed fresh"

        requests_get_mock.side_effect = [http_error, signed_response]
        get_document_status_mock.return_value = {
            "token": "doc-token-123",
            "status": "signed",
            "signed_file": "https://files.example/fresh-signed.pdf",
        }

        signature_request = SignatureRequest.objects.create(
            document_name="contrato.pdf",
            document_url="http://testserver/api/signatures/fake/document/",
            document_file=SimpleUploadedFile(
                "contrato.pdf",
                b"%PDF-1.4 test pdf",
                content_type="application/pdf",
            ),
            signer_name="Ana Gomez",
            signer_email="ana@example.com",
            status=SignatureRequest.SignatureStatus.SIGNED,
            provider_document_id="doc-token-123",
            provider_signed_document_url="https://files.example/expired-signed.pdf",
        )

        response = self.client.get(f"/api/signatures/{signature_request.id}/download/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        signature_request.refresh_from_db()
        self.assertTrue(signature_request.signed_document_file.name)

    @patch("signature_service.providers.ZapSignProvider.validate_webhook_signature")
    def test_process_webhook(self, validate_webhook_signature_mock):
        validate_webhook_signature_mock.return_value = True
        signature_request = SignatureRequest.objects.create(
            document_name="contrato.pdf",
            document_url="http://testserver/api/signatures/fake/document/",
            document_file=SimpleUploadedFile(
                "contrato.pdf",
                b"%PDF-1.4 test pdf",
                content_type="application/pdf",
            ),
            signer_name="Ana Gomez",
            signer_email="ana@example.com",
            status=SignatureRequest.SignatureStatus.PENDING,
            provider_document_id="doc-token-123",
        )

        response = self.client.post(
            "/api/webhooks/signatures/",
            data='{"event":"doc_signed","token":"doc-token-123","status":"signed","signers":[{"ip":"203.0.113.10"}]}',
            content_type="application/json",
            HTTP_X_ZAPSIGN_SECRET="webhook-secret",
        )

        self.assertEqual(response.status_code, 200)
        signature_request.refresh_from_db()
        self.assertEqual(signature_request.status, SignatureRequest.SignatureStatus.SIGNED)
        self.assertEqual(signature_request.signer_ip, "203.0.113.10")
        self.assertTrue(
            SignatureEventLog.objects.filter(
                signature_request=signature_request,
                event_type=SignatureEventLog.EventType.DOCUMENT_SIGNED,
                processed=True,
            ).exists()
        )

    @patch("signature_service.providers.ZapSignProvider.get_document_status")
    def test_detail_syncs_pending_signature_from_provider(self, get_document_status_mock):
        get_document_status_mock.return_value = {
            "token": "doc-token-123",
            "status": "signed",
            "signed_at": "2026-04-18T17:54:00Z",
            "signers": [{"ip": "203.0.113.10"}],
            "signed_file": "https://files.example/signed.pdf",
        }
        signature_request = SignatureRequest.objects.create(
            document_name="contrato.pdf",
            document_url="http://testserver/api/signatures/fake/document/",
            document_file=SimpleUploadedFile(
                "contrato.pdf",
                b"%PDF-1.4 test pdf",
                content_type="application/pdf",
            ),
            signer_name="Ana Gomez",
            signer_email="ana@example.com",
            status=SignatureRequest.SignatureStatus.PENDING,
            provider_document_id="doc-token-123",
        )

        response = self.client.get(f"/api/signatures/{signature_request.id}/")

        self.assertEqual(response.status_code, 200)
        signature_request.refresh_from_db()
        self.assertEqual(signature_request.status, SignatureRequest.SignatureStatus.SIGNED)
        self.assertEqual(signature_request.provider_status, "signed")
        self.assertEqual(signature_request.signer_ip, "203.0.113.10")
