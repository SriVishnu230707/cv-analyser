"""Phase 9: ATS alignment, NLP matching, and OpenAI enrichment."""
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from backend.services.document_parser import ExtractionError, MAX_TEXT_CHARS, require_useful_text, tessdata_path
from backend.services.extraction_runner import run_extraction
from backend.services.resume_sections import normalize_text
from backend.services.structured_profile import prepare_profile
from backend.services.analysis_service import compare
from backend.services.extraction_context import sign_context
from backend.services.skill_extractor import CATALOG
from backend.services.report_export import pdf_report
from backend.services.ai_enrichment import configuration, enrich, AIError
import json

ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 5 * 1024 * 1024
app = FastAPI(title="CV Analyser", version="0.9.0", description="Extract resumes and compare reviewed evidence with job requirements.")


def error(code: str, message: str, field: str, status: int = 422):
    return JSONResponse(status_code=status, content={"code": code, "message": message, "field": field})


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, exc: RequestValidationError):
    field = str(exc.errors()[0]["loc"][-1])
    missing = exc.errors()[0]["type"] == "missing"
    return error("missing_input" if missing else "invalid_input", "Provide the required input." if missing else "Check the text length and input format.", field)


@app.exception_handler(Exception)
async def processing_error(_request: Request, _exc: Exception):
    return error("processing_error", "Something went wrong. Please try again.", "request", 500)


@app.get("/health")
def health():
    return {"status": "ok", "phase": 9, "analysis_mode": "evidence_based", "ocr_available": tessdata_path() is not None}


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


@app.post("/api/extract")
async def extract(resume: UploadFile = File(...)):
    try:
        extension = Path(resume.filename or "").suffix.lower()
        if extension not in {".pdf", ".docx"}:
            return error("unsupported_file", "Upload a PDF or DOCX file.", "resume", 415)
        # A bounded read prevents loading an unlimited file into application memory.
        if resume.size is not None and resume.size > MAX_FILE_BYTES:
            return error("file_too_large", "Your resume must be 5 MiB or smaller.", "resume", 413)
        content = await resume.read(MAX_FILE_BYTES + 1)
        if len(content) > MAX_FILE_BYTES:
            return error("file_too_large", "Your resume must be 5 MiB or smaller.", "resume", 413)
        if not content:
            return error("empty_file", "This file is empty. Choose another resume.", "resume")
        result = await run_extraction(content, extension)
        if not result["ok"]:
            return JSONResponse(result["error"], status_code=result["status"], headers={"Cache-Control": "no-store"})
        response = JSONResponse(result["result"], headers={"Cache-Control": "no-store"})
        response.headers['X-Extraction-Context'] = sign_context(result['result'])
        return response
    finally:
        await resume.close()


class PreviewInput(BaseModel):
    resume_text: str = Field(max_length=MAX_TEXT_CHARS)
    job_description: str = Field(max_length=20000)


@app.post("/api/preview")
def preview(body: PreviewInput):
    text = normalize_text(body.resume_text)
    try:
        require_useful_text(text)
    except ExtractionError as exc:
        return error(exc.code, exc.message, "resume_text", exc.status)
    job = body.job_description.strip()
    if not 100 <= len(job) <= 20000:
        return error("invalid_job_description", "Enter a job description between 100 and 20,000 characters.", "job_description")
    result = prepare_profile(text, job)
    return JSONResponse(result, headers={"Cache-Control": "no-store"})


class CategoryCorrection(BaseModel):
    requirement_id: str = Field(max_length=80)
    category: Literal["required_skill", "preferred_skill", "unclassified_skill", "responsibility", "mandatory_qualification", "qualification", "experience_requirement", "other_requirement", "excluded"]


class RequirementReviewInput(PreviewInput):
    corrections: list[CategoryCorrection] = Field(max_length=500)


class SkillMapping(BaseModel):
    requirement_id: str = Field(max_length=80)
    canonical_skill: str = Field(max_length=80)


class EvidenceDecision(BaseModel):
    requirement_id: str = Field(max_length=80)
    evidence_id: str = Field(max_length=80)
    decision: Literal['accept', 'reject']


class ComparisonInput(PreviewInput):
    requirements_confirmed: Literal[True]
    category_corrections: list[CategoryCorrection] = Field(max_length=500)
    skill_mappings: list[SkillMapping] = Field(default_factory=list, max_length=500)
    evidence_decisions: list[EvidenceDecision] = Field(default_factory=list, max_length=500)
    extraction_context: str | None = Field(default=None, max_length=20000)
    ai_context: str | None = Field(default=None, max_length=200000)


@app.get('/api/skills')
def skill_catalog():
    return json.loads(CATALOG.read_text(encoding='utf-8'))


def prepare_comparison(body: ComparisonInput):
    text, job = normalize_text(body.resume_text), body.job_description.strip()
    try:
        require_useful_text(text)
        if len(job) < 100:
            return error('invalid_job_description', 'Enter at least 100 characters of job description.', 'job_description')
        result = compare(text, job, [c.model_dump() for c in body.category_corrections], [m.model_dump() for m in body.skill_mappings], [d.model_dump() for d in body.evidence_decisions], body.extraction_context, body.ai_context)
    except ExtractionError as exc:
        return error(exc.code, exc.message, 'resume_text', exc.status)
    except ValueError as exc:
        return error('invalid_comparison', str(exc), 'review')
    return result


@app.post('/api/compare')
def compare_resume(body: ComparisonInput):
    result = prepare_comparison(body)
    return result if isinstance(result, JSONResponse) else JSONResponse(result, headers={'Cache-Control': 'no-store'})


@app.get('/api/ai/status')
def ai_status():
    return JSONResponse(configuration(), headers={'Cache-Control': 'no-store'})


class AIInput(ComparisonInput):
    cloud_consent: Literal[True]


@app.post('/api/ai/analyze')
def ai_analyze(body: AIInput):
    if body.ai_context:
        return error('already_enhanced', 'Start a fresh comparison before requesting new AI advice.', 'ai_context')
    report = prepare_comparison(body)
    if isinstance(report, JSONResponse):
        return report
    try:
        token = enrich(report)
    except AIError as exc:
        return error(exc.code, exc.message, 'ai', exc.status)
    enhanced = prepare_comparison(body.model_copy(update={'ai_context': token}))
    if isinstance(enhanced, JSONResponse):
        return enhanced
    return JSONResponse({'report': enhanced, 'ai_context': token}, headers={'Cache-Control': 'no-store'})


class ExportInput(ComparisonInput):
    format: Literal['pdf', 'json']


@app.post('/api/report/export')
def export_report(body: ExportInput):
    result = prepare_comparison(body)
    if isinstance(result, JSONResponse):
        return result
    try:
        content = pdf_report(result) if body.format == 'pdf' else json.dumps(result, ensure_ascii=False, indent=2).encode('utf-8')
    except ValueError as exc:
        return error('export_too_large', str(exc), 'format')
    filename = f"cv-analysis-{result['analysis_id'][:8]}.{body.format}"
    return Response(content, media_type='application/pdf' if body.format == 'pdf' else 'application/json', headers={'Cache-Control': 'no-store', 'Content-Disposition': f'attachment; filename="{filename}"', 'X-Content-Type-Options': 'nosniff'})


@app.post("/api/requirements/review")
def review(body: RequirementReviewInput):
    text = normalize_text(body.resume_text)
    try:
        require_useful_text(text)
    except ExtractionError as exc:
        return error(exc.code, exc.message, "resume_text", exc.status)
    job = body.job_description.strip()
    if not 100 <= len(job) <= 20000:
        return error("invalid_job_description", "Enter a job description between 100 and 20,000 characters.", "job_description")
    try:
        result = prepare_profile(text, job, [item.model_dump() for item in body.corrections])
    except ValueError as exc:
        return error("invalid_review", str(exc), "corrections")
    return JSONResponse(result, headers={"Cache-Control": "no-store"})


@app.post("/api/analyze", deprecated=True)
async def analyze(resume: UploadFile = File(...), job_description: str = Form(...)):
    """Phase 2 compatibility entry point: now returns extraction, never a fake score."""
    if not 100 <= len(job_description.strip()) <= 20000:
        await resume.close()
        return error("invalid_job_description", "Enter a job description between 100 and 20,000 characters.", "job_description")
    return await extract(resume)
