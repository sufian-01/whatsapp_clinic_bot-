# PostgreSQL Database Schema Inventory & pgAdmin Guide

**Project:** Clinic Management SaaS  
**Database Host:** `localhost:5432`  
**Database Name:** `clinic_db`  
**PostgreSQL Version:** 18.6 (x86_64)  
**Alembic Revision Head:** `523c13307c3c` (`phase_2_operational_cutover_fields`)  
**Audit Date:** October 13, 2026  

---

## 1. Executive Summary

This inventory documents all 12 operational relational tables currently active in the `public` schema of PostgreSQL (`clinic_db`). Every table enforces primary keys, foreign key referential integrity with cascading constraints, tenant-scoped unique constraints, and automated timestamps.

### Database Table Overview

| Table Name | Entity Type | Primary Key | Foreign Keys | Unique Constraints | Live Row Count | Primary Application Workflow |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `clinics` | Root Tenant | `id` | None | None | 1 | Platform Tenant Provisioning, Super Admin CMS |
| `users` | Auth Accounts | `id` | `tenant_id -> clinics.id` | `(tenant_id, username)` | 5 | Authentication, Doctor Portal Login, RBAC |
| `doctors` | Attending Doctors | `id` | `tenant_id -> clinics.id` | `(tenant_id, doctor_id)` | 8 | Doctor Directory, Consultation Scheduling, CMS |
| `patients` | Clinic Patients | `id` | `tenant_id -> clinics.id` | `(patient_id, tenant_id)` | 16 | Patient Registry, CRM Search, Chatbot Booking |
| `appointment_slots` | Scheduling Slots | `id` | `doctor_id -> doctors.id`<br>`tenant_id -> clinics.id` | `(doctor_id, date, start_time)`<br>`(tenant_id, slot_id)` | 23 | Slot Creation, Concurrency Locking, Release |
| `appointments` | Booking Records | `id` | `doctor_id -> doctors.id`<br>`patient_id -> patients.id`<br>`slot_id -> appointment_slots.id`<br>`tenant_id -> clinics.id` | `(doctor_id, date, time)`<br>`(tenant_id, token_no)` | 11 | Appointment Lifecycle, Rescheduling, Cancelling |
| `invoices` | Clinical Invoices | `id` | `appointment_id -> appointments.id`<br>`patient_id -> patients.id`<br>`tenant_id -> clinics.id` | `(tenant_id, invoice_number)` | 11 | Billing Invoices, PDF Generation |
| `payments` | Transactions | `id` | `appointment_id -> appointments.id`<br>`invoice_id -> invoices.id`<br>`tenant_id -> clinics.id` | `(tenant_id, payment_id)` | 11 | Offline Payments, UPI QR Tracking |
| `prescriptions` | Digital Rx Header | `id` | `appointment_id -> appointments.id`<br>`doctor_id -> doctors.id`<br>`patient_id -> patients.id`<br>`tenant_id -> clinics.id` | `(tenant_id, prescription_id)` | 56 | Doctor Portal Rx Draft, Finalization, Amendments |
| `prescription_items` | Rx Medications | `id` | `prescription_id -> prescriptions.id` | None | 66 | Medication Line Items, Dosage & Frequency |
| `audit_logs` | Security & Events | `id` | `tenant_id -> clinics.id` | `(tenant_id, audit_id)` | 1,142 | Immutable Compliance Audit Logging |
| `alembic_version` | Migrations | `version_num`| None | None | 1 | Alembic Schema Version Tracking |

---

## 2. Table-by-Table Schema Specification

### 2.1 Table: `clinics`
- **Purpose:** Central tenant registry.
- **Tenant Ownership:** Platform root.
- **Row Count:** 1 (`default`)

| Column | PostgreSQL Data Type | Nullable | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | NO | Primary Key | Unique tenant identifier (`default` or UUID) |
| `name` | `VARCHAR(150)` | NO | None | Display clinic name (e.g., "XYZ Clinic") |
| `legal_name` | `VARCHAR(200)` | YES | None | Registered legal entity name |
| `phone` | `VARCHAR(50)` | YES | None | Reception & support phone number |
| `email` | `VARCHAR(150)` | YES | None | Contact email |
| `address` | `TEXT` | YES | None | Physical address |
| `timezone` | `VARCHAR(50)` | NO | None | Timezone (e.g. `Asia/Kolkata`) |
| `currency` | `VARCHAR(10)` | NO | None | Operating currency (`INR`) |
| `upi_id` | `VARCHAR(100)` | YES | None | UPI ID for QR code generation |
| `logo` | `VARCHAR(255)` | YES | None | Relative path to logo image |
| `website` | `VARCHAR(255)` | YES | None | Official website URL |
| `status` | `VARCHAR(50)` | NO | None | Tenant status (`Active`, `Suspended`) |
| `working_days` | `VARCHAR(100)` | YES | None | Clinic working schedule |
| `working_hours` | `VARCHAR(100)` | YES | None | Operational hours |
| `appointment_duration` | `INTEGER` | NO | None | Standard appointment slot minutes |
| `booking_settings` | `TEXT` | YES | None | Serialized configuration settings |
| `rag_config_status` | `VARCHAR(50)` | NO | None | RAG knowledge base sync status |
| `channel_config_status` | `VARCHAR(50)` | NO | None | Channel integration status |
| `is_active` | `BOOLEAN` | NO | None | Boolean tenant active flag |
| `created_at` | `TIMESTAMPTZ` | NO | None | Timestamp of creation |
| `updated_at` | `TIMESTAMPTZ` | NO | None | Timestamp of last modification |

---

### 2.2 Table: `users`
- **Purpose:** User accounts, platform admins, tenant admins, and attending doctors.
- **Tenant Ownership:** Tenant-scoped (`tenant_id`).
- **Row Count:** 5

| Column | PostgreSQL Data Type | Nullable | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | NO | Primary Key | Unique user UUID |
| `tenant_id` | `VARCHAR(36)` | YES | FK -> `clinics.id` | Scoped clinic tenant (None for platform) |
| `username` | `VARCHAR(100)` | NO | None | Unique login username per tenant |
| `password_hash` | `VARCHAR(255)` | NO | None | Secure PBKDF2-SHA256 password hash |
| `role` | `VARCHAR(50)` | NO | None | Role (`SUPER_ADMIN`, `TENANT_ADMIN`, `doctor`) |
| `doctor_id` | `VARCHAR(50)` | YES | None | Linked doctor profile identifier |
| `full_name` | `VARCHAR(150)` | YES | None | User's full name |
| `email` | `VARCHAR(150)` | YES | None | Contact email |
| `phone` | `VARCHAR(50)` | YES | None | Contact phone |
| `status` | `VARCHAR(50)` | NO | None | Account state (`Active`, `Inactive`, `Locked`) |
| `must_change_password`| `BOOLEAN` | NO | None | Forced credential change flag |
| `last_login` | `TIMESTAMPTZ` | YES | None | Timestamp of latest successful auth |
| `created_at` | `TIMESTAMPTZ` | NO | None | Timestamp of creation |
| `updated_at` | `TIMESTAMPTZ` | NO | None | Timestamp of last modification |

**Constraints & Indexes:**
- Primary Key: `pk_users(id)`
- Foreign Key: `fk_users_tenant_id_clinics(tenant_id)` ON DELETE CASCADE
- Unique: `uq_user_tenant_username(tenant_id, username)`
- Indexes: `ix_users_username`, `ix_users_doctor_id`, `ix_users_role`

---

### 2.3 Table: `doctors`
- **Purpose:** Attending medical practitioners and clinical profiles.
- **Tenant Ownership:** Tenant-scoped (`tenant_id`).
- **Row Count:** 8

| Column | PostgreSQL Data Type | Nullable | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | NO | Primary Key | Unique doctor UUID |
| `tenant_id` | `VARCHAR(36)` | YES | FK -> `clinics.id` | Clinic ownership |
| `doctor_id` | `VARCHAR(50)` | NO | None | Business ID (e.g., `DOC001`) |
| `name` | `VARCHAR(150)` | NO | None | Full doctor name with title |
| `specialization` | `VARCHAR(150)` | NO | None | Primary specialty (e.g., "Cardiology") |
| `qualification` | `VARCHAR(150)` | YES | None | Degrees & certifications (e.g., "MBBS, MD") |
| `registration_no` | `VARCHAR(100)` | YES | None | Medical Council registration number |
| `phone` | `VARCHAR(50)` | YES | None | Contact phone |
| `email` | `VARCHAR(150)` | YES | None | Professional email |
| `available_days` | `VARCHAR(200)` | YES | None | Working days schedule |
| `start_time` | `VARCHAR(50)` | YES | None | Shift start time |
| `end_time` | `VARCHAR(50)` | YES | None | Shift end time |
| `consultation_fee` | `VARCHAR(50)` | NO | None | Standard consultation fee |
| `status` | `VARCHAR(50)` | NO | None | State (`Active`, `Inactive`) |
| `created_at` | `TIMESTAMPTZ` | NO | None | Record creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | NO | None | Record update timestamp |

**Constraints & Indexes:**
- Primary Key: `pk_doctors(id)`
- Foreign Key: `fk_doctors_tenant_id_clinics(tenant_id)` ON DELETE CASCADE
- Unique: `uq_doctor_tenant_doctor_id(tenant_id, doctor_id)`
- Indexes: `ix_doctors_name`, `ix_doctors_specialization`, `ix_doctors_status`

---

### 2.4 Table: `patients`
- **Purpose:** Registered patient directory and master demographics.
- **Tenant Ownership:** Tenant-scoped (`tenant_id`).
- **Row Count:** 16

| Column | PostgreSQL Data Type | Nullable | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | NO | Primary Key | Unique patient UUID |
| `tenant_id` | `VARCHAR(36)` | YES | FK -> `clinics.id` | Clinic ownership |
| `patient_id` | `VARCHAR(50)` | NO | None | Business patient ID (`PAT001`, `PAT-...`) |
| `name` | `VARCHAR(150)` | NO | None | Patient's full name |
| `phone` | `VARCHAR(50)` | NO | None | Mobile phone number |
| `email` | `VARCHAR(150)` | YES | None | Contact email address |
| `age` | `VARCHAR(10)` | YES | None | Patient age |
| `gender` | `VARCHAR(20)` | YES | None | Gender (`Male`, `Female`, `Other`) |
| `address` | `TEXT` | YES | None | Residential address |
| `medical_history`| `TEXT` | YES | None | Chronic conditions / notes |
| `status` | `VARCHAR(50)` | NO | `'Active'` | Lifecycle state (`Active`, `Inactive`) |
| `created_at` | `TIMESTAMPTZ` | NO | None | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | NO | None | Update timestamp |

**Constraints & Indexes:**
- Primary Key: `pk_patients(id)`
- Foreign Key: `fk_patients_tenant_id_clinics(tenant_id)` ON DELETE CASCADE
- Unique: `uq_patient_tenant_patient_id(patient_id, tenant_id)`
- Indexes: `ix_patients_phone`, `ix_patients_name`, `ix_patients_status`

---

### 2.5 Table: `appointment_slots`
- **Purpose:** Doctor schedule slots and real-time availability locking.
- **Tenant Ownership:** Tenant-scoped (`tenant_id`).
- **Row Count:** 23

| Column | PostgreSQL Data Type | Nullable | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | NO | Primary Key | Unique slot UUID |
| `tenant_id` | `VARCHAR(36)` | YES | FK -> `clinics.id` | Clinic ownership |
| `slot_id` | `VARCHAR(50)` | NO | None | Slot identifier (e.g. `SLOT001`, `S1`) |
| `doctor_id` | `VARCHAR(36)` | NO | FK -> `doctors.id` | Attending doctor relation |
| `date` | `VARCHAR(20)` | NO | None | Slot date (`YYYY-MM-DD`) |
| `start_time` | `VARCHAR(50)` | NO | None | Slot start time (`10:00 AM`) |
| `end_time` | `VARCHAR(50)` | NO | None | Slot end time (`10:30 AM`) |
| `status` | `VARCHAR(50)` | NO | None | Availability (`available`, `booked`, `cancelled`) |
| `locked_by` | `VARCHAR(100)` | YES | None | User or session holding booking lock |
| `locked_at` | `TIMESTAMPTZ` | YES | None | Lock timestamp |
| `booked_patient_id`| `VARCHAR(50)`| YES | None | ID of patient who reserved this slot |
| `booked_token_no` | `VARCHAR(50)`| YES | None | Token number of active appointment |
| `created_at` | `TIMESTAMPTZ` | NO | None | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | NO | None | Update timestamp |

**Constraints & Indexes:**
- Primary Key: `pk_appointment_slots(id)`
- Foreign Key: `fk_appointment_slots_doctor_id_doctors(doctor_id)` ON DELETE CASCADE
- Foreign Key: `fk_appointment_slots_tenant_id_clinics(tenant_id)` ON DELETE CASCADE
- Unique: `uq_slot_doctor_date_start_time(doctor_id, date, start_time)` (Prevents double scheduling)
- Unique: `uq_slot_tenant_slot_id(tenant_id, slot_id)`
- Indexes: `ix_appointment_slots_status`, `ix_appointment_slots_date`, `ix_appointment_slots_booked_token_no`

---

### 2.6 Table: `appointments`
- **Purpose:** Verified patient clinical bookings and status tracking.
- **Tenant Ownership:** Tenant-scoped (`tenant_id`).
- **Row Count:** 11

| Column | PostgreSQL Data Type | Nullable | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | NO | Primary Key | Unique appointment UUID |
| `tenant_id` | `VARCHAR(36)` | YES | FK -> `clinics.id` | Clinic ownership |
| `token_no` | `VARCHAR(50)` | NO | None | Token number (`TKN-0001`) |
| `patient_id` | `VARCHAR(36)` | NO | FK -> `patients.id`| Linked patient entity |
| `doctor_id` | `VARCHAR(36)` | NO | FK -> `doctors.id` | Linked doctor entity |
| `slot_id` | `VARCHAR(36)` | YES | FK -> `slots.id` | Reserved slot entity |
| `appointment_date`| `VARCHAR(20)` | NO | None | Appointment date (`YYYY-MM-DD`) |
| `appointment_time`| `VARCHAR(50)` | NO | None | Appointment time (`10:00 AM`) |
| `amount` | `VARCHAR(50)` | NO | None | Consultation charge |
| `payment_method` | `VARCHAR(50)` | NO | None | Method (`Offline`, `UPI`, `Cash`) |
| `payment_status` | `VARCHAR(50)` | NO | None | Payment state (`Pending`, `Paid`) |
| `booking_status` | `VARCHAR(50)` | NO | None | Status (`Confirmed`, `Completed`, `Cancelled`) |
| `notes` | `TEXT` | YES | None | Clinical / Reception notes |
| `created_at` | `TIMESTAMPTZ` | NO | None | Booking timestamp |
| `updated_at` | `TIMESTAMPTZ` | NO | None | Status modification timestamp |

**Constraints & Indexes:**
- Primary Key: `pk_appointments(id)`
- Foreign Keys: `fk_appointments_doctor_id_doctors`, `fk_appointments_patient_id_patients`, `fk_appointments_slot_id_appointment_slots`, `fk_appointments_tenant_id_clinics`
- Unique: `uq_appointment_doctor_datetime(doctor_id, appointment_date, appointment_time)` (Prevents double-booking)
- Unique: `uq_appointment_tenant_token_no(tenant_id, token_no)`
- Indexes: `ix_appointments_booking_status`, `ix_appointments_payment_status`, `ix_appointments_appointment_date`

---

### 2.7 Table: `invoices`
- **Purpose:** Itemized billing invoices for clinical visits.
- **Tenant Ownership:** Tenant-scoped (`tenant_id`).
- **Row Count:** 11

| Column | PostgreSQL Data Type | Nullable | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | NO | Primary Key | Unique invoice UUID |
| `tenant_id` | `VARCHAR(36)` | YES | FK -> `clinics.id` | Clinic ownership |
| `invoice_number` | `VARCHAR(50)` | NO | None | Unique invoice number (`INV-0001`, `INV-...`) |
| `appointment_id` | `VARCHAR(36)` | YES | FK -> `appts.id` | Linked appointment |
| `patient_id` | `VARCHAR(36)` | NO | FK -> `patients.id`| Linked patient |
| `amount` | `VARCHAR(50)` | NO | None | Invoiced amount |
| `payment_method` | `VARCHAR(50)` | NO | None | Expected / chosen payment method |
| `payment_status` | `VARCHAR(50)` | NO | None | Invoiced status (`Pending`, `Paid`) |
| `upi_id` | `VARCHAR(100)` | YES | None | UPI ID encoded in invoice |
| `qr_path` | `VARCHAR(500)` | YES | None | Path to generated payment QR image |
| `pdf_path` | `VARCHAR(500)` | YES | None | Path to generated invoice PDF |
| `issued_date` | `VARCHAR(50)` | YES | None | Date of invoice issuance |
| `notes` | `TEXT` | YES | None | Payment / invoice notes |
| `created_at` | `TIMESTAMPTZ` | NO | None | Timestamp of generation |
| `updated_at` | `TIMESTAMPTZ` | NO | None | Timestamp of last status change |

**Constraints & Indexes:**
- Primary Key: `pk_invoices(id)`
- Foreign Keys: `fk_invoices_appointment_id_appointments`, `fk_invoices_patient_id_patients`, `fk_invoices_tenant_id_clinics`
- Unique: `uq_invoice_tenant_inv_no(tenant_id, invoice_number)`

---

### 2.8 Table: `payments`
- **Purpose:** Ledger of collected and verified payment transactions.
- **Tenant Ownership:** Tenant-scoped (`tenant_id`).
- **Row Count:** 11

| Column | PostgreSQL Data Type | Nullable | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | NO | Primary Key | Unique payment UUID |
| `tenant_id` | `VARCHAR(36)` | YES | FK -> `clinics.id` | Clinic ownership |
| `payment_id` | `VARCHAR(50)` | NO | None | Payment tracking reference (`PAY-0001`, `PAY-...`)|
| `appointment_id` | `VARCHAR(36)` | YES | FK -> `appts.id` | Linked appointment |
| `invoice_id` | `VARCHAR(36)` | YES | FK -> `invoices.id`| Linked invoice |
| `amount` | `VARCHAR(50)` | NO | None | Paid amount |
| `currency` | `VARCHAR(10)` | NO | None | Currency (`INR`) |
| `payment_method` | `VARCHAR(50)` | NO | None | Method (`Cash`, `UPI`, `Card`) |
| `payment_status` | `VARCHAR(50)` | NO | None | Ledger status (`Pending`, `Paid`, `Failed`) |
| `transaction_reference`| `VARCHAR(100)`| YES | None | Bank reference or receipt number |
| `gateway` | `VARCHAR(50)` | YES | None | Gateway name (`Offline`, `UPI_QR`) |
| `gateway_payload` | `JSON` | YES | None | Structured transaction payload |
| `paid_at` | `TIMESTAMPTZ` | YES | None | Exact timestamp payment was collected |
| `created_at` | `TIMESTAMPTZ` | NO | None | Ledger entry creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | NO | None | Ledger entry modification timestamp |

**Constraints & Indexes:**
- Primary Key: `pk_payments(id)`
- Foreign Keys: `fk_payments_appointment_id_appointments`, `fk_payments_invoice_id_invoices`, `fk_payments_tenant_id_clinics`
- Unique: `uq_payment_tenant_payment_id(payment_id, tenant_id)`

---

### 2.9 Table: `prescriptions`
- **Purpose:** Digital prescriptions authored by attending physicians with versioning.
- **Tenant Ownership:** Tenant-scoped (`tenant_id`).
- **Row Count:** 56

| Column | PostgreSQL Data Type | Nullable | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | NO | Primary Key | Unique prescription UUID |
| `tenant_id` | `VARCHAR(36)` | YES | FK -> `clinics.id` | Clinic ownership |
| `prescription_id`| `VARCHAR(50)` | NO | None | Business reference (`RX-0001`, `RX-...`) |
| `patient_id` | `VARCHAR(36)` | NO | FK -> `patients.id`| Attending patient |
| `doctor_id` | `VARCHAR(36)` | NO | FK -> `doctors.id` | Attending physician |
| `appointment_id` | `VARCHAR(36)` | YES | FK -> `appts.id` | Linked clinical visit |
| `date` | `VARCHAR(20)` | NO | None | Prescription date (`YYYY-MM-DD`) |
| `version` | `INTEGER` | NO | None | Incremental version number (1, 2, ...) |
| `status` | `VARCHAR(50)` | NO | None | Lifecycle state (`draft`, `finalized`, `amended`)|
| `chief_complaints`| `TEXT` | YES | None | Primary complaints presented by patient |
| `diagnosis` | `TEXT` | YES | None | Verified medical diagnosis |
| `symptoms` | `TEXT` | YES | None | Clinical symptoms observed |
| `vitals` | `JSON` | YES | None | Structured vital signs (`bp`, `pulse`, `temp`) |
| `clinical_notes` | `TEXT` | YES | None | Doctor's private clinical notes |
| `tests_advised` | `TEXT` | YES | None | Diagnostic laboratory tests advised |
| `advice` | `TEXT` | YES | None | Dietary and lifestyle advice |
| `follow_up_date` | `VARCHAR(20)` | YES | None | Scheduled follow-up visit date |
| `created_by` | `VARCHAR(100)` | YES | None | Username of attending doctor |
| `updated_by` | `VARCHAR(100)` | YES | None | Username of doctor who amended |
| `finalized_at` | `TIMESTAMPTZ` | YES | None | Timestamp of clinical sign-off |
| `version_history` | `JSON` | YES | None | Audited snapshot array of previous versions |
| `email_delivery` | `JSON` | YES | None | Email delivery log & status |
| `pdf_path` | `VARCHAR(500)` | YES | None | Path to generated ReportLab PDF |
| `created_at` | `TIMESTAMPTZ` | NO | None | Draft creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | NO | None | Latest edit timestamp |

**Constraints & Indexes:**
- Primary Key: `pk_prescriptions(id)`
- Foreign Keys: `fk_prescriptions_patient_id_patients`, `fk_prescriptions_doctor_id_doctors`, `fk_prescriptions_appointment_id_appointments`, `fk_prescriptions_tenant_id_clinics`
- Unique: `uq_prescription_tenant_rx_id(tenant_id, prescription_id)`
- Index: `ix_prescription_tenant_date_status(tenant_id, date, status)`

---

### 2.10 Table: `prescription_items`
- **Purpose:** Normalized medication line items for clinical safety.
- **Tenant Ownership:** Linked to prescription parent.
- **Row Count:** 66

| Column | PostgreSQL Data Type | Nullable | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | NO | Primary Key | Unique line item UUID |
| `prescription_id`| `VARCHAR(36)` | NO | FK -> `prescriptions.id` | Parent prescription record |
| `order_index` | `INTEGER` | NO | None | Display position order (1, 2, ...) |
| `name` | `VARCHAR(255)` | NO | None | Drug / medication brand or generic name |
| `strength` | `VARCHAR(100)` | YES | None | Strength / concentration (e.g. `500 mg`) |
| `dosage` | `VARCHAR(100)` | YES | None | Form / units (e.g. `1 tablet`, `5 ml`) |
| `frequency` | `VARCHAR(100)` | YES | None | Schedule (e.g. `1-0-1`, `0-0-1`) |
| `duration` | `VARCHAR(100)` | YES | None | Duration of treatment (e.g. `5 days`) |
| `instructions` | `TEXT` | YES | None | Patient instructions (e.g. `After food`) |
| `created_at` | `TIMESTAMPTZ` | NO | None | Line item timestamp |
| `updated_at` | `TIMESTAMPTZ` | NO | None | Line item update timestamp |

**Constraints & Indexes:**
- Primary Key: `pk_prescription_items(id)`
- Foreign Key: `fk_prescription_items_prescription_id_prescriptions(prescription_id)` ON DELETE CASCADE
- Index: `ix_prescription_items_prescription_id`

---

### 2.11 Table: `audit_logs`
- **Purpose:** Immutable audit ledger for security compliance, data mutations, and access logs.
- **Tenant Ownership:** Tenant-scoped (`tenant_id`), nullable for platform events.
- **Row Count:** 1,142

| Column | PostgreSQL Data Type | Nullable | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | NO | Primary Key | Unique audit UUID |
| `tenant_id` | `VARCHAR(36)` | YES | FK -> `clinics.id` | Tenant context (NULL for Super Admin) |
| `audit_id` | `VARCHAR(50)` | NO | None | Unique event sequence identifier |
| `timestamp` | `TIMESTAMPTZ` | NO | None | Event timestamp |
| `user` | `VARCHAR(100)` | NO | None | Actor username or caller identifier |
| `action` | `VARCHAR(100)` | NO | None | Action type (`APPOINTMENT_CREATE`, `AUTH_LOGIN`, etc.) |
| `entity_type` | `VARCHAR(50)` | NO | None | Entity domain (`appointment`, `prescription`, `slot`) |
| `entity_id` | `VARCHAR(100)` | NO | None | Identifier of affected entity |
| `details` | `JSON` | YES | None | Full before/after metadata payload |
| `ip_address` | `VARCHAR(50)` | YES | None | Client IP address |
| `user_agent` | `VARCHAR(255)` | YES | None | Client browser / device user agent |
| `created_at` | `TIMESTAMPTZ` | NO | None | Log entry timestamp |
| `updated_at` | `TIMESTAMPTZ` | NO | None | Log entry timestamp |

**Constraints & Indexes:**
- Primary Key: `pk_audit_logs(id)`
- Foreign Key: `fk_audit_logs_tenant_id_clinics(tenant_id)` ON DELETE CASCADE
- Unique: `uq_audit_tenant_audit_id(tenant_id, audit_id)`
- Indexes: `ix_audit_logs_action`, `ix_audit_logs_timestamp`, `ix_audit_logs_user`

---

## 3. How to Inspect Live Data in pgAdmin

Follow these steps to inspect the operational tables and verified data in pgAdmin:

1. **Launch pgAdmin 4:**
   - Open pgAdmin 4 on Windows.
2. **Connect to Server:**
   - Server Name: `Local PostgreSQL` (or `PostgreSQL 18`)
   - Host: `localhost`
   - Port: `5432`
   - Maintenance Database: `postgres`
   - Username: `postgres`
   - Password: Enter your configured master password.
3. **Navigate to Database:**
   - Expand `Servers` -> `Local PostgreSQL` -> `Databases` -> `clinic_db`.
4. **Locate Schema & Tables:**
   - Expand `clinic_db` -> `Schemas` -> `public` -> `Tables`.
   - You will see all 12 operational tables:
     - `alembic_version`
     - `appointment_slots`
     - `appointments`
     - `audit_logs`
     - `clinics`
     - `doctors`
     - `invoices`
     - `patients`
     - `payments`
     - `prescription_items`
     - `prescriptions`
     - `users`
5. **View Table Data:**
   - Right-click any table (e.g. `appointments`, `prescriptions`, `patients`, `appointment_slots`).
   - Select **View/Edit Data** -> **All Rows**.
   - Review live operational records persisted directly from application workflows.
6. **Query Quick Row Counts:**
   - Open the **Query Tool** on `clinic_db` (`Tools` -> `Query Tool`) and run:
   ```sql
   SELECT 
       table_name, 
       (xpath('/row/cnt/text()', xml_count))[1]::text::int as row_count
   FROM (
       SELECT 
           table_name, 
           query_to_xml(format('select count(*) as cnt from %I', table_name), false, true, '') as xml_count
       FROM information_schema.tables
       WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
   ) t
   ORDER BY table_name;
   ```

