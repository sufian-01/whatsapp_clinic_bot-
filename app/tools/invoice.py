"""Professional PDF invoice generation for confirmed offline appointments."""

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


@dataclass(frozen=True)
class InvoiceData:
    clinic_name: str
    clinic_phone: str
    clinic_email: str
    clinic_address: str
    patient_name: str
    patient_email: str
    patient_phone: str
    doctor_name: str
    specialization: str
    appointment_date: str
    appointment_time: str
    token_no: str
    amount: str
    payment_method: str
    payment_status: str


def generate_invoice(data: InvoiceData, output_dir: Path) -> tuple[str, Path]:
    invoice_number = f"INV-{uuid4().hex[:12].upper()}"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{invoice_number}.pdf"
    styles = getSampleStyleSheet()
    document = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm)
    story = [Paragraph(data.clinic_name, styles["Title"]), Paragraph(data.clinic_address, styles["Normal"]), Paragraph(f"Phone: {data.clinic_phone} | Email: {data.clinic_email}", styles["Normal"]), Spacer(1, 8 * mm), Paragraph(f"Invoice: {invoice_number}", styles["Heading2"])]
    rows = [
        ["Patient", data.patient_name], ["Email", data.patient_email], ["Phone", data.patient_phone],
        ["Doctor", data.doctor_name], ["Specialization", data.specialization],
        ["Appointment", f"{data.appointment_date} {data.appointment_time}"], ["Token", data.token_no],
        ["Amount", data.amount], ["Payment Method", data.payment_method], ["Payment Status", f"{data.payment_status} / Pay at Clinic"],
    ]
    table = Table(rows, colWidths=[42 * mm, 125 * mm])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eaf1f8")), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 7)]))
    story.extend([table, Spacer(1, 8 * mm), Paragraph("Offline payment is pending and must be paid at the clinic.", styles["Normal"])])
    document.build(story)
    return invoice_number, path