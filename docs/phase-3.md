# Phase 3: document extraction and review

The application now reads actual resume content. The Phase 2 fixed report is no longer presented as a submission result. Job requirement extraction, matching, scoring, and suggestions remain later phases.

## User workflow

1. Upload one PDF or DOCX (up to 5 MiB), or load the synthetic example.
2. Click **Extract resume text**. A job description is not needed for extraction.
3. Review the editable text and extraction checks. Common heading aliases identify Summary, Skills, Experience, Projects, Education, Certifications, and other sections; unmatched introductory text is Overview.
4. Correct missing content or reading order. Editing or restoring the text clears review confirmation and any prepared result.
5. Add a job description of 100–20,000 characters and confirm the text review.
6. Click **Prepare for matching**. The API normalizes the edited text and rebuilds sections without requiring another upload. The prepared text remains in memory; it is not saved to a database.

## Extraction behavior

- PyMuPDF extracts PDF text with reading-order sorting. PDF pages are counted and documents over 10 pages are rejected before extraction.
- Large image regions trigger local English OCR, including PDFs with a mixture of searchable text and scanned pages. OCR output is explicitly flagged for review.
- Multi-column layouts produce a reading-order warning. The parser preserves content for correction; it does not guarantee correct order for all designs.
- python-docx reads body paragraphs and tables in document order, including nested/merged cells, plus header/footer text. Skill punctuation and Unicode are preserved.
- DOCX pagination depends on a rendering engine, so page count is null and the preview warns that the 10-page limit cannot be verified. Export as PDF when page-limit verification matters.
- DOCX images are not OCR-processed. Documents with text boxes or tracked changes are rejected with instructions to export as PDF rather than silently omitting that text.
- Password-protected, damaged, unsupported, blank, excessively complex, or insufficiently readable documents return actionable error messages and no scores.
- Text has a 50,000-character cap. DOCX unpacking has a 25 MiB/2,000-entry cap. Deeply nested tables are rejected.

Extraction runs in a separate process with a 45-second deadline and a two-worker concurrency limit. Timed-out processes are terminated. Uploads use bounded reads and closed file handles; document contents are not stored or logged by application code. Before exposing the service publicly, enforce total request limits at the HTTP ingress as well, because multipart parsing occurs before the endpoint's file-size check.

## API contracts

| Route | Input | Output |
|---|---|---|
| `GET /health` | None | Phase, status, analysis availability, OCR availability |
| `POST /api/extract` | Multipart `resume` | Text, sections, page text, source readability findings, OCR flag |
| `POST /api/preview` | JSON `resume_text`, `job_description` | Normalized reviewed text, rebuilt sections, preparation ID, `analysis_available: false` |
| `POST /api/analyze` | Legacy multipart resume/job description | Deprecated Phase 2 entry point; returns real extraction rather than the fixed sample report |

Errors keep the `{code, message, field}` envelope. Successful extraction and preparation responses use `Cache-Control: no-store`. The extraction JSON contract is in `contracts/extraction-result.schema.json`. The Phase 1 analysis schema remains the future scoring contract; extraction responses are a separate type.

## Setup

Python 3.11+ is required for the extraction timeout mechanism. Follow the existing frontend/API setup in `docs/phase-2.md`, with the updated requirements. Stop the API before upgrading native dependencies on Windows to avoid locked DLLs.

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
powershell -ExecutionPolicy Bypass -File scripts/setup_ocr.ps1
.\.venv\Scripts\python.exe scripts/run_backend.py --port 8001
```

In the frontend terminal:

```powershell
cd frontend
npm install
$env:BACKEND_URL = 'http://127.0.0.1:8001'
npm run dev
```

Open http://127.0.0.1:5173. The current session uses port 8001 for the API. OCR English data is already installed locally under `.tools/tessdata`; it is ignored by Git. Other deployments can set `TESSDATA_PREFIX` to a directory containing `eng.traineddata`. Without language data, searchable PDFs and DOCX still work; scanned/image-rich PDFs receive an OCR-availability message.

The setup script downloads the English model from the official [Tesseract fast language-data repository](https://github.com/tesseract-ocr/tessdata_fast) and verifies the model checksum. [PyMuPDF OCR documentation](https://pymupdf.readthedocs.io/en/latest/page.html) describes local OCR; [python-docx document APIs](https://python-docx.readthedocs.io/en/latest/api/document.html) describe ordered paragraph/table iteration.

## Reproducible verification

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\python.exe scripts/build_phase3_fixtures.py
cd frontend
npm run build
```

The fixture script generates eight fictional documents: searchable PDF, two-column PDF, scanned PDF, mixed PDF, 11-page PDF, password-protected PDF, damaged PDF, and a DOCX with headers and merged/nested tables. The encrypted fixture's user password is `test-secret`, but the application intentionally requires an unlocked export rather than accepting passwords.

The real OCR tests skip only when English language data is unavailable; they were run with language data in this session. Tests check content preservation, section recognition, API errors, limits, corrected-text preparation, and timeout behavior. These are parser/integration checks, not NLP accuracy measurements.

## Completed verification

- 33 backend tests passed, including both real OCR tests; no tests skipped.
- TypeScript validation and the production frontend build passed.
- Desktop browser flow extracted the actual example PDF and displayed its text and sections.
- Browser preparation accepted edited text without another upload; subsequent editing cleared review confirmation and disabled preparation.
- At 390px mobile width, the preview had no horizontal overflow and remained usable.
- A scanned fixture produced actual OCR text with Python, SQL, Flask, C++, C#, and Education preserved; the preview displayed the OCR review warning.
- Password-protected PDF submission displayed an unlocked-copy instruction.
- No browser runtime errors or Vite error overlays were recorded.
