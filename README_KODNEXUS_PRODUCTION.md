# Kodnexus Healthcare AI — Multi-Tenant SaaS Platform
## Production Architecture & Operational Runbook

Welcome to the **Kodnexus Healthcare AI Platform** (`D:\telegram_bot`), an enterprise-grade, multi-tenant conversational AI suite designed for clinics, diagnostic centers, and multi-specialty hospitals.

The platform provides unified multi-channel patient engagement across **WhatsApp Cloud API** and **Telegram**, backed by **LangGraph**, **Google Gemini**, **Sarvam AI (Voice STT/TTS)**, isolated **Tenant RAG Vector Stores**, and a centralized **Super Admin Console** branded for **Kodnexus**.

---

## Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [Dynamic WhatsApp Routing & Fail-Closed Isolation](#2-dynamic-whatsapp-routing--fail-closed-isolation)
3. [Super Admin Console & Tenant Onboarding](#3-super-admin-console--tenant-onboarding)
4. [Subscription Plans & Feature Toggle Matrix](#4-subscription-plans--feature-toggle-matrix)
5. [Tenant-Isolated RAG Knowledge Base](#5-tenant-isolated-rag-knowledge-base)
6. [Meta WhatsApp Cloud API Setup Guide](#6-meta-whatsapp-cloud-api-setup-guide)
7. [Production Deployment Checklist & Runbook](#7-production-deployment-checklist--runbook)
8. [API Reference & Security](#8-api-reference--security)

---

## 1. Architecture Overview

```
                      +---------------------------------------+
                      |       Meta WhatsApp Cloud API         |
                      |   (POST /webhook/whatsapp)            |
                      +-------------------+-------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        Kodnexus FastAPI Platform Hub                              |
|                                                                                   |
|  1. Webhook Signature Verification (X-Hub-Signature-256 HMAC-SHA256)              |
|  2. In-Memory Message Deduplication (anti-replay cache)                           |
|  3. Dynamic Tenant Resolution (phone_number_id -> tenant_id via DB + TTL Cache)   |
|  4. Fail-Closed Gate: Reject unmapped numbers without touching clinical data      |
+-----------------------------------------------------------------------------------+
                                          |
          +-------------------------------+-------------------------------+
          |                                                               |
          v                                                               v
+-----------------------+                                       +-------------------+
|   Clinic Alpha        |                                       |   Clinic Beta     |
|   (STARTER)           |                                       |   (ENTERPRISE)    |
|   - Text Chat         |                                       |   - Voice In/Out  |
|   - Interactive Lists |                                       |   - Instant UPI   |
|   - Pay at Clinic     |                                       |   - Custom RAG    |
|   - RAG Knowledge     |                                       |   - All Toggles ON|
+-----------------------+                                       +-------------------+
          |                                                               |
          +-------------------------------+-------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                     Tenant-Isolated Clinical Services & Storage                   |
|                                                                                   |
|   - PostgreSQL (Clinics, Doctors, Schedules, Appointments, Patients, Invoices)    |
|   - RAG Knowledge Base: data/tenants/{tenant_id}/knowledge/                       |
|   - Vectorstore Index: data/tenants/{tenant_id}/vectorstore/                      |
|   - LangGraph State Machine & Gemini LLM Execution Context                        |
|   - Sarvam AI Speech-to-Text & Text-to-Speech Processing                          |
+-----------------------------------------------------------------------------------+
```

### Key Architectural Tenets
- **Single Multi-Tenant Endpoint**: All clinic WhatsApp traffic hits one single URL: `POST /webhook/whatsapp`.
- **Dynamic Phone Number ID Routing**: Meta webhooks provide `metadata.phone_number_id`. The platform dynamically resolves this to the respective clinic tenant using the PostgreSQL database with an in-memory cache.
- **Strict Fail-Closed Multi-Tenancy**: If an incoming message originates from an unknown or unmapped `phone_number_id`, the system immediately logs a security warning and drops the request. No patient records, doctor schedules, or LLM tokens are consumed.
- **Parent Platform Branding**: The Super Admin infrastructure is branded for **Kodnexus**, allowing platform operators to manage subscriptions, feature flags, and knowledge bases across hundreds of clinic clients.

---

## 2. Dynamic WhatsApp Routing & Fail-Closed Isolation

### Inbound Flow
1. Patient sends a message (text, button selection, list item, or voice note) to the clinic's WhatsApp Business Number.
2. Meta Cloud API dispatches a webhook to `POST /webhook/whatsapp`.
3. The router validates the payload signature using the Meta App Secret (`x-hub-signature-256`).
4. `WhatsAppHandler.resolve_tenant_id(phone_number_id)` inspects `entry[0].changes[0].value.metadata.phone_number_id`.
5. The handler checks `TenantManagementService`:
   - Checks the in-memory cache `_phone_id_to_tenant`.
   - If not cached, executes a database query against `clinics.whatsapp_phone_number_id`.
   - Caches the resolution for zero-latency subsequent requests.
6. If the ID is unmapped: **Fail-Closed**. Execution halts immediately.
7. If mapped: Loads clinic configuration, applies tenant-specific feature flags, and dispatches the interaction into the tenant-scoped LangGraph session.

### Outbound Reply Flow
- The agent formats the reply using **Interactive WhatsApp Elements** (quick-reply buttons, selection lists, UPI payment callouts, or Sarvam voice audio notes).
- Outbound requests are sent directly to `https://graph.facebook.com/v21.0/{phone_number_id}/messages` using the Meta Bearer Token.

---

## 3. Super Admin Console & Tenant Onboarding

The Kodnexus Super Admin Console is available at:
```
http://localhost:8000/super-admin
```
*(Production URL: `https://<your-domain>/super-admin`)*

### Access Credentials
- **Default Super Admin Username**: `superadmin`
- **Default Super Admin Password**: `AdminSecret2026!` *(Configurable via `SUPER_ADMIN_PASSWORD` in `.env`)*

### Platform Dashboard Features
1. **Platform Metrics**: Live count of Total Clinics, Active Clinics, Suspended Clinics, Tenant Administrators, and RAG index health.
2. **Onboard New Clinic**:
   - Clinic ID (slug identifier, e.g., `apollo_delhi`, `max_saket`).
   - Facility Name & Legal Business Entity Name.
   - Contact details (phone, email, address, timezone, currency).
   - **WhatsApp Business Credentials**:
     * WhatsApp Display Phone Number (e.g., `+1 555 661 1657`).
     * Meta Phone Number ID (e.g., `1345059468697224`).
     * WhatsApp Business Account ID (WABA ID).
   - **Subscription Plan Selection**: `STARTER`, `PROFESSIONAL`, or `ENTERPRISE`.
   - **Initial Clinic Admin Account**: Automatically provisions a tenant administrator with scoped credentials.
3. **Tenant Management Modal**:
   - **Overview Tab**: Edit clinic contact details, WhatsApp phone IDs, and subscription tier (`ACTIVE`, `INACTIVE`, `SUSPENDED`).
   - **AI Feature Toggles Tab**: Real-time switchboard of 8 AI capabilities with instant database persistence and zero restart required.
   - **RAG Knowledge Base Tab**: Drag-and-drop document upload (`.pdf`, `.txt`, `.md`), file list with sizes and update timestamps, document deletion, and real-time vector re-indexing.
4. **Platform Audit Trail**: View real-time security events, subscription upgrades, feature toggles, and document updates with all sensitive tokens automatically redacted.

---

## 4. Subscription Plans & Feature Toggle Matrix

Kodnexus provides 3 baseline subscription tiers. Every clinic is assigned a tier, which sets the default baseline capabilities. Platform administrators can also toggle individual flags on or off for any clinic on demand.

### Plan Tiers Summary

| Feature Capability | Flag Key | STARTER | PROFESSIONAL | ENTERPRISE |
| :--- | :--- | :---: | :---: | :---: |
| **Conversational Text AI** | Built-in | Yes | Yes | Yes |
| **Interactive Selection Lists** | `interactive_lists` | Yes | Yes | Yes |
| **Clinic Knowledge Base (RAG)**| `rag_knowledge` | Yes | Yes | Yes |
| **Self-Service Rescheduling** | `rescheduling` | Yes | Yes | Yes |
| **Self-Service Cancellation** | `cancellation` | Yes | Yes | Yes |
| **Inbound Voice Notes (STT)** | `voice_inbound` | No | **Yes** | **Yes** |
| **Outbound Voice Notes (TTS)**| `voice_outbound` | No | No | **Yes** |
| **Online UPI Payments & QR** | `online_payments` | No | **Yes** | **Yes** |
| **Report Enquiry Service** | `report_enquiry` | No | No | **Yes** |

### Graceful Fallbacks & Patient Communication
When a patient attempts to access a disabled capability, the AI agent does not error or crash. It replies politely with a personalized message:

- **Voice Inbound Disabled (e.g. Starter Plan)**:
  > *"Voice messaging is currently not enabled for [Clinic Name]. Please send your message or appointment request as a text message."*
  *(Audio files are rejected at the webhook boundary before downloading, preserving network bandwidth and Sarvam API credits).*

- **Online Payments Disabled**:
  The bot omits online UPI payment links and presents only the **"Pay at Clinic"** option on WhatsApp buttons.

- **Interactive Lists Disabled**:
  The bot formats doctor choices, departments, and time slots into numbered, readable text prompts instead of native WhatsApp list widgets.

- **Cancellation / Rescheduling Disabled**:
  > *"Online appointment cancellation is currently disabled for [Clinic Name]. Please contact our clinic reception at [Support Phone] directly to cancel or modify your booking."*

---

## 5. Tenant-Isolated RAG Knowledge Base

Each clinic maintains a completely segregated knowledge base. Documents uploaded for Clinic A can never be retrieved by patients of Clinic B.

### Partitioning Scheme
- **Document Source Files**: `data/tenants/{tenant_id}/knowledge/`
- **Vector Embeddings Store**: `data/tenants/{tenant_id}/vectorstore/`

### Supported Document Types
- **PDF Documents** (`.pdf`): Clinical brochures, doctor profiles, service price lists, policy manuals.
- **Text Files** (`.txt`): FAQs, clinic timings, insurance provider lists.
- **Markdown Files** (`.md`): Structured treatment guides, preparation instructions.

### Management via Super Admin API
- **List Documents**: `GET /api/super-admin/tenants/{tenant_id}/documents`
- **Upload Document**: `POST /api/super-admin/tenants/{tenant_id}/documents` (multipart form with file)
  * Sanitizes filenames to prevent path traversal.
  * Automatically triggers `rag_service.rebuild_index()` for the tenant.
- **Delete Document**: `DELETE /api/super-admin/tenants/{tenant_id}/documents/{filename}`
  * Safely removes the file and automatically rebuilds the vector store.

---

## 6. Meta WhatsApp Cloud API Setup Guide

To connect a clinic's live WhatsApp Business number to Kodnexus, follow these steps:

### Step 1: Meta Developer Account & App Creation
1. Go to [developers.facebook.com](https://developers.facebook.com/) and log in with your Meta account.
2. Click **My Apps** -> **Create App**.
3. Select **Other** -> **Business** as the app type.
4. Name the app (e.g., `Kodnexus AI Healthcare Platform`) and associate it with your Meta Business Account.
5. In the App Dashboard, add the **WhatsApp** product.

### Step 2: Obtain a Permanent System User Token
> **WARNING**: Never use the 24-hour temporary token in production! It will expire daily and break messaging.

1. Navigate to **Meta Business Suite** -> **Settings** -> **Business Settings** (`business.facebook.com/settings`).
2. Go to **Users** -> **System Users**.
3. Click **Add**, name the system user (e.g., `kodnexus-bot`), and assign the **Admin** role.
4. Under **Assets**, click **Add Assets**:
   - Select **Apps** -> Choose your WhatsApp App -> Enable **Full Control**.
   - Select **WhatsApp Business Accounts** -> Choose your WABA -> Enable **Full Control**.
5. Click **Generate New Token**:
   - Select your WhatsApp App.
   - Set Token Expiration to **Never** (Permanent).
   - Select permissions:
     * `whatsapp_business_messaging`
     * `whatsapp_business_management`
6. Copy the generated permanent token and save it securely in your `.env` as `WHATSAPP_ACCESS_TOKEN`.

### Step 3: Configure Webhook in Meta Developer Portal
1. In the App Dashboard, go to **WhatsApp** -> **Configuration**.
2. Under **Webhook**, click **Edit**:
   - **Callback URL**: `https://<your-domain>/webhook/whatsapp`
   - **Verify Token**: Enter the value configured in `.env` (`WHATSAPP_VERIFY_TOKEN`, e.g., `clinic_secret_token_2026`).
3. Click **Verify and Save**. Meta will send a GET challenge request; FastAPI will return HTTP 200.
4. Under **Webhook fields**, click **Manage** and subscribe to:
   - `messages` (Mandatory: incoming text, interactive replies, audio notes).

### Step 4: Add Clinic Phone Number to Kodnexus Super Admin
1. Copy the **Phone Number ID** from Meta WhatsApp Dashboard (e.g., `1345059468697224`).
2. Log into the Kodnexus Super Admin Console (`/super-admin`).
3. Create or Edit the Clinic Tenant, and enter the Phone Number ID.
4. Save. Incoming messages to that number will instantly route to that clinic!

---

## 7. Production Deployment Checklist & Runbook

### Pre-Requisites
- **Operating System**: Ubuntu 22.04 LTS / Debian 12 / Windows Server 2022
- **Python**: 3.12+
- **Database**: PostgreSQL 15+
- **Reverse Proxy**: Nginx or Caddy with valid SSL certificate (Let's Encrypt)
- **Domain**: Fully Qualified Domain Name (FQDN) pointing to server IP

### Environment Configuration (`.env`)
Create `.env` based on `.env.example`:
```dotenv
# Platform Secrets
APP_ENV=production
DEBUG=false
SECRET_KEY=generate_a_random_64_char_hex_secret
SUPER_ADMIN_PASSWORD=SetAStrongProductionSecret!2026

# Database
DATABASE_URL=postgresql://clinic_user:strong_password@localhost:5432/clinic_db

# Meta WhatsApp Cloud API
WHATSAPP_VERIFY_TOKEN=clinic_secret_token_2026
WHATSAPP_APP_SECRET=your_meta_app_secret_here
WHATSAPP_ACCESS_TOKEN=EAAG...your_permanent_system_user_token...
WHATSAPP_PHONE_NUMBER_ID=1345059468697224

# Sarvam AI (Voice STT / TTS)
SARVAM_API_KEY=your_sarvam_api_key_here
SARVAM_STT_MODEL=saaras:v3
SARVAM_TTS_MODEL=bulbul:v3
SARVAM_TTS_SPEAKER=shubh

# Google Gemini AI
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash
```

### Database Migration
Apply all database schema upgrades:
```bash
alembic upgrade head
```

### Systemd Service Unit (`/etc/systemd/system/kodnexus.service`)
```ini
[Unit]
Description=Kodnexus Healthcare AI Platform
After=network.target postgresql.service

[Service]
Type=simple
User=kodnexus
WorkingDirectory=/opt/kodnexus/telegram_bot
EnvironmentFile=/opt/kodnexus/telegram_bot/.env
ExecStart=/opt/kodnexus/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```
Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable kodnexus
sudo systemctl start kodnexus
```

### Nginx Reverse Proxy Configuration
```nginx
server {
    server_name api.kodnexus.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 90;
        client_max_body_size 25M;
    }

    listen 443 ssl http2;
    ssl_certificate /etc/letsencrypt/live/api.kodnexus.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.kodnexus.com/privkey.pem;
}
```

---

## 8. API Reference & Security

### Key Super Admin Endpoints (`/api/super-admin/`)
*Protected by HTTP Basic Authentication (`superadmin:SUPER_ADMIN_PASSWORD`)*

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/super-admin/login` | Authenticate Super Admin and obtain session cookie / state |
| `GET` | `/api/super-admin/dashboard` | Platform metrics, clinic totals, and service health |
| `GET` | `/api/super-admin/tenants` | List all registered clinic tenants |
| `POST` | `/api/super-admin/tenants` | Onboard a new clinic tenant with WhatsApp credentials and plan |
| `PATCH` | `/api/super-admin/tenants/{id}/features` | Update live AI feature toggles (`voice_inbound`, `online_payments`, etc.) |
| `PATCH` | `/api/super-admin/tenants/{id}/subscription` | Update subscription tier (`STARTER`, `PROFESSIONAL`, `ENTERPRISE`) |
| `GET` | `/api/super-admin/tenants/{id}/documents` | List uploaded RAG documents |
| `POST` | `/api/super-admin/tenants/{id}/documents` | Upload and auto-index document (`.pdf`, `.txt`, `.md`) |
| `DELETE`| `/api/super-admin/tenants/{id}/documents/{filename}` | Delete document and rebuild vector index |
| `GET` | `/api/super-admin/audit-logs` | Retrieve platform operations audit trail |

### Security Guarantees
- **HMAC-SHA256 Webhook Verification**: Meta webhooks are authenticated with the Meta App Secret. Tampered or unsigned requests return HTTP 403.
- **Fail-Closed Protection**: Unmapped numbers never query clinic databases or trigger LLM generation.
- **Zero Token Leakage**: Tokens and credentials (`WHATSAPP_ACCESS_TOKEN`, `GEMINI_API_KEY`, `SARVAM_API_KEY`) are excluded from JSON responses, logs, and audit records.
- **Data Isolation**: Database queries enforce `WHERE clinic_id = :tenant_id` at every layer.

---
*Kodnexus Healthcare AI Platform — Engineering Documentation 2026*

