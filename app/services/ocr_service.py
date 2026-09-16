"""OCR service using pytesseract.

Graceful fallback: if Tesseract binary is not installed, OCR is skipped
and the function returns None without raising.
"""
import io
import logging

logger = logging.getLogger(__name__)


def extract_text_from_bytes(file_bytes: bytes, mime_type: str = "") -> str | None:
    """Extract textual content from document bytes.

    Supports PDF (via pdf2image → tesseract) and direct images.
    Returns extracted text string or None if OCR is unavailable / fails.
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        logger.warning("pytesseract / Pillow not available – OCR skipped.")
        return None

    try:
        # Determine file type
        is_pdf = mime_type == "application/pdf" or file_bytes[:4] == b"%PDF"
        texts: list[str] = []

        if is_pdf:
            # Convert PDF pages to images
            try:
                from pdf2image import convert_from_bytes
                pages = convert_from_bytes(file_bytes, dpi=200)
                for page in pages:
                    text = pytesseract.image_to_string(page, lang="eng")
                    texts.append(text)
            except Exception as pdf_err:
                logger.warning(f"pdf2image failed: {pdf_err} – trying raw image fallback.")
                # Fallback: try reading as image directly
                img = Image.open(io.BytesIO(file_bytes))
                text = pytesseract.image_to_string(img, lang="eng")
                texts.append(text)
        else:
            # Treat as image
            img = Image.open(io.BytesIO(file_bytes))
            text = pytesseract.image_to_string(img, lang="eng")
            texts.append(text)

        combined = "\n".join(texts).strip()
        return combined if combined else None

    except Exception as e:
        logger.warning(f"OCR extraction failed: {e}")
        return None
