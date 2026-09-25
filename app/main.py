"""FastAPI application factory."""

from fastapi import FastAPI

from .api.knowledge import create_knowledge_router
from .api.webhook import create_webhook_router
from .core.config import get_settings, validate_settings
from .core.logging import configure_logging
from .graph.graph import build_graph
from .graph.nodes import GraphNodes
from .llm.gemini import GeminiClient
from .rag.service import RagService
from .telegram.bot import TelegramBot
from .tools.doctors import DoctorDirectory
from .tools.doctors import DoctorTools
from .tools.invoices import InvoiceTools
from .tools.gmail import GmailTools
from .tools.patients import PatientRepository, PatientTools
from .tools.payments import PaymentTools
from .tools.slots import SlotRepository
from .tools.appointments import AppointmentTools


def _build_doctor_directory(settings):
    if not settings.clinic_sheet_id:
        return None
    from sheet_tools import read_sheet

    return DoctorDirectory(
        lambda: read_sheet.invoke({
            "spreadsheet_id": settings.clinic_sheet_id,
            "range_name": settings.clinic_sheet_range,
        })
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
    graph = build_graph(GraphNodes(
        settings.clinic_name,
        llm,
        rag,
        doctors=DoctorTools(doctor_directory) if doctor_directory else None,
        support_phone=settings.support_phone,
        patients=PatientTools(patients) if patients else None,
        slots=AppointmentTools(slots) if slots else None,
        payments=PaymentTools(),
        invoices=InvoiceTools(),
        gmail=GmailTools(email_sender),
    ))
    bot = TelegramBot(settings.telegram_bot_token)
    app = FastAPI(title=f"{settings.clinic_name} AI Assistant")
    app.include_router(create_webhook_router(settings, graph, bot))
    app.include_router(create_knowledge_router(settings.knowledge_dir / "uploads", rag))

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()