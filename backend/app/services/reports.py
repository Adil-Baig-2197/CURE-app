import io
import re
import uuid
from pathlib import Path

import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
from pypdf import PdfReader

ALLOWED_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}
SUFFIX_BY_CONTENT_TYPE = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}


def extract_text(content: bytes, content_type: str) -> tuple[str, list[str]]:
    limitations: list[str] = []
    if content_type == "application/pdf":
        reader = PdfReader(io.BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        if text:
            return text, limitations
        limitations.append("No embedded PDF text was found; local OCR was used on rendered pages.")
        pages = convert_from_bytes(content)
        return "\n".join(pytesseract.image_to_string(page) for page in pages).strip(), limitations
    image = Image.open(io.BytesIO(content))
    limitations.append("Image text was extracted with local OCR and may contain recognition errors.")
    return pytesseract.image_to_string(image).strip(), limitations


def structured_candidates(text: str) -> dict:
    """Extract only explicitly labelled fields; everything remains unverified."""
    diagnoses = re.findall(r"(?im)^\s*(?:diagnosis|diagnoses)\s*:\s*(.+)$", text)
    medications = re.findall(r"(?im)^\s*(?:medication|medications)\s*:\s*(.+)$", text)
    labs = re.findall(r"(?im)^\s*([a-z][a-z /()-]{2,50})\s*[:=]\s*([0-9]+(?:\.[0-9]+)?\s*[a-zA-Z/%µ]+)\s*$", text)
    return {"diagnoses": diagnoses, "medications": medications, "laboratory_results": [{"name": name.strip(), "value": value.strip()} for name, value in labs], "verification_required": True}


def save_original(storage_root: Path, content: bytes, content_type: str) -> str:
    storage_root.mkdir(parents=True, exist_ok=True)
    key = f"{uuid.uuid4()}{SUFFIX_BY_CONTENT_TYPE[content_type]}"
    (storage_root / key).write_bytes(content)
    return key
