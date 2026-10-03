"""Create synthetic PDF/DOCX files for reproducible browser QA."""
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
if (root / ".tools/backend").is_dir():
    sys.path.insert(0, str(root / ".tools/backend"))

from backend.tests.document_fixtures import docx_bytes, pdf_bytes, scanned_pdf

if __name__ == "__main__":
    output = root / "data/phase-3/fixtures"
    output.mkdir(parents=True, exist_ok=True)
    files = {"resume.pdf": pdf_bytes(), "columns.pdf": pdf_bytes(columns=True), "scan.pdf": scanned_pdf(), "mixed.pdf": scanned_pdf(mixed=True), "eleven-pages.pdf": pdf_bytes(pages=11), "encrypted.pdf": pdf_bytes(encrypted=True), "resume.docx": docx_bytes(), "damaged.pdf": b"%PDF-1.4\nnot a document"}
    for name, content in files.items():
        (output / name).write_bytes(content)
    print("Created 8 synthetic Phase 3 document fixtures.")
