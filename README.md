# Kodnexus: Enterprise Multi-Tenant Clinical AI & Hospital Management Platform

A production-grade, multi-tenant clinical automation and SaaS platform designed for clinics and multi-specialty hospitals.

---

## 🏛️ Architectural Overview

```text
                                  +---------------------------------------+
                                  |     KODNEXUS SUPER ADMIN HUB          |
                                  | (/super-admin/ - Platform Management) |
                                  +-------------------+-------------------+
                                                      |
                  +-----------------------------------+-----------------------------------+
                  |                                   |                                   |
                  v                                   v                                   v
        +-------------------+               +-------------------+               +-------------------+
        |  Clinic Tenant A  |               |  Clinic Tenant B  |               |  Clinic Tenant C  |
        |  - PostgreSQL RLS |               |  - PostgreSQL RLS |               |  - PostgreSQL RLS |
        |  - Isolated RAG   |               |  - Isolated RAG   |               |  - Isolated RAG   |
        |  - WABA Phone ID  |               |  - WABA Phone ID  |               |  - WABA Phone ID  |
        |  - Feature Flags  |               |  - Feature Flags  |               |  - Feature Flags  |
        +---------+---------+               +---------+---------+               +---------+---------+
                  |                                   |                                   |
                  +-----------------------------------+-----------------------------------+
                                                      |
                                                      v
                                    +-----------------------------------+
                                    |     CONVERSATIONAL AI ENGINE      |
                                    |     (LangGraph + Gemini)          |
                                    +-----------------+-----------------+
                                                      |
                                                      v
                                        [Meta WhatsApp Cloud API]
                                   - Inbound Text & Voice Notes (Sarvam STT)
                                   - Outbound Text & Interactive Action Buttons
                                   - Dynamic Multi-Tenant Webhook Routing
                                   - Natural Voice Note Replies (Sarvam TTS)
```

---

## ✨ Core Production Features

### 1. Multi-Tenant SaaS & Data Isolation
- **Strict Data Partitioning:** Each clinic facility operates inside an isolated PostgreSQL namespace (`tenant_id`). Zero data leakage between clinics.
- **Fail-Closed Security:** Unrecognized phone number IDs or unauthenticated requests are rejected immediately before touching database layers.
- **Granular AI Feature Flags:** Toggled per clinic from Super Admin (e.g. `voice_inbound`, `voice_outbound`, `interactive_lists`, `online_payments`, `rag_knowledge`, `prescription_generation`).

### 2. Super Admin Platform Hub (`/super-admin/`)
- **Clinic Onboarding:** Add new healthcare facilities with dedicated timezones, working hours, and billing configurations.
- **WhatsApp Self-Serve Management:** Configure Phone Number ID, Display Number, and WABA Account ID with a live **"⚡ Test Meta Connection"** diagnostic ping against Meta Graph API.
- **Isolated RAG Knowledge Base:** Upload PDFs, TXT, or Markdown documents per tenant to ground AI responses strictly in each clinic's clinical policy and pricing.
- **Platform Audit Trail:** Comprehensive, tamper-evident logs tracking administrative changes with automatic secret redaction.

### 3. Doctor Priority Consultation Queue & Payment Gate
- **Payment Confirmation Gate:** Doctors can filter consultation queues to view patients whose payments have been verified and confirmed by reception/admin (`require_paid=true`).
- **Priority Queue Numbers:** Chronological consultation order (`#1 NEXT`, `#2`, `#3...`) computed naturally by appointment date, time, and token sequence.
- **Server-Side Pagination:** Zero browser freezing on large patient and prescription datasets with server-side limit/offset queries (`page` & `page_size`).

### 4. Natural Conversational AI & Dual-Engine Mode
- **Dual-Engine Architecture (Super Admin Switchboard):**
  - **🧠 AI-Powered Agent Mode (Default: Active):** Full dynamic LLM understanding at every step. Patient can speak in Hindi, Hinglish, or English, ask side-questions (address, timing, fees) mid-booking without breaking flow, and receive intelligent contextual resumption.
  - **⚡ Rule-Based Mode (Token-Saver):** Toggled OFF per clinic from Super Admin. Operates strictly via deterministic menus, interactive quick buttons, and regex phone/name validators with zero/minimal LLM token consumption.
- **Side-Question Resumption:** When a patient asks clinic information (e.g. *"hospital ka address dena"*) while choosing a doctor or giving a phone number, the bot answers accurately from RAG knowledge and gracefully appends step resumption guidance.
- **Conversational Disambiguation:** Distinguishes clarifying remarks (e.g. *"number du ?"*) from step input without blindly storing conversational queries into patient records.

### 5. Automated WhatsApp Prescription Dispatch (HealthPlix Style)
- **Instant Consultation Delivery:** When a physician clicks **"Finalize"** on a prescription in the Doctor Portal, the system generates a high-fidelity ReportLab PDF document.
- **Direct Patient WhatsApp Delivery:** Dispatches the digital prescription PDF directly to the patient's registered WhatsApp phone number via Meta WhatsApp Cloud API (`send_document` / `upload_media`) with a personalized clinical message and appointment token reference.
- **Non-Blocking Reliability:** Asynchronous, fail-safe background dispatch ensuring clinical workflows never hang even during transient network or WhatsApp provider outages.

---

## 🔐 Default Access Credentials

| Portal | URL | Default Username | Default Password | Environment Key |
|---|---|---|---|---|
| **Super Admin Platform** | `http://localhost:8000/super-admin/` | `superadmin` | `AdminSecret2026!` | `SUPER_ADMIN_PASSWORD` |
| **Admin CRM** | `http://localhost:8000/admin/` | `admin` | `admin123` | `CRM_ADMIN_PASSWORD` |
| **Doctor Portal** | `http://localhost:8000/admin/` *(select Doctor Login)* | `dr_arjun` | `DocPassword2026!` | Set via Admin CRM / DB |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11 or 3.12
- PostgreSQL 15+ running on port `5432`

### 1. Environment Configuration
Copy `.env.example` to `.env` and configure your API keys:

```dotenv
# Database
DATABASE_URL=postgresql+psycopg2://postgres:1234@localhost:5432/telegram_bot

# Super Admin Credentials
SUPER_ADMIN_USERNAME=superadmin
SUPER_ADMIN_PASSWORD=AdminSecret2026!

# Admin CRM Credentials
CRM_ADMIN_USERNAME=admin
CRM_ADMIN_PASSWORD=admin123

# LLM & AI
GEMINI_API_KEY=your_gemini_api_key

# Meta WhatsApp Cloud API
WHATSAPP_ACCESS_TOKEN=your_permanent_or_system_user_token
WHATSAPP_PHONE_NUMBER_ID=1345059468697224
WHATSAPP_WEBHOOK_VERIFY_TOKEN=your_secure_verify_token
WHATSAPP_API_VERSION=v21.0

# Sarvam Voice AI
SARVAM_API_KEY=your_sarvam_api_key
SARVAM_STT_MODEL=saaras:v3
SARVAM_TTS_MODEL=bulbul:v3
SARVAM_TTS_SPEAKER=shubh
```

### 2. Run Database Migrations
```bash
python -m alembic upgrade head
```

### 3. Start Application
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🐳 Docker & Containerized Production Deployment

The entire Kodnexus platform is fully containerized with automated PostgreSQL healthchecks, directory provisioning, and automatic Alembic migrations.

### Quick Start with Docker Compose:

1. **Configure Production Environment:**
   ```bash
   cp .env.docker.example .env
   # Edit .env with your Gemini API key and Meta WhatsApp credentials
   ```

2. **Build and Launch Containerized Stack:**
   ```bash
   docker compose up --build -d
   ```

3. **Verify Deployment & Container Health:**
   ```bash
   docker compose ps
   docker compose logs -f app
   ```

The application automatically:
- Connects to the isolated `postgres:15-alpine` container on port `5432`.
- Waits for database readiness with automated retry backoffs.
- Applies all database migrations automatically (`alembic upgrade head`).
- Creates persistent volumes for clinic data (`clinic_data`) and logs (`clinic_logs`).
- Binds to `http://localhost:8000` with active container healthchecks on `/health`.

---

## 🧪 Automated Test Suites

All 452 automated tests covering Multi-Tenant Isolation, Dynamic RAG Ingestion, Doctor Consultation Queues, Super Admin Switchboards, AI Reasoning, and WhatsApp Cloud API dispatches pass cleanly:

```bash
python -m pytest tests/ -q
```

---

## 📄 License & Ownership
Proprietary software developed for **Kodnexus Multi-Tenant Clinical Systems**. All rights reserved.
