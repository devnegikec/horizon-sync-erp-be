"""Document parser for ASN ingestion.

Extracts raw text from PDF, Excel, and image files.
Uses unstructured-io when available; falls back to basic libraries.
"""

import io
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Try importing unstructured; mark availability
UNSTRUCTURED_AVAILABLE = False
try:
    from unstructured.partition.auto import partition
    from unstructured.partition.pdf import partition_pdf
    from unstructured.partition.xlsx import partition_xlsx

    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    logger.warning("unstructured not installed; PDF/Excel parsing will be limited")

# Try importing PIL for image OCR fallback
PIL_AVAILABLE = False
try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    pass


class DocumentParser:
    """Parse uploaded ASN documents into raw text."""

    SUPPORTED_MIME_TYPES = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
        "application/vnd.ms-excel": "xls",
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/tiff": "tiff",
        "text/plain": "txt",
        "text/csv": "csv",
        "message/rfc822": "email",
    }

    def __init__(self, ocr_enabled: bool = True):
        self.ocr_enabled = ocr_enabled

    def detect_file_type(self, filename: str, content_type: Optional[str] = None) -> str:
        """Infer file extension from content-type or filename."""
        if content_type:
            ext = self.SUPPORTED_MIME_TYPES.get(content_type.lower())
            if ext:
                return ext
        suffix = Path(filename).suffix.lower().lstrip(".")
        if suffix in ("pdf", "xlsx", "xls", "png", "jpg", "jpeg", "tiff", "txt", "csv", "eml", "msg"):
            return suffix
        return "unknown"

    def parse(self, file_bytes: bytes, filename: str, content_type: Optional[str] = None) -> str:
        """Parse document bytes into raw text string."""
        file_type = self.detect_file_type(filename, content_type)
        logger.info("Parsing document: %s (type=%s)", filename, file_type)

        if file_type == "pdf":
            return self._parse_pdf(file_bytes, filename)
        if file_type in ("xlsx", "xls"):
            return self._parse_excel(file_bytes, filename)
        if file_type in ("png", "jpg", "jpeg", "tiff"):
            return self._parse_image(file_bytes, filename)
        if file_type in ("txt", "csv"):
            return file_bytes.decode("utf-8", errors="replace")
        if file_type == "email":
            return self._parse_email(file_bytes, filename)

        # Fallback: try unstructured auto-detect
        if UNSTRUCTURED_AVAILABLE:
            return self._parse_unstructured_auto(file_bytes, filename)

        raise ValueError(f"Unsupported file type: {file_type} ({filename})")

    def _parse_pdf(self, file_bytes: bytes, filename: str) -> str:
        if UNSTRUCTURED_AVAILABLE:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            try:
                elements = partition_pdf(tmp_path)
                return "\n".join(el.text for el in elements if hasattr(el, "text") and el.text)
            finally:
                os.unlink(tmp_path)
        # Minimal fallback: cannot parse PDF without unstructured
        raise RuntimeError("PDF parsing requires 'unstructured' library. Install: pip install unstructured[pdf]")

    def _parse_excel(self, file_bytes: bytes, filename: str) -> str:
        if UNSTRUCTURED_AVAILABLE:
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            try:
                elements = partition_xlsx(tmp_path)
                return "\n".join(el.text for el in elements if hasattr(el, "text") and el.text)
            finally:
                os.unlink(tmp_path)
        # Fallback using openpyxl if available
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
            lines = []
            for sheet in wb.worksheets:
                lines.append(f"Sheet: {sheet.title}")
                for row in sheet.iter_rows(values_only=True):
                    row_text = " | ".join(str(cell) for cell in row if cell is not None)
                    if row_text.strip():
                        lines.append(row_text)
            return "\n".join(lines)
        except ImportError:
            raise RuntimeError("Excel parsing requires 'unstructured' or 'openpyxl'. Install either.")

    def _parse_image(self, file_bytes: bytes, filename: str) -> str:
        if not self.ocr_enabled:
            raise RuntimeError("OCR is disabled; cannot parse image files")
        # Try pytesseract if available
        try:
            import pytesseract
            if PIL_AVAILABLE:
                image = Image.open(io.BytesIO(file_bytes))
                return pytesseract.image_to_string(image)
        except ImportError:
            pass
        raise RuntimeError("Image OCR requires 'pytesseract' and 'Pillow'. Install both.")

    def _parse_email(self, file_bytes: bytes, filename: str) -> str:
        try:
            import email
            msg = email.message_from_bytes(file_bytes)
            parts = [f"Subject: {msg.get('Subject', '')}", f"From: {msg.get('From', '')}", f"To: {msg.get('To', '')}"]
            if msg.is_multipart():
                for part in msg.walk():
                    ctype = part.get_content_type()
                    if ctype == "text/plain":
                        parts.append(part.get_payload(decode=True).decode("utf-8", errors="replace"))
                    elif ctype == "text/html":
                        # Basic HTML stripping
                        html = part.get_payload(decode=True).decode("utf-8", errors="replace")
                        parts.append(self._strip_html(html))
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    parts.append(payload.decode("utf-8", errors="replace"))
            return "\n\n".join(parts)
        except Exception as e:
            raise RuntimeError(f"Email parsing failed: {e}")

    def _parse_unstructured_auto(self, file_bytes: bytes, filename: str) -> str:
        with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            elements = partition(tmp_path)
            return "\n".join(el.text for el in elements if hasattr(el, "text") and el.text)
        finally:
            os.unlink(tmp_path)

    @staticmethod
    def _strip_html(html: str) -> str:
        try:
            from bs4 import BeautifulSoup
            return BeautifulSoup(html, "html.parser").get_text(separator="\n")
        except ImportError:
            import re
            return re.sub(r"<[^>]+>", "", html)


def get_parser() -> DocumentParser:
    """Factory: return a DocumentParser instance."""
    return DocumentParser(ocr_enabled=True)
