"""Script to generate the comprehensive Healthcare WhatsApp SaaS Architecture PDF
with embedded visual vector architecture graphs, flowcharts, and state diagrams.
"""

from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon, Group
import math
import os
import sys

# Color Palette
PRIMARY = HexColor("#1E3A8A")       # Deep Blue
SECONDARY = HexColor("#0D9488")     # Teal Accent
DARK_TEXT = HexColor("#1F2937")     # Charcoal Body
MUTED_TEXT = HexColor("#4B5563")    # Medium Gray
LIGHT_BG = HexColor("#F8FAFC")      # Slate Light
ACCENT_BG = HexColor("#F0FDFA")     # Soft Teal Light
BORDER_COLOR = HexColor("#CBD5E1")  # Light Gray Border
HEADER_BG = HexColor("#1E293B")     # Dark Slate Header
ROW_ALT = HexColor("#F1F5F9")       # Table Alternating Row
SUCCESS_COLOR = HexColor("#059669") # Green
WARN_COLOR = HexColor("#D97706")    # Amber
CONTAINER_BG = HexColor("#F8FAFC")  # Container background


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for dynamic total page count and professional running headers/footers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        
        # Suppress headers/footers on cover page (page 1)
        if self._pageNumber > 1:
            # Running Header
            self.setFont("Helvetica-Bold", 7.5)
            self.setFillColor(MUTED_TEXT)
            self.drawString(45, 752, "HEALTHCARE MULTI-TENANT WHATSAPP SAAS")
            self.setFont("Helvetica", 7.5)
            self.drawString(250, 752, "|   System Architecture, Flowcharts & State Graphs")
            self.drawRightString(567, 752, "PRODUCTION BLUEPRINT")
            
            self.setStrokeColor(BORDER_COLOR)
            self.setLineWidth(0.6)
            self.line(45, 745, 567, 745)

            # Running Footer
            self.line(45, 42, 567, 42)
            self.setFont("Helvetica", 7.5)
            self.setFillColor(MUTED_TEXT)
            self.drawString(45, 30, "Confidential • Healthcare AI Architecture Blueprint • D:\\telegram_bot")
            page_text = f"Page {self._pageNumber} of {page_count}"
            self.drawRightString(567, 30, page_text)
            
        self.restoreState()


# =============================================================================
# VECTOR GRAPHICS PRIMITIVES & DIAGRAM BUILDERS
# =============================================================================

def draw_arrow(g: Group, x1: float, y1: float, x2: float, y2: float, color=HexColor("#475569"), stroke_width=1.0, arrow_size=3.5):
    """Draw a vector line with an arrowhead pointing to (x2, y2)."""
    g.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=stroke_width))
    angle = math.atan2(y2 - y1, x2 - x1)
    p1_x = x2 - arrow_size * math.cos(angle - math.pi / 6)
    p1_y = y2 - arrow_size * math.sin(angle - math.pi / 6)
    p2_x = x2 - arrow_size * math.cos(angle + math.pi / 6)
    p2_y = y2 - arrow_size * math.sin(angle + math.pi / 6)
    g.add(Polygon([x2, y2, p1_x, p1_y, p2_x, p2_y], fillColor=color, strokeColor=color))


def draw_box(g: Group, x: float, y: float, w: float, h: float, title: str, subtitle: str = "",
             bg_color=HexColor("#FFFFFF"), border_color=BORDER_COLOR, text_color=HexColor("#0F172A"),
             title_size=7.5, subtitle_size=6.0, radius=3):
    """Draw a clean rounded rectangle box with centered title and optional subtitle."""
    g.add(Rect(x, y, w, h, rx=radius, ry=radius, fillColor=bg_color, strokeColor=border_color, strokeWidth=0.8))
    if subtitle:
        g.add(String(x + w / 2, y + h / 2 + 3, title, textAnchor="middle", fontName="Helvetica-Bold", fontSize=title_size, fillColor=text_color))
        g.add(String(x + w / 2, y + h / 2 - 7, subtitle, textAnchor="middle", fontName="Helvetica", fontSize=subtitle_size, fillColor=HexColor("#64748B")))
    else:
        g.add(String(x + w / 2, y + h / 2 - 2.5, title, textAnchor="middle", fontName="Helvetica-Bold", fontSize=title_size, fillColor=text_color))


def draw_container(g: Group, x: float, y: float, w: float, h: float, title: str,
                   bg_color=HexColor("#F8FAFC"), border_color=HexColor("#CBD5E1")):
    """Draw a grouping container boundary box with a top header label."""
    g.add(Rect(x, y, w, h, rx=5, ry=5, fillColor=bg_color, strokeColor=border_color, strokeWidth=0.75, strokeDashArray=[2, 2]))
    # Header badge
    badge_w = len(title) * 4.8 + 14
    g.add(Rect(x + 8, y + h - 8, badge_w, 14, rx=2, ry=2, fillColor=HexColor("#FFFFFF"), strokeColor=border_color, strokeWidth=0.5))
    g.add(String(x + 8 + badge_w / 2, y + h - 4, title.upper(), textAnchor="middle", fontName="Helvetica-Bold", fontSize=5.5, fillColor=HexColor("#475569")))


def create_system_architecture_diagram() -> Drawing:
    """Create High-Level End-to-End System Architecture Vector Diagram (522 x 275 pt)."""
    d = Drawing(522, 275)
    g = Group()

    # Background card
    g.add(Rect(0, 0, 522, 275, rx=6, ry=6, fillColor=HexColor("#FFFFFF"), strokeColor=BORDER_COLOR, strokeWidth=0.75))

    # Title bar inside card
    g.add(Rect(0, 255, 522, 20, rx=6, ry=6, fillColor=HEADER_BG, strokeColor=None))
    g.add(Rect(0, 255, 522, 10, fillColor=HEADER_BG, strokeColor=None)) # square bottom corners
    g.add(String(12, 261, "END-TO-END SAAS SYSTEM ARCHITECTURE & DATA FLOW", fontName="Helvetica-Bold", fontSize=8, fillColor=HexColor("#FFFFFF")))
    g.add(String(510, 261, "TIER 1 - 8 ARCHITECTURE", textAnchor="end", fontName="Helvetica", fontSize=6.5, fillColor=HexColor("#94A3B8")))

    # 1. Inbound Channels Container (Left Column)
    draw_container(g, 10, 15, 105, 230, "1. Inbound Clients")
    draw_box(g, 16, 175, 93, 38, "WhatsApp Patient", "Meta Cloud API v21.0", bg_color=HexColor("#F0FDF4"), border_color=HexColor("#86EFAC"), text_color=HexColor("#166534"))
    draw_box(g, 16, 115, 93, 38, "Web CRM Users", "Clinic Staff & Doctors", bg_color=HexColor("#EFF6FF"), border_color=HexColor("#93C5FD"), text_color=HexColor("#1E40AF"))
    draw_box(g, 16, 55, 93, 38, "Telegram Bot", "Secondary Channel", bg_color=HexColor("#FDF4FF"), border_color=HexColor("#F0ABFC"), text_color=HexColor("#86198F"))

    # 2. Gateway & Concurrency Container (Middle-Left Column)
    draw_container(g, 125, 15, 120, 230, "2. Gateway & Locks")
    draw_box(g, 131, 185, 108, 30, "FastAPI Webhook Gateway", "Signature HMAC-SHA256", bg_color=HexColor("#FFFFFF"), border_color=HexColor("#CBD5E1"))
    draw_box(g, 131, 140, 108, 30, "Deduplication Filter", "1-Hour TTL RAM + DB Index", bg_color=HexColor("#FFFFFF"), border_color=HexColor("#CBD5E1"))
    draw_box(g, 131, 95, 108, 30, "Tenant Resolver", "phone_number_id -> tenant_id", bg_color=HexColor("#FEF3C7"), border_color=HexColor("#FCD34D"), text_color=HexColor("#92400E"))
    draw_box(g, 131, 35, 108, 45, "PerThreadLockManager", "clinic:{id}:whatsapp:{phone}\nAsync Lock Serialization", bg_color=HexColor("#EFF6FF"), border_color=HexColor("#93C5FD"), text_color=HexColor("#1E3A8A"))

    # 3. LangGraph Brain Container (Center-Right Column)
    draw_container(g, 255, 15, 135, 230, "3. LangGraph State Brain")
    draw_box(g, 261, 185, 123, 30, "Hybrid Intent Router", "0ms Fast-Path + Semantic LLM", bg_color=HexColor("#FEF3C7"), border_color=HexColor("#FCD34D"), text_color=HexColor("#92400E"))
    draw_box(g, 261, 130, 123, 40, "LangGraph StateGraph", "GraphState (Draft, Resume,\nPending Field, Summary)", bg_color=HexColor("#EEF2FF"), border_color=HexColor("#A5B4FC"), text_color=HexColor("#3730A3"))
    draw_box(g, 261, 80, 123, 36, "11 Specialized Nodes", "Doctor, Slot, Cancel, RAG,\nGreeting, Answer Fallback", bg_color=HexColor("#FFFFFF"), border_color=HexColor("#CBD5E1"))
    draw_box(g, 261, 30, 123, 36, "Postgres Checkpointer", "Persistent across restarts\n(checkpoints table)", bg_color=HexColor("#F0FDF4"), border_color=HexColor("#86EFAC"), text_color=HexColor("#166534"))

    # 4. Storage & External Layer (Right Column)
    draw_container(g, 400, 15, 112, 230, "4. DB & External")
    draw_box(g, 406, 175, 100, 38, "PostgreSQL CRM", "Tenants, Patients, Doctors,\nAppointments, Messages", bg_color=HexColor("#F0FDF4"), border_color=HexColor("#86EFAC"), text_color=HexColor("#166534"))
    draw_box(g, 406, 115, 100, 38, "Google Gemini AI", "Multi-Tier LLM Chain\n(2.5 Flash -> Lite -> 1.5)", bg_color=HexColor("#EFF6FF"), border_color=HexColor("#93C5FD"), text_color=HexColor("#1E40AF"))
    draw_box(g, 406, 55, 100, 38, "Meta WhatsApp Outbound", "Interactive Buttons & Lists\nPOST /v21.0/messages", bg_color=HexColor("#FDF4FF"), border_color=HexColor("#F0ABFC"), text_color=HexColor("#86198F"))

    # Connecting Flow Arrows
    # Clients -> Gateway
    draw_arrow(g, 109, 194, 131, 200, color=PRIMARY)
    draw_arrow(g, 109, 134, 131, 195, color=PRIMARY)

    # Within Gateway
    draw_arrow(g, 185, 185, 185, 170, color=MUTED_TEXT)
    draw_arrow(g, 185, 140, 185, 125, color=MUTED_TEXT)
    draw_arrow(g, 185, 95, 185, 80, color=MUTED_TEXT)

    # Gateway -> LangGraph Router
    draw_arrow(g, 239, 57, 261, 195, color=SECONDARY, stroke_width=1.2)

    # Within LangGraph
    draw_arrow(g, 322, 185, 322, 170, color=MUTED_TEXT)
    draw_arrow(g, 322, 130, 322, 116, color=MUTED_TEXT)
    draw_arrow(g, 322, 80, 322, 66, color=MUTED_TEXT)

    # LangGraph -> DB & External
    draw_arrow(g, 384, 194, 406, 194, color=PRIMARY)
    draw_arrow(g, 384, 145, 406, 134, color=PRIMARY)
    draw_arrow(g, 384, 98, 406, 74, color=SECONDARY)

    # Outbound loop back to Patient
    draw_arrow(g, 406, 74, 40, 213, color=HexColor("#166534"), stroke_width=0.75, arrow_size=3)

    d.add(g)
    return d


def create_interruption_flow_diagram() -> Drawing:
    """Create Inbound Lifecycle & Interruption Handling Flowchart Diagram (522 x 250 pt)."""
    d = Drawing(522, 250)
    g = Group()

    # Background card
    g.add(Rect(0, 0, 522, 250, rx=6, ry=6, fillColor=HexColor("#FFFFFF"), strokeColor=BORDER_COLOR, strokeWidth=0.75))

    # Title bar
    g.add(Rect(0, 230, 522, 20, rx=6, ry=6, fillColor=HEADER_BG, strokeColor=None))
    g.add(Rect(0, 230, 522, 10, fillColor=HEADER_BG, strokeColor=None))
    g.add(String(12, 236, "INBOUND MESSAGE LIFECYCLE & INTERRUPTION RESUME ENGINE", fontName="Helvetica-Bold", fontSize=8, fillColor=HexColor("#FFFFFF")))
    g.add(String(510, 236, "DECISION FLOWCHART", textAnchor="end", fontName="Helvetica", fontSize=6.5, fillColor=HexColor("#94A3B8")))

    # Step 1: Patient Message Ingest
    draw_box(g, 10, 170, 85, 40, "1. Patient Message", "'doctor ki fees kitni hai?'\n(Mid-Appointment)", bg_color=HexColor("#F0FDF4"), border_color=HexColor("#86EFAC"), text_color=HexColor("#166534"))

    # Step 2: Ingestion & Locks
    draw_box(g, 115, 170, 95, 40, "2. Ingest & Lock", "Deduplicate wamid\nAcquire Thread Lock", bg_color=HexColor("#EFF6FF"), border_color=HexColor("#93C5FD"), text_color=HexColor("#1E40AF"))

    # Step 3: Checkpoint State Loaded
    draw_box(g, 230, 170, 105, 40, "3. Load Checkpoint", "active_flow = booking\npending_field = date", bg_color=HexColor("#EEF2FF"), border_color=HexColor("#A5B4FC"), text_color=HexColor("#3730A3"))

    # Step 4: Decision Router Box (Diamond / Highlighted Box)
    draw_box(g, 355, 165, 155, 50, "4. Hybrid Intent Classification", "Is Regular Field Input? Side Question?\nOr Explicit Cancellation ('rehne do')?", bg_color=HexColor("#FEF3C7"), border_color=HexColor("#FCD34D"), text_color=HexColor("#92400E"), title_size=8)

    # Connectors for top pipeline
    draw_arrow(g, 95, 190, 115, 190, color=PRIMARY)
    draw_arrow(g, 210, 190, 230, 190, color=PRIMARY)
    draw_arrow(g, 335, 190, 355, 190, color=PRIMARY)

    # 3 Branches Coming Out of Decision (Step 4)

    # Branch A: Side Question Interruption (Middle)
    draw_container(g, 10, 20, 180, 125, "Branch A: Side Question Interruption")
    draw_box(g, 18, 95, 164, 30, "Preserve Draft & Set Resume Context", "resume_context = {'pending_field': 'date'}", bg_color=HexColor("#F0FDFA"), border_color=HexColor("#5EEAD4"), text_color=HexColor("#0F766E"))
    draw_box(g, 18, 55, 164, 30, "Answer Question from Doctor Context", "'Dr. Mehta fee is Rs. 500. Continue booking?'", bg_color=HexColor("#FFFFFF"), border_color=BORDER_COLOR)
    draw_box(g, 18, 25, 164, 22, "Resume Exactly from 'date' Field!", "Zero data lost, no conversation restart", bg_color=HexColor("#ECFDF5"), border_color=HexColor("#A7F3D0"), text_color=HexColor("#065F46"))
    draw_arrow(g, 100, 95, 100, 85, color=MUTED_TEXT)
    draw_arrow(g, 100, 55, 100, 47, color=MUTED_TEXT)

    # Branch B: Explicit Cancellation (Right-Center)
    draw_container(g, 205, 20, 150, 125, "Branch B: Cancel Flow ('rehne do')")
    draw_box(g, 213, 85, 134, 32, "Detect Cancellation Intent", "Clear flow_data & active_flow", bg_color=HexColor("#FEF2F2"), border_color=HexColor("#FECACA"), text_color=HexColor("#991B1B"))
    draw_box(g, 213, 35, 134, 35, "Confirm Cancellation Cleanly", "'Aapka appointment cancel ho gaya.'\nNext message = Fresh Greeting", bg_color=HexColor("#FFFFFF"), border_color=BORDER_COLOR)
    draw_arrow(g, 280, 85, 280, 70, color=MUTED_TEXT)

    # Branch C: Normal Flow Progression (Right)
    draw_container(g, 370, 20, 142, 125, "Branch C: Normal Step Progression")
    draw_box(g, 376, 85, 130, 32, "Advance Booking Field", "Date -> Slot -> Name -> Email", bg_color=HexColor("#F0FDF4"), border_color=HexColor("#86EFAC"), text_color=HexColor("#166534"))
    draw_box(g, 376, 35, 130, 35, "Confirm Booking & Send Invoice", "Atomic DB insert + WhatsApp card", bg_color=HexColor("#FFFFFF"), border_color=BORDER_COLOR)
    draw_arrow(g, 441, 85, 441, 70, color=MUTED_TEXT)

    # Arrows from Step 4 down to 3 Branches
    draw_arrow(g, 375, 165, 140, 145, color=HexColor("#0D9488"), stroke_width=1.2) # To Branch A
    draw_arrow(g, 420, 165, 280, 145, color=HexColor("#DC2626"), stroke_width=1.2) # To Branch B
    draw_arrow(g, 475, 165, 441, 145, color=HexColor("#166534"), stroke_width=1.2) # To Branch C

    d.add(g)
    return d


def create_langgraph_nodes_diagram() -> Drawing:
    """Create LangGraph Conversational State Machine Vector Diagram (522 x 210 pt)."""
    d = Drawing(522, 210)
    g = Group()

    # Background card
    g.add(Rect(0, 0, 522, 210, rx=6, ry=6, fillColor=HexColor("#FFFFFF"), strokeColor=BORDER_COLOR, strokeWidth=0.75))

    # Title bar
    g.add(Rect(0, 190, 522, 20, rx=6, ry=6, fillColor=HEADER_BG, strokeColor=None))
    g.add(Rect(0, 190, 522, 10, fillColor=HEADER_BG, strokeColor=None))
    g.add(String(12, 196, "LANGGRAPH STATE MACHINE NODES & CONDITIONAL ROUTING", fontName="Helvetica-Bold", fontSize=8, fillColor=HexColor("#FFFFFF")))
    g.add(String(510, 196, "STATE TRANSITION GRAPH", textAnchor="end", fontName="Helvetica", fontSize=6.5, fillColor=HexColor("#94A3B8")))

    # START Node
    g.add(Rect(15, 85, 40, 24, rx=12, ry=12, fillColor=PRIMARY, strokeColor=None))
    g.add(String(35, 93, "START", textAnchor="middle", fontName="Helvetica-Bold", fontSize=7, fillColor=HexColor("#FFFFFF")))

    # classify_intent Node
    draw_box(g, 75, 75, 85, 44, "classify_intent", "app/graph/router.py\nHybrid Classifier", bg_color=HexColor("#FEF3C7"), border_color=HexColor("#FCD34D"), text_color=HexColor("#92400E"))
    draw_arrow(g, 55, 97, 75, 97, color=PRIMARY)

    # Nodes Column (Center-Right)
    # Row 1: Doctor & Knowledge
    draw_box(g, 210, 145, 90, 28, "doctor_list_node", "Deterministic 0-Token", bg_color=HexColor("#F8FAFC"), border_color=BORDER_COLOR)
    draw_box(g, 210, 110, 90, 28, "doctor_lookup", "Doctor Bio & Fees", bg_color=HexColor("#F8FAFC"), border_color=BORDER_COLOR)
    draw_box(g, 210, 75, 90, 28, "retrieve (RAG)", "Clinic Knowledge Search", bg_color=HexColor("#F8FAFC"), border_color=BORDER_COLOR)

    # Row 2: Appointment Flow
    draw_box(g, 320, 145, 95, 28, "appointment_start", "Draft Initialization", bg_color=HexColor("#EEF2FF"), border_color=HexColor("#A5B4FC"), text_color=HexColor("#3730A3"))
    draw_box(g, 320, 110, 95, 28, "appointment_progress", "Slots / Phone / Name Guard", bg_color=HexColor("#EEF2FF"), border_color=HexColor("#A5B4FC"), text_color=HexColor("#3730A3"))
    draw_box(g, 320, 75, 95, 28, "draft_cancel", "Clear Active Flow", bg_color=HexColor("#FEF2F2"), border_color=HexColor("#FECACA"), text_color=HexColor("#991B1B"))
    draw_box(g, 320, 40, 95, 28, "reschedule / cancel", "Token Number Flow", bg_color=HexColor("#F8FAFC"), border_color=BORDER_COLOR)

    # Answer Node (Generative LLM)
    draw_box(g, 210, 25, 90, 42, "answer", "Gemini Multi-Model\nResilient Fallback", bg_color=HexColor("#F0FDFA"), border_color=HexColor("#5EEAD4"), text_color=HexColor("#0F766E"))

    # END Node
    g.add(Rect(465, 85, 38, 24, rx=12, ry=12, fillColor=HexColor("#059669"), strokeColor=None))
    g.add(String(484, 93, "END", textAnchor="middle", fontName="Helvetica-Bold", fontSize=7, fillColor=HexColor("#FFFFFF")))

    # Conditional Router Connections to Nodes
    draw_arrow(g, 160, 105, 210, 159, color=MUTED_TEXT)
    draw_arrow(g, 160, 100, 210, 124, color=MUTED_TEXT)
    draw_arrow(g, 160, 95, 210, 89, color=MUTED_TEXT)
    draw_arrow(g, 160, 90, 210, 46, color=MUTED_TEXT)

    draw_arrow(g, 160, 108, 320, 159, color=SECONDARY)
    draw_arrow(g, 160, 102, 320, 124, color=SECONDARY)
    draw_arrow(g, 160, 85, 320, 89, color=HexColor("#DC2626"))
    draw_arrow(g, 160, 80, 320, 54, color=MUTED_TEXT)

    # Converging connections to answer or END
    draw_arrow(g, 300, 124, 280, 67, color=MUTED_TEXT) # doc_lookup -> answer
    draw_arrow(g, 300, 89, 280, 67, color=MUTED_TEXT)  # RAG -> answer

    draw_arrow(g, 300, 159, 465, 97, color=MUTED_TEXT)
    draw_arrow(g, 415, 159, 465, 102, color=MUTED_TEXT)
    draw_arrow(g, 415, 124, 465, 97, color=MUTED_TEXT)
    draw_arrow(g, 415, 89, 465, 92, color=MUTED_TEXT)
    draw_arrow(g, 415, 54, 465, 88, color=MUTED_TEXT)
    draw_arrow(g, 300, 46, 465, 85, color=MUTED_TEXT)

    d.add(g)
    return d


# =============================================================================
# MAIN PDF GENERATION LOGIC
# =============================================================================

def build_pdf(output_path: str = "D:/telegram_bot/HEALTHCARE_SAAS_ARCHITECTURE.pdf"):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=45,
        rightMargin=45,
        topMargin=50,
        bottomMargin=50
    )

    base_styles = getSampleStyleSheet()

    # Custom Typography Styles
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=base_styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=PRIMARY,
        alignment=0,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=base_styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        textColor=SECONDARY,
        spaceAfter=12
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=base_styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=PRIMARY,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=base_styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=SECONDARY,
        spaceBefore=9,
        spaceAfter=4,
        keepWithNext=True
    )

    h3_style = ParagraphStyle(
        "Heading3_Custom",
        parent=base_styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=DARK_TEXT,
        spaceBefore=6,
        spaceAfter=3,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=base_styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11.5,
        textColor=DARK_TEXT,
        spaceAfter=5
    )

    callout_style = ParagraphStyle(
        "Callout_Custom",
        parent=base_styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        leading=11,
        textColor=HexColor("#0F766E"),
    )

    table_cell = ParagraphStyle(
        "TableCell",
        parent=base_styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        leading=9.5,
        textColor=DARK_TEXT
    )

    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=table_cell,
        fontName="Helvetica-Bold",
        textColor=HexColor("#0F172A")
    )

    table_header = ParagraphStyle(
        "TableHeader",
        parent=base_styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=10,
        textColor=HexColor("#FFFFFF")
    )

    story = []

    # =========================================================================
    # COVER / HEADER BLOCK
    # =========================================================================
    story.append(Paragraph("Healthcare Multi-Tenant WhatsApp SaaS", title_style))
    story.append(Paragraph("System Architecture, LangGraph State Engine & Visual Process Flowcharts", subtitle_style))
    
    # Metadata Badge Table
    meta_data = [
        [
            Paragraph("<b>Document Version:</b> 2.1 (Full Visual Architecture Blueprint)", table_cell),
            Paragraph("<b>Stack:</b> FastAPI + LangGraph + PostgreSQL + SQLAlchemy 2.x", table_cell)
        ],
        [
            Paragraph("<b>Channel:</b> Meta WhatsApp Cloud API (v21.0) & Telegram", table_cell),
            Paragraph("<b>AI Engine:</b> Gemini 2.5 Flash / Flash-Lite / 1.5 Flash Fallback", table_cell)
        ],
        [
            Paragraph("<b>Persistence:</b> PostgreSQL Checkpointer + Multi-Tenant RLS", table_cell),
            Paragraph("<b>Test Status:</b> 106/106 Unit Tests Passing (100% Verified)", table_cell)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[260, 262])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # =========================================================================
    # 1. EXECUTIVE OVERVIEW & PROBLEM STATEMENT
    # =========================================================================
    story.append(Paragraph("1. Executive Overview & Problem Statement", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=6))

    story.append(Paragraph(
        "This platform is an enterprise-grade <b>multi-tenant healthcare communication SaaS</b> designed to automate patient appointments, "
        "doctor schedule inquiries, and medical clinic operations over WhatsApp Cloud API and web channels. It allows hundreds of independent clinics "
        "to operate on a single shared codebase and database while enforcing <b>absolute data isolation</b>, deterministic conversation threading, and resilient LLM execution.",
        body_style
    ))

    # Problem Callout Box
    problem_box_data = [
        [
            Paragraph(
                "<b>Core Problem Solved (State Memory & Interruption Handling):</b><br/>"
                "In traditional chatbots, when an appointment booking starts (e.g., asking for patient name or date), any unexpected patient reply "
                "(e.g., <i>'clinic timing kya hai?'</i>, <i>'doctor ki fees kitni hai?'</i>, or <i>'rehne do nahi chahiye'</i>) either crashes the flow, "
                "treats the question as patient details, or restarts the entire process from scratch. This system provides a <b>2-tier hybrid intent router</b> "
                "with an explicit <b>resume context engine</b> that answers side questions without losing the active appointment draft, "
                "handles cancellation immediately, and guards against edge-case name conflicts.",
                callout_style
            )
        ]
    ]
    prob_table = Table(problem_box_data, colWidths=[522])
    prob_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ACCENT_BG),
        ("BOX", (0, 0), (-1, -1), 1, SECONDARY),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(prob_table)
    story.append(Spacer(1, 10))

    # =========================================================================
    # 2. END-TO-END SYSTEM ARCHITECTURE & VISUAL GRAPH
    # =========================================================================
    story.append(Paragraph("2. End-to-End System Architecture (Visual Graph & Layer Breakdown)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=6))

    story.append(Paragraph(
        "The following visual diagram illustrates the complete architectural blueprint across all 8 tiers, "
        "from Inbound WhatsApp Webhook ingestion to PostgreSQL persistence and external AI model fallback:",
        body_style
    ))

    # EMBEDDED ARCHITECTURE GRAPH 1
    story.append(create_system_architecture_diagram())
    story.append(Spacer(1, 8))

    # Architecture Table
    arch_table_data = [
        [
            Paragraph("Layer / Tier", table_header),
            Paragraph("Primary Components & File Paths", table_header),
            Paragraph("Core Function & Security Guarantees", table_header)
        ],
        [
            Paragraph("<b>1. Inbound Ingestion</b>", table_cell_bold),
            Paragraph("Meta WhatsApp Cloud API v21.0<br/>Telegram Bot Poller | Web CRM", table_cell),
            Paragraph("Receives inbound JSON webhooks. Validates HMAC-SHA256 signatures (<code>X-Hub-Signature-256</code>). Rejects unauthorized calls.", table_cell)
        ],
        [
            Paragraph("<b>2. Tenant & Dedup</b>", table_cell_bold),
            Paragraph("<code>app/channels/whatsapp/handler.py</code><br/><code>TenantManagementService</code>", table_cell),
            Paragraph("Resolves <code>phone_number_id</code> &rarr; <code>tenant_id</code> (strict fail-closed). Deduplicates <code>wamid</code> via 1-hour RAM cache + DB index.", table_cell)
        ],
        [
            Paragraph("<b>3. Concurrency Control</b>", table_cell_bold),
            Paragraph("<code>app/core/concurrency.py</code><br/><code>PerThreadLockManager</code>", table_cell),
            Paragraph("Ensures concurrent messages from the same patient are processed sequentially without checkpoint race conditions. Different patients run fully in parallel.", table_cell)
        ],
        [
            Paragraph("<b>4. LangGraph Engine</b>", table_cell_bold),
            Paragraph("<code>app/graph/graph.py</code><br/><code>app/graph/checkpointer.py</code>", table_cell),
            Paragraph("Executes the conversation StateGraph. Persists every turn to PostgreSQL (<code>checkpoints</code> table) keyed deterministically by tenant + phone.", table_cell)
        ],
        [
            Paragraph("<b>5. Hybrid Intent Router</b>", table_cell_bold),
            Paragraph("<code>app/graph/router.py</code><br/>Tier 1: Fast Regex | Tier 2: Gemini LLM", table_cell),
            Paragraph("0ms/0-token routing for buttons, phone/email inputs, and cancellations. Smart LLM semantic classification for Hinglish questions and interruptions.", table_cell)
        ],
        [
            Paragraph("<b>6. Graph Workers</b>", table_cell_bold),
            Paragraph("<code>app/graph/nodes.py</code><br/>(11 Specialized Nodes)", table_cell),
            Paragraph("Handles Greeting, Doctor Lookup, Doctor Listing, Appointment Start/Progress/Cancel, RAG Knowledge, and LLM Resilient Answers.", table_cell)
        ],
        [
            Paragraph("<b>7. Database Repositories</b>", table_cell_bold),
            Paragraph("PostgreSQL via SQLAlchemy 2.0<br/><code>app/repositories/postgres_crm_*.py</code>", table_cell),
            Paragraph("Stores Tenants, Patients, Doctors, Slots, Appointments, Messages, and Audit Logs. Enforces strict tenant scoping on every query.", table_cell)
        ],
        [
            Paragraph("<b>8. External Integrations</b>", table_cell_bold),
            Paragraph("Google Gemini AI (LLM)<br/>Meta Cloud API | Sarvam AI Voice", table_cell),
            Paragraph("Multi-model fallback chain (Gemini 2.5 &rarr; Flash-Lite &rarr; 1.5). WhatsApp interactive button/list dispatch. Speech audio transcription.", table_cell)
        ]
    ]

    arch_table = Table(arch_table_data, colWidths=[105, 155, 262])
    arch_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#FFFFFF"), ROW_ALT]),
    ]))
    story.append(arch_table)
    story.append(Spacer(1, 10))

    # =========================================================================
    # 3. INBOUND LIFECYCLE & INTERRUPTION RESUME ENGINE GRAPH
    # =========================================================================
    story.append(Paragraph("3. Inbound Lifecycle & Interruption Handling (Visual Flowchart)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=6))

    story.append(Paragraph(
        "When an incoming WhatsApp message arrives, the system resolves tenant context, acquires an async per-thread lock, "
        "and evaluates whether the message is a regular flow step, an informational interruption (side question), or an explicit cancellation:",
        body_style
    ))

    # EMBEDDED LIFECYCLE FLOW GRAPH 2
    story.append(create_interruption_flow_diagram())
    story.append(Spacer(1, 8))

    # Lifecycle Step Table
    lifecycle_data = [
        [
            Paragraph("Step", table_header),
            Paragraph("Phase", table_header),
            Paragraph("Action & Architectural Behavior", table_header),
            Paragraph("Failure & Resilience Handling", table_header)
        ],
        [
            Paragraph("01", table_cell_bold),
            Paragraph("Webhook Ingest", table_cell_bold),
            Paragraph("Meta sends HTTP POST to <code>/webhook/whatsapp</code>. Verifies <code>X-Hub-Signature-256</code> HMAC header against <code>WHATSAPP_APP_SECRET</code>.", table_cell),
            Paragraph("If signature mismatch &rarr; HTTP 403 Forbidden. Dropped.", table_cell)
        ],
        [
            Paragraph("02", table_cell_bold),
            Paragraph("Deduplication", table_cell_bold),
            Paragraph("Checks incoming <code>wamid</code> against in-memory TTL dictionary (3600s) and PostgreSQL <code>whatsapp_messages.whatsapp_message_id</code> unique index.", table_cell),
            Paragraph("If duplicate &rarr; ignores silently, returns HTTP 200 (prevents double processing).", table_cell)
        ],
        [
            Paragraph("03", table_cell_bold),
            Paragraph("Tenant Resolution", table_cell_bold),
            Paragraph("Maps <code>phone_number_id</code> to <code>tenant_id</code> via <code>TenantManagementService</code> (cached DB lookup).", table_cell),
            Paragraph("If unmapped &rarr; logs warning, drops request (fail-closed).", table_cell)
        ],
        [
            Paragraph("04", table_cell_bold),
            Paragraph("Thread Lock", table_cell_bold),
            Paragraph("Acquires per-thread async lock for <code>clinic:{tenant_id}:whatsapp:{phone}</code> via <code>PerThreadLockManager</code>.", table_cell),
            Paragraph("Serializes rapid successive taps from the same user safely.", table_cell)
        ],
        [
            Paragraph("05", table_cell_bold),
            Paragraph("State Loading", table_cell_bold),
            Paragraph("Fetches previous checkpoint from PostgreSQL. Loads active flow, appointment draft, pending field, and short-term message history.", table_cell),
            Paragraph("Maintains bounded history (last 10 turns) with rolling summary.", table_cell)
        ],
        [
            Paragraph("06", table_cell_bold),
            Paragraph("Intent Routing", table_cell_bold),
            Paragraph("Executes Tier 1 deterministic checks (buttons, regex, cancel keywords). If ambiguous &rarr; executes Tier 2 Gemini semantic classifier.", table_cell),
            Paragraph("Detects Flow Interruption, Side Question, or Cancellation.", table_cell)
        ],
        [
            Paragraph("07", table_cell_bold),
            Paragraph("Node Execution", table_cell_bold),
            Paragraph("Graph advances: Slot retrieval, Doctor lookup, Draft updates, or RAG search. Doctor resolution guarded to prevent name hijacking.", table_cell),
            Paragraph("Zero-LLM token usage for direct deterministic actions.", table_cell)
        ],
        [
            Paragraph("08", table_cell_bold),
            Paragraph("LLM Generation", table_cell_bold),
            Paragraph("Generates conversational response using system prompt and clinic context.", table_cell),
            Paragraph("If Gemini 2.5 rate-limited (429) &rarr; auto-fallbacks to Flash-Lite.", table_cell)
        ],
        [
            Paragraph("09", table_cell_bold),
            Paragraph("Checkpoint Save", table_cell_bold),
            Paragraph("Saves updated state + <code>resume_context</code> to PostgreSQL checkpointer.", table_cell),
            Paragraph("Ensures crash-proof persistence across restarts.", table_cell)
        ],
        [
            Paragraph("10", table_cell_bold),
            Paragraph("Outbound Send", table_cell_bold),
            Paragraph("Renders response as WhatsApp Interactive Buttons, Interactive Lists, or Markdown Text. Sends via Meta Graph API v21.0.", table_cell),
            Paragraph("If dispatch fails &rarr; logs error, attempts clinic support fallback.", table_cell)
        ]
    ]

    lifecycle_table = Table(lifecycle_data, colWidths=[22, 78, 235, 187])
    lifecycle_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#FFFFFF"), ROW_ALT]),
    ]))
    story.append(lifecycle_table)
    story.append(Spacer(1, 10))

    # =========================================================================
    # 4. LANGGRAPH STATE MACHINE NODES & CONDITIONAL GRAPH
    # =========================================================================
    story.append(Paragraph("4. LangGraph State Machine Architecture (Visual State Graph)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=6))

    story.append(Paragraph(
        "LangGraph compiles a cyclical state machine where the user query enters at <code>START</code>, "
        "is evaluated by <code>classify_intent</code>, and branches along conditional edges to specialized node workers:",
        body_style
    ))

    # EMBEDDED LANGGRAPH STATE MACHINE GRAPH 3
    story.append(create_langgraph_nodes_diagram())
    story.append(Spacer(1, 8))

    # State Fields Table
    state_table_data = [
        [
            Paragraph("Field Name", table_header),
            Paragraph("Type", table_header),
            Paragraph("Role & Significance in Interruption Handling", table_header)
        ],
        [
            Paragraph("<code>tenant_id / clinic_id</code>", table_cell_bold),
            Paragraph("str", table_cell),
            Paragraph("Identifies the active clinic tenant. Ensures total multi-tenant database barrier.", table_cell)
        ],
        [
            Paragraph("<code>patient_phone</code>", table_cell_bold),
            Paragraph("str", table_cell),
            Paragraph("Normalized E.164 phone number of the patient (e.g. <code>916200126662</code>).", table_cell)
        ],
        [
            Paragraph("<code>active_flow</code>", table_cell_bold),
            Paragraph("Optional[str]", table_cell),
            Paragraph("Currently active multi-turn workflow: <code>appointment_booking</code>, <code>reschedule</code>, <code>cancel</code>, or <code>None</code>.", table_cell)
        ],
        [
            Paragraph("<code>flow_data</code>", table_cell_bold),
            Paragraph("Dict[str, Any]", table_cell),
            Paragraph("Holds partially collected booking fields: <code>doctor_id</code>, <code>appointment_date</code>, <code>slot_time</code>, <code>patient_name</code>, etc.", table_cell)
        ],
        [
            Paragraph("<code>pending_field</code>", table_cell_bold),
            Paragraph("Optional[str]", table_cell),
            Paragraph("The exact field the bot is currently waiting for (e.g. <code>appointment_date</code>, <code>slot</code>, <code>name</code>, <code>email</code>).", table_cell)
        ],
        [
            Paragraph("<code>resume_context</code>", table_cell_bold),
            Paragraph("Dict[str, Any]", table_cell),
            Paragraph("Explicit memory of interrupted state: <code>{'flow': 'appointment_booking', 'pending_field': 'date', 'interrupted_at': ts}</code>.", table_cell)
        ],
        [
            Paragraph("<code>conversation_summary</code>", table_cell_bold),
            Paragraph("str", table_cell),
            Paragraph("Compressed rolling summary of older conversation history (preserves context without token blowup).", table_cell)
        ],
        [
            Paragraph("<code>messages</code>", table_cell_bold),
            Paragraph("List[Dict]", table_cell),
            Paragraph("Bounded window of recent messages (last 6-10 turns) providing immediate conversational context.", table_cell)
        ]
    ]

    state_table = Table(state_table_data, colWidths=[130, 75, 317])
    state_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#FFFFFF"), ROW_ALT]),
    ]))
    story.append(state_table)
    story.append(Spacer(1, 10))

    # =========================================================================
    # 5. MULTI-TENANT DATABASE SCHEMA SPECIFICATION
    # =========================================================================
    story.append(Paragraph("5. Multi-Tenant PostgreSQL Schema Specification", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=6))

    db_schema_data = [
        [
            Paragraph("Table Name", table_header),
            Paragraph("Primary & Foreign Keys", table_header),
            Paragraph("Core Columns & Types", table_header),
            Paragraph("Tenant Isolation & Indexing", table_header)
        ],
        [
            Paragraph("<code>tenants</code>", table_cell_bold),
            Paragraph("PK: <code>id</code> (varchar)", table_cell),
            Paragraph("name, phone_number_id, status (ACTIVE/SUSPENDED), settings (JSONB), created_at", table_cell),
            Paragraph("Root tenant table. Unique index on <code>phone_number_id</code> for O(1) webhook resolution.", table_cell)
        ],
        [
            Paragraph("<code>users</code>", table_cell_bold),
            Paragraph("PK: <code>id</code><br/>FK: <code>tenant_id</code>", table_cell),
            Paragraph("username, password_hash, role (SUPER_ADMIN, CLINIC_ADMIN, STAFF), is_active", table_cell),
            Paragraph("Scoped by tenant. SuperAdmin has null tenant_id with global privilege.", table_cell)
        ],
        [
            Paragraph("<code>patients</code>", table_cell_bold),
            Paragraph("PK: <code>id</code><br/>FK: <code>tenant_id</code>", table_cell),
            Paragraph("phone_number (E.164), full_name, email, medical_history, notes", table_cell),
            Paragraph("Composite unique index on <code>(tenant_id, phone_number)</code>. Never shared across clinics.", table_cell)
        ],
        [
            Paragraph("<code>doctors</code>", table_cell_bold),
            Paragraph("PK: <code>id</code><br/>FK: <code>tenant_id</code>", table_cell),
            Paragraph("full_name, specialization, consultation_fee, available_days, is_active", table_cell),
            Paragraph("Scoped by tenant. Indexed on <code>(tenant_id, is_active, specialization)</code>.", table_cell)
        ],
        [
            Paragraph("<code>doctor_slots</code>", table_cell_bold),
            Paragraph("PK: <code>id</code><br/>FK: <code>doctor_id, tenant_id</code>", table_cell),
            Paragraph("slot_date (date), start_time, end_time, status (AVAILABLE/BOOKED/BLOCKED)", table_cell),
            Paragraph("Atomic slot reservation prevents double booking across concurrent users.", table_cell)
        ],
        [
            Paragraph("<code>appointments</code>", table_cell_bold),
            Paragraph("PK: <code>id</code><br/>FK: <code>tenant_id, patient_id, doctor_id</code>", table_cell),
            Paragraph("appointment_date, slot_time, status (CONFIRMED/CANCELLED/RESCHEDULED), token_no, payment_status", table_cell),
            Paragraph("Scoped by tenant. Indexed on <code>(tenant_id, appointment_date, status)</code>.", table_cell)
        ],
        [
            Paragraph("<code>whatsapp_messages</code>", table_cell_bold),
            Paragraph("PK: <code>id</code><br/>FK: <code>tenant_id</code>", table_cell),
            Paragraph("whatsapp_message_id (wamid), phone_number, direction, message_type, body, status", table_cell),
            Paragraph("Unique index on <code>whatsapp_message_id</code> for deduplication.", table_cell)
        ],
        [
            Paragraph("<code>checkpoints</code>", table_cell_bold),
            Paragraph("PK: <code>thread_id, checkpoint_id</code>", table_cell),
            Paragraph("checkpoint (JSONB / blob), metadata (JSONB), parent_checkpoint_id", table_cell),
            Paragraph("LangGraph checkpointer table. Thread ID includes <code>tenant_id</code> for physical partition.", table_cell)
        ],
        [
            Paragraph("<code>audit_logs</code>", table_cell_bold),
            Paragraph("PK: <code>id</code><br/>FK: <code>tenant_id</code>", table_cell),
            Paragraph("user_identifier, action, entity_type, entity_id, ip_address, timestamp, details (JSONB)", table_cell),
            Paragraph("Immutable compliance audit trail for all admin and bot actions.", table_cell)
        ]
    ]

    db_table = Table(db_schema_data, colWidths=[88, 92, 178, 164])
    db_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#FFFFFF"), ROW_ALT]),
    ]))
    story.append(db_table)
    story.append(Spacer(1, 10))

    # =========================================================================
    # 6. RELIABILITY, RESILIENCE & CODEBASE AUDIT MATRIX
    # =========================================================================
    story.append(Paragraph("6. Reliability, Failure Recovery & Codebase Verification Matrix", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=6))

    audit_data = [
        [
            Paragraph("Architecture Module", table_header),
            Paragraph("Primary Source Code File", table_header),
            Paragraph("Status", table_header),
            Paragraph("Verified Test Coverage", table_header)
        ],
        [
            Paragraph("WhatsApp Webhook & Dispatch", table_cell_bold),
            Paragraph("<code>app/channels/whatsapp/handler.py</code>", table_cell),
            Paragraph("<font color='#059669'><b>PRODUCTION READY</b></font>", table_cell),
            Paragraph("Signature check, dedup, outbound interactive buttons & lists verified.", table_cell)
        ],
        [
            Paragraph("LangGraph State Machine", table_cell_bold),
            Paragraph("<code>app/graph/graph.py</code>", table_cell),
            Paragraph("<font color='#059669'><b>PRODUCTION READY</b></font>", table_cell),
            Paragraph("11 nodes wired, conditional intent routing, end-to-end flow verified.", table_cell)
        ],
        [
            Paragraph("Hybrid Intent Router", table_cell_bold),
            Paragraph("<code>app/graph/router.py</code>", table_cell),
            Paragraph("<font color='#059669'><b>PRODUCTION READY</b></font>", table_cell),
            Paragraph("Fast regex + semantic LLM classifier with interruption preservation verified.", table_cell)
        ],
        [
            Paragraph("Interruption & Resume Nodes", table_cell_bold),
            Paragraph("<code>app/graph/nodes.py</code>", table_cell),
            Paragraph("<font color='#059669'><b>PRODUCTION READY</b></font>", table_cell),
            Paragraph("Side questions, cancellations, and doctor-matching name guards verified.", table_cell)
        ],
        [
            Paragraph("Concurrency & Thread Locks", table_cell_bold),
            Paragraph("<code>app/core/concurrency.py</code>", table_cell),
            Paragraph("<font color='#059669'><b>PRODUCTION READY</b></font>", table_cell),
            Paragraph("Thread-safe lock manager with event-loop tracking verified.", table_cell)
        ],
        [
            Paragraph("PostgreSQL Persistence & DB", table_cell_bold),
            Paragraph("<code>app/db/session.py</code><br/><code>app/repositories/</code>", table_cell),
            Paragraph("<font color='#059669'><b>PRODUCTION READY</b></font>", table_cell),
            Paragraph("Multi-tenant CRM schema, Alembic migrations, PostgreSQL checkpointer verified.", table_cell)
        ],
        [
            Paragraph("Automated Test Suite", table_cell_bold),
            Paragraph("<code>tests/test_interruption_*.py</code><br/><code>tests/test_*.py</code>", table_cell),
            Paragraph("<font color='#059669'><b>106/106 PASSING</b></font>", table_cell),
            Paragraph("100% of memory, interruption, edge-case, and channel tests green.", table_cell)
        ]
    ]

    audit_table = Table(audit_data, colWidths=[120, 150, 95, 157])
    audit_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#FFFFFF"), ROW_ALT]),
    ]))
    story.append(audit_table)
    story.append(Spacer(1, 10))

    # =========================================================================
    # 7. USER FEEDBACK & ARCHITECTURAL ADJUSTMENT NOTES
    # =========================================================================
    story.append(Paragraph("7. Feedback & Planned Architecture Changes (Review Section)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=6))

    story.append(Paragraph(
        "Please use this section as a reference to specify any changes, custom business rules, "
        "or feature modifications you would like to introduce. Once reviewed, provide your instructions and they will be incorporated systematically.",
        body_style
    ))

    feedback_box_data = [
        [
            Paragraph("<b>Architecture Review Notes / Proposed Modifications:</b>", table_cell_bold)
        ],
        [
            Paragraph(
                "• <b>Interruption Handling:</b> Does the current flow (answering questions & resuming pending fields) match your clinic workflow?<br/>"
                "• <b>Doctor Selection & Slot Discovery:</b> Are the button menus and date/time selection structures aligned with your staff preferences?<br/>"
                "• <b>Multi-Clinic Tenants:</b> Do you require additional tenant-level feature flags (e.g. online payment mandatory vs clinic pay)?<br/>"
                "• <b>Notification & Alerts:</b> Would you like SMS / Email / WhatsApp reminders for confirmed appointments?<br/>"
                "• <i>(Write your feedback and share in the chat — no code will be modified until you confirm your changes)</i>",
                body_style
            )
        ]
    ]
    fb_table = Table(feedback_box_data, colWidths=[522])
    fb_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(fb_table)

    # Build document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Architecture PDF generated successfully at: {output_path}")
    print(f"File size: {os.path.getsize(output_path)} bytes")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "D:/telegram_bot/HEALTHCARE_SAAS_ARCHITECTURE.pdf"
    build_pdf(out)
