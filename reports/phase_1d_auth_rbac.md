# Phase 1D — Production Authentication + RBAC Report

**Project:** Clinic Management CRM (`D:\telegram_bot`)  
**Phase:** 1D (Production Authentication & Role-Based Access Control)  
**Status:** **COMPLETED & VERIFIED**  
**Date:** October 5, 2026  

---

## 1. Executive Summary

Phase 1D transitions the clinic SaaS platform from legacy, single-clinic credential assumptions to a **production-ready multi-tenant authentication and Role-Based Access Control (RBAC) foundation**.

The authentication pipeline strictly follows the authoritative hierarchy:
$$\text{Authenticated User} \longrightarrow \text{User Identity} \longrightarrow \text{Role} \longrightarrow \text{Tenant ID} \longrightarrow \text{TenantContext}$$

Clients are strictly prevented from arbitrarily switching or spoofing clinic tenants. All 335 tests across the repository pass cleanly (**0 failed, 2 skipped**), preserving 100% backwards compatibility with Google Sheets, JSON files, Doctor Portal, CRM SPA, and Telegram bot workflows.

---

## 2. Authentication & RBAC Architecture

### 2.1 Target SaaS Roles

| Role | Scope | Description |
|---|---|---|
| **`SUPER_ADMIN`** | Platform | Platform owner; manages clinics/tenants, platform config, cross-tenant administration when explicitly requested. Does **not** have default clinical access. |
| **`TENANT_ADMIN`** | Clinic Tenant | Full clinic administrator; manages clinic staff, doctors, appointments, slots, billing, clinic settings, audit logs, and clinic RAG knowledge. |
| **`DOCTOR`** | Clinic Tenant | Verified clinician; manages own clinical schedule/slots, assigned patients, drafts and signs prescriptions, clinical operations. |
| **`RECEPTIONIST`**| Clinic Tenant | Front-desk staff; manages patient check-in, bookings, appointment slot availability, offline payment collection. |
| **`STAFF`** | Clinic Tenant | Operational staff; limited patient lookup and appointment status assistance. |
| **`PATIENT`** | Patient Identity | Patient self-service; access to own demographic profile, bookings, invoices, and prescriptions. |

### 2.2 Discrete Permissions & Capabilities

Implemented in [`app/core/rbac.py`](file:///d:/telegram_bot/app/core/rbac.py):
* **Platform:** `platform:manage`, `platform:config`, `platform:audit`
* **Tenant Admin:** `tenant:config`, `user:manage`, `doctor:manage`, `clinic:audit_view`, `knowledge:upload`
* **Clinical & Operations:** `clinical:operation`, `prescription:manage`, `appointment:manage`, `slot:manage`, `patient:manage`, `billing:manage`
* **Patient Self-Service:** `patient:self_service`

### 2.3 Role-Permission Matrix

```
┌─────────────────────┬───────────────────┬──────────────┬────────┬──────────────┬───────┬─────────┐
│ Permission          │ SUPER_ADMIN       │ TENANT_ADMIN │ DOCTOR │ RECEPTIONIST │ STAFF │ PATIENT │
├─────────────────────┼───────────────────┼──────────────┼────────┼──────────────┼───────┼─────────┤
│ platform:manage     │         ✓         │      -       │   -    │      -       │   -   │    -    │
│ platform:config     │         ✓         │      -       │   -    │      -       │   -   │    -    │
│ platform:audit      │         ✓         │      -       │   -    │      -       │   -   │    -    │
│ tenant:config       │         -         │      ✓       │   -    │      -       │   -   │    -    │
│ user:manage         │         -         │      ✓       │   -    │      -       │   -   │    -    │
│ doctor:manage       │         -         │      ✓       │   -    │      -       │   -   │    -    │
│ patient:manage      │         -         │      ✓       │   -    │      ✓       │   ✓   │    -    │
│ appointment:manage  │         -         │      ✓       │   ✓    │      ✓       │   ✓   │    -    │
│ slot:manage         │         -         │      ✓       │   ✓    │      ✓       │   -   │    -    │
│ prescription:manage │         -         │      ✓       │   ✓    │      -       │   -   │    -    │
│ billing:manage      │         -         │      ✓       │   -    │      ✓       │   -   │    -    │
│ clinic:audit_view   │         -         │      ✓       │   -    │      -       │   -   │    -    │
│ knowledge:upload    │         ✓         │      ✓       │   -    │      -       │   -   │    -    │
│ clinical:operation  │         -         │      ✓       │   ✓    │      -       │   -   │    -    │
│ patient:self_service│         -         │      -       │   -    │      -       │   -   │    ✓    │
└─────────────────────┴───────────────────┴──────────────┴────────┴──────────────┴───────┴─────────┘
```

> [!NOTE]
> Following the **Principle of Least Privilege**, `SUPER_ADMIN` does not automatically receive unrestricted clinical data access (e.g. browsing patient medical records or prescribing medications). Cross-tenant clinic oversight requires explicit tenant designation.

---

## 3. Password Security & Session Architecture

### 3.1 Password Security
* **Algorithm:** PBKDF2-HMAC-SHA256 with 100,000 iterations and a 16-byte cryptographically secure salt (`secrets.token_hex(16)`).
* **Storage:** Passwords are never stored in plaintext and never logged. Only the salt-prefixed hash format `pbkdf2:sha256:100000${salt}${digest}` is retained.
* **Verification:** Constant-time verification using `hmac.compare_digest` to prevent timing attacks.
* **Demo Backdoor:** The legacy `"1234"` demo password is disabled by default in production and development; attempts to use it without explicit opt-in are rejected.

### 3.2 Session & Token Design
* **Token Generation:** 32-byte cryptographic random bearer token (`secrets.token_urlsafe(32)`).
* **Transport:** Supported via `Authorization: Bearer <token>` and `HttpOnly`, `SameSite=Lax` cookies (`admin_session`).
* **Session Metadata:** Authoritative binding contains:
  ```python
  {
      "user_id": "usr_xxxx",
      "username": username,
      "email": email,
      "role": normalized_role,
      "tenant_id": tenant_id,
      "is_active": True,
      "doctor_id": doctor_id,
      "expires_at": iso_timestamp,
  }
  ```
* **Lifecycle & Invalidation:** Invalidation supported via `revoke_session(token)` and automatic expiration pruner. Inactive or suspended accounts are rejected on every request with `HTTP 401 Unauthorized`.

---

## 4. Tenant Context & Anti-Spoofing Protections

### 4.1 Authoritative Tenant Resolution
In [`app/core/tenant.py`](file:///d:/telegram_bot/app/core/tenant.py):
1. **Authenticated Sessions:** The session's `tenant_id` is strictly authoritative.
2. **Cross-Tenant Spoofing Prevention:** If a client presents an `Authorization` token bound to `tenant_A` and supplies `X-Tenant-ID: tenant_B`, the server immediately returns **`HTTP 403 Forbidden`**.
3. **Super Admin Exception:** `SUPER_ADMIN` is permitted to explicitly specify an `X-Tenant-ID` header to inspect or configure a specific clinic facility.
4. **Public / Unauthenticated Access:** If unauthenticated, `X-Tenant-ID` is accepted for public patient widget lookups, or defaults to `"default"` for backward compatibility.

---

## 5. Centralized Authorization Dependencies

Exported in [`app/core/rbac.py`](file:///d:/telegram_bot/app/core/rbac.py) and [`app/core/auth.py`](file:///d:/telegram_bot/app/core/auth.py):

* **`require_authenticated_user`**: Validates active, unexpired session; binds tenant context.
* **`require_role(*roles)`**: Dependency factory enforcing that `current_user["role"]` matches one of the specified roles.
* **`require_permission(permission)`**: Dependency factory checking capabilities against the `ROLE_PERMISSIONS` matrix.
* **Pre-configured dependencies:**
  * `require_super_admin`: Requires `SUPER_ADMIN`.
  * `require_tenant_admin`: Accepts `TENANT_ADMIN` and `SUPER_ADMIN`.
  * `require_doctor`: Accepts `DOCTOR`.
  * `require_receptionist`: Accepts `RECEPTIONIST`, `TENANT_ADMIN`, `SUPER_ADMIN`.
  * `require_staff`: Accepts `STAFF`, `RECEPTIONIST`, `TENANT_ADMIN`, `SUPER_ADMIN`.
  * `require_patient`: Accepts `PATIENT`.
  * `require_admin_or_doctor`: Accepts `TENANT_ADMIN`, `SUPER_ADMIN`, `DOCTOR`.

---

## 6. Route-Level Protections & Integration

### 6.1 Knowledge Upload Endpoint (`/api/v1/knowledge/upload`)
* In [`app/api/knowledge.py`](file:///d:/telegram_bot/app/api/knowledge.py), upload requires `Permission.KNOWLEDGE_UPLOAD`.
* `TENANT_ADMIN` and `SUPER_ADMIN` are permitted.
* `DOCTOR`, `RECEPTIONIST`, `STAFF`, and `PATIENT` are rejected with `HTTP 403 Forbidden`.
* Files are partitioned into tenant storage paths (`data/tenants/{tenant_id}/knowledge/`).

### 6.2 Doctor Portal & CRM Admin
* **Doctor Portal:** Authenticated clinicians are assigned `DOCTOR` role, permitting access to `/api/doctor/*` while preventing access to administrative settings.
* **CRM Admin:** Administrators operate under `TENANT_ADMIN` role semantics, permitting clinic configuration and doctor/patient management.
* **Frontend Compatibility:** [`frontend/js/auth.js`](file:///d:/telegram_bot/frontend/js/auth.js) upgraded to evaluate `getRole()`, `isSuperAdmin()`, `isAdmin()`, `isDoctor()`, `isReceptionist()`, and `isStaff()`.

---

## 7. Verification & Test Results

### 7.1 Phase 1D Dedicated Suite (`tests/test_phase1d_auth_rbac.py`)
**21 passed, 0 failed:**
1. `test_valid_login` — PASSED
2. `test_invalid_password` — PASSED
3. `test_inactive_user_cannot_login_or_access` — PASSED
4. `test_password_hash_is_not_plaintext` — PASSED
5. `test_1234_demo_password_remains_disabled_by_default` — PASSED
6. `test_authenticated_user_gets_correct_role` — PASSED
7. `test_authenticated_user_gets_correct_tenant` — PASSED
8. `test_client_tenant_spoofing_returns_403` — PASSED
9. `test_tenant_admin_cannot_access_another_tenant` — PASSED
10. `test_doctor_cannot_access_tenant_admin_endpoints` — PASSED
11. `test_receptionist_cannot_access_admin_only_endpoints` — PASSED
12. `test_staff_permissions_are_restricted` — PASSED
13. `test_patient_cannot_access_staff_or_admin_endpoints` — PASSED
14. `test_super_admin_role_works` — PASSED
15. `test_logout_and_session_invalidation_works` — PASSED
16. `test_expired_token_rejected` — PASSED
17. `test_knowledge_upload_respects_tenant_and_role` — PASSED
18. `test_role_supplied_by_client_cannot_elevate_privileges` — PASSED
19. `test_user_id_supplied_by_client_cannot_bypass_authorization` — PASSED
20. `test_permission_matrix_and_helpers` — PASSED
21. `test_user_model_properties` — PASSED

### 7.2 Regression Suites
* **Phase 1A + 1B + 1C Tests:** **34 passed, 0 failed**
* **Full Repository Test Suite:** **335 passed, 2 skipped, 0 failed** (in 54.57s)
* **Application Factory Import:** `XYZ Clinic AI Assistant & CRM` loaded cleanly.
* **Health Check Endpoint:** `GET /health?details=true` returned `HTTP 200 OK` (`rag_available: True`).

---

## 8. Summary of Files Changed

* **Created:**
  * [`app/core/rbac.py`](file:///d:/telegram_bot/app/core/rbac.py) — SaaS role enums, permission matrix, and FastAPI authorization dependencies.
  * [`tests/test_phase1d_auth_rbac.py`](file:///d:/telegram_bot/tests/test_phase1d_auth_rbac.py) — Comprehensive 21-case test suite.
  * [`reports/phase_1d_auth_rbac.md`](file:///d:/telegram_bot/reports/phase_1d_auth_rbac.md) — Documentation report.
* **Modified:**
  * [`app/core/auth.py`](file:///d:/telegram_bot/app/core/auth.py) — Enhanced session management, active status validation, tenant context binding, and RBAC normalization.
  * [`app/core/tenant.py`](file:///d:/telegram_bot/app/core/tenant.py) — Added `SUPER_ADMIN` explicit tenant handling and anti-spoofing for all other roles.
  * [`app/db/models/user.py`](file:///d:/telegram_bot/app/db/models/user.py) — Added `is_active` getter/setter, `last_login_at` synonym, and `set_role` validator.
  * [`app/api/knowledge.py`](file:///d:/telegram_bot/app/api/knowledge.py) — Protected with `Permission.KNOWLEDGE_UPLOAD` and tenant-scoped directory routing.
  * [`frontend/js/auth.js`](file:///d:/telegram_bot/frontend/js/auth.js) — Expanded role helpers for all SaaS roles.

---

## 9. Checkpoint & Next Steps

Phase 1D is **100% complete and verified**. All implementation is paused. Awaiting explicit instruction before proceeding to **Phase 1E** (PostgreSQL Data Migration & Persistence Switch).
