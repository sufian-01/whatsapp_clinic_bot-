# Production Deployment & Operations Guide

**Project:** Clinic Management AI Assistant & CRM  
**Target Environment:** Windows Server / Linux VPS  
**Python Runtime:** Python 3.12.10  
**Application Server:** FastAPI + Uvicorn ASGI  

---

## 1. System Requirements & Prerequisites

* **Operating System:** Windows Server 2022 / Windows 11, or Ubuntu 22.04+ LTS.
* **Python:** Python 3.12.10 (64-bit).
* **Database:** PostgreSQL 16 (local or cloud-managed e.g. AWS RDS, Supabase).
* **Memory / CPU:** Minimum 2 vCPU, 4GB RAM (8GB recommended for FAISS vector search & concurrent LLM calls).
* **Network:** Inbound HTTPS port 443 with valid SSL certificate for Meta webhooks.

---

## 2. Environment Installation & Dependencies

### Windows (PowerShell)
```powershell
# Navigate to project directory
cd D:\telegram_bot

# Create and activate Python virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Upgrade pip and install pinned production dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Linux (Bash)
```bash
cd /opt/telegram_bot
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. Database Setup & Safe Migration

### Step 1: Provision PostgreSQL
Connect to your PostgreSQL 16 instance and create the database:
```sql
CREATE DATABASE clinic_crm;
CREATE USER clinic_user WITH ENCRYPTED PASSWORD 'StrongProductionPassword_123';
GRANT ALL PRIVILEGES ON DATABASE clinic_crm TO clinic_user;
```

### Step 2: Apply Schema Migrations with Alembic
Set the database URL and run migrations to the latest revision (`7d231a392105`):
```powershell
$env:DATABASE_URL="postgresql://clinic_user:StrongProductionPassword_123@localhost:5432/clinic_crm"
alembic upgrade head
```

### Step 3: Run Dry-Run Data Migration Validation
Validate that existing Google Sheets & JSON data can be mapped cleanly into PostgreSQL without altering source data:
```powershell
python app/scripts/migrate_sheets_and_json_to_postgres.py --database-url "$env:DATABASE_URL" --dry-run
```
*Review the output summary to ensure 0 validation errors across clinics, doctors, patients, slots, and prescriptions.*

### Step 4: Execute Live Data Migration
```powershell
python app/scripts/migrate_sheets_and_json_to_postgres.py --database-url "$env:DATABASE_URL" --tenant-id default
```

---

## 4. Production Startup Commands

### Development / Staging Mode (Single Worker with Auto-Reload)
```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### High-Throughput Production Mode (4 ASGI Workers)
```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers --forwarded-allow-ips "*" --log-config app/core/logging_config.json
```

### Running as a Windows Service (NSSM)
To keep the application running automatically across server reboots on Windows:
```powershell
# Download NSSM (Non-Sucking Service Manager)
nssm install ClinicBotService "D:\telegram_bot\.venv\Scripts\python.exe" "-m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers --forwarded-allow-ips '*'"
nssm set ClinicBotService AppDirectory "D:\telegram_bot"
nssm start ClinicBotService
```

### Running with Systemd on Linux
`/etc/systemd/system/clinic-bot.service`:
```ini
[Unit]
Description=Clinic AI Assistant & CRM
After=network.target postgresql.service

[Service]
User=clinic
WorkingDirectory=/opt/telegram_bot
ExecStart=/opt/telegram_bot/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers --forwarded-allow-ips "*"
Restart=always
RestartSec=5
EnvironmentFile=/opt/telegram_bot/.env

[Install]
WantedBy=multi-user.target
```

---

## 5. Reverse Proxy & SSL Configuration (Caddy / Nginx)

Meta WhatsApp webhooks require a valid HTTPS certificate.

### Caddy (Automated SSL - Recommended)
`Caddyfile`:
```caddy
api.yourclinic.com {
    reverse_proxy localhost:8000 {
        header_up X-Forwarded-Proto https
        header_up Host {host}
    }
}
```

### Nginx (Ubuntu / CentOS)
```nginx
server {
    server_name api.yourclinic.com;

    client_max_body_size 25M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 60s;
    }

    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/api.yourclinic.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourclinic.com/privkey.pem;
}
```

---

## 6. Health Monitoring & Observability

### Endpoint 1: Basic Liveness
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
```
Response:
```json
{"status": "ok"}
```

### Endpoint 2: Comprehensive Diagnostics
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health?details=true"
```
Response:
```json
{
  "status": "ok",
  "uptime_seconds": 128.4,
  "clinic": "Your Clinic Name",
  "rag_available": true,
  "storage": {
    "free_gb": 314.67,
    "total_gb": 379.28
  }
}
```

---

## 7. Backup, Disaster Recovery & Secret Rotation

### Daily PostgreSQL Backup (PowerShell Script)
Save as `scripts/backup_db.ps1`:
```powershell
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = "D:\backups\clinic_crm_$timestamp.sql"
pg_dump -U clinic_user -h localhost -d clinic_crm -F c -b -v -f $backupFile
# Keep only last 14 days of backups
Get-ChildItem "D:\backups\clinic_crm_*.sql" | Where-Object { $_.CreationTime -lt (Get-Date).AddDays(-14) } | Remove-Item
```

### Restoring from Backup
```powershell
pg_restore -U clinic_user -h localhost -d clinic_crm -v "D:\backups\clinic_crm_20261012_120000.sql"
```

### Secret Rotation Runbook
1. **Rotate `CRM_SECRET_KEY`:**
   - Update `CRM_SECRET_KEY` in `.env`.
   - Existing active sessions in localStorage will be logged out upon next token validation.
2. **Rotate `WHATSAPP_APP_SECRET`:**
   - Generate new App Secret in Meta Dashboard > Basic Settings.
   - Update `WHATSAPP_APP_SECRET` in `.env` and restart service (`nssm restart ClinicBotService`).
3. **Rotate Super Admin Credentials:**
   - Generate a new PBKDF2 hash using `python -c "from app.core.auth import hash_password; print(hash_password('NewStrongPassword123!'))"`.
   - Set `SUPER_ADMIN_PASSWORD_HASH=<generated_hash>` in `.env`.
   - Leave `SUPER_ADMIN_PASSWORD` blank.

