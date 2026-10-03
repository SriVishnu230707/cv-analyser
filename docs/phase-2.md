# Phase 2: application foundation

Historical Phase 2 record. The current application implements real extraction and review; see `docs/phase-3.md` for current behavior and setup.

React + TypeScript + Vite frontend, FastAPI backend, and the Phase 1 sample report connected through a real multipart request.

## Implemented

- Resume file picker, replacement/removal, and job-description field.
- Client and server checks for extension, empty file, 5 MiB size, and trimmed 100–20,000-character job description.
- Initial content checks: PDF signature; DOCX ZIP structure. These do not establish complete document validity.
- `GET /health`, `GET /api/demo/job`, `GET /api/demo/resume`, and `POST /api/analyze`.
- Loading/disabled states, timeout handling, clear error envelopes, accessible labels and status announcements.
- Fixed example scores, components, evidence, gaps, qualification review, and suggestions.
- In-memory bounded reads; uploaded file handles close after each request. No application-level upload storage, database, document logs, external AI API, or credentials.
- Vite same-origin API proxy for local development and preview; no broad CORS policy needed.

## Intentionally deferred

Phase 3 implements real PDF/DOCX extraction, encrypted/corrupt document handling, page-count limits, text preview/correction, and OCR. Phase 4–6 implement personalized extraction, matching, scoring, and suggestions. Phase 2 accepts valid-looking files and returns the same fixed report, regardless of submitted content. Both the UI and API docs disclose this; response header `X-Analysis-Mode: demo` makes it machine-readable.

The upload byte limit applies after multipart parsing; a production deployment must also enforce request limits at its ingress before parsing. This local demo is not production deployment.

## Run locally

Prerequisites: Python 3.10+ and Node.js 20.19+ or 22.12+ (Vite 7). From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173. Click **Load example**, then **View sample analysis**. Alternatively, upload a PDF/DOCX and paste a job description. Open http://127.0.0.1:8000/docs for interactive API documentation.

If port 8000 is already occupied, run the API with `--port 8001` and set `$env:BACKEND_URL = 'http://127.0.0.1:8001'` in the frontend terminal before `npm run dev`. This session uses port 8001 for the API because another local service already uses 8000.

The Codex session has installed Python dependencies in `.tools/backend`. On this computer, the bundled Python can run `scripts/run_backend.py --port 8001`; on other computers use the virtual-environment commands above. The runner supports both setups.

## Checks

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
cd frontend
npm run build
```

API design follows [FastAPI multipart form/file documentation](https://fastapi.tiangolo.com/tutorial/request-forms-and-files/). Local proxy configuration follows [Vite server documentation](https://vite.dev/config/server-options).

## Verification completed

- 13 API tests passed, including schema equality, valid PDF/DOCX structure, missing inputs, invalid files, oversized files, and job-description bounds.
- TypeScript checks and the Vite production build passed.
- Browser verified at desktop size and 390px mobile width: meaningful page content, no Vite overlay, no recorded runtime errors, and no horizontal overflow.
- Example loading and real multipart submission rendered the fixed 60.5 report with four evidence entries. Expanding an entry revealed the supporting resume text.
- Unsupported-file selection displayed a client validation message. Uploading a text file renamed to PDF displayed the API validation message in the form.
- React review covered stable list keys, typed props/state, accessible labels/status/error feedback, async handling, and concurrent independent example requests.

These checks establish Phase 2 integration only. They do not evaluate NLP or PDF/DOCX extraction, which are not implemented yet.
