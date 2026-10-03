# Phase 4: skill extraction and job requirements

Phase 4 converts reviewed resume text and a job description into a traceable structured profile. It does not compare the two documents or generate scores yet; matching and scoring are Phase 5.

## Workflow

1. Load the synthetic example or upload a PDF/DOCX and click **Extract resume text**.
2. Review and correct the extracted text. Add a job description of 100–20,000 characters and check the review checkbox.
3. Click **Extract skills & requirements**.
4. Expand resume skills to inspect their original wording and section. Expand requirement sources to inspect job-description excerpts and line numbers.
5. Change unclear or conflicting requirement categories. Choose **Confirm requirement categories**. Conflicts remain flagged until resolved; a duplicate can be excluded.
6. Editing the resume or job description clears the structured profile. Resume text edits also clear the text-review checkbox. Extract again to use the new wording.

Nothing is persisted to a database. Review corrections are applied to the current request's text, and unknown/duplicate requirement IDs are rejected. This phase adds no external AI calls or API keys.

## Extraction approach

`backend/data/skills.json` is a versioned, curated skill dictionary. spaCy's English tokenizer and [PhraseMatcher](https://spacy.io/api/phrasematcher) normalize approved aliases with case-insensitive token matching. No pretrained language model download is needed. This is deterministic NLP, not a trained proficiency classifier or semantic embedding model.

- Aliases such as `postgres`, `JS`, and `k8s` become PostgreSQL, JavaScript, and Kubernetes. Punctuation is preserved for C++, C#, and Node.js. Longer overlapping phrases win; Java does not match inside JavaScript. Angular and AngularJS remain distinct.
- Ambiguous everyday words are conservative: Go is recognized through `golang`/`Go programming`/`Go language`, and Express through `Express.js`/`expressjs`.
- Each resume skill includes exact source text, source-section name, matched wording, character offsets relative to that excerpt, assertion, and evidence level. Repeated mentions group under one canonical skill; identical evidence is deduplicated.
- Evidence is **listed** in a Skills section, **demonstrated** when a Projects/Experience line includes an action verb, or **mentioned** elsewhere. **Negated** and **learning** mentions remain visible separately. These labels describe wording, not verified proficiency, employment history, or skill level.
- Required/preferred markers and section headings classify job skills. Responsibilities, qualifications, mandatory qualifications, and years-of-experience statements remain separate categories. Qualification/experience weights are zero; other weights are provisional one. These weights do not calculate any score in this phase.
- Skills without explicit required/preferred wording need review. Sentences mixing both categories need review; semicolons scope separate clauses. Contradictory required/preferred mentions of the same skill are flagged. Negated skill requirements appear separately as excluded mentions.
- An explicit requirement with no dictionary match is retained as an **Other requirement** for review, rather than silently discarded. Benefit sections are ignored.

The dictionary and grammar are intentionally bounded. Unknown skills embedded beside known skills may not be recognized separately. Sarcasm, complex negation, advanced layout, multilingual content, and subtle qualification equivalence need human review. The parser does not infer a candidate's years of experience or degree equivalence. Source excerpts and editable categories make these limitations reviewable.

To extend skill coverage, add canonical names and unambiguous aliases to the JSON dictionary, bump its version, and add independent extraction tests. Do not tune against the six reserved evaluation cases in the Phase 1 dataset.

## API

| Route | Input | Output |
|---|---|---|
| `POST /api/preview` | `resume_text`, `job_description` | Reviewed text/sections, canonical resume skills, job requirements, excluded mentions, review state, warnings |
| `POST /api/requirements/review` | Same text plus `corrections: [{requirement_id, category}]` | Recomputed profile with validated user categories and unresolved conflicts |
| `GET /health` | None | Phase 4, OCR availability, `analysis_mode: not_available` |

The profile contract is [`contracts/structured-profile.schema.json`](../contracts/structured-profile.schema.json). `review_status` is `needs_review`, `not_confirmed`, or `confirmed`. `analysis_available` remains false even after confirmation. Each preparation has a new UUID; category corrections reference stable extracted requirement IDs. Successful profile responses carry `Cache-Control: no-store`. Errors use the existing `{code, message, field}` envelope and status 422 for invalid review input.

## Setup

Use Python 3.11+ and the frontend prerequisites in [Phase 2](phase-2.md). Stop the API before upgrading native dependencies on Windows. Install the updated backend requirements, including spaCy:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe scripts/run_backend.py --port 8001
```

For local English PDF OCR, follow [Phase 3](phase-3.md) and run `scripts/setup_ocr.ps1` if the language data is not already installed. No spaCy model installation command is required.

In another terminal:

```powershell
cd frontend
npm install
$env:BACKEND_URL = 'http://127.0.0.1:8001'
npm run dev
```

Open http://127.0.0.1:5173. The Codex workspace runner also discovers ignored dependencies under `.tools/backend` and `.tools/nlp`; a normal virtual environment uses its own installed packages.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
cd frontend
npm run build
```

Verified in this workspace: **51 backend tests passed** and the frontend production build passed. Tests cover aliases and boundaries, source offsets, deduplication, negation/learning, headings and ambiguity, unknown requirements, conflicts, category correction validation, edited text, the profile JSON schema, and the previous document/OCR regressions. Required/preferred skill categories match authored labels across all 18 development cases. The six reserved evaluation cases were not used for Phase 4 tuning or assertions.

Browser verification passed for example loading, PDF extraction, text review, skill evidence expansion, unclear-category correction, requirement confirmation, and invalidation after editing. Desktop and 390px mobile layouts were inspected; the mobile view had no horizontal overflow and no browser errors were reported.
