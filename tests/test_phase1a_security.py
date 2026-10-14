"""Tests for Phase 1A Security and Production Hardening.

Verifies:
1. Dynamic UPI ID configuration (no hardcoded personal UPI).
2. Demo password (1234) disabled by default.
3. Knowledge upload endpoint protected by Admin RBAC.
4. Production CRM_SECRET_KEY validation.
"""

from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.api.knowledge import create_knowledge_router
from app.core.auth import create_session
from app.core.config import Settings, validate_settings
from app.rag.service import RagService
from app.services.doctor_account_service import DoctorAccountService
from app.tools.invoice import InvoiceData, generate_invoice
from app.tools.payments import PaymentTools


def make_dummy_pdf(text: str = "Clinic policy") -> bytes:
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, content in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode() + content + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    pdf.extend(b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:]))
    pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return bytes(pdf)


class Phase1aSecurityTests(unittest.TestCase):
    # -------------------------------------------------------------------------
    # 1. Dynamic UPI ID
    # -------------------------------------------------------------------------
    def test_payment_qr_uses_configured_upi(self):
        with tempfile.TemporaryDirectory() as d:
            tools = PaymentTools(upi_id="clinic@okhdfcbank")
            res = tools.generate_offline_upi_qr("500", "City Clinic", "TKN-100", Path(d))
            self.assertTrue(res["success"])
            self.assertEqual(tools.upi_id, "clinic@okhdfcbank")
            query = parse_qs(urlparse(res["upi_uri"]).query)
            self.assertEqual(query["pa"], ["clinic@okhdfcbank"])
            self.assertNotIn("khansyrian1@okhdfcbank", res["upi_uri"])

    def test_payment_qr_default_does_not_contain_hardcoded_personal_upi(self):
        with tempfile.TemporaryDirectory() as d:
            tools = PaymentTools()
            res = tools.generate_offline_upi_qr("500", "City Clinic", "TKN-101", Path(d))
            self.assertTrue(res["success"])
            self.assertEqual(tools.upi_id, "")
            query = parse_qs(urlparse(res["upi_uri"]).query)
            self.assertNotEqual(query.get("pa"), ["khansyrian1@okhdfcbank"])

    def test_invoice_pdf_includes_dynamic_upi(self):
        with tempfile.TemporaryDirectory() as d:
            qr = PaymentTools(upi_id="merchant@upi").generate_offline_upi_qr("700", "City Clinic", "TKN-102", Path(d))
            data = InvoiceData(
                clinic_name="City Clinic",
                clinic_phone="1234567890",
                clinic_email="clinic@test.com",
                clinic_address="Medical Way",
                patient_name="John Doe",
                patient_email="john@example.com",
                patient_phone="9876543210",
                doctor_name="Dr. Smith",
                specialization="Cardiology",
                appointment_date="2026-10-10",
                appointment_time="10:00",
                token_no="TKN-102",
                amount="700",
                payment_method="Offline",
                payment_status="Pending",
                qr_path=qr["qr_path"],
                upi_id="merchant@upi",
            )
            _, path = generate_invoice(data, Path(d))
            text = "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
            self.assertIn("merchant@upi", text)
            self.assertNotIn("khansyrian1@okhdfcbank", text)

    # -------------------------------------------------------------------------
    # 2. Demo Password Protection
    # -------------------------------------------------------------------------
    def test_demo_password_rejected_by_default(self):
        service = DoctorAccountService(
            storage_path=Path(tempfile.mktemp()),
            allow_demo_password=False,
        )
        self.assertFalse(service.allow_demo_password)
        with self.assertRaises(ValueError) as ctx:
            service.validate_password_strength("1234")
        self.assertIn("8 characters", str(ctx.exception))

    def test_demo_password_accepted_only_when_explicitly_configured(self):
        service = DoctorAccountService(
            storage_path=Path(tempfile.mktemp()),
            allow_demo_password=True,
        )
        self.assertTrue(service.allow_demo_password)
        # Should not raise
        service.validate_password_strength("1234")

    def test_settings_disables_demo_password_by_default(self):
        settings = Settings(
            clinic_name="Clinic",
            telegram_bot_token="tok",
            telegram_webhook_secret="sec",
            gemini_api_key="key",
            gemini_model="mod",
            telegram_webhook_url="url",
            knowledge_dir=Path("k"),
            vectorstore_dir=Path("v"),
        )
        self.assertFalse(settings.allow_demo_password)

    # -------------------------------------------------------------------------
    # 3. Knowledge Upload RBAC
    # -------------------------------------------------------------------------
    def test_knowledge_upload_requires_admin_authentication(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            rag = RagService(root / "k", root / "v")
            app = FastAPI()
            app.include_router(create_knowledge_router(root / "k", rag))
            client = TestClient(app)

            # 1. No auth -> 401
            res_no_auth = client.post(
                "/api/v1/knowledge/upload",
                files={"file": ("guide.pdf", make_dummy_pdf("Clinic hours"), "application/pdf")},
            )
            self.assertEqual(res_no_auth.status_code, 401)

            # 2. Doctor auth (non-admin) -> 403 Forbidden
            doc_token = create_session("dr_test", role="doctor", doctor_id="DOC1")
            res_doc = client.post(
                "/api/v1/knowledge/upload",
                headers={"Authorization": f"Bearer {doc_token}"},
                files={"file": ("guide.pdf", make_dummy_pdf("Clinic hours"), "application/pdf")},
            )
            self.assertEqual(res_doc.status_code, 403)

            # 3. Admin auth -> 200 OK
            admin_token = create_session("admin", role="admin")
            res_admin = client.post(
                "/api/v1/knowledge/upload",
                headers={"Authorization": f"Bearer {admin_token}"},
                files={"file": ("guide.pdf", make_dummy_pdf("Clinic hours"), "application/pdf")},
            )
            self.assertEqual(res_admin.status_code, 200)

    # -------------------------------------------------------------------------
    # 4. Production Secret Key Validation
    # -------------------------------------------------------------------------
    def test_production_rejects_default_secret_key(self):
        settings = Settings(
            clinic_name="Clinic",
            telegram_bot_token="tok",
            telegram_webhook_secret="sec",
            gemini_api_key="key",
            gemini_model="mod",
            telegram_webhook_url="url",
            knowledge_dir=Path("k"),
            vectorstore_dir=Path("v"),
            crm_secret_key="clinic-crm-secret-key-change-in-production",
            app_env="production",
        )
        with self.assertRaises(RuntimeError) as ctx:
            validate_settings(settings)
        self.assertIn("CRM_SECRET_KEY", str(ctx.exception))

    def test_production_rejects_weak_secret_key(self):
        settings = Settings(
            clinic_name="Clinic",
            telegram_bot_token="tok",
            telegram_webhook_secret="sec",
            gemini_api_key="key",
            gemini_model="mod",
            telegram_webhook_url="url",
            knowledge_dir=Path("k"),
            vectorstore_dir=Path("v"),
            crm_secret_key="short",
            app_env="production",
        )
        with self.assertRaises(RuntimeError) as ctx:
            validate_settings(settings)
        self.assertIn("CRM_SECRET_KEY", str(ctx.exception))

    def test_production_accepts_strong_secret_key(self):
        settings = Settings(
            clinic_name="Clinic",
            telegram_bot_token="tok",
            telegram_webhook_secret="sec",
            gemini_api_key="key",
            gemini_model="mod",
            telegram_webhook_url="url",
            knowledge_dir=Path("k"),
            vectorstore_dir=Path("v"),
            crm_secret_key="super-strong-production-key-abc-12345",
            app_env="production",
        )
        # Should not raise
        validate_settings(settings)

    def test_development_allows_default_secret_key(self):
        settings = Settings(
            clinic_name="Clinic",
            telegram_bot_token="tok",
            telegram_webhook_secret="sec",
            gemini_api_key="key",
            gemini_model="mod",
            telegram_webhook_url="url",
            knowledge_dir=Path("k"),
            vectorstore_dir=Path("v"),
            crm_secret_key="clinic-crm-secret-key-change-in-production",
            app_env="development",
        )
        # Should not raise in development
        validate_settings(settings)


if __name__ == "__main__":
    unittest.main()

