# PostgreSQL Data Reconciliation & Source-of-Truth Audit Report

**Project:** Clinic Management SaaS  
**Target Database:** PostgreSQL 18.6 (`localhost:5432/clinic_db`)  
**Alembic Schema Revision:** `523c13307c3c`  
**Audit Date:** October 13, 2026  

---

## 1. Executive Summary

This report reconciles the clinical operational data between the legacy stores (Google Sheets, `data/prescriptions.json`, `data/doctor_accounts.json`, `data/audit_logs.jsonl`) and the live PostgreSQL database (`clinic_db`).

**Key Verification Highlights:**
1. **Zero Data Loss:** 100% of valid business records across doctors, patients, appointments, slots, prescriptions, line items, and audit logs were migrated to PostgreSQL.
2. **PostgreSQL as Single Source of Truth:** All active runtime operations (slot creation, bookings, cancellations, rescheduling, prescription drafts, finalizations, amendments, doctor accounts, payments, and invoices) now read and write directly to PostgreSQL.
3. **No Uncontrolled Dual Writes:** Legacy files (`data/prescriptions.json`, `data/doctor_accounts.json`) remain archived in backups; new operational records are committed transactionally to PostgreSQL tables.

---

## 2. Table-by-Table Data Reconciliation Matrix

The following table compares the original source records against the live PostgreSQL records in `clinic_db`:

| Relational Table | Legacy Source Store | Source Row Count | Live PostgreSQL Count | Reconciliation Status | Explanation of Variance |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `clinics` | Seed / Config | 1 | **1** | **Reconciled** | Root tenant `default` (`XYZ Clinic`) provisioned. |
| `users` | `doctor_accounts.json` + Admin | 4 | **5** | **Reconciled** | 4 original accounts (2 admins, 2 doctors) + 1 new doctor account created and verified during live API operational cutover testing (`dr_neha_cutover`). |
| `doctors` | Google Sheet `doctor!A1:H` | 8 | **8** | **Reconciled** | Doctors `DOC001` through `DOC008` migrated with full consultation fees, specialties, and schedules. |
| `patients` | Google Sheet `patient!A1:O` | 10 | **16** | **Reconciled (10 + 2 + 4)**| 10 original Sheet patients + 2 legacy prescription foreign-key stubs + 4 new patients registered during live end-to-end booking tests. |
| `appointment_slots` | Google Sheet `appointment_slots!A1:J` | 21 | **23** | **Reconciled (21 + 2)**| 21 original slots + 2 new slots created and booked during live API operational cutover testing. |
| `appointments` | Google Sheet `patient!A1:O` bookings | 10 | **11** | **Reconciled (10 + 1)**| 10 original bookings (`TKN-0001` to `TKN-0010`) + 1 appointment booked during live API operational cutover testing. |
| `invoices` | Generated invoices | 10 | **11** | **Reconciled (10 + 1)**| 10 original invoices (`INV-0001` to `INV-0010`) + 1 newly generated invoice during live appointment booking. |
| `payments` | Google Sheet payment records | 10 | **11** | **Reconciled (10 + 1)**| 10 original payment transactions (`PAY-0001` to `PAY-0010`) + 1 new payment recorded and marked Paid via API. |
| `prescriptions` | `data/prescriptions.json` | 41 | **56** | **Reconciled (41 + 15)**| 41 initial prescriptions + 15 clinical prescriptions drafted, finalized, and amended across live test suites. |
| `prescription_items`| `data/prescriptions.json` items | 41 | **66** | **Reconciled (41 + 25)**| 41 initial items + 25 normalized medication items added in live test cases. |
| `audit_logs` | `data/audit_logs.jsonl` | 1,082 | **1,142** | **Reconciled (1082 + 60)**| 1,082 historical audit events + 60 new compliance events recorded directly into PostgreSQL by active workflows. |
| `alembic_version` | Migration revision | 1 | **1** | **Reconciled** | Migration head revision `523c13307c3c`. |

---

## 3. Detailed Variance Analysis

### 3.1 Patient Count (10 Source -> 16 Live)
1. **Initial Migration:** The legacy Google Sheet contained 10 patient rows (`PAT001` to `PAT010`).
2. **Foreign Key Stubs (+2):** In historical test records in `data/prescriptions.json`, 2 prescriptions referenced legacy patient IDs that were not present in the Google Sheet. To preserve medical prescription history while satisfying the PostgreSQL foreign key constraint `fk_prescriptions_patient_id_patients`, the migration pipeline generated 2 stub records (`Legacy Prescription Patient`).
3. **Live API Tests (+4):** Live end-to-end tests (`tests/test_postgres_live_operational_cutover.py`, `tests/test_live_two_clinics_isolation.py`) created new patient bookings (`PAT-A-*`, `PAT-B-*`, `Priya Sharma`), all of which persisted correctly to PostgreSQL.
4. **Current Total:** 16 active patient records in PostgreSQL `patients` table.

### 3.2 Prescription & Medication Items (41 -> 56 Prescriptions, 41 -> 66 Items)
1. **Initial Migration:** 41 digital prescriptions were migrated from `data/prescriptions.json`.
2. **Live Clinical Finalization & Amendments (+15 Prescriptions, +25 Items):** The Doctor Portal API endpoints were executed in live tests to draft, finalize, and amend multi-medication prescriptions (e.g. Paracetamol, Levocetirizine, Montelukast, Fluticasone). Each medication is normalized into `prescription_items` linked by foreign key to `prescriptions.id`.

### 3.3 Appointments, Invoices & Payments (+1 New Linked Lifecycle)
1. **Atomic Transaction:** In `test_03_appointment_booking_and_payment_persistence`, an appointment booking for patient "Priya Sharma" was submitted via `POST /api/admin/appointments`.
2. **Atomic Verification:** PostgreSQL atomically:
   - Reserved slot `SLOT...` (marking `status="booked"`, `booked_token_no="TKN-..."`).
   - Created appointment row with `booking_status="Confirmed"` and `payment_status="Pending"`.
   - Created invoice row with `payment_status="Pending"`.
   - Created payment row with `payment_status="Pending"`.
3. **Manual Collection:** Upon calling `POST /api/admin/payments/{token_no}/record`, PostgreSQL updated the payment status to `"Paid"`, recorded `paid_at=NOW()`, and synchronized the appointment and invoice status.

---

## 4. Source of Truth Verification by Entity

| Entity | Active Source of Truth | Verification Method | Legacy Fallback Status |
| :--- | :--- | :--- | :--- |
| **Clinics / Tenants** | **PostgreSQL** (`clinics`) | Verified via Super Admin CRUD APIs & live queries | Removed. PostgreSQL authoritative. |
| **User Accounts & RBAC** | **PostgreSQL** (`users`) | Verified via `/api/admin/auth/login` PBKDF2 hash verification | Removed. `data/doctor_accounts.json` archived. |
| **Doctor Directory** | **PostgreSQL** (`doctors`) | Verified via `PostgresDoctorDirectory` & Admin routes | Disconnected from Google Sheets. |
| **Appointment Slots** | **PostgreSQL** (`appointment_slots`) | Verified via `PostgresSlotRepository` & row-locking `FOR UPDATE` | Disconnected from Google Sheets. |
| **Appointments** | **PostgreSQL** (`appointments`) | Verified via `PostgresPatientRepository` & CRM endpoints | Disconnected from Google Sheets. |
| **Invoices** | **PostgreSQL** (`invoices`) | Verified via `PostgresPatientRepository` & CRM endpoints | Disconnected from file store. |
| **Payments** | **PostgreSQL** (`payments`) | Verified via `PostgresPaymentRepository` & manual record routes | Disconnected from Google Sheets. |
| **Prescriptions** | **PostgreSQL** (`prescriptions`, `prescription_items`) | Verified via `PostgresPrescriptionService` & Doctor Portal | `data/prescriptions.json` archived. |
| **Audit Logs** | **PostgreSQL** (`audit_logs`) | Verified via `PostgresAuditService` & `/api/admin/audit-logs` | `data/audit_logs.jsonl` archived. |

---

## 5. Backup Location & Disaster Recovery

### 5.1 Local Backup Archives
1. **Pre-Migration Snapshot:**
   - Directory: `D:\telegram_bot\data\backup_pre_postgres_migration\`
   - Contents:
     - `doctor_accounts.json`
     - `doctor_demo_credentials.local.json`
     - `prescriptions.json`
     - `audit_logs.jsonl`
     - `google_sheets_doctors.json`
     - `google_sheets_patients.json`
     - `google_sheets_slots.json`
     - `manifest.json`
2. **Pre-Cutover Operational Snapshot:**
   - Directory: `D:\telegram_bot\data\backup_pre_operational_cutover\`
   - SHA-256 verified archives of operational configurations prior to cutting over CRM services.

### 5.2 PostgreSQL Backup Procedure (pg_dump)
To take a full, recoverable backup of the live PostgreSQL database:
```powershell
pg_dump -U postgres -h localhost -p 5432 -F c -b -v -f "D:\telegram_bot\data\clinic_db_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').dump" clinic_db
```

### 5.3 Database Recovery Procedure (pg_restore)
To restore the database from a backup dump:
```powershell
# 1. Terminate existing connections (if needed)
# 2. Restore using pg_restore
pg_restore -U postgres -h localhost -p 5432 -d clinic_db -v --clean --if-exists "D:\telegram_bot\data\<backup_file>.dump"
```

