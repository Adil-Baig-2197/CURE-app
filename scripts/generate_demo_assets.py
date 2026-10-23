"""Create clearly fictional files for local CURE upload demonstrations."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "output" / "pdf"
IMAGE_DIR = ROOT / "demo-assets" / "images"
SYNTHETIC_RED = (170, 35, 45)
NAVY = (24, 51, 83)
TEAL = (19, 117, 123)


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    windows_font = Path("C:/Windows/Fonts/arial.ttf")
    if windows_font.is_file():
        return ImageFont.truetype(str(windows_font), size)
    return ImageFont.load_default(size=size)


def draw_image_report(path: Path, title: str, rows: list[tuple[str, str]], subtitle: str) -> None:
    width, height = 1600, 2000
    image = Image.new("RGB", (width, height), "#f7fafc")
    draw = ImageDraw.Draw(image)
    margin = 120
    draw.rounded_rectangle((margin, 90, width - margin, 205), radius=28, fill="#aa232d")
    draw.text((margin + 35, 120), "SYNTHETIC DEMO - NOT A REAL PATIENT", font=load_font(44), fill="white")
    draw.text((margin, 285), title, font=load_font(64), fill="#183353")
    draw.text((margin, 380), subtitle, font=load_font(34), fill="#46566b")

    y = 510
    draw.rounded_rectangle((margin, y, width - margin, y + 175), radius=22, fill="#e8f3f5")
    draw.text((margin + 35, y + 35), "DEMO RECORD", font=load_font(32), fill="#13757b")
    draw.text((margin + 35, y + 92), "Sample ID: DEMO-001    Date: 2026-10-01", font=load_font(34), fill="#183353")

    y += 250
    for label, value in rows:
        draw.rounded_rectangle((margin, y, width - margin, y + 175), radius=18, fill="white", outline="#ccd6e0", width=3)
        draw.text((margin + 35, y + 25), label, font=load_font(34), fill="#46566b")
        draw.text((margin + 35, y + 85), value, font=load_font(44), fill="#183353")
        y += 205

    footer_y = height - 315
    draw.rounded_rectangle((margin, footer_y, width - margin, height - 105), radius=24, fill="#fff2df")
    draw.text((margin + 35, footer_y + 30), "FOR SOFTWARE TESTING ONLY", font=load_font(38), fill="#8a4b08")
    draw.text((margin + 35, footer_y + 95), "All names, dates, and values are fictional.", font=load_font(34), fill="#6f4a21")
    draw.text((margin + 35, footer_y + 145), "Not medical advice. Do not use for care decisions.", font=load_font(34), fill="#6f4a21")
    image.save(path, quality=92)


def make_pdf(path: Path) -> None:
    doc = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.72 * inch,
        bottomMargin=0.62 * inch,
        title="CURE Synthetic Demo Lab Summary",
        author="CURE Demo Assets",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Banner", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=colors.white))
    styles.add(ParagraphStyle(name="TitleCure", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=23, leading=28, textColor=colors.HexColor("#183353"), spaceAfter=7))
    styles.add(ParagraphStyle(name="Subtle", parent=styles["BodyText"], fontSize=10, leading=14, textColor=colors.HexColor("#46566b")))
    styles.add(ParagraphStyle(name="Caution", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=9, leading=13, textColor=colors.HexColor("#6f4a21")))
    story = []
    banner = Table([[Paragraph("SYNTHETIC DEMO - NOT A REAL PATIENT - NOT FOR CLINICAL USE", styles["Banner"])]], colWidths=[7.15 * inch])
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#aa232d")),
        ("BOX", (0, 0), (-1, -1), 0, colors.HexColor("#aa232d")),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.extend([banner, Spacer(1, 22), Paragraph("Sample Laboratory Summary", styles["TitleCure"]), Paragraph("Fictional sample file for testing CURE report upload, text extraction, and patient verification.", styles["Subtle"]), Spacer(1, 18)])

    patient = Table([
        ["SAMPLE ID", "DATE", "STATUS"],
        ["DEMO-001", "2026-10-01", "Synthetic example"],
    ], colWidths=[2.1 * inch, 2.1 * inch, 2.95 * inch])
    patient.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f3f5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#13757b")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#ccd6e0")),
        ("PADDING", (0, 0), (-1, -1), 9),
    ]))
    story.extend([patient, Spacer(1, 20)])
    story.append(Paragraph("Example values", styles["Heading2"]))
    values = [
        ["Test name", "Fictional value", "Units"],
        ["Hemoglobin", "13.8", "g/dL"],
        ["White blood cells", "6.2", "10^9/L"],
        ["Platelets", "250", "10^9/L"],
        ["Sodium", "139", "mmol/L"],
    ]
    table = Table(values, colWidths=[3.1 * inch, 2 * inch, 2.05 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#183353")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f6f9")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#ccd6e0")),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("PADDING", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 1), (-1, -1), "LEFT"),
    ]))
    story.extend([table, Spacer(1, 22)])

    note = Table([[Paragraph("For software testing only. All names, dates, and values are invented. This file is not a real clinical record, medical advice, or a basis for care decisions. Extracted fields in CURE must be treated as unverified until reviewed by the user.", styles["Caution"])]], colWidths=[7.15 * inch])
    note.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff2df")),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#e7c28f")),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(note)

    def page_footer(canvas, _doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#ccd6e0"))
        canvas.line(0.65 * inch, 0.48 * inch, 7.85 * inch, 0.48 * inch)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#65758b"))
        canvas.drawString(0.65 * inch, 0.3 * inch, "CURE local demo asset | fictional data | not for clinical use")
        canvas.restoreState()

    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)


def main() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    make_pdf(PDF_DIR / "cure_synthetic_demo_lab_report.pdf")
    draw_image_report(
        IMAGE_DIR / "cure_synthetic_demo_lab_report.png",
        "Sample Laboratory Summary",
        [("Hemoglobin", "13.8 g/dL - fictional"), ("White blood cells", "6.2 x 10^9/L - fictional"), ("Platelets", "250 x 10^9/L - fictional")],
        "Example lab values for report-upload and OCR testing",
    )
    draw_image_report(
        IMAGE_DIR / "cure_synthetic_demo_visit_note.jpg",
        "Sample Visit Note",
        [("Example symptom", "Mild headache - invented"), ("Example duration", "One day - invented"), ("Purpose", "Upload and extraction testing only")],
        "A fictional note with no real person or clinical findings",
    )
    print(f"PDF: {PDF_DIR / 'cure_synthetic_demo_lab_report.pdf'}")
    print(f"Image: {IMAGE_DIR / 'cure_synthetic_demo_lab_report.png'}")
    print(f"Image: {IMAGE_DIR / 'cure_synthetic_demo_visit_note.jpg'}")


if __name__ == "__main__":
    main()
