# Meta WhatsApp Cloud API Setup & Go-Live Guide

**Project:** Clinic Management AI Assistant & CRM  
**Target Channel:** Official Meta WhatsApp Cloud API  
**Auditor:** Antigravity Principal Software Architect  
**Backend Webhook URL:** `https://<your-public-domain>/webhook/whatsapp`  

---

## 1. Meta Developer Dashboard Setup

Follow these exact steps in the Meta developer portal:

### Step 1: Create or Select Your Meta Business App
1. Go to [developers.facebook.com](https://developers.facebook.com/) and log in with your business Facebook account.
2. Click **My Apps** > **Create App**.
3. Select **Other** as the app use case > Click **Next**.
4. Select App Type: **Business** > Click **Next**.
5. Give your app a display name (e.g. `Clinic AI Assistant`) and associate your **Meta Business Account**.
6. Click **Create app**.

### Step 2: Add WhatsApp Product
1. On the App Dashboard screen, scroll to **Add products to your app**.
2. Find **WhatsApp** and click **Set up**.
3. You will be redirected to the **WhatsApp > Quickstart / API Setup** page.

### Step 3: Gather API Credentials
In **WhatsApp > API Setup**:
* **Phone Number ID:** Copy the 15–16 digit number displayed under **From** (e.g. `104829384918293`).
* **WhatsApp Business Account ID:** Copy the 15–16 digit account ID.
* **Temporary Access Token:** Copy this for initial testing (valid for 24 hours).

### Step 4: Create a Permanent System User Token (Crucial for Production)
*Temporary tokens expire in 24 hours. For live production, you MUST generate a permanent token:*
1. Go to [business.facebook.com/settings](https://business.facebook.com/settings).
2. Under **Users** > click **System Users** > click **Add**.
3. Name: `whatsapp-bot-service`, Role: **Admin**.
4. Under **Assigned Assets**, click **Assign Assets** > select your WhatsApp Business Account > grant **Full Control**.
5. Click **Generate New Token**:
   - Select your App.
   - Token Expiration: **Never**.
   - Check permissions: `whatsapp_business_messaging` and `whatsapp_business_management`.
   - Click **Generate Token** and store it securely.

### Step 5: Copy App Secret
1. Go to **App Settings** > **Basic** in the Meta Developer Dashboard.
2. Next to **App Secret**, click **Show** and copy the secret.

---

## 2. Local Configuration (`.env`)

Add the following variables to your production `.env` file at `D:\telegram_bot\.env`:

```ini
# ==========================================
# Meta WhatsApp Cloud API Configuration
# ==========================================
WHATSAPP_ENABLED=true
WHATSAPP_API_VERSION=v21.0
WHATSAPP_ACCESS_TOKEN=<your_permanent_system_user_token>
WHATSAPP_PHONE_NUMBER_ID=<your_phone_number_id>
WHATSAPP_BUSINESS_ACCOUNT_ID=<your_business_account_id>
WHATSAPP_APP_SECRET=<your_app_secret>
WHATSAPP_VERIFY_TOKEN=<generate_a_secure_random_string_e.g_clinic_token_9f82d1>
WHATSAPP_WEBHOOK_URL=https://<your-public-domain>/webhook/whatsapp
WHATSAPP_DEFAULT_COUNTRY_CODE=91

# Tenant Routing Mapping (JSON format: phone_number_id -> tenant_id)
WHATSAPP_TENANT_PHONE_MAP={"<your_phone_number_id>": "default"}
```

### How to Verify Configuration Safely (Without Printing Secrets)
Run this PowerShell command in `D:\telegram_bot`:
```powershell
python -c "
from app.core.config import get_settings
s = get_settings()
print('WhatsApp Enabled:', s.whatsapp_enabled)
print('Phone Number ID:', s.whatsapp_phone_number_id)
print('Token Configured:', bool(s.whatsapp_access_token))
print('Secret Configured:', bool(s.whatsapp_app_secret))
print('Verify Token Set:', bool(s.whatsapp_verify_token))
print('Tenant Mapping:', s.get_whatsapp_tenant_mapping())
"
```

---

## 3. Public HTTPS Webhook Setup

Meta servers cannot send webhooks to `http://localhost:8000`. You must expose an HTTPS endpoint.

### Option A: Local Testing with Cloudflare Tunnel (Recommended for Development)
1. Download `cloudflared.exe` from Cloudflare.
2. In PowerShell, run:
   ```powershell
   cloudflared tunnel --url http://localhost:8000
   ```
3. Copy the generated public URL (e.g. `https://random-subdomain.trycloudflare.com`).
4. Your webhook callback URL will be:
   `https://random-subdomain.trycloudflare.com/webhook/whatsapp`

### Option B: Production Staging on a VPS (Nginx + Let's Encrypt)
On your Linux or Windows server with domain `api.yourclinic.com`:
```nginx
server {
    server_name api.yourclinic.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/api.yourclinic.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourclinic.com/privkey.pem;
}
```

### Step 4: Register Webhook in Meta Dashboard
1. Go to **WhatsApp > Configuration** in the Meta Developer Dashboard.
2. In the **Webhook** section, click **Edit**.
3. **Callback URL:** `https://<your-public-domain>/webhook/whatsapp`
4. **Verify Token:** The exact value of `WHATSAPP_VERIFY_TOKEN` configured in `.env`.
5. Click **Verify and Save**.
   - *Meta will send a GET request with `hub.challenge`. Your FastAPI server will automatically verify the token and return the challenge with HTTP 200.*
6. Under **Webhook fields**, click **Manage** > click **Subscribe** on the **`messages`** row.

---

## 4. Testing End-to-End Inbound & Outbound

### 1. Launch FastAPI Application
In PowerShell:
```powershell
cd D:\telegram_bot
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Verify Health Check
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health?details=true"
```

### 3. Send a Real WhatsApp Test Message
1. In Meta Dashboard > **WhatsApp > API Setup**:
   - In the **To** field, add your personal WhatsApp mobile number as an authorized test recipient.
   - Verify your phone using the 6-digit OTP sent by Meta.
2. Open WhatsApp on your phone and send a message to the test business phone number:
   > *"Hello, I want to book an appointment with Dr. Mehta for tomorrow."*
3. The chatbot will reply via WhatsApp with doctor availability and interactive confirmation buttons (`Confirm Booking` / `Cancel`).
4. Tap **Confirm Booking** to complete the reservation and receive your appointment token and UPI payment details.

---

## 5. Production Activation Checklist

- [ ] Permanent System User Token generated with `whatsapp_business_messaging` permissions.
- [ ] Registered live business phone number (not a personal number) verified via SMS/Voice in Meta Business Manager.
- [ ] Completed Meta Business Verification (removes 250 conversations/day messaging tier limit).
- [ ] Created and submitted notification templates in Meta WhatsApp Manager (e.g. `appointment_confirmation_v1`, `appointment_reminder_v1`) for re-engaging patients outside the 24-hour service window.
- [ ] Webhook URL configured with a valid SSL/TLS certificate.
- [ ] Subscribed to `messages` webhook field in Meta dashboard.
- [ ] Set `ALLOW_DEMO_PASSWORD=false` and high-entropy `CRM_SECRET_KEY` in `.env`.
- [ ] Tested cancellation and rescheduling flows.

---

## 6. Comprehensive Troubleshooting Guide

| Issue | Likely Root Cause | How to Confirm | Resolution |
| :--- | :--- | :--- | :--- |
| **Meta displays: "The URL couldn't be validated"** | Callback URL is unreachable, or `hub.verify_token` did not match. | Check terminal logs for `GET /webhook/whatsapp`. | Ensure public HTTPS domain is online and `WHATSAPP_VERIFY_TOKEN` matches `.env` exactly. |
| **HTTP 403 Forbidden on incoming messages** | Webhook HMAC signature verification failed (`X-Hub-Signature-256`). | Logs show `Invalid X-Hub-Signature-256`. | Verify that `WHATSAPP_APP_SECRET` in `.env` matches the App Secret in App Settings > Basic. |
| **Messages received but no AI response sent** | `WHATSAPP_ACCESS_TOKEN` is missing, expired, or lacking permissions. | Logs show `Meta WhatsApp API error: 401 Unauthorized` or `OAuthException`. | Generate a Permanent System User Token with `whatsapp_business_messaging` permission. |
| **Message says: "Recipient phone number not in allowed list"** | Meta development sandbox is active and recipient number is not verified. | Error code 131030 in logs. | Add recipient phone number to the sandbox allowlist in WhatsApp > API Setup, or switch App Mode from Development to Live. |
| **AI response generated but cannot reach patient** | 24-hour customer service window expired, and ordinary text was sent instead of a pre-approved template. | Error code 131047 in logs (`Re-engagement message`). | The patient must initiate the conversation, or you must send an approved template message. |
| **Duplicate responses sent to patient** | Meta retried the webhook because processing took >500ms. | Repeated webhook deliveries in logs. | Ensure background task dispatch is active (`BackgroundTasks.add_task`). The system already returns HTTP 200 in <50ms. |
| **Interactive buttons do not appear on phone** | Button text exceeds 20 characters or message has more than 3 buttons. | Client logs fallback to standard text. | Character count is automatically truncated to 20 chars by `MetaWhatsAppClient.send_interactive_buttons`. |
| **Wrong clinic context loaded** | Receiving business phone number ID not mapped in `WHATSAPP_TENANT_PHONE_MAP`. | Session logs show `tenant=default`. | Add `"phone_number_id": "clinic_tenant_id"` to `WHATSAPP_TENANT_PHONE_MAP` in `.env`. |

