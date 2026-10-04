from io import BytesIO
from zipfile import ZipFile
import asyncio
import json

import pymupdf
import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from backend.main import MAX_FILE_BYTES, ROOT, app, demo_pdf
from backend.services import extraction_runner
from backend.services.document_parser import ExtractionError, extract_document, tessdata_path
from backend.services.resume_sections import normalize_text, parse_sections
from backend.tests.document_fixtures import RESUME, docx_bytes, pdf_bytes, scanned_pdf

client = TestClient(app)
JOB = (ROOT / "data/phase-1/cases/backend-02/job-description.txt").read_text(encoding="utf-8")


def post(filename="resume.pdf", content=None):
    return client.post("/api/extract", files={"resume": (filename, pdf_bytes() if content is None else content)})


def test_health_and_examples():
    response = client.get("/health").json()
    assert response["phase"] == 7
    assert response["analysis_mode"] == "evidence_based"
    assert isinstance(response["ocr_available"], bool)
    assert client.get("/api/demo/job").json()["job_description"] == JOB
    pdf = client.get("/api/demo/resume")
    assert pdf.headers["content-type"] == "application/pdf"
    assert extract_document(pdf.content, ".pdf")["text"].startswith("Synthetic Candidate backend-02")


def test_pdf_real_text_and_sections():
    response = post()
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "extracted"
    assert result["text"] == RESUME
    assert result["page_count"] == 1
    assert not result["ocr_used"]
    assert {s["name"] for s in result["sections"]} >= {"Skills", "Projects", "Education", "Summary"}
    assert "scores" not in result
    assert response.headers["cache-control"] == "no-store"
    schema = json.loads((ROOT / "contracts/extraction-result.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(result)


def test_docx_order_headers_nested_and_merged_tables():
    response = post("resume.DOCX", docx_bytes())
    assert response.status_code == 200
    result = response.json()
    text = result["text"]
    assert "fictional contact header" in text
    assert text.index("Backend project") < text.index("Built REST APIs") < text.index("Education")
    assert text.count("Queried application data using SQL.") == 1
    assert text.count("Nested project detail retained.") == 1
    assert "C++, C#" in text
    assert result["page_count"] is None
    assert any("page count" in issue for issue in result["readability"]["issues"])


@pytest.mark.parametrize("filename,content,status,code", [
    ("resume.txt", b"hello", 415, "unsupported_file"),
    ("resume.pdf", b"", 422, "empty_file"),
    ("resume.pdf", b"this is not a PDF", 422, "invalid_file"),
    ("resume.pdf", b"%PDF-1.4\nnot a document", 422, "damaged_document"),
    ("resume.docx", b"damaged zip", 422, "damaged_document"),
    ("resume.pdf", b"%PDF-" + b"x" * MAX_FILE_BYTES, 413, "file_too_large"),
], ids=["unsupported", "empty", "fake-pdf", "damaged-pdf", "damaged-docx", "oversized"])
def test_invalid_files(filename, content, status, code):
    response = post(filename, content)
    assert response.status_code == status
    assert response.json()["code"] == code
    assert response.json()["field"] == "resume"


@pytest.mark.parametrize("pages,encrypted,code", [(11, False, "too_many_pages"), (1, True, "encrypted_document")], ids=["page-limit", "password"])
def test_pdf_limits(pages, encrypted, code):
    response = post(content=pdf_bytes(pages=pages, encrypted=encrypted))
    assert response.status_code == 422
    assert response.json()["code"] == code
    assert "scores" not in response.json()


def test_exact_page_limit_is_accepted():
    result = extract_document(pdf_bytes(pages=10), ".pdf")
    assert result["page_count"] == 10
    assert len(result["pages"]) == 10


def test_blank_pdf_blocks_continuation():
    with pymupdf.open() as document:
        document.new_page()
        content = document.tobytes()
    response = post(content=content)
    assert response.status_code == 422
    assert response.json()["code"] == "insufficient_text"


def test_column_content_is_preserved_and_flagged():
    result = extract_document(pdf_bytes(columns=True), ".pdf")
    assert "Python" in result["text"] and "Built REST APIs" in result["text"]
    assert any("columns" in issue for issue in result["readability"]["issues"])


@pytest.mark.skipif(tessdata_path() is None, reason="Local English OCR language data not installed")
@pytest.mark.parametrize("mixed", [False, True], ids=["scan", "mixed"])
def test_real_english_ocr(mixed):
    response = post(content=scanned_pdf(mixed=mixed))
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["ocr_used"]
    assert "Python" in result["text"]
    assert "Education" in result["text"]
    assert result["page_count"] == (2 if mixed else 1)
    assert any("OCR" in issue for issue in result["readability"]["issues"])


def test_scan_without_ocr_is_actionable(monkeypatch):
    monkeypatch.setattr("backend.services.document_parser.tessdata_path", lambda: None)
    with pytest.raises(ExtractionError) as exception:
        extract_document(scanned_pdf(), ".pdf")
    assert exception.value.code == "ocr_unavailable"


def test_arbitrary_zip_is_not_docx():
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("file.txt", "not a document")
    response = post("resume.docx", buffer.getvalue())
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_file"


def test_docx_unpacked_limit_blocks_compressed_bomb():
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=8) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "x" * (26 * 1024 * 1024))
    assert len(buffer.getvalue()) < MAX_FILE_BYTES
    assert post("resume.docx", buffer.getvalue()).json()["code"] == "document_too_complex"


def test_docx_textboxes_are_not_silently_omitted():
    from docx import Document
    from docx.oxml import OxmlElement
    document = Document()
    paragraph = document.add_paragraph(RESUME)
    paragraph._p.append(OxmlElement("w:txbxContent"))
    buffer = BytesIO()
    document.save(buffer)
    assert post("resume.docx", buffer.getvalue()).json()["code"] == "unsupported_docx_content"


def test_legacy_endpoint_extracts_instead_of_returning_sample_score():
    response = client.post("/api/analyze", files={"resume": ("resume.pdf", demo_pdf())}, data={"job_description": JOB})
    assert response.status_code == 200
    assert response.json()["status"] == "extracted"
    assert "scores" not in response.json()


@pytest.mark.parametrize("job", ["short", " " * 100, "x" * 20001], ids=["short", "blank", "too-long"])
def test_legacy_job_description_bounds(job):
    response = client.post("/api/analyze", files={"resume": ("resume.pdf", demo_pdf())}, data={"job_description": job})
    assert response.status_code == 422
    assert response.json()["field"] == "job_description"


def test_missing_input_has_safe_error_envelope():
    response = client.post("/api/extract")
    assert response.status_code == 422
    assert set(response.json()) == {"code", "message", "field"}


def test_reviewed_text_preparation_uses_edits_without_upload():
    edited = RESUME + "\nCertifications\nCompleted a fictional SQL course."
    response = client.post("/api/preview", json={"resume_text": edited, "job_description": JOB})
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "ready_for_matching"
    assert result["resume_text"] == edited
    assert result["job_description"] == JOB.strip()
    assert result["analysis_available"] is False
    assert result["resume_sections"][-1]["name"] == "Certifications"
    assert "scores" not in result
    assert response.headers["cache-control"] == "no-store"
    second = client.post("/api/preview", json={"resume_text": RESUME, "job_description": JOB}).json()
    assert second["preparation_id"] != result["preparation_id"]


@pytest.mark.parametrize("text,job,field", [("", JOB, "resume_text"), ("!" * 100, JOB, "resume_text"), (RESUME, "short", "job_description"), ("x" * 50001, JOB, "resume_text")], ids=["empty", "no-readable-text", "short-job", "long-resume"])
def test_preview_validation(text, job, field):
    response = client.post("/api/preview", json={"resume_text": text, "job_description": job})
    assert response.status_code == 422
    assert response.json()["field"] == field


def test_normalization_preserves_symbols_unicode_and_boundaries():
    assert normalize_text("Skills\r\n C++,\t C#,\u00a0Python\r\n\r\n\r\n\u00c9ducation") == "Skills\nC++, C#, Python\n\n\u00c9ducation"


def test_heading_aliases_inline_values_and_preamble():
    result = parse_sections("Synthetic Candidate\nTECHNICAL SKILLS: C++, C#\nWORK EXPERIENCE\nBuilt useful tools.\nCertifications:\nSQL course")
    assert [s["name"] for s in result] == ["Overview", "Skills", "Experience", "Certifications"]
    assert result[1]["text"] == "C++, C#"


def test_worker_timeout_is_bounded_and_process_is_terminated(tmp_path, monkeypatch):
    slow_worker = tmp_path / "slow_worker.py"
    slow_worker.write_text("import sys,time\nsys.stdin.buffer.read()\ntime.sleep(30)\n", encoding="utf-8")
    monkeypatch.setattr(extraction_runner, "WORKER", slow_worker)
    monkeypatch.setattr(extraction_runner, "EXTRACTION_TIMEOUT", .2)
    result = asyncio.run(extraction_runner.run_extraction(b"sample", ".pdf"))
    assert result["status"] == 408
    assert result["error"]["code"] == "extraction_timeout"
