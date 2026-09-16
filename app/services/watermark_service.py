"""Watermark service – injects dynamic watermarks into document streams.

All operations are performed IN MEMORY. Plaintext never touches disk.

Supports:
  - PDF: reportlab overlay merged via pypdf
  - Images (PNG/JPG/TIFF): Pillow text overlay → converted to single-page PDF
"""
import io
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _build_watermark_pdf(text_lines: list[str], page_width: float, page_height: float) -> bytes:
    """Create a single-page transparent PDF with diagonal watermark text using reportlab."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import Color

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(page_width, page_height))

    # Semi-transparent grey
    wm_color = Color(0.5, 0.5, 0.5, alpha=0.35)
    c.setFillColor(wm_color)
    c.setFont("Helvetica-Bold", 14)

    # Diagonal (45°) repeating watermark across the page
    import math
    c.saveState()
    # Rotate around page center
    cx, cy = page_width / 2, page_height / 2
    c.translate(cx, cy)
    c.rotate(45)

    line_height = 22
    y_start = -page_height
    y_end = page_height
    x_start = -page_width
    x_end = page_width

    step_y = 90
    step_x = 280

    y = y_start
    while y < y_end:
        x = x_start
        while x < x_end:
            for i, line in enumerate(text_lines):
                c.drawString(x, y + i * line_height, line)
            x += step_x
        y += step_y

    c.restoreState()
    c.save()
    buf.seek(0)
    return buf.read()


def _merge_watermark_on_pdf(original_pdf_bytes: bytes, watermark_pdf_bytes: bytes) -> bytes:
    """Merge watermark PDF overlay onto each page of the original PDF."""
    from pypdf import PdfReader, PdfWriter

    original_reader = PdfReader(io.BytesIO(original_pdf_bytes))
    watermark_reader = PdfReader(io.BytesIO(watermark_pdf_bytes))
    watermark_page = watermark_reader.pages[0]

    writer = PdfWriter()
    for page in original_reader.pages:
        page.merge_page(watermark_page)
        writer.add_page(page)

    out_buf = io.BytesIO()
    writer.write(out_buf)
    out_buf.seek(0)
    return out_buf.read()


def _image_to_watermarked_pdf(image_bytes: bytes, text_lines: list[str]) -> bytes:
    """Convert an image to a PDF and apply watermark overlay."""
    from PIL import Image, ImageDraw, ImageFont
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.utils import ImageReader

    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    width, height = img.size

    # Draw watermark text on image using Pillow
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        from PIL import ImageFont
        font = ImageFont.truetype("arial.ttf", size=max(20, width // 40))
    except Exception:
        font = ImageFont.load_default()

    import math
    watermark_img = Image.new("RGBA", img.size, (255, 255, 255, 0))
    wm_draw = ImageDraw.Draw(watermark_img)

    text = " | ".join(text_lines)
    step = max(80, height // 8)
    for y_pos in range(-height, height * 2, step):
        for x_pos in range(-width, width * 2, step + 100):
            wm_draw.text((x_pos, y_pos), text, fill=(128, 128, 128, 90), font=font)

    rotated_wm = watermark_img.rotate(45, expand=False)
    img = Image.alpha_composite(img, rotated_wm)
    img = img.convert("RGB")

    # Convert to PDF via reportlab
    img_buf = io.BytesIO()
    img.save(img_buf, format="PNG")
    img_buf.seek(0)

    from reportlab.lib.pagesizes import A4
    pdf_buf = io.BytesIO()
    page_w, page_h = A4
    c = rl_canvas.Canvas(pdf_buf, pagesize=(page_w, page_h))
    c.drawImage(ImageReader(img_buf), 0, 0, width=page_w, height=page_h, preserveAspectRatio=True)
    c.save()
    pdf_buf.seek(0)
    return pdf_buf.read()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_watermark(
    file_bytes: bytes,
    mime_type: str,
    viewer_username: str,
    viewer_role: str,
    timestamp: datetime | None = None,
) -> bytes:
    """Apply dynamic watermark to document bytes in memory.

    Args:
        file_bytes: Decrypted document bytes
        mime_type: MIME type string (application/pdf, image/png, etc.)
        viewer_username: Current viewer's username
        viewer_role: Current viewer's role label
        timestamp: Viewing timestamp (defaults to now)

    Returns:
        Watermarked PDF bytes (always returns a PDF regardless of input type)
    """
    if timestamp is None:
        timestamp = datetime.utcnow()

    ts_str = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
    text_lines = [
        f"CLASSIFIED – VIEW ONLY",
        f"Viewer: {viewer_username}",
        f"Role: {viewer_role}",
        f"Timestamp: {ts_str}",
    ]

    is_pdf = (
        mime_type == "application/pdf"
        or file_bytes[:4] == b"%PDF"
    )

    try:
        if is_pdf:
            from reportlab.lib.pagesizes import A4
            # Get page dimensions from the original PDF
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(file_bytes))
                if reader.pages:
                    page = reader.pages[0]
                    pw = float(page.mediabox.width)
                    ph = float(page.mediabox.height)
                else:
                    pw, ph = A4
            except Exception:
                pw, ph = A4

            watermark_pdf = _build_watermark_pdf(text_lines, pw, ph)
            return _merge_watermark_on_pdf(file_bytes, watermark_pdf)
        else:
            # Image path
            return _image_to_watermarked_pdf(file_bytes, text_lines)

    except Exception as e:
        logger.error(f"Watermark application failed: {e}")
        # Return original bytes as fallback (don't break viewer)
        if is_pdf:
            return file_bytes
        # For images, return a minimal PDF error page
        return file_bytes
