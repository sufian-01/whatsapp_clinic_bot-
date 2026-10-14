# Architecture Audit & Multi-Tenant SaaS Transformation Plan

**Project:** Clinic Management CRM & AI Chatbot  
**Location:** `D:\telegram_bot`  
**Audit Type:** Comprehensive Multi-Tenant SaaS & PostgreSQL Migration Audit  
**Status:** Audit Completed — Implementation Planning  
**Target:** Multi-Tenant Healthcare SaaS (FastAPI + PostgreSQL + Tenant Isolation)

---

# 1. Executive Summary

The existing system is a single-tenant clinic operations platform comprising:
1. A **FastAPI** backend powering an Admin CRM and Doctor Portal.
2. A **Telegram AI Chatbot** powered by **LangGraph** and **Google Gemini** for patient scheduling and medical triage.
3. A **Retrieval-Augmented Generation (RAG)** engine for clinic policy and medical FAQs.
4. An external datastore composed of **Google Sheets** for patients, doctors, and appointment slots, combined with local **JSON/JSONL flat files** for doctor accounts, prescriptions, and audit logging.
5. An SPA frontend built with vanilla ES modules, modular CSS, skeleton loaders, and theme management.

### Key Finding & Verdict
The product currently operates strictly as a **Single-Tenant Desktop/Single-Process Appliance**. It is coupled to single-clinic environment variables (`CLINIC_NAME`, `CLINIC_SHEET_ID`), local JSON files (`data/prescriptions.json`, `data/doctor_accounts.json`), hardcoded in-memory caches and locks (`SlotRepository._booking_lock`), interactive local Google OAuth (`google_auth.py`), and unisolated global directories (`data/invoices/`, `data/prescriptions/`).

To transform this system into a multi-tenant SaaS serving independent clinics (`tenant_A`, `tenant_B`, etc.) from a unified codebase without code duplication or data leaks, the architecture must transition to:
- **Relational PostgreSQL Datastore:** Shared tables with mandatory `tenant_id` partitioning, foreign keys, row-level locking (`SELECT ... FOR UPDATE`), and atomic ACID transactions.
- **Unified Multi-Tenant Identity & Access Management (IAM):** Multi-role hierarchy (`SUPER_ADMIN`, `TENANT_ADMIN`, `DOCTOR`, `STAFF`, `PATIENT`) with JWT tokens embedding `tenant_id`, and tenant resolution via subdomains, custom domains, or request headers.
- **Channel Adapter Pattern:** Decoupling business logic from Telegram-specific constructs to enable unified multi-channel communication (Telegram, WhatsApp, Web Widget).
- **Tenant-Isolated Vector Storage:** Migrating RAG to PostgreSQL `pgvector` or isolated tenant namespaces to ensure Clinic A never retrieves Clinic B clinical documents.

---

# 2. Current Architecture

```
                       +---------------------------------------+
                       |           External Clients            |
                       |  - Telegram User / Webhook            |
                       |  - Browser: Admin CRM / Doctor Portal |
                       +-------------------+-------------------+
                                           |
                                           v
                       +---------------------------------------+
                       |         FastAPI Gateway               |
                       |  - Perf Middleware (X-Request-ID)     |
                       |  - Static Files Mount (/admin)        |
                       +---+---------------+---------------+---+
                           |               |               |
             +-------------+               |               +-------------+
             v                             v                             v
+--------------------------+ +--------------------------+ +--------------------------+
|      Telegram Webhook    | |     Knowledge Router     | |   CRM & Doctor Routers   |
| app/api/webhook.py       | | app/api/knowledge.py     | | app/api/admin.py         |
|                          | |                          | | app/api/doctor.py        |
+------------+-------------+ +-------------+------------+ +-------------+------------+
             |                             |                            |
             v                             v                            v
+--------------------------+ +--------------------------+ +--------------------------+
|  LangGraph Agent & Bot   | |    RAG Service & Store   | |       CrmService         |
| app/graph/graph.py       | | app/rag/service.py       | | app/services/crm_service |
| app/graph/nodes.py       | | app/rag/vectorstore.py   | |                          |
+------------+-------------+ +-------------+------------+ +-------------+------------+
             |                             |                            |
             +----------------------+      |      +---------------------+
                                    v      v      v
                       +---------------------------------------+
                       |              Data Layer               |
                       | - Google Sheets API (3 ranges)        |
                       | - data/doctor_accounts.json           |
                       | - data/prescriptions.json             |
                       | - data/audit_logs.jsonl               |
                       | - data/invoices/*.pdf                 |
                       | - data/vectorstore/index.faiss        |
                       +---------------------------------------+
```

### Entrypoints and Initialization Flow
- **`app/main.py:94-225` (`create_app`)**:
  - Initializes logging and reads single-tenant settings from `get_settings()`.
  - Instantiates `RagService` targeting global paths `data/knowledge` and `data/vectorstore`.
  - Builds Google Sheets repositories using global sheet ID (`settings.clinic_sheet_id`).
  - Instantiates single `CrmService` injecting sheet tools, doctor accounts, and prescriptions.
  - Builds the compiled LangGraph workflow with injected single-tenant settings.
  - Mounts routes (`/webhook/telegram`, `/api/v1/knowledge`, `/api/admin`, `/api/doctor`, `/admin`).

---

# 3. Current Feature Map

| Area | Component | Implementation File | Datastore | Concurrency / Isolation Guard |
|---|---|---|---|---|
| **Patient Chat** | Telegram Bot & Natural Language Dialog | `app/telegram/handlers.py`, `app/graph/nodes.py` | In-memory `SessionStore` (`app/telegram/sessions.py`) | Threading `RLock`, in-process only |
| **Voice Processing** | Speech-to-Text & Text-to-Speech | `app/services/sarvam_service.py` | None (REST streaming) | In-memory payload limit |
| **CRM Dashboard** | Aggregated Metrics & Analytics | `app/services/crm_service.py:98-276` | Google Sheets (`patient`, `appointment_slots`) | 20s TTL in-memory cache |
| **Doctor Directory** | Doctor Roster, Specialty Matching | `app/tools/doctors.py`, `app/services/crm_service.py:550-705` | Google Sheets (`doctor!A1:Z1000`) | 60s TTL in-memory cache |
| **Doctor Auth** | Doctor Account Management | `app/services/doctor_account_service.py` | `data/doctor_accounts.json` | File `.tmp` atomic write + `RLock` |
| **Doctor Portal** | My Schedule, Slots, Assigned Patients | `app/api/doctor.py`, `app/services/crm_service.py:1637-2050` | Google Sheets + `prescriptions.json` | Filter by `doctor_id` in Python memory |
| **Appointments** | Booking, Reschedule, Cancellation | `app/services/crm_service.py:813-1189` | Google Sheets (`patient`, `appointment_slots`) | Class-level `SlotRepository._booking_lock` |
| **Prescriptions** | Clinical Draft, Finalization, Amendment | `app/services/prescription_service.py` | `data/prescriptions.json` | File `.tmp` atomic write + `RLock` |
| **Prescription PDF** | ReportLab Medical PDF Generation | `app/tools/prescription_pdf.py` | `data/prescriptions/*.pdf` | Disk file existence check |
| **Invoicing & QR** | Invoice Generation & Offline UPI QR | `app/tools/invoice.py`, `app/tools/payments.py` | `data/invoices/*.pdf`, `*.png` | Disk file write |
| **Email Delivery** | Gmail Dispatch (Prescriptions, Invoices) | `app/tools/gmail.py`, `gmail_tools.py` | Google Gmail API (OAuth2) | None (asynchronous background call) |
| **Audit Logging** | Immutable Action Logging | `app/services/audit_service.py` | `data/audit_logs.jsonl` | Append-only file write + `Lock` |
| **RAG Knowledge** | Clinic FAQ & Document Search | `app/rag/service.py`, `app/rag/vectorstore.py` | `data/vectorstore/index.faiss` | Lazy FAISS import |

---

# 4. Important Business Flows

### Flow 1: Telegram Appointment Booking
1. **Webhook Reception** (`app/api/webhook.py:14-27`): Telegram update received at `/webhook/telegram`, validated via `x-telegram-bot-api-secret-token`.
2. **Session Retrieval** (`app/telegram/handlers.py:78`): Chat state fetched from `sessions.get(chat)` (`app/telegram/sessions.py:11-13`).
3. **Graph Execution** (`app/telegram/handlers.py:85`): `graph.invoke(state)` executed on worker thread.
4. **Intent Classification** (`app/graph/router.py`): Message routed to `appointment_start` or `appointment_progress`.
5. **Slot Reservation & Booking** (`app/graph/nodes.py:496` -> `app/tools/slots.py:129-148`):
   - Acquires `SlotRepository._booking_lock`.
   - Forces refresh of Google Sheets rows via HTTP.
   - Updates slot cells to `Status="Booked"`, `Patient ID=...`, `Token No=...`.
   - Re-reads sheet to verify booking.
6. **Patient Record Creation** (`app/graph/nodes.py:503` / `app/tools/patients.py:108-148`): Appends a new row to `PATIENT_SHEET_RANGE`.
7. **Offline Invoice & Email** (`app/graph/nodes.py:513` -> `app/tools/invoice.py:36-56`): Generates PDF invoice in `data/invoices/`, queues email via `GmailTools`.

### Flow 2: Appointment Rescheduling
1. **Request Trigger** (`app/api/admin.py:688-708` or Chatbot): `/api/admin/appointments/{appointment_id}/reschedule`.
2. **Lock Acquisition** (`app/services/crm_service.py:1085`): Acquires `SlotRepository._booking_lock`.
3. **Validation**: Confirms current appointment is not `Cancelled` or `Completed`. Validates target slot is `Available`.
4. **Target Slot Booking**: Sets target slot to `Status="Booked"` with patient ID and token.
5. **Sheet Record Update**: Modifies patient appointment row with new date and time.
6. **Old Slot Release**: Reverts old slot to `Status="Available"`, blanking `Patient ID` and `Token No`.
7. **Cache Invalidation & Audit**: Clears caches and appends entry to `data/audit_logs.jsonl`.

### Flow 3: Appointment Cancellation
1. **Request Trigger** (`app/api/admin.py:710-730`): `/api/admin/appointments/{appointment_id}/cancel`.
2. **Lock Acquisition** (`app/services/crm_service.py:1032`): Acquires `SlotRepository._booking_lock`.
3. **Patient Row Update**: Finds appointment row by `token_no` or `patient_id` and sets `Booking Status="Cancelled"`.
4. **Associated Slot Release**: Finds booked slot in `appointment_slots` matching patient/token and sets `Status="Available"`.
5. **Audit Logging & Cache Flush**: Records event in `AuditService` and invalidates caches.

### Flow 4: Doctor Prescription Creation & Finalization
1. **Draft Autosave** (`app/api/doctor.py:300-330` -> `app/services/prescription_service.py:108-190`):
   - Doctor submits clinical notes, vitals, diagnosis, and medicine items.
   - Enforces cross-doctor check: `prescription.doctor_id == current_doctor.doctor_id`.
   - Saves record into `data/prescriptions.json` via atomic `.tmp` swap.
2. **Prescription Finalization** (`app/api/doctor.py:348-366` -> `app/services/prescription_service.py:193-244`):
   - Validates that diagnosis and at least one complete medication row exist.
   - Marks status `Finalized`, sets `finalized_at` timestamp.
   - Generates immutable PDF via ReportLab in `data/prescriptions/{rx_id}_v1.pdf`.
3. **Prescription Amendment** (`app/api/doctor.py:369-391` -> `app/services/prescription_service.py:246-328`):
   - Requires non-empty `amendment_reason`.
   - Increments version counter (`version += 1`), archives previous snapshot in `history` array.
   - Generates new version PDF: `data/prescriptions/{rx_id}_v2.pdf`.

---

# 5. Current Data Model

The application currently has no relational database. Data models are split across three different paradigms:
1. **Google Sheets Rows** (untyped strings in fixed column positions).
2. **Dataclasses & Pydantic Models** (in-memory representations).
3. **JSON Objects in Flat Files** (schemaless document storage).

```
+-------------------------------------------------------------------------------------------------+
|                                    Google Sheet: patient                                        |
| Patient ID | Name | Email | Phone | Age | Gender | Doctor | Appt Date | Appt Time | Token No   |
| Amount | Payment Method | Payment Status | Booking Status | Created At                          |
+-------------------------------------------------------------------------------------------------+
                                               |
                                               | Matches Doctor Name & Token No
                                               v
+-------------------------------------------------------------------------------------------------+
|                                 Google Sheet: appointment_slots                                 |
| Slot ID | Doctor ID | Doctor Name | Date | Start Time | End Time | Status | Patient ID         |
| Token No | Booked At                                                                            |
+-------------------------------------------------------------------------------------------------+
                                               ^
                                               | Matches Doctor ID & Name
                                               |
+-------------------------------------------------------------------------------------------------+
|                                    Google Sheet: doctor                                         |
| Doctor ID | Doctor Name | Specialization | Available Days | Start Time | End Time               |
| Consultation Fee | Status | Qualification | Registration Number                                 |
+-------------------------------------------------------------------------------------------------+
```

### Critical Data Architecture Flaws
1. **Tangled Patient & Appointment Entities:** The `patient` sheet row combines both patient demographic details and appointment details. Every time a returning patient books an appointment, a new row is appended with duplicated name, phone, age, and gender, but a new token.
2. **Denormalized Doctor Names:** Slots store `Doctor Name` as a raw string rather than relying solely on a foreign key reference. Renaming a doctor breaks slot associations.
3. **No Foreign Key Integrity:** Relationships between `patient.Doctor` and `doctor.Doctor Name`, or between `patient.Token No` and `appointment_slots.Token No`, are maintained only by application-level string comparisons.

---

# 6. Google Sheets Audit

| Sheet / Range | Header Columns | Implicit IDs | Data Duplication Risks | Migration Concerns |
|---|---|---|---|---|
| **`patient`** (`PATIENT_SHEET_RANGE`, def: `patient!A1:Z1000`) | `Patient ID`, `Name`, `Email`, `Phone`, `Age`, `Gender`, `Doctor`, `Appointment Date`, `Appointment Time`, `Status`, `Token No`, `Amount`, `Payment Method`, `Payment Status`, `Booking Status`, `Created At` | `Patient ID` (`PAT-<hex>`), `Token No` (`TKN-<seq>`) | Patient demographics duplicated on every booking; status columns duplicated (`Status` vs `Booking Status`) | Must split into two distinct tables: `patients` (demographics) and `appointments` (bookings). |
| **`doctor`** (`CLINIC_SHEET_RANGE`, def: `Sheet1!A1:Z1000`) | `Doctor ID`, `Doctor Name`, `Specialization`, `Available Days`, `Start Time`, `End Time`, `Consultation Fee`, `Status`, `Qualification`, `Registration Number` | `Doctor ID` (`D1`, `D2`, ...) | Specializations stored as unindexed free-form strings; available days stored as comma-separated string | Working hours must be normalized into a `doctor_schedules` table. |
| **`appointment_slots`** (`APPOINTMENT_SLOT_SHEET_RANGE`, def: `appointment_slots!A1:Z5000`) | `Slot ID`, `Doctor ID`, `Doctor Name`, `Date`, `Start Time`, `End Time`, `Status`, `Patient ID`, `Token No`, `Booked At` | `Slot ID` (`S1`, `S2`, ...) | `Doctor Name` duplicated from doctor sheet; `Patient ID` and `Token No` stored without integrity checks | Move to `appointment_slots` with foreign keys to `doctors`, `appointments`, and `patients`. |

### Performance & Reliability Bottlenecks with Sheets
- **Latency:** Every booking or status update incurs 500ms–2500ms of synchronous HTTP calls to Google Sheets API (`sheet_tools.py:40-100`).
- **Quota Throttling:** Google Sheets enforces a limit of 300 requests per minute per project. Multi-tenant SaaS with multiple clinics would exhaust this quota immediately.
- **No ACID Transactions:** If updating `appointment_slots` succeeds but appending to `patient` fails, the system attempts an application rollback (`slots.release_slot_if_needed`), which can fail, leaving corrupted "ghost" bookings.

---

# 7. Authentication & Authorization Audit

### Mechanism & Implementation
- **File:** `app/core/auth.py`
- **Tokens:** Cryptographically random session tokens generated via `secrets.token_urlsafe(32)` (`app/core/auth.py:124`).
- **Storage:** In-memory dictionary `_ACTIVE_SESSIONS: dict[str, dict]` (`app/core/auth.py:22`) protected by a threading `Lock`.
- **Password Hashing:** PBKDF2-HMAC-SHA256 with 100,000 iterations and 16-byte random salt (`app/core/auth.py:35-46`).
- **Brute-Force Protection:** IP/Account lockout after 5 failed attempts within 15 minutes (`app/core/auth.py:30-32`).

### Vulnerabilities & Architectural Gaps
1. **Ephemeral In-Memory Sessions:** Restarting the FastAPI service logs out all users across the entire system. In a multi-worker deployment (e.g. Uvicorn with 4 workers), requests routed to worker B fail authentication if the login occurred on worker A.
2. **Demo Password Backdoor:** `DoctorAccountService` (`app/services/doctor_account_service.py:30, 67-68`) defaults `allow_demo_password=True`, allowing doctors to authenticate using the insecure static password `1234`.
3. **No Tenant Context in Auth:** Sessions store `{"username": ..., "role": ..., "doctor_id": ...}` but contain **no `tenant_id`**.
4. **Unprotected Endpoint:** `POST /api/v1/knowledge/upload` (`app/api/knowledge.py:32-75`) lacks authentication. Anyone on the internet can upload files into the clinic's knowledge base.

---

# 8. Tenant Isolation Audit

### Code Coupling Points

| Component | Exact File & Lines | Current Single-Tenant Implementation | Multi-Tenant Vulnerability | Future Multi-Tenant Requirement |
|---|---|---|---|---|
| **Environment Settings** | `app/core/config.py:15-48` | `clinic_name`, `clinic_sheet_id`, `support_phone` loaded globally from `.env` | Only 1 clinic can exist per deployment instance. | Move clinic config to `tenants` and `clinics` tables in PostgreSQL. |
| **Doctor Accounts** | `app/services/doctor_account_service.py:34, 42` | Global file `data/doctor_accounts.json` keyed by username | Usernames collide across different clinics (e.g., two clinics having `dr_smith`). | Key user accounts by `(tenant_id, username)` composite uniqueness. |
| **Prescriptions** | `app/services/prescription_service.py:32-37` | Single JSON dictionary `_prescriptions` in `data/prescriptions.json` | Clinic A can read Clinic B prescriptions if ID is guessed; file writes overwrite data. | Relational `prescriptions` table with mandatory `tenant_id` foreign key. |
| **Audit Logs** | `app/services/audit_service.py:32, 70-78` | Single append-only file `data/audit_logs.jsonl` | Admin of Clinic A can view operational audit logs of Clinic B via `/api/admin/audit-logs`. | Store audit events in PostgreSQL `audit_logs` table partitioned by `tenant_id`. |
| **Invoice Files** | `app/services/crm_service.py:1488`, `app/tools/invoice.py:38` | PDFs written to unpartitioned `data/invoices/` directory | Filename collisions; unauthorized access to cross-tenant financial documents. | Partition storage paths: `storage/tenants/{tenant_id}/invoices/`. |
| **Prescription PDFs** | `app/services/prescription_service.py:33, 420` | PDFs written to `data/prescriptions/` | Cross-tenant document disclosure risk. | Partition storage paths: `storage/tenants/{tenant_id}/prescriptions/`. |
| **In-Memory Caches** | `app/services/crm_service.py:67-86` | Global cache keys (`_cached_records`, `_cached_rows`) | Cache invalidation in Clinic A has no tenant scoping. | Tenant-scoped cache keys in Redis: `cache:{tenant_id}:doctors`. |
| **Hardcoded UPI** | `app/tools/payments.py:28`, `app/tools/invoice.py:53` | `upi_id = "khansyrian1@okhdfcbank"` hardcoded in code | All clinics generate QR codes paying into one personal account! | Dynamic clinic billing profiles: `clinic_payment_gateways.upi_id`. |
| **System Prompts** | `app/core/prompts/clinic_system.txt:1` | Static text file loaded with `.format(clinic_name=..., support_phone=...)` | Cannot customize tone, policies, or languages per clinic. | Store customized system prompts in `tenant_settings` table. |

---

# 9. RAG / FAISS Audit

### Current Implementation & Limitations
- **Files:** `app/rag/service.py`, `app/rag/vectorstore.py`, `app/rag/loader.py`, `app/rag/splitter.py`
- **Mechanism:** Text extracted from `.txt`, `.md`, and `.pdf` files is split into 1200-character chunks with zero overlap (`app/rag/splitter.py:4`). Chunks are vectorized using a custom scikit-learn TF-IDF fallback vectorizer and indexed in FAISS via `IndexFlatIP` (`app/rag/vectorstore.py:173-179`).
- **Index Persistence:** Pickled metadata (`metadata.pkl`) and native FAISS index (`index.faiss`) saved in single global directory `data/vectorstore/`.

### Windows Application Control Policy Issue
- **Root Cause:** Windows Application Control (AppLocker / WDAC) blocks unsigned or unauthorized native DLLs (`_swigfaiss.pyd`).
- **Current Fix Implemented:** Module-level `import faiss` was replaced with lazy `get_faiss()` in `app/rag/vectorstore.py:19-37`. If unavailable, `RagService` operates in degraded mode returning empty search results (`service.py:31-40`), and `POST /upload` returns HTTP 503 instead of crashing the server.
- **Multi-Tenant Limitation:** Even when FAISS works, the current implementation maintains a single index for all uploaded documents. If Clinic A uploads its internal fee schedule and Clinic B uploads patient guidelines, search queries will cross-contaminate chunks.

### Future Multi-Tenant Vector Architecture
1. **Eliminate Native FAISS Dependency:** Replace local FAISS with **PostgreSQL `pgvector`**.
2. **Schema Isolation:**
   ```sql
   CREATE TABLE knowledge_documents (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
       filename VARCHAR(255) NOT NULL,
       file_url TEXT NOT NULL,
       created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
   );

   CREATE TABLE knowledge_chunks (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
       document_id UUID NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
       chunk_index INT NOT NULL,
       content TEXT NOT NULL,
       embedding vector(1536) NOT NULL,
       created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
   );

   CREATE INDEX idx_knowledge_chunks_tenant_vector 
   ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)
   WHERE tenant_id IS NOT NULL;
   ```
3. **Retrieval Isolation:** Every query enforces `WHERE tenant_id = :current_tenant_id`. No cross-tenant data leakage is possible.

---

# 10. Telegram Coupling Audit

### Current Coupling Analysis
- **Entrypoint:** `app/telegram/handlers.py:50` accepts Telegram `Update` objects.
- **State Machine UI Hints:** `app/graph/state.py:42` and `app/graph/nodes.py:30, 484` directly set Telegram UI instructions (e.g. `ui: "doctor_select"`, `ui: "confirm"`, `doctor_choices`).
- **Transport Lock-in:** Keyboard generators (`app/telegram/keyboards.py`) construct Telegram `InlineKeyboardMarkup` and `InlineKeyboardButton` objects.

### Decoupling Plan: Channel Adapter Pattern
To allow WhatsApp, Web Chat Widgets, and Telegram to run against the same core AI workflow:

```
[ Telegram Webhook ]   [ WhatsApp Webhook ]   [ Web Chat Widget ]
         |                      |                      |
         v                      v                      v
[ Telegram Adapter ]   [ WhatsApp Adapter ]   [ Web Chat Adapter ]
         |                      |                      |
         +----------------------+----------------------+
                                |
                                v
               [ Canonical Inbound Message Model ]
               { tenant_id, session_id, user_id, text, channel }
                                |
                                v
             [ Core Agent & Conversational Pipeline ]
                                |
                                v
               [ Canonical Outbound Message Model ]
               { text, quick_replies: [...], attachments: [...] }
                                |
         +----------------------+----------------------+
         |                      |                      |
         v                      v                      v
[ Telegram Outbound ]  [ WhatsApp Outbound ]  [ Web Chat Outbound ]
```

1. **Canonical Schema:** Define `ChannelMessage(tenant_id, channel_type, sender_id, text, attachments)`.
2. **Abstract Router:** The LangGraph graph receives canonical state and outputs canonical choices (`options: [{"id": "S1", "label": "10:00 AM"}]`).
3. **Channel Formatter:** The specific channel adapter translates canonical options into Telegram Inline Keyboards, WhatsApp Interactive Buttons, or Web UI JSON.

---

# 11. Cache & Global State Audit

### Discovered In-Memory Caches & Singletons
1. **`PatientRepository._cached_records`** (`app/tools/patients.py:57-81`): In-memory list with 20s TTL and `RLock`.
2. **`DoctorDirectory._cached_records`** (`app/tools/doctors.py:100-140`): In-memory list with 60s TTL and `RLock`.
3. **`SlotRepository._cached_records`** (`app/tools/slots.py:37-77`): In-memory list with 20s TTL and `RLock`.
4. **`SessionStore._sessions`** (`app/telegram/sessions.py:8`): Global in-memory dict storing user conversation states.
5. **`AuditService._entries`** (`app/services/audit_service.py:38`): Global in-memory list of the latest 2000 log records.
6. **`app/main.py:143` (`perf_history`)**: In-memory `deque(maxlen=200)` for performance logging.

### Multi-Tenant Hazards
- **No Tenant Namespacing:** If Tenant A modifies a patient, calling `invalidate_all_caches()` flushes the cache for that process instance, but cache entries themselves are not separated per tenant.
- **Multi-Worker Inconsistency:** If the application runs with multiple worker processes, updating a doctor on Worker 1 invalidates only Worker 1's local cache. Worker 2 continues returning stale data until its TTL expires.
- **Production Remedy:** Replace in-memory dictionaries with **Redis**. Key pattern:
  `cache:{tenant_id}:{entity}:{id_or_query}` with distributed invalidation via Redis pub/sub.

---

# 12. File & Storage Audit

### Discovered Storage Paths & Artifacts
- **Prescription Records:** `data/prescriptions.json` (`app/services/prescription_service.py:32`)
- **Prescription PDFs:** `data/prescriptions/*.pdf` (`app/services/prescription_service.py:33`)
- **Doctor Accounts:** `data/doctor_accounts.json` (`app/services/doctor_account_service.py:34`)
- **Audit Logs:** `data/audit_logs.jsonl` (`app/services/audit_service.py:32`)
- **Invoice PDFs:** `data/invoices/INV-*.pdf` (`app/services/crm_service.py:1488`)
- **UPI QR Code Images:** `data/invoices/*-upi.png` (`app/tools/payments.py:31`)
- **Knowledge Base Uploads:** `data/knowledge/uploads/*.pdf` (`app/main.py:189`)
- **Vector Store Index:** `data/vectorstore/index.faiss` & `metadata.pkl` (`app/core/config.py:23`)

### Storage Multi-Tenancy Strategy
All local flat-file storage must be migrated to cloud object storage (S3 / GCS / Azure Blob) or structured PostgreSQL tables:
1. **Prescriptions, Accounts, Audit Logs:** Move to PostgreSQL tables.
2. **Generated PDFs & Uploaded Documents:** Store in cloud object storage with tenant prefixing:
   `s3://{bucket_name}/tenants/{tenant_id}/{entity_type}/{year}/{month}/{file_id}.pdf`
3. Access to files must be governed by short-lived, pre-signed URLs generated after verifying the user's `tenant_id` authorization.

---

# 13. Security Audit

> [!CAUTION]
> **Hardcoded Secrets & Credential Exposure Found in Codebase:**
> 1. **Hardcoded Payment Receiver:** `app/tools/payments.py:28` and `app/tools/invoice.py:53` contain a hardcoded personal UPI identifier (`khansyrian1@okhdfcbank`).
> 2. **Insecure Demo Credentials in Source:** `app/services/doctor_account_service.py:67` permits static demo password `1234`.
> 3. **Default Admin Secrets in Config:** `app/core/config.py:44, 46` provide default fallback credentials (`admin123`) and fallback secret key (`clinic-crm-secret-key-change-in-production`).
> 4. **Local Credentials Files on Disk:** Root directory contains OAuth tokens and secret files (`token.json`, `credentials.json`, `data/doctor_accounts.json`, `data/doctor_demo_credentials.local.json`).

### Additional Security Risks
- **Unauthenticated Knowledge Upload:** `POST /api/v1/knowledge/upload` accepts arbitrary PDF files without requiring an admin or doctor session token.
- **In-Memory JWT/Session Expiry:** Session tokens are stored in memory without server-side revocation lists in Redis, allowing tokens to remain active until memory wipe.
- **Missing Tenant Context Verification:** No API routes currently inspect or validate tenant ownership of the requested records.

---

# 14. Performance & Concurrency Audit

### Existing Optimizations Review
The previous performance optimizations (O(1) dictionary indexing for prescriptions, TTL-based repository caches, and in-flight GET request deduplication in the frontend) improved single-tenant response times. However, their concurrency model fails under multi-tenant conditions:

### Concurrency Vulnerabilities
1. **The In-Memory Lock Bottleneck:**
   - `SlotRepository._booking_lock = RLock()` (`app/tools/slots.py:22`).
   - This lock is process-local. In a multi-worker production deployment (e.g. Uvicorn with 4 workers behind Nginx), concurrent requests for the same slot hitting different workers will execute simultaneously.
   - While holding this lock, the application executes multiple blocking HTTP calls to Google Sheets (`_snapshot(force_refresh=True)`), stalling all other threads.
2. **PostgreSQL Solution:**
   Use database-level row locking with transactions:
   ```sql
   BEGIN;
   SELECT id, status 
   FROM appointment_slots 
   WHERE id = :slot_id AND tenant_id = :tenant_id 
   FOR UPDATE;
   
   -- Check if available, then:
   UPDATE appointment_slots 
   SET status = 'BOOKED', booked_at = NOW() 
   WHERE id = :slot_id;
   
   INSERT INTO appointments (...);
   COMMIT;
   ```
   This guarantees zero race conditions across unlimited worker nodes and processes.

---

# 15. Frontend Architecture Audit

### Frontend Inspection
- **Shell & Navigation:** Single Page Application (SPA) in `frontend/index.html` with vanilla ES modules (`app.js`, `api.js`, `auth.js`, `utils.js`).
- **Views:** 14 view controllers in `frontend/js/views/` implementing standard `init()`, `render()`, and `loadData()` lifecycles.
- **Authentication State:** Stores session token (`crm_admin_token`) and user metadata (`crm_admin_user`) in browser `localStorage` (`frontend/js/auth.js:33-46`).

### Coupling to Single-Tenant Backend
1. **Hardcoded Endpoints:** `frontend/js/api.js:7` sets `BASE_URL = "/api/admin"`.
2. **Missing Tenant Header:** Requests sent via `executeRequest` attach `Authorization: Bearer <token>` but include no `X-Tenant-ID` header.
3. **Locale & Currency Assumptions:** `frontend/js/utils.js:46` hardcodes INR currency symbol (`₹`) and `en-IN` date formatting.
4. **Target SaaS Frontend Architecture:**
   - Resolve tenant identity from subdomain (`clinic-a.saasdomain.com`) or initial login response.
   - Automatically inject `X-Tenant-ID` header on all outgoing API requests.
   - Dynamic localization: Fetch currency code, timezone, and clinic branding during app bootstrap (`/api/tenant/config`).

---

# 16. Test Coverage Audit

### Current Test Suite Overview
- **Total Test Files:** 25 files in `tests/`.
- **Total Collected Tests:** 281 tests passing.
- **Execution Speed:** ~7.3 seconds for test collection.

### Test Breakdown by Subsystem
- **Appointment & Conversational Flows:** `test_appointment_flow.py`, `test_conversational_flow.py`, `test_reschedule_cancel.py`, `test_slots.py`.
- **Doctor Portal & Prescriptions:** `test_phase2_doctor_portal.py` (19 tests), `test_prescription_system.py` (7 tests), `test_doctor_api_endpoints.py`.
- **RAG & Knowledge Degradation:** `test_rag.py` (9 tests verifying graceful FAISS degradation and status endpoints).
- **CRM Admin & Optimizations:** `test_admin_crm.py`, `test_performance_optimization.py`, `test_all_views.py`.
- **Frontend Contract Verification:** `check_js.py` (validates ES module import/export integrity across all 14 views).

### Missing Test Areas for Multi-Tenant SaaS
1. **Zero Tenant Isolation Tests:** No tests currently assert that Tenant A cannot access Tenant B's patients, doctors, or slots.
2. **Zero PostgreSQL Integration Tests:** Current tests mock repository callables (`read_rows`, `append_row`).
3. **Zero Multi-Worker Concurrency Tests:** Tests run within a single Python process; no tests verify behavior under distributed race conditions.

---

# 17. Proposed PostgreSQL Architecture

Based strictly on existing data entities, the target PostgreSQL domain model is defined below:

```
+--------------------+       +--------------------+
|      tenants       |       |  tenant_settings   |
+--------------------+       +--------------------+
| id (PK)            |<----->| tenant_id (PK, FK) |
| slug (UNIQUE)      |       | timezone           |
| name               |       | currency           |
| status             |       | upi_id             |
+---------+----------+       +--------------------+
          |
          +-------------------------------+-------------------------------+
          |                               |                               |
          v                               v                               v
+--------------------+       +--------------------+       +--------------------+
|       users        |       |      doctors       |       |      patients      |
+--------------------+       +--------------------+       +--------------------+
| id (PK)            |       | id (PK)            |       | id (PK)            |
| tenant_id (FK)     |       | tenant_id (FK)     |       | tenant_id (FK)     |
| username           |       | user_id (FK)       |       | name, phone        |
| password_hash      |       | name, fee          |       | email, age         |
| role               |       | specialization     |       | gender             |
+--------------------+       +---------+----------+       +---------+----------+
                                       |                            |
                                       +--------------+-------------+
                                                      |
                                                      v
                                         +--------------------------+
                                         |       appointments       |
                                         +--------------------------+
                                         | id (PK)                  |
                                         | tenant_id (FK)           |
                                         | patient_id (FK)          |
                                         | doctor_id (FK)           |
                                         | slot_id (FK)             |
                                         | token_no                 |
                                         | booking_status           |
                                         | payment_status           |
                                         +------------+-------------+
                                                      |
                         +----------------------------+----------------------------+
                         v                                                         v
            +--------------------------+                              +--------------------------+
            |      prescriptions       |                              |         invoices         |
            +--------------------------+                              +--------------------------+
            | id (PK)                  |                              | id (PK)                  |
            | tenant_id (FK)           |                              | tenant_id (FK)           |
            | appointment_id (FK)      |                              | appointment_id (FK)      |
            | doctor_id (FK)           |                              | invoice_number           |
            | patient_id (FK)          |                              | amount, status           |
            | diagnosis, status        |                              | pdf_url                  |
            +--------------------------+                              +--------------------------+
```

### Proposed Table Definitions

#### 1. `tenants`
- **Columns:** `id UUID PK`, `slug VARCHAR(50) UNIQUE`, `name VARCHAR(150)`, `status VARCHAR(20) DEFAULT 'active'`, `created_at TIMESTAMPTZ`.
- **Purpose:** Root entity representing an independent clinic or healthcare organization.

#### 2. `tenant_settings`
- **Columns:** `tenant_id UUID PK FK(tenants.id)`, `support_phone VARCHAR(30)`, `timezone VARCHAR(50) DEFAULT 'Asia/Kolkata'`, `currency VARCHAR(10) DEFAULT 'INR'`, `upi_id VARCHAR(100)`, `system_prompt TEXT`, `created_at TIMESTAMPTZ`, `updated_at TIMESTAMPTZ`.
- **Purpose:** Replaces all single-clinic environment variables.

#### 3. `users`
- **Columns:** `id UUID PK`, `tenant_id UUID NOT NULL FK(tenants.id)`, `username VARCHAR(50)`, `password_hash VARCHAR(255)`, `role VARCHAR(30)`, `must_change_password BOOLEAN DEFAULT false`, `created_at TIMESTAMPTZ`.
- **Unique Constraint:** `UNIQUE (tenant_id, username)`.

#### 4. `doctors`
- **Columns:** `id UUID PK`, `tenant_id UUID NOT NULL FK(tenants.id)`, `user_id UUID NULL FK(users.id)`, `name VARCHAR(150)`, `specialization VARCHAR(150)`, `qualification VARCHAR(150)`, `registration_number VARCHAR(100)`, `consultation_fee NUMERIC(10,2)`, `status VARCHAR(20) DEFAULT 'active'`, `created_at TIMESTAMPTZ`.
- **Indexes:** `CREATE INDEX idx_doctors_tenant ON doctors(tenant_id)`.

#### 5. `patients`
- **Columns:** `id UUID PK`, `tenant_id UUID NOT NULL FK(tenants.id)`, `patient_code VARCHAR(50)`, `name VARCHAR(150)`, `phone VARCHAR(30)`, `email VARCHAR(150)`, `age INT`, `gender VARCHAR(20)`, `created_at TIMESTAMPTZ`.
- **Unique Constraint:** `UNIQUE (tenant_id, patient_code)`.
- **Indexes:** `CREATE INDEX idx_patients_tenant_phone ON patients(tenant_id, phone)`.

#### 6. `appointment_slots`
- **Columns:** `id UUID PK`, `tenant_id UUID NOT NULL FK(tenants.id)`, `doctor_id UUID NOT NULL FK(doctors.id)`, `slot_date DATE NOT NULL`, `start_time TIME NOT NULL`, `end_time TIME NOT NULL`, `status VARCHAR(20) DEFAULT 'available'`, `version INT DEFAULT 1`.
- **Unique Constraint:** `UNIQUE (tenant_id, doctor_id, slot_date, start_time)`.
- **Indexes:** `CREATE INDEX idx_slots_lookup ON appointment_slots(tenant_id, doctor_id, slot_date, status)`.

#### 7. `appointments`
- **Columns:** `id UUID PK`, `tenant_id UUID NOT NULL FK(tenants.id)`, `patient_id UUID NOT NULL FK(patients.id)`, `doctor_id UUID NOT NULL FK(doctors.id)`, `slot_id UUID NOT NULL FK(appointment_slots.id)`, `token_no VARCHAR(50) NOT NULL`, `amount NUMERIC(10,2)`, `payment_method VARCHAR(30)`, `payment_status VARCHAR(30)`, `booking_status VARCHAR(30)`, `created_at TIMESTAMPTZ`.
- **Unique Constraint:** `UNIQUE (tenant_id, token_no)`.

#### 8. `prescriptions`
- **Columns:** `id UUID PK`, `tenant_id UUID NOT NULL FK(tenants.id)`, `prescription_code VARCHAR(50)`, `appointment_id UUID NOT NULL FK(appointments.id)`, `doctor_id UUID NOT NULL FK(doctors.id)`, `patient_id UUID NOT NULL FK(patients.id)`, `date DATE NOT NULL`, `chief_complaints TEXT`, `diagnosis TEXT NOT NULL`, `symptoms TEXT`, `vitals JSONB`, `clinical_notes TEXT`, `advice TEXT`, `tests_advised TEXT`, `follow_up_date DATE`, `status VARCHAR(20) DEFAULT 'draft'`, `version INT DEFAULT 1`, `created_at TIMESTAMPTZ`, `finalized_at TIMESTAMPTZ`.
- **Unique Constraint:** `UNIQUE (tenant_id, prescription_code)`.

#### 9. `prescription_items`
- **Columns:** `id UUID PK`, `tenant_id UUID NOT NULL FK(tenants.id)`, `prescription_id UUID NOT NULL FK(prescriptions.id) ON DELETE CASCADE`, `name VARCHAR(150) NOT NULL`, `strength VARCHAR(50)`, `dosage VARCHAR(50)`, `frequency VARCHAR(50)`, `duration VARCHAR(50)`, `instructions TEXT`.

#### 10. `invoices`
- **Columns:** `id UUID PK`, `tenant_id UUID NOT NULL FK(tenants.id)`, `appointment_id UUID NOT NULL FK(appointments.id)`, `invoice_number VARCHAR(50) NOT NULL`, `amount NUMERIC(10,2) NOT NULL`, `payment_method VARCHAR(30)`, `payment_status VARCHAR(30)`, `pdf_url TEXT`, `created_at TIMESTAMPTZ`.
- **Unique Constraint:** `UNIQUE (tenant_id, invoice_number)`.

#### 11. `audit_logs`
- **Columns:** `id UUID PK`, `tenant_id UUID NOT NULL FK(tenants.id)`, `user_id UUID NULL`, `username VARCHAR(50)`, `action VARCHAR(100) NOT NULL`, `entity_type VARCHAR(50) NOT NULL`, `entity_id VARCHAR(100)`, `details JSONB`, `created_at TIMESTAMPTZ DEFAULT NOW()`.

---

# 18. Proposed Multi-Tenant Architecture

```
                  Incoming Request (HTTP / Webhook)
                                |
                                v
               +----------------------------------+
               |   Tenant Resolution Middleware   |
               | - Resolves via Subdomain         |
               | - Resolves via X-Tenant-ID       |
               | - Resolves via Telegram Bot ID   |
               +----------------+-----------------+
                                | Sets tenant context (ContextVar)
                                v
               +----------------------------------+
               |     FastAPI Dependencies / Auth  |
               | - Extracts user role & tenant_id |
               | - Verifies user.tenant == ctx    |
               +----------------+-----------------+
                                |
                                v
               +----------------------------------+
               |          Service Layer           |
               | (CrmService, PrescriptionService)|
               | Injects current tenant_id        |
               +----------------+-----------------+
                                |
                                v
               +----------------------------------+
               |   Tenant-Aware Repositories      |
               | Enforces WHERE tenant_id = :id   |
               | on all SELECT, UPDATE, DELETE    |
               +----------------+-----------------+
                                |
                                v
               +----------------------------------+
               |      PostgreSQL Database         |
               | Shared Tables + tenant_id        |
               +----------------------------------+
```

### Tenant Resolution Strategies
1. **Web Admin CRM & Doctor Portal:** Resolved via **Subdomain** (`acme-clinic.saas.com` -> `tenant_id`) or custom request header `X-Tenant-ID`.
2. **Telegram Webhook:** Resolved via the bot token or webhook route (`/webhook/telegram/{tenant_slug}`).
3. **Context Variable:** Python `contextvars.ContextVar("current_tenant_id")` holds the tenant ID across the async request lifecycle.

---

# 19. Proposed Production Folder Structure

```
D:\telegram_bot\
├── app\
│   ├── api\
│   │   ├── v1\
│   │   │   ├── admin\          # Tenant admin endpoints
│   │   │   ├── doctor\         # Doctor portal endpoints
│   │   │   ├── superadmin\     # SaaS platform oversight & tenant provisioning
│   │   │   ├── knowledge\      # Knowledge base & RAG endpoints
│   │   │   └── webhooks\       # Inbound channel webhooks (Telegram, WhatsApp)
│   │   └── deps.py             # FastAPI dependency injection (get_tenant, get_user)
│   ├── channels\               # Decoupled communication channel adapters
│   │   ├── base.py             # Abstract channel adapter interface
│   │   ├── telegram\           # Telegram adapter & keyboard builders
│   │   └── whatsapp\           # Future WhatsApp adapter
│   ├── core\
│   │   ├── auth.py             # JWT token issuance, verification, password hashing
│   │   ├── config.py           # Global platform settings (PostgreSQL URL, Redis URL)
│   │   ├── context.py          # Tenant contextvar management
│   │   └── exceptions.py       # Domain error definitions
│   ├── db\
│   │   ├── base.py             # SQLAlchemy DeclarativeBase
│   │   ├── session.py          # Async session factory
│   │   └── models\             # SQLAlchemy ORM models (Tenant, User, Doctor, Patient, etc.)
│   ├── repositories\           # Tenant-scoped database repositories
│   │   ├── base.py             # Base repository enforcing tenant_id filtering
│   │   ├── appointment_repo.py
│   │   ├── doctor_repo.py
│   │   ├── patient_repo.py
│   │   └── slot_repo.py
│   ├── services\               # Pure business logic services
│   │   ├── appointment_service.py
│   │   ├── audit_service.py
│   │   ├── crm_service.py
│   │   ├── prescription_service.py
│   │   └── tenant_service.py
│   ├── rag\
│   │   ├── pgvector_store.py   # PostgreSQL pgvector retrieval implementation
│   │   └── service.py          # Tenant-scoped knowledge search & ingestion
│   └── main.py                 # Application factory & middleware configuration
├── frontend\                   # Multi-tenant SPA
├── migrations\                 # Alembic database migration scripts
└── tests\                      # Pytest suite with tenant-isolation verification
```

---

# 20. Migration Strategy (Google Sheets → PostgreSQL)

### Staged Migration Steps
1. **Phase 1: Abstract Data Access Layer (Repository Pattern)**
   - Create abstract repository interfaces (`IPatientRepo`, `ISlotRepo`, `IDoctorRepo`).
   - Implement temporary Sheets adapters behind these interfaces to ensure zero breakage to existing tests.
2. **Phase 2: Introduce PostgreSQL & Alembic**
   - Initialize PostgreSQL engine and Alembic migration scripts.
   - Deploy proposed table schemas with foreign keys and `tenant_id` constraints.
3. **Phase 3: Data Migration Script**
   - Write an idempotent extraction script:
     - Read rows from `patient`, `doctor`, `appointment_slots` Google Sheets and local JSON files.
     - Create a default tenant (`tenant_id = default-uuid`, slug: `demo-clinic`).
     - Split patient rows into normalized `patients` and `appointments` records.
     - Migrate `doctor_accounts.json` into `users` table with existing PBKDF2 password hashes.
     - Migrate `prescriptions.json` into `prescriptions` and `prescription_items` tables.
4. **Phase 4: Dual-Run / Verification Mode**
   - Run API against PostgreSQL repositories in staging, verifying that all 281 existing tests pass against PostgreSQL test databases.
5. **Phase 5: Cutover & Deprecate Sheets**
   - Switch production environment to PostgreSQL repositories.
   - Decommission Google Sheets synchronization.

---

# 21. Risk Register

| Risk ID | Severity | Category | Risk Description | Impact | Mitigation Strategy |
|---|---|---|---|---|---|
| **RSK-01** | **CRITICAL** | Security | Cross-tenant data leakage if `tenant_id` is omitted in SQL queries. | Clinic A views Clinic B medical records (HIPAA / GDPR violation). | Enforce mandatory `tenant_id` in repository base class and enable PostgreSQL Row-Level Security (RLS). |
| **RSK-02** | **CRITICAL** | Concurrency | Double bookings during high-traffic scheduling. | Multiple patients assigned to same doctor slot. | PostgreSQL `SELECT ... FOR UPDATE` row-level locks on `appointment_slots` inside database transactions. |
| **RSK-03** | **HIGH** | Stability | Native FAISS DLL failure on Windows Application Control environments. | Application crashes during startup or RAG queries fail. | Replace FAISS with PostgreSQL `pgvector`, eliminating all native OS-level library dependencies. |
| **RSK-04** | **HIGH** | Security | Shared local disk storage for invoices and prescriptions. | Cross-tenant document tampering or unauthorized downloads. | Move all generated files to S3-compatible cloud storage with tenant path prefixes. |
| **RSK-05** | **MEDIUM** | Performance | Multi-worker cache inconsistency. | Doctors see stale slot availability on different server workers. | Migrate in-memory Python dictionaries to centralized Redis instance. |
| **RSK-06** | **MEDIUM** | Operations | Google Sheets quota limits during cutover phase. | API failures during parallel read/write migration. | Execute migration as a single-pass offline extraction job with rate limiting. |

---

# 22. Phase 1 Implementation Plan

```
Phase 1A: Security & Secret Hardening
├── Remove hardcoded UPI ID, demo passwords, and fallback secrets
└── Protect /api/v1/knowledge/upload with authentication dependency

Phase 1B: PostgreSQL Infrastructure Setup
├── Install SQLAlchemy 2.0 (asyncpg) and Alembic
├── Configure database connection handling and base models
└── Execute initial schema migration (tenants, users, tenant_settings)

Phase 1C: Multi-Tenant Context & Auth Upgrade
├── Implement TenantResolutionMiddleware & contextvars
├── Update JWT session creation to include tenant_id & role hierarchy
└── Add tenant validation dependency to all FastAPI routers

Phase 1D: Relational Domain Model Implementation
├── Create models for doctors, patients, appointment_slots, appointments
├── Create models for prescriptions, prescription_items, invoices, audit_logs
└── Implement repository layer with automatic tenant_id scoping

Phase 1E: Concurrency & Booking Transaction Engine
├── Implement PostgreSQL SELECT FOR UPDATE atomic slot reservation
└── Port CrmService appointment booking/reschedule/cancel logic

Phase 1F: RAG Migration to pgvector
├── Enable pgvector extension on PostgreSQL
└── Port RagService to query knowledge_chunks with tenant_id filter

Phase 1G: Multi-Tenant Test Suite & Verification
├── Implement tenant-isolation assertion test suite
└── Verify all 281 tests pass under multi-tenant architecture
```

---

# 23. Exact First Implementation Task

### Task 1.1: Security Hardening & Secret Extraction
Before introducing database tables or refactoring business logic, all critical security risks and hardcoded credentials must be sanitized:
1. **Extract Hardcoded Payment IDs:** Remove `upi_id = "khansyrian1@okhdfcbank"` from `app/tools/payments.py:28` and `app/tools/invoice.py:53`. Replace with a configurable setting `settings.clinic_upi_id`.
2. **Disable Default Demo Passwords:** In `app/services/doctor_account_service.py:30`, change `allow_demo_password = True` to `False` by default; require explicit opt-in via environment configuration only in non-production environments.
3. **Protect Knowledge Upload:** Add `Depends(get_current_admin)` to `POST /api/v1/knowledge/upload` in `app/api/knowledge.py:33` to prevent unauthenticated document uploads.
4. **Remove Default Production Passwords:** Raise a validation error in `app/core/config.py:83-93` if `CRM_SECRET_KEY` remains the default insecure string when starting in production mode.
