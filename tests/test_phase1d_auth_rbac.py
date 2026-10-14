"""Comprehensive tests for Phase 1D: Multi-Tenant Production Authentication and RBAC.

Covers:
1. Valid login
2. Invalid password
3. Inactive user cannot login or access
4. Password hash is not plaintext
5. 1234 demo password remains disabled
6. Authenticated user gets correct role
7. Authenticated user gets correct tenant
8. Client tenant spoofing returns 403
9. Tenant admin cannot access another tenant
10. Doctor cannot access tenant admin endpoints
11. Receptionist cannot access admin-only endpoints
12. Staff permissions are restricted
13. Patient cannot access staff/admin endpoints
14. SUPER_ADMIN role works (with explicit cross-tenant capability)
15. Logout / session invalidation works
16. Expired token / session rejected
17. Knowledge upload respects tenant + role
18. Role supplied by client cannot elevate privileges
19. User_id supplied by client cannot bypass authorization
20. Role and permission matrix validation
21. User model properties (is_active, set_role, last_login_at)
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.testclient import TestClient

from app.api.admin import create_admin_router
from app.api.knowledge import create_knowledge_router
from app.core.auth import (
    _ACTIVE_SESSIONS,
    create_session,
    get_current_admin,
    get_current_admin_or_doctor,
    get_current_doctor,
    get_current_user,
    get_session,
    hash_password,
    revoke_session,
    verify_password,
)
from app.core.config import Settings
from app.core.rbac import (
    Permission,
    ROLE_PERMISSIONS,
    UserRole,
    get_role_permissions,
    has_any_permission,
    has_permission,
    require_admin_or_doctor,
    require_authenticated_user,
    require_doctor,
    require_patient,
    require_permission,
    require_receptionist,
    require_role,
    require_staff,
    require_super_admin,
    require_tenant_admin,
)
from app.core.tenant import get_current_tenant, resolve_tenant_context
from app.db.models.user import User
from app.services.crm_service import CrmService
from app.services.doctor_account_service import DoctorAccountService


def make_dummy_pdf(text: str = "Policy") -> bytes:
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


class Phase1dAuthRbacTests(unittest.TestCase):
    def setUp(self):
        # Build test app with RBAC protected test endpoints
        self.app = FastAPI()

        @self.app.get("/test/user")
        async def user_route(u: dict = Depends(require_authenticated_user)):
            return {"status": "ok", "user": u["username"], "role": u["role"]}

        @self.app.get("/test/super-admin")
        async def super_route(u: dict = Depends(require_super_admin)):
            return {"status": "ok", "super": True}

        @self.app.get("/test/tenant-admin")
        async def tenant_admin_route(u: dict = Depends(require_tenant_admin)):
            return {"status": "ok", "admin": True, "tenant": u.get("tenant_id")}

        @self.app.get("/test/doctor")
        async def doctor_route(u: dict = Depends(require_doctor)):
            return {"status": "ok", "doctor": True}

        @self.app.get("/test/receptionist")
        async def receptionist_route(u: dict = Depends(require_receptionist)):
            return {"status": "ok", "receptionist": True}

        @self.app.get("/test/staff")
        async def staff_route(u: dict = Depends(require_staff)):
            return {"status": "ok", "staff": True}

        @self.app.get("/test/patient")
        async def patient_route(u: dict = Depends(require_patient)):
            return {"status": "ok", "patient": True}

        @self.app.get("/test/admin-or-doctor")
        async def admin_or_doc_route(u: dict = Depends(require_admin_or_doctor)):
            return {"status": "ok", "clinical_or_admin": True}

        @self.app.get("/test/billing-perm")
        async def billing_route(u: dict = Depends(require_permission(Permission.BILLING_MANAGE))):
            return {"status": "ok", "billing": True}

        @self.app.get("/test/tenant-context")
        async def tenant_ctx_route(
            u: dict = Depends(require_authenticated_user),
            ctx=Depends(resolve_tenant_context),
        ):
            return {"status": "ok", "tenant_id": ctx.tenant_id, "user_tenant": u.get("tenant_id")}

        self.client = TestClient(self.app)

    # -------------------------------------------------------------------------
    # 1. Valid Login
    # -------------------------------------------------------------------------
    def test_valid_login(self):
        crm_mock = MagicMock(spec=CrmService)
        crm_mock.doctor_accounts = None

        settings = Settings(
            clinic_name="Alpha Clinic",
            telegram_bot_token="tok",
            telegram_webhook_secret="sec",
            gemini_api_key="key",
            gemini_model="mod",
            telegram_webhook_url="url",
            knowledge_dir=Path("k"),
            vectorstore_dir=Path("v"),
            crm_admin_username="admin_user",
            crm_admin_password_hash=hash_password("StrongPassword123"),
        )

        app = FastAPI()
        app.include_router(create_admin_router(crm_mock, settings))
        c = TestClient(app)

        res = c.post("/api/admin/auth/login", json={"username": "admin_user", "password": "StrongPassword123"})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn("token", body)
        self.assertEqual(body["username"], "admin_user")

    # -------------------------------------------------------------------------
    # 2. Invalid Password
    # -------------------------------------------------------------------------
    def test_invalid_password(self):
        crm_mock = MagicMock(spec=CrmService)
        crm_mock.doctor_accounts = None

        settings = Settings(
            clinic_name="Alpha Clinic",
            telegram_bot_token="tok",
            telegram_webhook_secret="sec",
            gemini_api_key="key",
            gemini_model="mod",
            telegram_webhook_url="url",
            knowledge_dir=Path("k"),
            vectorstore_dir=Path("v"),
            crm_admin_username="admin_user",
            crm_admin_password_hash=hash_password("StrongPassword123"),
        )

        app = FastAPI()
        app.include_router(create_admin_router(crm_mock, settings))
        c = TestClient(app)

        res = c.post("/api/admin/auth/login", json={"username": "admin_user", "password": "WrongPassword"})
        self.assertEqual(res.status_code, 401)
        self.assertIn("Invalid username or password", res.json()["detail"])

    # -------------------------------------------------------------------------
    # 3. Inactive User Cannot Login or Access
    # -------------------------------------------------------------------------
    def test_inactive_user_cannot_login_or_access(self):
        # Create session with inactive status
        token = create_session("inactive_staff", role="STAFF", is_active=False)
        res = self.client.get("/test/user", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 401)
        self.assertIn("inactive or suspended", res.json()["detail"])

    # -------------------------------------------------------------------------
    # 4. Password Hash Is Not Plaintext
    # -------------------------------------------------------------------------
    def test_password_hash_is_not_plaintext(self):
        raw_pw = "DoctorSecret123"
        hashed = hash_password(raw_pw)

        self.assertNotIn(raw_pw, hashed)
        self.assertTrue(hashed.startswith("pbkdf2:sha256:100000$"))
        self.assertTrue(verify_password(raw_pw, hashed))
        self.assertFalse(verify_password("wrong_password", hashed))

    # -------------------------------------------------------------------------
    # 5. 1234 Demo Password Remains Disabled By Default
    # -------------------------------------------------------------------------
    def test_1234_demo_password_remains_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc = DoctorAccountService(
                storage_path=Path(tmp) / "accounts.json",
                allow_demo_password=False,
            )
            # Must raise ValueError for weak demo password 1234
            with self.assertRaises(ValueError):
                svc.validate_password_strength("1234")

    # -------------------------------------------------------------------------
    # 6. Authenticated User Gets Correct Role
    # -------------------------------------------------------------------------
    def test_authenticated_user_gets_correct_role(self):
        roles = [
            ("super", UserRole.SUPER_ADMIN),
            ("tenant_admin", UserRole.TENANT_ADMIN),
            ("doctor", UserRole.DOCTOR),
            ("receptionist", UserRole.RECEPTIONIST),
            ("staff", UserRole.STAFF),
            ("patient", UserRole.PATIENT),
        ]
        for role_name, expected_enum in roles:
            tok = create_session(f"user_{role_name}", role=role_name)
            res = self.client.get("/test/user", headers={"Authorization": f"Bearer {tok}"})
            self.assertEqual(res.status_code, 200)
            self.assertEqual(UserRole.normalize(res.json()["role"]), expected_enum)

    # -------------------------------------------------------------------------
    # 7. Authenticated User Gets Correct Tenant
    # -------------------------------------------------------------------------
    def test_authenticated_user_gets_correct_tenant(self):
        tok = create_session("tenant_user", role="TENANT_ADMIN", tenant_id="clinic_alpha")
        res = self.client.get("/test/tenant-context", headers={"Authorization": f"Bearer {tok}"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["tenant_id"], "clinic_alpha")
        self.assertEqual(res.json()["user_tenant"], "clinic_alpha")

    # -------------------------------------------------------------------------
    # 8. Client Tenant Spoofing Returns 403
    # -------------------------------------------------------------------------
    def test_client_tenant_spoofing_returns_403(self):
        tok = create_session("legit_user", role="DOCTOR", tenant_id="clinic_alpha")

        # Client attempts to spoof header with different tenant
        res = self.client.get(
            "/test/tenant-context",
            headers={"Authorization": f"Bearer {tok}", "X-Tenant-ID": "clinic_beta"},
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("Access forbidden", res.json()["detail"])

    # -------------------------------------------------------------------------
    # 9. Tenant Admin Cannot Access Another Tenant
    # -------------------------------------------------------------------------
    def test_tenant_admin_cannot_access_another_tenant(self):
        tok = create_session("admin_alpha", role="TENANT_ADMIN", tenant_id="clinic_alpha")

        # Admin of clinic_alpha cannot send X-Tenant-ID for clinic_beta
        res = self.client.get(
            "/test/tenant-context",
            headers={"Authorization": f"Bearer {tok}", "X-Tenant-ID": "clinic_beta"},
        )
        self.assertEqual(res.status_code, 403)

    # -------------------------------------------------------------------------
    # 10. Doctor Cannot Access Tenant Admin Endpoints
    # -------------------------------------------------------------------------
    def test_doctor_cannot_access_tenant_admin_endpoints(self):
        doc_tok = create_session("dr_smith", role="DOCTOR", tenant_id="clinic_alpha")

        # Doctor can access /test/doctor
        res_doc = self.client.get("/test/doctor", headers={"Authorization": f"Bearer {doc_tok}"})
        self.assertEqual(res_doc.status_code, 200)

        # Doctor CANNOT access /test/tenant-admin
        res_admin = self.client.get("/test/tenant-admin", headers={"Authorization": f"Bearer {doc_tok}"})
        self.assertEqual(res_admin.status_code, 403)

    # -------------------------------------------------------------------------
    # 11. Receptionist Cannot Access Admin-Only Endpoints
    # -------------------------------------------------------------------------
    def test_receptionist_cannot_access_admin_only_endpoints(self):
        rec_tok = create_session("rec_user", role="RECEPTIONIST", tenant_id="clinic_alpha")

        # Can access receptionist endpoint
        res_rec = self.client.get("/test/receptionist", headers={"Authorization": f"Bearer {rec_tok}"})
        self.assertEqual(res_rec.status_code, 200)

        # Can access billing permission endpoint
        res_bill = self.client.get("/test/billing-perm", headers={"Authorization": f"Bearer {rec_tok}"})
        self.assertEqual(res_bill.status_code, 200)

        # CANNOT access tenant-admin endpoint
        res_admin = self.client.get("/test/tenant-admin", headers={"Authorization": f"Bearer {rec_tok}"})
        self.assertEqual(res_admin.status_code, 403)

    # -------------------------------------------------------------------------
    # 12. Staff Permissions Are Restricted
    # -------------------------------------------------------------------------
    def test_staff_permissions_are_restricted(self):
        staff_tok = create_session("staff_user", role="STAFF", tenant_id="clinic_alpha")

        # Can access staff endpoint
        res_staff = self.client.get("/test/staff", headers={"Authorization": f"Bearer {staff_tok}"})
        self.assertEqual(res_staff.status_code, 200)

        # Cannot access doctor endpoint
        res_doc = self.client.get("/test/doctor", headers={"Authorization": f"Bearer {staff_tok}"})
        self.assertEqual(res_doc.status_code, 403)

        # Cannot access billing permission
        res_bill = self.client.get("/test/billing-perm", headers={"Authorization": f"Bearer {staff_tok}"})
        self.assertEqual(res_bill.status_code, 403)

    # -------------------------------------------------------------------------
    # 13. Patient Cannot Access Staff/Admin Endpoints
    # -------------------------------------------------------------------------
    def test_patient_cannot_access_staff_or_admin_endpoints(self):
        pat_tok = create_session("patient_user", role="PATIENT", tenant_id="clinic_alpha")

        # Can access patient endpoint
        res_pat = self.client.get("/test/patient", headers={"Authorization": f"Bearer {pat_tok}"})
        self.assertEqual(res_pat.status_code, 200)

        # Cannot access staff endpoint
        res_staff = self.client.get("/test/staff", headers={"Authorization": f"Bearer {pat_tok}"})
        self.assertEqual(res_staff.status_code, 403)

        # Cannot access doctor endpoint
        res_doc = self.client.get("/test/doctor", headers={"Authorization": f"Bearer {pat_tok}"})
        self.assertEqual(res_doc.status_code, 403)

        # Cannot access admin endpoint
        res_admin = self.client.get("/test/tenant-admin", headers={"Authorization": f"Bearer {pat_tok}"})
        self.assertEqual(res_admin.status_code, 403)

    # -------------------------------------------------------------------------
    # 14. SUPER_ADMIN Role Works (With Explicit Cross-Tenant Capability)
    # -------------------------------------------------------------------------
    def test_super_admin_role_works(self):
        super_tok = create_session("platform_owner", role="SUPER_ADMIN", tenant_id="platform")

        # Passes require_super_admin
        res_super = self.client.get("/test/super-admin", headers={"Authorization": f"Bearer {super_tok}"})
        self.assertEqual(res_super.status_code, 200)

        # Passes require_tenant_admin
        res_admin = self.client.get("/test/tenant-admin", headers={"Authorization": f"Bearer {super_tok}"})
        self.assertEqual(res_admin.status_code, 200)

        # Super Admin CAN explicitly specify X-Tenant-ID to manage any clinic
        res_switch = self.client.get(
            "/test/tenant-context",
            headers={"Authorization": f"Bearer {super_tok}", "X-Tenant-ID": "clinic_target_123"},
        )
        self.assertEqual(res_switch.status_code, 200)
        self.assertEqual(res_switch.json()["tenant_id"], "clinic_target_123")

    # -------------------------------------------------------------------------
    # 15. Logout / Session Invalidation Works
    # -------------------------------------------------------------------------
    def test_logout_and_session_invalidation_works(self):
        tok = create_session("user_to_logout", role="STAFF")

        # Access succeeds
        res_before = self.client.get("/test/user", headers={"Authorization": f"Bearer {tok}"})
        self.assertEqual(res_before.status_code, 200)

        # Invalidate session
        self.assertTrue(revoke_session(tok))

        # Access fails with 401
        res_after = self.client.get("/test/user", headers={"Authorization": f"Bearer {tok}"})
        self.assertEqual(res_after.status_code, 401)

    # -------------------------------------------------------------------------
    # 16. Expired Token / Session Rejected
    # -------------------------------------------------------------------------
    def test_expired_token_rejected(self):
        # Create token that expired 1 hour ago
        tok = create_session("expired_user", role="STAFF", expires_hours=-1)

        res = self.client.get("/test/user", headers={"Authorization": f"Bearer {tok}"})
        self.assertEqual(res.status_code, 401)

    # -------------------------------------------------------------------------
    # 17. Knowledge Upload Respects Tenant + Role
    # -------------------------------------------------------------------------
    def test_knowledge_upload_respects_tenant_and_role(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            knowledge_dir = root_path / "k"
            rag_mock = MagicMock()
            rag_mock.is_available.return_value = True
            rag_mock.ingest_pdf.return_value = 5

            app = FastAPI()
            app.include_router(create_knowledge_router(knowledge_dir, rag_mock))
            client = TestClient(app)

            # Doctor attempt -> 403 Forbidden
            doc_tok = create_session("dr_test", role="DOCTOR", tenant_id="clinic_alpha")
            res_doc = client.post(
                "/api/v1/knowledge/upload",
                headers={"Authorization": f"Bearer {doc_tok}"},
                files={"file": ("guide.pdf", make_dummy_pdf("Clinic policies"), "application/pdf")},
            )
            self.assertEqual(res_doc.status_code, 403)

            # Staff attempt -> 403 Forbidden
            staff_tok = create_session("staff_test", role="STAFF", tenant_id="clinic_alpha")
            res_staff = client.post(
                "/api/v1/knowledge/upload",
                headers={"Authorization": f"Bearer {staff_tok}"},
                files={"file": ("guide.pdf", make_dummy_pdf("Clinic policies"), "application/pdf")},
            )
            self.assertEqual(res_staff.status_code, 403)

            # Tenant admin attempt -> 200 OK
            admin_tok = create_session("admin_test", role="TENANT_ADMIN", tenant_id="clinic_alpha")
            res_admin = client.post(
                "/api/v1/knowledge/upload",
                headers={"Authorization": f"Bearer {admin_tok}"},
                files={"file": ("guide.pdf", make_dummy_pdf("Clinic policies"), "application/pdf")},
            )
            self.assertEqual(res_admin.status_code, 200)
            self.assertEqual(res_admin.json()["status"], "indexed")

    # -------------------------------------------------------------------------
    # 18. Role Supplied by Client Cannot Elevate Privileges
    # -------------------------------------------------------------------------
    def test_role_supplied_by_client_cannot_elevate_privileges(self):
        # Authenticated as STAFF
        tok = create_session("staff_sneaky", role="STAFF", tenant_id="clinic_alpha")

        # Client adds spoofed role header and query param
        res = self.client.get(
            "/test/tenant-admin",
            headers={"Authorization": f"Bearer {tok}", "X-User-Role": "SUPER_ADMIN"},
            params={"role": "SUPER_ADMIN"},
        )
        # Server must strictly enforce the session's role (STAFF), returning 403 Forbidden
        self.assertEqual(res.status_code, 403)

    # -------------------------------------------------------------------------
    # 19. User ID Supplied by Client Cannot Bypass Authorization
    # -------------------------------------------------------------------------
    def test_user_id_supplied_by_client_cannot_bypass_authorization(self):
        tok = create_session("staff_user", role="STAFF", user_id="usr_111")

        # Client supplies a different user_id in headers and query
        res = self.client.get(
            "/test/user",
            headers={"Authorization": f"Bearer {tok}", "X-User-ID": "usr_999_admin"},
            params={"user_id": "usr_999_admin"},
        )
        self.assertEqual(res.status_code, 200)
        # Authoritative identity remains staff_user
        self.assertEqual(res.json()["user"], "staff_user")

    # -------------------------------------------------------------------------
    # 20. Role and Permission Matrix Direct Validation
    # -------------------------------------------------------------------------
    def test_permission_matrix_and_helpers(self):
        # Super admin has platform manage but not clinical operations
        self.assertTrue(has_permission(UserRole.SUPER_ADMIN, Permission.PLATFORM_MANAGE))
        self.assertFalse(has_permission(UserRole.SUPER_ADMIN, Permission.CLINICAL_OPERATION))

        # Tenant admin has tenant config and prescription manage
        self.assertTrue(has_permission(UserRole.TENANT_ADMIN, Permission.TENANT_CONFIG))
        self.assertTrue(has_permission(UserRole.TENANT_ADMIN, Permission.PRESCRIPTION_MANAGE))

        # Doctor has clinical operation and prescription manage
        self.assertTrue(has_permission(UserRole.DOCTOR, Permission.CLINICAL_OPERATION))
        self.assertTrue(has_permission(UserRole.DOCTOR, Permission.PRESCRIPTION_MANAGE))
        self.assertFalse(has_permission(UserRole.DOCTOR, Permission.USER_MANAGE))

        # Receptionist has billing and slot manage
        self.assertTrue(has_permission(UserRole.RECEPTIONIST, Permission.BILLING_MANAGE))
        self.assertFalse(has_permission(UserRole.RECEPTIONIST, Permission.PRESCRIPTION_MANAGE))

        # Invalid role raises ValueError on normalization
        with self.assertRaises(ValueError):
            UserRole.normalize("HACKER_ROLE")

    # -------------------------------------------------------------------------
    # 21. User Model Properties (is_active, set_role, last_login_at)
    # -------------------------------------------------------------------------
    def test_user_model_properties(self):
        u = User(
            username="clinician_1",
            password_hash=hash_password("Pass12345"),
            role="DOCTOR",
            status="Active",
        )
        self.assertTrue(u.is_active)
        u.is_active = False
        self.assertFalse(u.is_active)
        self.assertEqual(u.status, "Inactive")

        # set_role normalizes cleanly
        u.set_role("tenant_admin")
        self.assertEqual(u.role, "TENANT_ADMIN")

        with self.assertRaises(ValueError):
            u.set_role("invalid_role")


if __name__ == "__main__":
    unittest.main()

