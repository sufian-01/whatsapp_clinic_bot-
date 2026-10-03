"""Professional medical prescription PDF generation."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
from typing import Optional
from uuid import uuid4

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


@dataclass(frozen=True)
class PrescriptionPDFData:
    clinic_name: str
    clinic_phone: str
    clinic_email: str
    clinic_address: str
    doctor_name: str
    doctor_specialization: str
    patient_id: str
    patient_name: str
    patient_phone: str
    patient_age: str
    patient_gender: str
    appointment_id: str
    prescription_id: str
    date: str
    diagnosis: str
    symptoms: str = ""
    chief_complaints: str = ""
    vitals: Optional[dict] = None
    clinical_notes: str = ""
    medicines: Optional[list[dict]] = None
    tests_advised: str = ""
    advice: str = ""
    follow_up_date: str = ""
    doctor_qualification: str = ""
    doctor_reg_no: str = ""
    version: int = 1


def _clean_html_for_pdf(text: str) -> str:
    """Strip unsupported HTML tags while preserving basic formatting for ReportLab."""
    if not text:
        return ""
    # Convert <br>, <p>, <div> to newlines or line breaks
    text = re.sub(r"<(?:br|p|div|/p|/div)[^>]*>", "<br/>", text, flags=re.IGNORECASE)
    # Remove all tags except b, i, u, font
    text = re.sub(r"<(?!(?:/?[biu]|/?font|\/?br))[^>]+>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(<br/>)+", "<br/>", text)
    return text.strip()


def generate_prescription_pdf(data: PrescriptionPDFData, output_dir: Path) -> tuple[str, Path]:
    """Generate a clean, high-resolution A4 medical prescription document."""
    output_dir.mkdir(parents=True, exist_ok=True)
    clean_id = data.prescription_id.replace("/", "_").replace("\\", "_")
    pdf_path = output_dir / f"{clean_id}_v{data.version}.pdf"

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )

    styles = getSampleStyleSheet()

    clinic_title_style = ParagraphStyle(
        "ClinicTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1e3a8a"),
    )
    clinic_sub_style = ParagraphStyle(
        "ClinicSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#475569"),
    )
    section_heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#1e3a8a"),
    )
    label_style = ParagraphStyle(
        "LabelStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#334155"),
    )
    val_style = ParagraphStyle(
        "ValStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
    )
    table_hdr_style = ParagraphStyle(
        "TableHdr",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
    )
    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0f172a"),
    )

    story = []

    # 1. Clinic Header
    story.append(Paragraph(data.clinic_name.upper(), clinic_title_style))
    contact_parts = []
    if data.clinic_address:
        contact_parts.append(data.clinic_address)
    if data.clinic_phone:
        contact_parts.append(f"Phone: {data.clinic_phone}")
    if data.clinic_email:
        contact_parts.append(f"Email: {data.clinic_email}")
    sub_text = " | ".join(contact_parts) if contact_parts else "Medical Consultation & Healthcare Services"
    story.append(Paragraph(sub_text, clinic_sub_style))
    story.append(Spacer(1, 2.5 * mm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1e3a8a"), spaceAfter=3.5 * mm))

    # 2. Doctor & Rx Meta Table
    doc_display = f"Dr. {data.doctor_name}" if not data.doctor_name.startswith("Dr.") else data.doctor_name
    credentials = [data.doctor_specialization]
    if data.doctor_qualification:
        credentials.append(data.doctor_qualification)
    if data.doctor_reg_no:
        credentials.append(f"Reg: {data.doctor_reg_no}")
    cred_str = " | ".join(credentials)

    meta_data = [
        [
            Paragraph(f"<b>CONSULTING PHYSICIAN:</b><br/>{doc_display}<br/><font color='#64748b' size='8'>{cred_str}</font>", val_style),
            Paragraph(f"<b>PRESCRIPTION NO:</b> {data.prescription_id}<br/><b>DATE:</b> {data.date}<br/><b>TOKEN:</b> {data.appointment_id} (Ver {data.version})", val_style),
        ]
    ]
    meta_table = Table(meta_data, colWidths=[94 * mm, 84 * mm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 3.5 * mm))

    # 3. Patient Details Box
    pt_meta = [
        [
            Paragraph("<b>Patient Name:</b>", label_style),
            Paragraph(data.patient_name, val_style),
            Paragraph("<b>Patient ID:</b>", label_style),
            Paragraph(data.patient_id, val_style),
        ],
        [
            Paragraph("<b>Age / Gender:</b>", label_style),
            Paragraph(f"{data.patient_age or 'N/A'} / {data.patient_gender or 'N/A'}", val_style),
            Paragraph("<b>Contact:</b>", label_style),
            Paragraph(data.patient_phone or "N/A", val_style),
        ]
    ]
    pt_table = Table(pt_meta, colWidths=[28 * mm, 62 * mm, 28 * mm, 60 * mm])
    pt_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("PADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(pt_table)
    story.append(Spacer(1, 3.5 * mm))

    # 4. Vitals Strip (if provided)
    if data.vitals and isinstance(data.vitals, dict):
        v_items = []
        if data.vitals.get("bp"):
            v_items.append(f"<b>BP:</b> {data.vitals['bp']} mmHg")
        if data.vitals.get("pulse"):
            v_items.append(f"<b>Pulse:</b> {data.vitals['pulse']} bpm")
        if data.vitals.get("temp"):
            v_items.append(f"<b>Temp:</b> {data.vitals['temp']} °F")
        if data.vitals.get("weight"):
            v_items.append(f"<b>Weight:</b> {data.vitals['weight']} kg")
        if data.vitals.get("spo2"):
            v_items.append(f"<b>SpO2:</b> {data.vitals['spo2']}%")

        if v_items:
            v_text = "   &bull;   ".join(v_items)
            v_table = Table([[Paragraph(f"<b>PATIENT VITALS:</b>   {v_text}", val_style)]], colWidths=[178 * mm])
            v_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#bfdbfe")),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(v_table)
            story.append(Spacer(1, 3.5 * mm))

    # 5. Clinical Assessment
    story.append(Paragraph("CLINICAL ASSESSMENT", section_heading_style))
    diag_rows = []
    if data.chief_complaints:
        cleaned_complaints = _clean_html_for_pdf(data.chief_complaints)
        diag_rows.append([Paragraph("<b>Chief Complaints:</b>", label_style), Paragraph(cleaned_complaints, val_style)])
    if data.diagnosis:
        diag_rows.append([Paragraph("<b>Primary Diagnosis:</b>", label_style), Paragraph(data.diagnosis, val_style)])
    if data.symptoms:
        diag_rows.append([Paragraph("<b>Symptoms / Observations:</b>", label_style), Paragraph(data.symptoms, val_style)])
    if data.clinical_notes:
        cleaned_notes = _clean_html_for_pdf(data.clinical_notes)
        diag_rows.append([Paragraph("<b>Clinical Notes:</b>", label_style), Paragraph(cleaned_notes, val_style)])

    if not diag_rows:
        diag_rows.append([Paragraph("<b>Evaluation:</b>", label_style), Paragraph("Clinical Evaluation Completed", val_style)])

    diag_table = Table(diag_rows, colWidths=[36 * mm, 142 * mm])
    diag_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 2.5),
    ]))
    story.append(diag_table)
    story.append(Spacer(1, 3.5 * mm))

    # 6. Rx Medicines Table
    story.append(Paragraph("Rx / MEDICATIONS", section_heading_style))
    story.append(Spacer(1, 1.5 * mm))

    med_headers = [
        Paragraph("#", table_hdr_style),
        Paragraph("Medicine & Strength", table_hdr_style),
        Paragraph("Dosage", table_hdr_style),
        Paragraph("Frequency", table_hdr_style),
        Paragraph("Duration", table_hdr_style),
        Paragraph("Instructions", table_hdr_style),
    ]
    med_rows = [med_headers]

    med_list = data.medicines or []
    for idx, m in enumerate(med_list, start=1):
        name_str = m.get("name", "")
        if m.get("strength"):
            name_str += f" ({m.get('strength')})"

        med_rows.append([
            Paragraph(str(idx), table_cell_style),
            Paragraph(name_str, table_cell_style),
            Paragraph(m.get("dosage", ""), table_cell_style),
            Paragraph(m.get("frequency", ""), table_cell_style),
            Paragraph(m.get("duration", ""), table_cell_style),
            Paragraph(m.get("instructions", "—"), table_cell_style),
        ])

    if len(med_rows) == 1:
        med_rows.append([Paragraph("1", table_cell_style), Paragraph("No medications prescribed", table_cell_style), Paragraph("—", table_cell_style), Paragraph("—", table_cell_style), Paragraph("—", table_cell_style), Paragraph("—", table_cell_style)])

    med_table = Table(med_rows, colWidths=[8 * mm, 48 * mm, 24 * mm, 28 * mm, 24 * mm, 46 * mm])
    med_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ("ALIGN", (0, 0), (-1, 0), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(med_table)
    story.append(Spacer(1, 3.5 * mm))

    # 7. Tests & Advice
    adv_rows = []
    if data.tests_advised:
        adv_rows.append([Paragraph("<b>Tests Advised:</b>", label_style), Paragraph(data.tests_advised, val_style)])
    if data.advice:
        adv_rows.append([Paragraph("<b>General Advice:</b>", label_style), Paragraph(data.advice, val_style)])
    if data.follow_up_date:
        adv_rows.append([Paragraph("<b>Follow-Up Date:</b>", label_style), Paragraph(f"<b>{data.follow_up_date}</b>", val_style)])

    if adv_rows:
        adv_table = Table(adv_rows, colWidths=[36 * mm, 142 * mm])
        adv_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 2.5),
        ]))
        story.append(adv_table)
        story.append(Spacer(1, 5 * mm))

    # 8. Signature Footer
    story.append(Spacer(1, 6 * mm))
    sig_text = f"_____________________________<br/><b>{doc_display}</b>"
    if cred_str:
        sig_text += f"<br/><font size='7.5' color='#64748b'>{cred_str}</font>"

    sig_data = [
        [
            Paragraph("<font color='#64748b' size='7.5'>This digital prescription is electronically generated and authenticated under clinical practice standards.</font>", val_style),
            Paragraph(sig_text, val_style),
        ]
    ]
    sig_table = Table(sig_data, colWidths=[108 * mm, 70 * mm])
    sig_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
    ]))
    story.append(sig_table)

    doc.build(story)
    return clean_id, pdf_path

