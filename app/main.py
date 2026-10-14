"""FastAPI application factory."""

from collections import deque
import logging
from pathlib import Path
import time
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .api.admin import create_admin_router
from .api.knowledge import create_knowledge_router
from .api.webhook import create_webhook_router
from .core.auth import get_current_admin
from .core.config import get_settings, validate_settings
from .core.logging import configure_logging
from .graph.graph import build_graph
from .graph.nodes import GraphNodes
from .llm.gemini import GeminiClient
from .rag.service import RagService
from .services.crm_service import CrmService
from .services.sarvam_service import SarvamService
from .telegram.bot import TelegramBot
from .tools.appointments import AppointmentTools
from .tools.doctors import DoctorDirectory, DoctorTools
from .tools.gmail import GmailTools
from .tools.invoices import InvoiceTools
from .tools.patients import PatientRepository, PatientTools
from .tools.payments import PaymentTools
from .tools.slots import SlotRepository


ROOT_DIR = Path(__file__).resolve().parents[1]


def _build_doctor_directory(settings):
    if not settings.clinic_sheet_id:
        return None
    from sheet_tools import append_row, read_sheet, update_cells

    return DoctorDirectory(
        lambda: read_sheet.invoke({
            "spreadsheet_id": settings.clinic_sheet_id,
            "range_name": settings.clinic_sheet_range,
        }),
        lambda values, range_name: append_row.invoke({
            "spreadsheet_id": settings.clinic_sheet_id,
            "values": values,
            "range_name": range_name,
        }),
        lambda range_name, values: update_cells.invoke({
            "spreadsheet_id": settings.clinic_sheet_id,
            "range_name": range_name,
            "values": values,
        }),
        settings.clinic_sheet_range,
    )


def _build_sheet_repositories(settings):
    if not settings.clinic_sheet_id:
        return None, None
    from sheet_tools import append_row, read_sheet, update_cells

    def read(range_name):
        return read_sheet.invoke({"spreadsheet_id": settings.clinic_sheet_id, "range_name": range_name})

    patients = PatientRepository(
        lambda: read(settings.patient_sheet_range),
        lambda values, range_name: append_row.invoke({"spreadsheet_id": settings.clinic_sheet_id, "values": values, "range_name": range_name}),
        lambda range_name, values: update_cells.invoke({"spreadsheet_id": settings.clinic_sheet_id, "range_name": range_name, "values": values}),
        settings.patient_sheet_range,
    )
    slots = SlotRepository(
        lambda: read(settings.appointment_slot_sheet_range),
        lambda range_name, values: update_cells.invoke({"spreadsheet_id": settings.clinic_sheet_id, "range_name": range_name, "values": values}),
        settings.appointment_slot_sheet_range,
        lambda values, range_name: append_row.invoke({"spreadsheet_id": settings.clinic_sheet_id, "values": values, "range_name": range_name}),
    )
    return patients, slots


def _build_email_sender():
    def send(to, subject, body, attachment_path):
        from gmail_tools import send_email_with_attachment

        return send_email_with_attachment.invoke({"to": to, "subject": subject, "body": body, "attachment_path": attachment_path})

    return send


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    validate_settings(settings)
    rag = RagService(settings.knowledge_dir, settings.vectorstore_dir)
    llm = GeminiClient(settings.gemini_api_key, settings.gemini_model)
    email_sender = _build_email_sender()
    invoice_tools = InvoiceTools()
    gmail_tools = GmailTools(email_sender)

    from .db.session import is_db_configured, get_session_factory, get_engine
    if is_db_configured():
        # Fail-fast check: ensure PostgreSQL is healthy and accessible at startup
        from sqlalchemy import text
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        session_factory = get_session_factory()
        from .repositories.postgres_crm_repositories import (
            PostgresPatientRepository,
            PostgresDoctorDirectory,
            PostgresSlotRepository,
            PostgresPrescriptionService,
            PostgresDoctorAccountService,
            PostgresAuditService,
            PostgresPaymentRepository,
        )
        patient_repo = PostgresPatientRepository(session_factory)
        patient_tools = PatientTools(patient_repo)
        doctor_dir = PostgresDoctorDirectory(session_factory)
        doctor_tools = DoctorTools(doctor_dir)
        slot_repo = PostgresSlotRepository(session_factory)
        slot_tools = AppointmentTools(slot_repo)
        payment_tools = PostgresPaymentRepository(session_factory, upi_id=settings.clinic_upi_id)
        audit_service = PostgresAuditService(session_factory)
        prescriptions = PostgresPrescriptionService(session_factory, audit_service=audit_service)
        doctor_accounts = PostgresDoctorAccountService(
            session_factory,
            doctor_directory=doctor_tools,
            audit_service=audit_service,
            allow_demo_password=settings.allow_demo_password,
        )
    else:
        patients, slots = _build_sheet_repositories(settings)
        doctor_directory = _build_doctor_directory(settings)
        patient_tools = PatientTools(patients) if patients else None
        doctor_tools = DoctorTools(doctor_directory) if doctor_directory else None
        slot_tools = AppointmentTools(slots) if slots else None
        payment_tools = PaymentTools(upi_id=settings.clinic_upi_id)
        audit_service = None
        prescriptions = None
        doctor_accounts = None

    crm_service = CrmService(
        patients_tools=patient_tools,
        doctors_tools=doctor_tools,
        slots_tools=slot_tools,
        payments_tools=payment_tools,
        invoices_tools=invoice_tools,
        gmail_tools=gmail_tools,
        audit_service=audit_service,
        clinic_name=settings.clinic_name,
        clinic_timezone=settings.clinic_timezone,
        support_phone=settings.support_phone,
        clinic_upi_id=settings.clinic_upi_id,
        doctor_accounts=doctor_accounts,
        prescriptions=prescriptions,
        allow_demo_password=settings.allow_demo_password,
    )

    graph = build_graph(GraphNodes(
        settings.clinic_name,
        llm,
        rag,
        doctors=doctor_tools,
        support_phone=settings.support_phone,
        patients=patient_tools,
        slots=slot_tools,
        payments=payment_tools,
        invoices=invoice_tools,
        gmail=gmail_tools,
        clinic_timezone=settings.clinic_timezone,
        crm_service=crm_service,
    ))
    bot = TelegramBot(settings.telegram_bot_token)
    sarvam = SarvamService.from_settings(settings)

    app = FastAPI(title=f"{settings.clinic_name} AI Assistant & CRM")

    perf_logger = logging.getLogger("crm.perf")
    perf_history = deque(maxlen=200)
    app_start_time = time.time()

    @app.middleware("http")
    async def performance_logging_middleware(request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Process-Time"] = f"{duration_ms}ms"
        response.headers["X-Request-ID"] = req_id

        path = request.url.path
        if path.startswith("/api") or path.startswith("/admin"):
            perf_logger.info(
                f"[PERF] id={req_id} method={request.method} path={path} status={response.status_code} duration_ms={duration_ms}"
            )
            perf_history.append({
                "id": req_id,
                "time": time.time(),
                "method": request.method,
                "path": path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            })
        return response

    @app.get("/api/admin/perf-stats", include_in_schema=False)
    async def get_perf_stats(current_admin: dict = Depends(get_current_admin)):
        """Development inspection of recent endpoint latencies."""
        entries = list(perf_history)
        if not entries:
            return {"count": 0, "avg_duration_ms": 0.0, "p95_duration_ms": 0.0, "recent": []}
        avg_dur = round(sum(e["duration_ms"] for e in entries) / len(entries), 2)
        durations = sorted(e["duration_ms"] for e in entries)
        p95_idx = int(len(durations) * 0.95)
        p95_dur = durations[min(p95_idx, len(durations) - 1)]
        return {
            "count": len(entries),
            "avg_duration_ms": avg_dur,
            "p95_duration_ms": p95_dur,
            "recent": entries[-20:],
        }

    # 1. Existing Webhook & Knowledge Routers
    app.include_router(create_webhook_router(settings, graph, bot, sarvam))
    app.include_router(create_knowledge_router(settings.knowledge_dir / "uploads", rag))

    # 1b. Meta WhatsApp Cloud API Channel Router
    from .channels.whatsapp.client import MetaWhatsAppClient
    from .channels.whatsapp.handler import WhatsAppHandler
    from .channels.whatsapp.router import create_whatsapp_router

    whatsapp_client = MetaWhatsAppClient(
        access_token=settings.whatsapp_access_token,
        api_version=settings.whatsapp_api_version,
        phone_number_id=settings.whatsapp_phone_number_id,
        default_country_code=settings.whatsapp_default_country_code,
    )
    whatsapp_repo = None
    if is_db_configured():
        from .repositories.whatsapp_repository import WhatsAppRepository
        whatsapp_repo = WhatsAppRepository(session_factory)

    whatsapp_handler = WhatsAppHandler(
        settings=settings,
        graph=graph,
        client=whatsapp_client,
        repository=whatsapp_repo,
        audit_service=crm_service.audit,
        sarvam=sarvam,
    )
    app.include_router(create_whatsapp_router(settings, whatsapp_handler))

    # 2. CRM Admin Service & API Router
    from .api.doctor import create_doctor_router
    app.include_router(create_admin_router(crm_service, settings))
    app.include_router(create_doctor_router(crm_service, settings))

    # 3. Super Admin & Platform Tenant Management Service & Router
    from .services.tenant_management_service import TenantManagementService
    from .api.super_admin import create_super_admin_router
    from .db.session import is_db_configured, get_session_factory, get_engine
    session_factory = get_session_factory() if is_db_configured() else None
    tenant_mgmt_service = TenantManagementService(audit_service=crm_service.audit, session_factory=session_factory)
    app.include_router(create_super_admin_router(tenant_mgmt_service, settings))

    # 4. Mount CRM & Super Admin Frontend static files
    frontend_dir = ROOT_DIR / "frontend"
    if frontend_dir.exists():
        @app.get("/admin", include_in_schema=False)
        async def admin_redirect():
            return RedirectResponse(url="/admin/")

        app.mount("/admin", StaticFiles(directory=str(frontend_dir), html=True), name="admin")

        super_admin_dir = frontend_dir / "super-admin"
        if super_admin_dir.exists():
            @app.get("/super-admin", include_in_schema=False)
            async def super_admin_redirect():
                return RedirectResponse(url="/super-admin/")

            app.mount("/super-admin", StaticFiles(directory=str(super_admin_dir), html=True), name="super-admin")

    @app.get("/health")
    async def health(details: bool = False) -> dict:
        data = {"status": "ok"}
        if details:
            data.update({
                "uptime_seconds": round(time.time() - app_start_time, 1),
                "clinic": settings.clinic_name,
                "rag_available": rag.is_available(),
            })
            if is_db_configured():
                try:
                    from sqlalchemy import text
                    engine = get_engine()
                    with engine.connect() as conn:
                        conn.execute(text("SELECT 1"))
                    data["database"] = {"status": "connected", "type": "postgresql"}
                except Exception as e:
                    data["database"] = {"status": "error", "error": type(e).__name__}
            try:
                import shutil
                total, used, free = shutil.disk_usage(".")
                data["storage"] = {
                    "free_gb": round(free / (1024**3), 2),
                    "total_gb": round(total / (1024**3), 2),
                }
            except Exception:
                pass
        return data

    return app


app = create_app()
