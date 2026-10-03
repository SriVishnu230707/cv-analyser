"""Phase 2 API: validate uploads and return the fixed example report."""
import json
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, BadZipFile
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 5 * 1024 * 1024
app = FastAPI(title="CV Analyser", version="0.2.0", description="Phase 2 demo. Every valid submission returns the fixed Phase 1 sample report.")
def error(code, message, field, status=422):
    return JSONResponse(status_code=status, content={"code": code, "message": message, "field": field})
@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, exc: RequestValidationError):
    return error("missing_input", "Upload a resume and provide a job description.", str(exc.errors()[0]["loc"][-1]))
@app.exception_handler(Exception)
async def processing_error(_request: Request, _exc: Exception):
    return error("processing_error", "Something went wrong. Please try again.", "request", 500)
@app.get("/health")
def health():
    return {"status": "ok", "phase": 2, "analysis_mode": "demo"}
@app.get("/api/demo/job")
def demo_job():
    return {"job_description": (ROOT / "data/phase-1/cases/backend-02/job-description.txt").read_text(encoding="utf-8")}

def demo_pdf() -> bytes:
    """Create a valid, one-page PDF of the synthetic backend-02 resume."""
    lines = (ROOT / "data/phase-1/cases/backend-02/resume.txt").read_text(encoding="utf-8").splitlines()
    escaped = [line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") for line in lines]
    stream = ("BT /F1 11 Tf 50 780 Td 18 TL " + " ".join(f"({line}) Tj T*" for line in escaped) + " ET").encode("ascii")
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>", b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>", f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(output)


@app.get("/api/demo/resume")
def demo_resume():
    return Response(demo_pdf(), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="sample-resume.pdf"'})



@app.post("/api/analyze")
async def analyze(resume: UploadFile = File(...), job_description: str = Form(...)):
    try:
        if not 100 <= len(job_description.strip()) <= 20000:
            return error("invalid_job_description", "Enter a job description between 100 and 20,000 characters.", "job_description")
        extension = Path(resume.filename or "").suffix.lower()
        if extension not in {".pdf", ".docx"}:
            return error("unsupported_file", "Upload a PDF or DOCX file.", "resume", 415)
        if resume.size is not None and resume.size > MAX_FILE_BYTES:
            return error("file_too_large", "Your resume must be 5 MiB or smaller.", "resume", 413)
        content = await resume.read(MAX_FILE_BYTES + 1)
        if len(content) > MAX_FILE_BYTES:
            return error("file_too_large", "Your resume must be 5 MiB or smaller.", "resume", 413)
        if not content:
            return error("empty_file", "This file is empty. Choose another resume.", "resume")
        if extension == ".pdf" and not content.startswith(b"%PDF-"):
            return error("invalid_file", "The file does not have a PDF signature. Choose a PDF document.", "resume")
        if extension == ".docx":
            try:
                with ZipFile(BytesIO(content)) as archive:
                    if not {"[Content_Types].xml", "word/document.xml"} <= set(archive.namelist()):
                        return error("invalid_file", "The file is not a DOCX document.", "resume")
            except BadZipFile:
                return error("invalid_file", "The DOCX file is damaged or invalid.", "resume")
        report = json.loads((ROOT / "data/phase-1/sample-report.json").read_text(encoding="utf-8"))
        return JSONResponse(report, headers={"X-Analysis-Mode": "demo", "Cache-Control": "no-store"})
    finally:
        await resume.close()
