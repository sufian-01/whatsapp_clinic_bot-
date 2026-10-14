# Production Readiness Checklist & Deployment Operations Guide

**Project:** Clinic Management SaaS (`D:\telegram_bot`)  
**Database:** PostgreSQL 18.6 (`localhost:5432/clinic_db`)  
**Alembic Head:** `523c13307c3c`  
**Test Suite Verification:** 418 passed, 2 skipped, 0 failed (100% green across 420 collected tests)  
**Date:** October 13, 2026  

---

## 1. Production Readiness Master Checklist

| Area / Component | Verification Criteria | Status | Notes |
| :--- | :--- | :--- | :--- |
| **Relational Database** | 12 tables in PostgreSQL `public` schema with PK, FK, and unique constraints | **VERIFIED** | Active on PostgreSQL 18.6 (`clinic_db`). |
| **Alembic Migrations** | Schema version matches code head (`523c13307c3c`) | **VERIFIED** | Upgrades run cleanly without data destruction. |
| **Operational Cutover** | All CRM, Doctor, and Chatbot reads/writes persist in PostgreSQL | **VERIFIED** | Google Sheets/JSON stores no longer receive operational writes. |
| **Multi-Tenant Isolation** | Zero cross-tenant data leakage across all entities and queries | **VERIFIED** | 11 automated isolation tests passing against PostgreSQL. |
| **Super Admin Platform Scope** | Platform level scope (`platform` / `None`); cannot access clinic without header | **VERIFIED** | Tested in `test_super_admin_isolation_fix.py`. |
| **Concurrency & Double-Booking**| Database constraints + `SELECT ... FOR UPDATE` row locks | **VERIFIED** | Tested in `test_unified_workflow_and_concurrency.py`. |
| **Prescription System** | Draft, finalization, amendment history, ReportLab PDF generation | **VERIFIED** | Tested in `test_prescription_system.py` and `test_postgres_live_operational_cutover.py`. |
| **Authentication & RBAC** | Cryptographic token sessions, PBKDF2 password hashing, lockout guards | **VERIFIED** | Tested in `test_phase1d_auth_rbac.py`. |
| **Audit Logging** | Immutable audit logs committed directly to `audit_logs` table | **VERIFIED** | 1,142 audit events active in `clinic_db`. |
| **Health Check & Ping** | `/health?details=true` pings database with `SELECT 1` | **VERIFIED** | Returns HTTP 200 with database status `connected`. |
| **WhatsApp Security** | HMAC-SHA256 signature verification, 15-min replay defense, deduplication | **VERIFIED** | 12 automated unit/integration tests passing. |
| **Data Backup** | Verified JSON and SQL backup archives in `data/` | **VERIFIED** | Pre-migration and pre-cutover archives stored. |
| **WhatsApp Production Traffic** | Live Meta WABA webhook delivery | **BLOCKED** | Awaiting production Meta System User token in `.env`. |
| **Telegram Production Token** | Telegram Bot API token | **BLOCKED** | Test token active in development; awaiting prod token. |
| **Production SMTP / Gmail** | Patient confirmation email delivery | **BLOCKED** | Mock active; awaiting production OAuth secrets. |
| **Online Payment Gateway** | Razorpay / Stripe automated webhook capture | **NOT_IMPLEMENTED** | Offline UPI QR & Cash recording active. |
| **SaaS Subscription Billing** | Automated recurring SaaS plans | **NOT_IMPLEMENTED** | Tenant provisioning active; recurring billing not built. |

---

## 2. Server Startup and Verification Commands

### 2.1 Starting the FastAPI Production Backend
From `D:\telegram_bot`:
```powershell
# Set environment (or rely on .env)
$env:DATABASE_URL="postgresql+psycopg://postgres:your_password@localhost:5432/clinic_db"
$env:APP_ENV="production"

# Start Uvicorn ASGI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 2.2 Verifying Database Connectivity via Health Endpoint
```powershell
curl http://localhost:8000/health?details=true
```
Expected response (`HTTP 200 OK`):
```json
{
  "status": "ok",
  "uptime_seconds": 3.42,
  "clinic": "XYZ Clinic",
  "rag_available": true,
  "database": {
    "status": "connected",
    "type": "postgresql"
  },
  "storage": {
    "free_gb": 313.2,
    "total_gb": 379.28
  }
}
```

### 2.3 Running the Live Integration Test Suite
```powershell
python -m pytest tests/test_postgres_live_operational_cutover.py -v
```

---

## 3. pgAdmin Verification Guide

To inspect the tables, constraints, and operational data in pgAdmin 4:

1. **Open pgAdmin 4** on your machine.
2. In the left-hand Browser tree, expand:
   `Servers` -> `Local PostgreSQL` -> `Databases` -> `clinic_db` -> `Schemas` -> `public` -> `Tables`.
3. You will observe all 12 operational tables:
   - `alembic_version` (Revision: `523c13307c3c`)
   - `appointment_slots` (23 rows)
   - `appointments` (11 rows)
   - `audit_logs` (1,142 rows)
   - `clinics` (1 row)
   - `doctors` (8 rows)
   - `invoices` (11 rows)
   - `patients` (16 rows)
   - `payments` (11 rows)
   - `prescription_items` (66 rows)
   - `prescriptions` (56 rows)
   - `users` (5 rows)
4. Right-click on any table (e.g. `appointments`, `prescriptions`, `patients`, `appointment_slots`) and choose **View/Edit Data** -> **All Rows**.
5. All records created during testing or normal operation are directly visible.

---

## 4. Production Security & Hardening Guidelines

1. **Environment Variables & Secrets:**
   - Never commit `.env` or database passwords to git.
   - Verify `.gitignore` contains `.env`, `data/backup_*`, and local credentials.
2. **Database Networking:**
   - PostgreSQL should not expose port 5432 to the public internet. Use internal VPC networking or SSL (`sslmode=require`).
3. **Database Connection Pool:**
   - Configured in `app/db/session.py` with `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`, and `pool_recycle=1800` (30 minutes).
4. **Account Lockout & Brute Force Defense:**
   - After 5 consecutive failed login attempts, the account is temporarily locked for 15 minutes.
5. **Webhook Deduplication & Replay Defense:**
   - WhatsApp webhooks older than 15 minutes are discarded.
   - Inbound message IDs are deduplicated using in-memory TTL caching to prevent double-bookings from Meta webhook retry logic.

---

## 5. Remaining Pre-Launch Configuration Steps

Before opening the platform to public patient traffic:

1. **Meta WhatsApp Cloud API Credentials:**
   - Obtain a Permanent System User Access Token from Meta Business Manager.
   - Set in `.env`:
     ```ini
     WHATSAPP_ENABLED=true
     WHATSAPP_ACCESS_TOKEN=<your_permanent_system_user_token>
     WHATSAPP_PHONE_NUMBER_ID=<meta_phone_number_id>
     WHATSAPP_BUSINESS_ACCOUNT_ID=<meta_waba_id>
     WHATSAPP_APP_SECRET=<meta_app_secret>
     WHATSAPP_VERIFY_TOKEN=<high_entropy_secret_string>
     WHATSAPP_TENANT_PHONE_MAP={"<meta_phone_number_id>": "default"}
     ```
   - Register webhook callback URL in Meta Developer Dashboard:
     `https://<your_domain>/webhook/whatsapp`
2. **Production Telegram Bot Token:**
   - Obtain from `@BotFather`.
   - Update `TELEGRAM_BOT_TOKEN=<production_token>` in `.env`.
3. **Google Workspace OAuth (Automated Emails):**
   - Provide production `client_secrets.json` to enable automated patient appointment confirmations and invoice emailing.

