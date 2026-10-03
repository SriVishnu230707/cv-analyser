"""Local PDF/DOCX extraction. Run through the bounded worker for uploads."""
import os
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pymupdf
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from backend.services.resume_sections import normalize_text, parse_sections

MAX_PAGES = 10
MAX_TEXT_CHARS = 50000
MAX_UNPACKED_BYTES = 25 * 1024 * 1024
ROOT = Path(__file__).resolve().parents[2]
pymupdf.TOOLS.mupdf_display_errors(False)
pymupdf.TOOLS.mupdf_display_warnings(False)


class ExtractionError(Exception):
    def __init__(self, code: str, message: str, status: int = 422):
        self.code, self.message, self.status = code, message, status
        super().__init__(message)


def tessdata_path():
    configured = os.environ.get("TESSDATA_PREFIX")
    path = Path(configured) if configured else ROOT / ".tools/tessdata"
    return str(path) if (path / "eng.traineddata").is_file() else None


def require_useful_text(text: str):
    if len(text.strip()) < 40 or sum(c.isalnum() for c in text) < 25:
        raise ExtractionError("insufficient_text", "Too little readable text was found. Upload a text-based resume or a clearer scan.")
    if len(text) > MAX_TEXT_CHARS:
        raise ExtractionError("text_too_long", "This document contains too much text. Limit the resume to 50,000 characters.")


def pdf_text(content: bytes):
    if not content.startswith(b"%PDF-"):
        raise ExtractionError("invalid_file", "The file does not have a PDF signature. Choose a PDF document.")
    pages, issues = [], []
    try:
        with pymupdf.open(stream=content, filetype="pdf") as document:
            if document.needs_pass or document.is_encrypted:
                raise ExtractionError("encrypted_document", "This PDF is password-protected. Upload an unlocked copy.")
            if document.page_count > MAX_PAGES:
                raise ExtractionError("too_many_pages", "Your PDF must contain 10 pages or fewer.")
            if document.is_repaired:
                raise ExtractionError("damaged_document", "This PDF required repair. Re-export it as a new PDF and upload again.")
            for number, page in enumerate(document, 1):
                text = page.get_text("text", sort=True)
                images = page.get_image_info()
                # Any substantial image can contain content absent from a text layer.
                substantial_image = any(pymupdf.Rect(image["bbox"]).get_area() > page.rect.get_area() * .15 for image in images)
                method = "text"
                if substantial_image:
                    tessdata = tessdata_path()
                    if not tessdata:
                        raise ExtractionError("ocr_unavailable", f"Page {number} contains image content that may need OCR. Upload a text-based PDF, or enable local English OCR on the server.")
                    if page.rect.width > 2000 or page.rect.height > 2000:
                        raise ExtractionError("page_too_large", "This PDF has unusually large pages. Re-export it at a standard page size.")
                    try:
                        textpage = page.get_textpage_ocr(language="eng", dpi=150, full=False, tessdata=tessdata)
                        text = page.get_text("text", textpage=textpage, sort=True)
                    except Exception:
                        raise ExtractionError("ocr_failed", f"OCR could not read page {number}. Upload a clearer scan or a text-based PDF.") from None
                    method = "ocr"
                    issues.append(f"Page {number} used OCR. Check spelling, symbols, and reading order.")
                if not text.strip():
                    issues.append(f"Page {number} contains no readable text. Check that no content is missing.")
                blocks = [b for b in page.get_text("blocks") if b[6] == 0]
                middle = page.rect.width / 2
                if any(b[2] < middle for b in blocks) and any(b[0] > middle for b in blocks):
                    issues.append(f"Page {number} may use columns. Check the reading order in the preview.")
                pages.append({"number": number, "text": normalize_text(text), "method": method})
    except ExtractionError:
        raise
    except Exception:
        raise ExtractionError("damaged_document", "This PDF could not be opened. Re-export it and upload again.") from None
    return pages, issues


def docx_text(content: bytes):
    issues = ["DOCX page count cannot be verified without rendering. Use PDF if you need the 10-page limit checked."]
    try:
        with ZipFile(BytesIO(content)) as archive:
            entries = archive.infolist()
            if len(entries) > 2000 or sum(entry.file_size for entry in entries) > MAX_UNPACKED_BYTES:
                raise ExtractionError("document_too_complex", "This DOCX is too large after unpacking. Simplify it or export as PDF.")
            if any(entry.flag_bits & 1 for entry in entries):
                raise ExtractionError("encrypted_document", "This document is protected. Upload an unlocked copy.")
            if not {"[Content_Types].xml", "word/document.xml"} <= set(archive.namelist()):
                raise ExtractionError("invalid_file", "The file is not a DOCX document.")
        document = Document(BytesIO(content))
        # Detect content containers the block API does not expose reliably.
        if document.element.xpath(".//w:txbxContent | .//w:ins | .//w:del"):
            raise ExtractionError("unsupported_docx_content", "This DOCX contains text boxes or tracked changes. Accept changes and export as PDF to preserve all text.")
        chunks = []

        def visit(container, depth=0):
            if depth > 8:
                raise ExtractionError("document_too_complex", "This DOCX has deeply nested tables. Simplify it or export as PDF.")
            for item in container.iter_inner_content():
                if isinstance(item, Paragraph):
                    if item.text.strip():
                        chunks.append(item.text)
                elif isinstance(item, Table):
                    seen = set()
                    for row in item.rows:
                        for cell in row.cells:
                            # Merged cells may appear repeatedly; retain their content once.
                            if cell._tc in seen:
                                continue
                            seen.add(cell._tc)
                            visit(cell, depth + 1)

        seen_parts = set()
        for section in document.sections:
            for header in (section.header, section.first_page_header, section.even_page_header):
                if header.part not in seen_parts:
                    seen_parts.add(header.part)
                    visit(header)
        visit(document)
        for section in document.sections:
            for footer in (section.footer, section.first_page_footer, section.even_page_footer):
                if footer.part not in seen_parts:
                    seen_parts.add(footer.part)
                    visit(footer)
        if document.inline_shapes:
            issues.append("Images in DOCX are not OCR-processed. If they contain resume text, export as PDF for OCR.")
        return [{"number": None, "text": normalize_text("\n".join(chunks)), "method": "text"}], issues
    except ExtractionError:
        raise
    except Exception:
        # Office-encrypted DOCX is an OLE container rather than a ZIP package.
        if content.startswith(bytes.fromhex("D0CF11E0A1B11AE1")):
            raise ExtractionError("encrypted_document", "This document is encrypted or in an older Word format. Upload an unlocked DOCX or PDF.") from None
        raise ExtractionError("damaged_document", "This DOCX is damaged or invalid. Re-save it and upload again.") from None


def extract_document(content: bytes, extension: str):
    pages, issues = pdf_text(content) if extension == ".pdf" else docx_text(content)
    text = normalize_text("\n\n".join(page["text"] for page in pages))
    require_useful_text(text)
    sections = parse_sections(text)
    if not any(section["name"] != "Overview" for section in sections):
        issues.append("No standard section headings were detected. Review the preview and add clear headings if appropriate.")
    if len(text) < 150:
        issues.append("The extracted resume is unusually short. Check for missing content.")
    return {"status": "extracted", "file_type": extension[1:], "text": text, "sections": sections, "pages": pages, "page_count": len(pages) if extension == ".pdf" else None, "ocr_used": any(page["method"] == "ocr" for page in pages), "readability": {"status": "needs_review" if issues else "readable", "issues": issues}, "warnings": ["Check the preview for missing content and reading order before continuing."]}
