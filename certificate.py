from pathlib import Path
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas

BASE_DIR = Path(__file__).resolve().parent.parent
CERTIFICATE_DIR = BASE_DIR / "storage" / "certificates"
CERTIFICATE_DIR.mkdir(parents=True, exist_ok=True)


def generate_certificate(*, recipient_name: str, event_name: str, issued_date: str, output_path: Path) -> None:
    """Render one certificate using the application's single predefined template."""
    page_width, page_height = landscape(A4)
    c = canvas.Canvas(str(output_path), pagesize=(page_width, page_height))

    c.setStrokeColor(colors.HexColor("#243B53"))
    c.setLineWidth(5)
    c.rect(35, 35, page_width - 70, page_height - 70)

    c.setFillColor(colors.HexColor("#243B53"))
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(page_width / 2, page_height - 105, "CERTIFICATE OF PARTICIPATION")

    c.setFillColor(colors.HexColor("#486581"))
    c.setFont("Helvetica", 14)
    c.drawCentredString(page_width / 2, page_height - 145, "This certificate is proudly presented to")

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(page_width / 2, page_height / 2 + 35, recipient_name)

    c.setFont("Helvetica", 15)
    c.drawCentredString(page_width / 2, page_height / 2 - 5, f"for successful participation in {event_name}")
    c.drawCentredString(page_width / 2, page_height / 2 - 32, f"Issued on {issued_date}")

    c.setStrokeColor(colors.HexColor("#9FB3C8"))
    c.line(page_width / 2 - 75, 105, page_width / 2 + 75, 105)
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#486581"))
    c.drawCentredString(page_width / 2, 88, "Authorized by the Organizing Committee")

    c.save()
