"""FastAPI application factory."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .api.admin import create_admin_router
from .api.knowledge import create_knowledge_router
from .api.webhook import create_webhook_router
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
    patients, slots = _build_sheet_repositories(settings)
    doctor_directory = _build_doctor_directory(settings)
    email_sender = _build_email_sender()

    patient_tools = PatientTools(patients) if patients else None
    doctor_tools = DoctorTools(doctor_directory) if doctor_directory else None
    slot_tools = AppointmentTools(slots) if slots else None
    payment_tools = PaymentTools()
    invoice_tools = InvoiceTools()
    gmail_tools = GmailTools(email_sender)

    crm_service = CrmService(
        patients_tools=patient_tools,
        doctors_tools=doctor_tools,
        slots_tools=slot_tools,
        payments_tools=payment_tools,
        invoices_tools=invoice_tools,
        clinic_name=settings.clinic_name,
        clinic_timezone=settings.clinic_timezone,
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

    # 1. Existing Webhook & Knowledge Routers
    app.include_router(create_webhook_router(settings, graph, bot, sarvam))
    app.include_router(create_knowledge_router(settings.knowledge_dir / "uploads", rag))

    # 2. CRM Admin Service & API Router
    app.include_router(create_admin_router(crm_service, settings))

    # 3. Mount CRM Frontend static files
    frontend_dir = ROOT_DIR / "frontend"
    if frontend_dir.exists():
        @app.get("/admin", include_in_schema=False)
        async def admin_redirect():
            return RedirectResponse(url="/admin/")

        app.mount("/admin", StaticFiles(directory=str(frontend_dir), html=True), name="admin")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
