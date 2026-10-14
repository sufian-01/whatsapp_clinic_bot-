"""Comprehensive tests for Phase 1E: Super Admin and Tenant Management Foundation.

Verifies:
1. Super Admin login
2. Non-Super Admin cannot access Super Admin APIs
3. Super Admin can create tenant
4. Tenant receives unique ID
5. Tenant defaults correctly
6. Tenant admin creation
7. Tenant admin belongs to correct tenant
8. Tenant admin cannot become Super Admin
9. Tenant activation
10. Tenant deactivation
11. Tenant suspension
12. Suspended tenant access denied
13. Inactive tenant access denied
14. Tenant reactivation
15. Tenant A isolation
16. Tenant B isolation
17. Super Admin explicit cross-tenant operation
18. Unauthorized cross-tenant operation denied
19. Platform audit logs
20. Tenant admin cannot access platform audit logs
21. Secrets not exposed in API responses
22. Password hashes not exposed
23. Role escalation prevented
24. Tenant_id spoofing prevented
25. Super Admin API routes protected server-side
"""

from pathlib import Path
import unittest
from unittest.mock import MagicMock

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.testclient import TestClient

from app.api.super_admin import create_super_admin_router
from app.core.auth import (
    create_session,
    hash_password,
    revoke_session,
    verify_password,
)
from app.core.config import Settings
from app.core.rbac import (
    UserRole,
    require_authenticated_user,
    require_super_admin,
    require_tenant_admin,
)
from app.core.tenant import (
    TenantContext,
    get_tenant_status,
    reset_tenant_status_cache,
    resolve_tenant_context,
    set_tenant_status,
)
from app.services.tenant_management_service import TenantManagementService


class Phase1eSuperAdminTests(unittest.TestCase):
    def setUp(self):
        reset_tenant_status_cache()
        self.settings = Settings(
            clinic_name="Platform SaaS",
            telegram_bot_token="tok",
            telegram_webhook_secret="sec",
            gemini_api_key="key",
            gemini_model="mod",
            telegram_webhook_url="url",
            knowledge_dir=Path("k"),
            vectorstore_dir=Path("v"),
            super_admin_username="superadmin",
            super_admin_password="SuperPassword123",
            super_admin_password_hash=hash_password("SuperPassword123"),
            crm_admin_username="admin",
            crm_admin_password="AdminPassword123",
            crm_admin_password_hash=hash_password("AdminPassword123"),
        )
        self.service = TenantManagementService()
        self.app = FastAPI()

        # Mount Super Admin router
        self.app.include_router(create_super_admin_router(self.service, self.settings))

        # Sample clinical/operational tenant-scoped endpoint to verify tenant lifecycle & isolation
        @self.app.get("/api/tenant-resource")
        async def tenant_resource(
            u: dict = Depends(require_authenticated_user),
            ctx: TenantContext = Depends(resolve_tenant_context),
        ):
            return {
                "status": "ok",
                "tenant_id": ctx.tenant_id,
                "user": u["username"],
                "role": u["role"],
            }

        self.client = TestClient(self.app)

        # Tokens
        self.super_token = create_session("superadmin", role="SUPER_ADMIN", tenant_id="platform")
        self.tenant_a_admin_token = create_session("admin_a", role="TENANT_ADMIN", tenant_id="clinic_a")
        self.doctor_token = create_session("dr_smith", role="DOCTOR", tenant_id="clinic_a")
        self.staff_token = create_session("staff_john", role="STAFF", tenant_id="clinic_a")

    def tearDown(self):
        reset_tenant_status_cache()

    # -------------------------------------------------------------------------
    # 1. Super Admin Login
    # -------------------------------------------------------------------------
    def test_super_admin_login(self):
        res = self.client.post(
            "/api/super-admin/auth/login",
            json={"username": "superadmin", "password": "SuperPassword123"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("token", data)
        self.assertEqual(data["username"], "superadmin")
        self.assertEqual(data["role"], "SUPER_ADMIN")
        self.assertEqual(data["tenant_id"], "platform")

    # -------------------------------------------------------------------------
    # 2. Non-Super Admin Cannot Access Super Admin APIs
    # -------------------------------------------------------------------------
    def test_non_super_admin_cannot_access_super_admin_apis(self):
        # Tenant admin attempt
        res_admin = self.client.get(
            "/api/super-admin/dashboard/stats",
            headers={"Authorization": f"Bearer {self.tenant_a_admin_token}"},
        )
        self.assertEqual(res_admin.status_code, 403)

        # Doctor attempt
        res_doc = self.client.get(
            "/api/super-admin/tenants",
            headers={"Authorization": f"Bearer {self.doctor_token}"},
        )
        self.assertEqual(res_doc.status_code, 403)

        # Staff attempt
        res_staff = self.client.get(
            "/api/super-admin/audit-logs",
            headers={"Authorization": f"Bearer {self.staff_token}"},
        )
        self.assertEqual(res_staff.status_code, 403)

    # -------------------------------------------------------------------------
    # 3. Super Admin Can Create Tenant
    # -------------------------------------------------------------------------
    def test_super_admin_can_create_tenant(self):
        payload = {
            "name": "Apollo Care Center",
            "phone": "9876543210",
            "email": "contact@apollocare.com",
            "timezone": "Asia/Kolkata",
            "currency": "INR",
        }
        res = self.client.post(
            "/api/super-admin/tenants",
            headers={"Authorization": f"Bearer {self.super_token}"},
            json=payload,
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["name"], "Apollo Care Center")
        self.assertTrue(data["id"].startswith("cln_"))
        self.assertEqual(data["status"], "ACTIVE")

    # -------------------------------------------------------------------------
    # 4. Tenant Receives Unique ID
    # -------------------------------------------------------------------------
    def test_tenant_receives_unique_id(self):
        t1 = self.client.post(
            "/api/super-admin/tenants",
            headers={"Authorization": f"Bearer {self.super_token}"},
            json={"name": "Clinic Alpha"},
        ).json()
        t2 = self.client.post(
            "/api/super-admin/tenants",
            headers={"Authorization": f"Bearer {self.super_token}"},
            json={"name": "Clinic Alpha"},
        ).json()
        self.assertNotEqual(t1["id"], t2["id"])

    # -------------------------------------------------------------------------
    # 5. Tenant Defaults Correctly
    # -------------------------------------------------------------------------
    def test_tenant_defaults_correctly(self):
        t = self.client.post(
            "/api/super-admin/tenants",
            headers={"Authorization": f"Bearer {self.super_token}"},
            json={"name": "Green Valley Medical"},
        ).json()
        self.assertEqual(t["timezone"], "Asia/Kolkata")
        self.assertEqual(t["currency"], "INR")
        self.assertEqual(t["working_days"], "Monday - Friday")
        self.assertEqual(t["working_hours"], "09:00 - 17:00")
        self.assertEqual(t["appointment_duration"], 30)
        self.assertEqual(t["status"], "ACTIVE")

    # -------------------------------------------------------------------------
    # 6. Tenant Admin Creation
    # -------------------------------------------------------------------------
    def test_tenant_admin_creation(self):
        t = self.client.post(
            "/api/super-admin/tenants",
            headers={"Authorization": f"Bearer {self.super_token}"},
            json={"name": "Lotus Health", "id": "lotus_health"},
        ).json()

        res = self.client.post(
            f"/api/super-admin/tenants/{t['id']}/admins",
            headers={"Authorization": f"Bearer {self.super_token}"},
            json={
                "username": "admin_lotus",
                "password": "Password12345",
                "full_name": "Dr. Lotus Admin",
                "email": "admin@lotus.com",
            },
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["username"], "admin_lotus")
        self.assertEqual(data["tenant_id"], "lotus_health")
        self.assertEqual(data["role"], "TENANT_ADMIN")
        self.assertNotIn("password_hash", data)
        self.assertNotIn("password", data)

    # -------------------------------------------------------------------------
    # 7. Tenant Admin Belongs to Correct Tenant
    # -------------------------------------------------------------------------
    def test_tenant_admin_belongs_to_correct_tenant(self):
        t = self.client.post(
            "/api/super-admin/tenants",
            headers={"Authorization": f"Bearer {self.super_token}"},
            json={"name": "City Medical", "id": "city_med"},
        ).json()

        admin_data = self.client.post(
            f"/api/super-admin/tenants/{t['id']}/admins",
            headers={"Authorization": f"Bearer {self.super_token}"},
            json={
                "username": "city_admin",
                "password": "SecurePassword1",
            },
        ).json()
        self.assertEqual(admin_data["tenant_id"], "city_med")

    # -------------------------------------------------------------------------
    # 8. Tenant Admin Cannot Become Super Admin
    # -------------------------------------------------------------------------
    def test_tenant_admin_cannot_become_super_admin(self):
        t = self.client.post(
            "/api/super-admin/tenants",
            headers={"Authorization": f"Bearer {self.super_token}"},
            json={"name": "Health Plus", "id": "health_plus"},
        ).json()

        # Service enforces role is TENANT_ADMIN regardless of input
        res = self.client.post(
            f"/api/super-admin/tenants/{t['id']}/admins",
            headers={"Authorization": f"Bearer {self.super_token}"},
            json={
                "username": "health_admin_user",
                "password": "Password123",
                "role": "SUPER_ADMIN",  # Attempted escalation
            },
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["role"], "TENANT_ADMIN")

    # -------------------------------------------------------------------------
    # 9. Tenant Activation
    # -------------------------------------------------------------------------
    def test_tenant_activation(self):
        t = self.client.post(
            "/api/super-admin/tenants",
            headers={"Authorization": f"Bearer {self.super_token}"},
            json={"name": "Clinic Act", "id": "clinic_act", "status": "INACTIVE"},
        ).json()
        self.assertEqual(t["status"], "INACTIVE")

        res = self.client.post(
            f"/api/super-admin/tenants/{t['id']}/activate",
            headers={"Authorization": f"Bearer {self.super_token}"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "ACTIVE")
        self.assertEqual(get_tenant_status("clinic_act"), "ACTIVE")

    # -------------------------------------------------------------------------
    # 10. Tenant Deactivation
    # -------------------------------------------------------------------------
    def test_tenant_deactivation(self):
        t = self.client.post(
            "/api/super-admin/tenants",
            headers={"Authorization": f"Bearer {self.super_token}"},
            json={"name": "Clinic Deact", "id": "clinic_deact"},
        ).json()

        res = self.client.post(
            f"/api/super-admin/tenants/{t['id']}/deactivate",
            headers={"Authorization": f"Bearer {self.super_token}"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "INACTIVE")
        self.assertEqual(get_tenant_status("clinic_deact"), "INACTIVE")

    # -------------------------------------------------------------------------
    # 11. Tenant Suspension
    # -------------------------------------------------------------------------
    def test_tenant_suspension(self):
        t = self.client.post(
            "/api/super-admin/tenants",
            headers={"Authorization": f"Bearer {self.super_token}"},
            json={"name": "Clinic Susp", "id": "clinic_susp"},
        ).json()

        res = self.client.post(
            f"/api/super-admin/tenants/{t['id']}/suspend",
            headers={"Authorization": f"Bearer {self.super_token}"},
            json={"reason": "Billing non-payment"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "SUSPENDED")
        self.assertEqual(get_tenant_status("clinic_susp"), "SUSPENDED")

    # -------------------------------------------------------------------------
    # 12. Suspended Tenant Access Denied
    # -------------------------------------------------------------------------
    def test_suspended_tenant_access_denied(self):
        # Create and suspend clinic_susp_test
        self.client.post(
            "/api/super-admin/tenants",
            headers={"Authorization": f"Bearer {self.super_token}"},
            json={"name": "Suspended Clinic", "id": "clinic_susp_test"},
        )
        self.client.post(
            "/api/super-admin/tenants/clinic_susp_test/suspend",
            headers={"Authorization": f"Bearer {self.super_token}"},
        )

        # User belonging to clinic_susp_test attempts to access normal tenant endpoint
        user_tok = create_session("dr_locked", role="DOCTOR", tenant_id="clinic_susp_test")
        res = self.client.get(
            "/api/tenant-resource",
            headers={"Authorization": f"Bearer {user_tok}"},
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("suspended", res.json()["detail"].lower())

    # -------------------------------------------------------------------------
    # 13. Inactive Tenant Access Denied
    # -------------------------------------------------------------------------
    def test_inactive_tenant_access_denied(self):
        self.client.post(
            "/api/super-admin/tenants",
            headers={"Authorization": f"Bearer {self.super_token}"},
            json={"name": "Inactive Clinic", "id": "clinic_inact_test"},
        )
        self.client.post(
            "/api/super-admin/tenants/clinic_inact_test/deactivate",
            headers={"Authorization": f"Bearer {self.super_token}"},
        )

        user_tok = create_session("admin_inact", role="TENANT_ADMIN", tenant_id="clinic_inact_test")
        res = self.client.get(
            "/api/tenant-resource",
            headers={"Authorization": f"Bearer {user_tok}"},
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("inactive", res.json()["detail"].lower())

    # -------------------------------------------------------------------------
    # 14. Tenant Reactivation
    # -------------------------------------------------------------------------
    def test_tenant_reactivation(self):
        # Deactivate
        self.client.post(
            "/api/super-admin/tenants",
            headers={"Authorization": f"Bearer {self.super_token}"},
            json={"name": "Reactivate Clinic", "id": "clinic_react"},
        )
        self.client.post(
            "/api/super-admin/tenants/clinic_react/deactivate",
            headers={"Authorization": f"Bearer {self.super_token}"},
        )

        user_tok = create_session("admin_react", role="TENANT_ADMIN", tenant_id="clinic_react")
        # Denied while inactive
        res1 = self.client.get(
            "/api/tenant-resource",
            headers={"Authorization": f"Bearer {user_tok}"},
        )
        self.assertEqual(res1.status_code, 403)

        # Reactivate
        self.client.post(
            "/api/super-admin/tenants/clinic_react/activate",
            headers={"Authorization": f"Bearer {self.super_token}"},
        )

        # Succeeded after reactivation
        res2 = self.client.get(
            "/api/tenant-resource",
            headers={"Authorization": f"Bearer {user_tok}"},
        )
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.json()["tenant_id"], "clinic_react")

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # 15. Tenant A Isolation
    # -------------------------------------------------------------------------
    def test_tenant_a_isolation(self):
        tok_a = create_session("admin_alpha", role="TENANT_ADMIN", tenant_id="tenant_alpha")
        res_a = self.client.get(
            "/api/tenant-resource",
            headers={"Authorization": f"Bearer {tok_a}"},
        )
        self.assertEqual(res_a.status_code, 200)
        self.assertEqual(res_a.json()["tenant_id"], "tenant_alpha")

    # -------------------------------------------------------------------------
    # 16. Tenant B Isolation
    # -------------------------------------------------------------------------
    def test_tenant_b_isolation(self):
        tok_b = create_session("admin_beta", role="TENANT_ADMIN", tenant_id="tenant_beta")
        res_b = self.client.get(
            "/api/tenant-resource",
            headers={"Authorization": f"Bearer {tok_b}"},
        )
        self.assertEqual(res_b.status_code, 200)
        self.assertEqual(res_b.json()["tenant_id"], "tenant_beta")

    # -------------------------------------------------------------------------
    # 17. Super Admin Explicit Cross-Tenant Operation
    # -------------------------------------------------------------------------
    def test_super_admin_explicit_cross_tenant_operation(self):
        # Super admin explicitly specifies X-Tenant-ID header
        res = self.client.get(
            "/api/tenant-resource",
            headers={"Authorization": f"Bearer {self.super_token}", "X-Tenant-ID": "target_clinic_xyz"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["tenant_id"], "target_clinic_xyz")

    # -------------------------------------------------------------------------
    # 18. Unauthorized Cross-Tenant Operation Denied
    # -------------------------------------------------------------------------
    def test_unauthorized_cross_tenant_operation_denied(self):
        # Tenant admin A attempts to supply X-Tenant-ID for tenant B
        res = self.client.get(
            "/api/tenant-resource",
            headers={"Authorization": f"Bearer {self.tenant_a_admin_token}", "X-Tenant-ID": "tenant_b"},
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("Access forbidden", res.json()["detail"])

    # -------------------------------------------------------------------------
    # 19. Platform Audit Logs
    # -------------------------------------------------------------------------
    def test_platform_audit_logs(self):
        # Trigger an administrative action
        self.client.post(
            "/api/super-admin/tenants",
            headers={"Authorization": f"Bearer {self.super_token}"},
            json={"name": "Audit Clinic", "id": "audit_clinic"},
        )

        res = self.client.get(
            "/api/super-admin/audit-logs",
            headers={"Authorization": f"Bearer {self.super_token}"},
        )
        self.assertEqual(res.status_code, 200)
        logs = res.json()
        self.assertTrue(len(logs) > 0)
        actions = [l["action"] for l in logs]
        self.assertIn("TENANT_CREATE", actions)

    # -------------------------------------------------------------------------
    # 20. Tenant Admin Cannot Access Platform Audit Logs
    # -------------------------------------------------------------------------
    def test_tenant_admin_cannot_access_platform_audit_logs(self):
        res = self.client.get(
            "/api/super-admin/audit-logs",
            headers={"Authorization": f"Bearer {self.tenant_a_admin_token}"},
        )
        self.assertEqual(res.status_code, 403)

    # -------------------------------------------------------------------------
    # 21. Secrets Not Exposed in API Responses
    # -------------------------------------------------------------------------
    def test_secrets_not_exposed_in_api_responses(self):
        res = self.client.get(
            "/api/super-admin/tenants",
            headers={"Authorization": f"Bearer {self.super_token}"},
        )
        self.assertEqual(res.status_code, 200)
        tenants = res.json()
        for t in tenants:
            self.assertNotIn("upi_id", t)
            self.assertNotIn("database_url", t)
            self.assertNotIn("secret_key", t)

    # -------------------------------------------------------------------------
    # 22. Password Hashes Not Exposed
    # -------------------------------------------------------------------------
    def test_password_hashes_not_exposed(self):
        t = self.client.post(
            "/api/super-admin/tenants",
            headers={"Authorization": f"Bearer {self.super_token}"},
            json={"name": "Hash Check Clinic"},
        ).json()

        admin_res = self.client.post(
            f"/api/super-admin/tenants/{t['id']}/admins",
            headers={"Authorization": f"Bearer {self.super_token}"},
            json={
                "username": "hash_check_admin",
                "password": "Password123!",
            },
        )
        self.assertEqual(admin_res.status_code, 201)
        data = admin_res.json()
        self.assertNotIn("password_hash", data)
        self.assertNotIn("password", data)

    # -------------------------------------------------------------------------
    # 23. Role Escalation Prevented
    # -------------------------------------------------------------------------
    def test_role_escalation_prevented(self):
        # Client tries to send role in header or params
        res = self.client.get(
            "/api/super-admin/dashboard/stats",
            headers={
                "Authorization": f"Bearer {self.tenant_a_admin_token}",
                "X-User-Role": "SUPER_ADMIN",
            },
            params={"role": "SUPER_ADMIN"},
        )
        self.assertEqual(res.status_code, 403)

    # -------------------------------------------------------------------------
    # 24. Tenant ID Spoofing Prevented
    # -------------------------------------------------------------------------
    def test_tenant_id_spoofing_prevented(self):
        res = self.client.get(
            "/api/tenant-resource",
            headers={
                "Authorization": f"Bearer {self.doctor_token}",
                "X-Tenant-ID": "spoofed_target_clinic",
            },
        )
        self.assertEqual(res.status_code, 403)

    # -------------------------------------------------------------------------
    # 25. Super Admin API Routes Protected Server-Side
    # -------------------------------------------------------------------------
    def test_super_admin_api_routes_protected_server_side(self):
        endpoints = [
            ("GET", "/api/super-admin/dashboard/stats"),
            ("GET", "/api/super-admin/tenants"),
            ("POST", "/api/super-admin/tenants"),
            ("GET", "/api/super-admin/audit-logs"),
        ]
        for method, ep in endpoints:
            # Without token -> 401
            res_no_auth = self.client.request(method, ep)
            self.assertEqual(res_no_auth.status_code, 401)

            # With non-super token -> 403
            res_forbidden = self.client.request(
                method, ep, headers={"Authorization": f"Bearer {self.staff_token}"}
            )
            self.assertEqual(res_forbidden.status_code, 403)


if __name__ == "__main__":
    unittest.main()
