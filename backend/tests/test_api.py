import json
from io import BytesIO
from zipfile import ZipFile
import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from backend.main import MAX_FILE_BYTES, ROOT, app, demo_pdf
client = TestClient(app)
JOB = (ROOT / "data/phase-1/cases/backend-02/job-description.txt").read_text(encoding="utf-8")
def post(filename="resume.pdf", content=None, job=JOB):
    return client.post("/api/analyze", files={"resume": (filename, demo_pdf() if content is None else content)}, data={"job_description": job})
def test_health_and_example():
    assert client.get("/health").json() == {"status": "ok", "phase": 2, "analysis_mode": "demo"}
    assert client.get("/api/demo/job").json()["job_description"] == JOB
    assert client.get("/api/demo/resume").content.startswith(b"%PDF-")
def test_fixed_sample_contract():
    response = post()
    assert response.status_code == 200
    assert response.headers["x-analysis-mode"] == "demo"
    assert response.json() == json.loads((ROOT / "data/phase-1/sample-report.json").read_text(encoding="utf-8"))
    Draft202012Validator(json.loads((ROOT / "contracts/analysis-result.schema.json").read_text(encoding="utf-8"))).validate(response.json())
    assert post(job="Another fictional software role. " * 8).json() == response.json()
def test_docx_structure():
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
    assert post("resume.DOCX", buffer.getvalue()).status_code == 200
@pytest.mark.parametrize("filename,content,status,code", [
    ("resume.txt", b"hello", 415, "unsupported_file"),
    ("resume.pdf", b"", 422, "empty_file"),
    ("resume.pdf", b"not a pdf", 422, "invalid_file"),
    ("resume.docx", b"damaged", 422, "invalid_file"),
    ("resume.pdf", b"%PDF-" + b"x" * MAX_FILE_BYTES, 413, "file_too_large"),
], ids=["unsupported", "empty", "fake-pdf", "damaged-docx", "oversized"])
def test_invalid_files(filename, content, status, code):
    response = post(filename, content)
    assert response.status_code == status
    assert response.json()["code"] == code
    assert response.json()["field"] == "resume"
def test_arbitrary_zip():
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("file.txt", "not a DOCX")
    assert post("resume.docx", buffer.getvalue()).json()["code"] == "invalid_file"
@pytest.mark.parametrize("job", ["short", " " * 100, "x" * 20001], ids=["short", "blank", "long"])
def test_job_bounds(job):
    assert post(job=job).json()["field"] == "job_description"
def test_missing_input():
    response = client.post("/api/analyze")
    assert response.status_code == 422
    assert set(response.json()) == {"code", "message", "field"}
