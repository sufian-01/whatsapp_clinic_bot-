# Clinic Management System (CMS) — Complete Implementation Plan

## 1. Executive Summary & Objective

This document outlines the architecture and upgrade plan to transform the existing Clinic CRM in `D:\telegram_bot` into a full-featured, enterprise-grade Clinic Management System (CMS). The system bridges the real-time Telegram AI Chatbot and a comprehensive Admin Web Dashboard using a single, unified FastAPI backend.

### Key Tenets & Invariants:
1. **Single Source of Truth**: All operations (appointments, patients, doctors, slots, payments) flow through a shared, centralized service layer (`CrmService`). Telegram Bot and Admin CRM share identical business rules.
2. **Transactional & Concurrency Guarantees**:
   - Google Sheets is used as a human-readable synchronization adapter, but **Google Sheets does NOT natively support ACID transactions, distributed locking, or atomic multi-sheet updates**.
   - Concurrency control is enforced at the application service layer via reentrant locks (`_booking_lock`), idempotent request tokens, and transactional state validation before writing.
3. **Zero Regressions**: All 214 existing automated tests must continue to pass without error.
4. **Security & Formula Injection Protection**:
   - Authenticated admin sessions via secure Bearer tokens and HttpOnly cookies.
   - Role-based validation.
   - Strict sanitization of all CSV/Excel export fields against formula injection (CWE-1236) by neutralizing characters (`=`, `+`, `-`, `@`, `\t`, `\r`).
5. **Immutable Audit Logging**: Every administrative mutation (creation, modification, cancellation, deactivation, payment verification) is immutably logged with timestamp, admin identity, entity type, entity ID, and change diff.

---

## 2. System Architecture & Component Interactions

```
+-----------------------------------------------------------------------------------+
|                                  CLIENT LAYER                                     |
|  +-------------------------------------+  +------------------------------------+  |
|  |     Telegram Patients / Users       |  |       Admin Web Dashboard          |  |
|  |  (Natural Language / Sarvam Voice)  |  |  (HTML5 / CSS3 / Vanilla ES Module)|  |
|  +------------------+------------------+  +-----------------+------------------+  |
+---------------------|---------------------------------------|---------------------+
                      |                                       |
                      v                                       v
+---------------------+-------------------+  +----------------+--------------------+
|  Telegram Handlers & LangGraph Workflow |  |  FastAPI Admin REST API Router     |
|  (app/telegram/, app/graph/)            |  |  (/api/admin/* in app/api/admin.py)|
+---------------------+-------------------+  +----------------+--------------------+
                      |                                       |
                      +-------------------+-------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        CENTRALIZED BUSINESS SERVICE LAYER                         |
|                                (app/services/)                                    |
|  +-----------------------------------------------------------------------------+  |
|  | CrmService:                                                                 |  |
|  | - Patient Lifecycle & Duplicate Detection                                   |  |
|  | - Doctor Scheduling & Deactivation Safety Checks                             |  |
|  | - Atomic Slot Reservation & Reschedule / Cancel Safeguards                  |  |
|  | - Billing, Manual Payment Recording & PDF Invoice Dispatch                 |  |
|  | - Timezone-Aware Operational Analytics & CSV Report Generators              |  |
|  +-----------------------------------------------------------------------------+  |
|  +-----------------------------------------------------------------------------+  |
|  | AuditService:                                                               |  |
|  | - Immutable Action Logging (SQLite / JSONL backed)                          |  |
|  | - Query & Filter Audit History                                              |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                   CONCURRENCY CONTROL & DATA ACCESS LAYER                         |
|  - Concurrency Lock: SlotRepository._booking_lock (Thread-Safe Single Process)    |
|  - PatientRepository, DoctorDirectory, SlotRepository, InvoiceTools              |
|  - Target Persistence: Google Sheets API (or Mock Repositories in tests)          |
+-----------------------------------------------------------------------------------+
```

---

## 3. Data Persistence & Concurrency Strategy

### 3.1 Clarification on Google Sheets Limitations
- **No ACID Transactions**: Google Sheets API calls are HTTP batch requests without two-phase commit, row-level locking, or transaction rollback.
- **Race Condition Vulnerabilities**: If two users attempt to book the same slot simultaneously across network calls without application-layer locking, a race condition occurs.
- **Single Process Locking**: We enforce thread-safe concurrency using `SlotRepository._booking_lock`.
- **Pre-Validation & Snapshot Verification**:
  1. Acquire lock.
  2. Take fresh snapshot of slot state.
  3. Validate slot is still `Available`.
  4. Write `Booked` status to slot sheet.
  5. Record patient booking in patient sheet.
  6. If patient record fails, immediately roll back slot status to `Available`.
  7. Release lock.

---

## 4. Module-by-Module Requirements & Enhancements

### 4.1 Patient Management
- **Manual Patient Creation**: Admin creates patient with full demographics (Name, Phone, Email, Age, Gender).
- **Duplicate Detection**: Check for existing records matching Phone or Email. If duplicate detected, return clear warning and link to existing patient profile.
- **Patient Profile View**: Comprehensive patient overview including demographic data, past visit history, upcoming appointments, payment balances, and lifetime spend.
- **Patient Update**: Admin can edit contact info and demographics.
- **Soft Deletion / Inactivation**: Mark patient status as `Inactive`. Never delete rows, ensuring billing and medical audit integrity.

### 4.2 Doctor Management
- **Manual Doctor Creation**: Add new doctors with Specialization, Available Days, Shift Timings, Consultation Fee, and Status.
- **Doctor Editing**: Update fees, schedule days, and clinic working hours.
- **Deactivation Safety Check**: When deactivating a doctor (`Inactive`), verify if there are upcoming confirmed/pending appointments. If found, require admin confirmation and return list of affected appointments.

### 4.3 Appointment Management
- **Manual Booking via CRM**: Admin can book an appointment directly from the CRM:
  1. Select existing patient (or create inline).
  2. Select doctor.
  3. Browse live available slots for selected date.
  4. Select payment method (`Cash`, `UPI`, `Card`, `Offline`) and payment status (`Pending`, `Paid`).
  5. Atomically reserve slot and create appointment.
- **Rescheduling**: Validates status (`Confirmed` or `Pending`), locks new slot, updates patient sheet, releases old slot.
- **Cancellation**: Validates eligibility, updates status to `Cancelled`, frees the slot in `appointment_slots`.
- **Status Progression**:
  - `Pending` $\rightarrow$ `Confirmed` $\rightarrow$ `Completed`
  - Any active status $\rightarrow$ `Cancelled` or `No-Show`.

### 4.4 Billing & Payments
- **Manual Payment Recording**: Record offline payments (Cash, Card, UPI reference, Cheque) with amount and notes.
- **Invoice Generation & Download**: Endpoint `GET /api/admin/appointments/{id}/invoice` generates a PDF invoice via ReportLab and streams it directly to admin browser.
- **Financial Balance Calculation**: Computes Total Billed, Total Paid, and Outstanding Balance per patient and clinic-wide.

### 4.5 Reporting & Analytics
- **Timezone-Aware Filtering**: All date calculations are localized to clinic timezone (`Asia/Kolkata`).
- **Date Range Filters**: Support `Today`, `Yesterday`, `This Week`, `This Month`, `Custom Date Range`.
- **CSV Export Endpoints**:
  - `GET /api/admin/reports/appointments/export?format=csv`
  - `GET /api/admin/reports/patients/export?format=csv`
  - `GET /api/admin/reports/payments/export?format=csv`
- **Formula Injection Sanitization (CWE-1236)**:
  - Any field starting with `=`, `+`, `-`, `@`, `\t`, `\r` is escaped with a prepended single quote (`'`).

### 4.6 Audit & Activity Logs
- **Immutable Log Store**: Backed by `data/audit_logs.jsonl` (and in-memory buffer for high-throughput queries).
- **Action Schema**:
  - `timestamp`: ISO-8601 UTC string
  - `user`: Admin username
  - `action`: E.g., `APPOINTMENT_CREATE`, `APPOINTMENT_RESCHEDULE`, `APPOINTMENT_CANCEL`, `PATIENT_CREATE`, `PATIENT_DEACTIVATE`, `DOCTOR_CREATE`, `DOCTOR_STATUS_CHANGE`, `PAYMENT_RECORD`
  - `entity_type`: `appointment` | `patient` | `doctor` | `slot` | `payment`
  - `entity_id`: ID or Token
  - `details`: Dictionary of change attributes
- **Endpoint**: `GET /api/admin/audit-logs` with pagination and entity filters.

---

## 5. Frontend UI/UX Architecture

The frontend is built with vanilla ES modules, responsive CSS, and a hash-based router:

```
frontend/
├── index.html               # Main SPA shell with sidebar navigation
├── login.html               # Admin authentication screen
├── css/
│   ├── base.css             # Base styles, typography, reset
│   ├── components.css       # Tables, cards, modals, buttons, badges, toast
│   ├── variables.css        # Color palette, spacing, elevations
│   └── views.css            # Custom layouts for views
└── js/
    ├── api.js               # Centralized HTTP client with token handling
    ├── app.js               # Hash router and view orchestrator
    ├── auth.js              # Session & cookie management
    ├── utils.js             # Formatting, debounce, date parsing, modal helpers
    └── views/
        ├── dashboard.js     # Operational stats with date range filter
        ├── appointments.js  # Bookings table, create modal, reschedule & cancel
        ├── calendar.js      # Visual calendar schedule
        ├── patients.js      # Patient directory, duplicate warning, profile modal
        ├── doctors.js       # Doctor directory, add/edit modal, deactivation safety
        ├── slots.js         # Slot master sheet view and status management
        ├── payments.js      # Billing records, manual payment modal, invoice download
        ├── reports.js       # Reports & Analytics with CSV exports
        ├── audit_logs.js    # Activity & Audit logs table with filters
        └── settings.js      # Clinic config & admin account info
```

---

## 6. Implementation Steps

1. **Step 1**: Audit Logging Service (`app/services/audit_service.py`).
2. **Step 2**: Enhance `CrmService` in `app/services/crm_service.py`:
   - Patient duplicate checking and soft deletion.
   - Doctor deactivation safety verification.
   - Manual appointment creation with atomic slot locking.
   - Manual payment recording and PDF invoice generation helper.
   - Timezone-aware dashboard metrics with range filtering.
   - Sanitized CSV export generation.
   - Audit logging integration across all mutations.
3. **Step 3**: Update Admin API Router in `app/api/admin.py`:
   - Endpoints for manual appointment booking, invoice download, reports export, audit logs, duplicate checks.
4. **Step 4**: Update Frontend Assets:
   - Add Reports and Activity Logs navigation items to `frontend/index.html`.
   - Implement `frontend/js/views/reports.js` and `frontend/js/views/audit_logs.js`.
   - Update `frontend/js/views/patients.js`, `appointments.js`, `doctors.js`, `payments.js`, and `dashboard.js`.
   - Update `frontend/js/api.js` and `frontend/js/app.js`.
5. **Step 5**: Automated Testing:
   - Write unit and integration tests in `tests/test_cms_upgrades.py`.
   - Verify double-booking rejection under concurrent calls.
   - Verify formula injection sanitization.
   - Verify audit log recording and immutability.
   - Verify full suite passes with 0 regressions.
