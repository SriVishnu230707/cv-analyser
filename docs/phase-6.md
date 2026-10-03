# Phase 6: factual resume improvement suggestions

Phase 6 adds a prioritized improvement plan to the real comparison report. Phase 5 was implemented first in a separate commit. Everything runs locally, with no cloud model, API key, or saved resume history.

## Workflow

Upload a PDF/DOCX or load the example, extract and review the text, extract skills and job requirements, resolve unclear categories, then confirm them. Click **Compare with this role**. The report contains scores, evidence, qualifications, readability findings, and **Your improvement plan**.

Filter advice by priority. Job-related suggestions name the affected requirements and expose source evidence where available. Review any suggested rewrite and copy it manually; it never modifies your resume automatically. Editing text or requirement categories clears the report. Review and compare again to refresh advice.

## Policy

- Missing required skills: high-priority, conditional advice to add an example only if the skill was actually used.
- Missing preferred skills: medium-priority conditional advice.
- Learning mentions: keep the learning label; do not claim proficiency from study alone.
- Listed skills: describe a truthful project/work example if applicable. Better wording may not raise the score because listed skills already earn coverage credit.
- Possible responsibility evidence: review the excerpt before treating it as documented evidence.
- Responsibility gaps: add your actual contribution and outcome only if you performed the task; never invent metrics.
- Qualifications: check exact credential/experience requirements. Mandatory findings take high priority; equivalence is not inferred.
- Readability issues: correct omissions and reading order before relying on the result.
- User-confirmed matches: clarify the connection and distinguish individual from team contributions.

The deterministic suggestion engine is `backend/services/suggestion_engine.py`. It uses current findings and evidence, rather than generating new experience. Scores are unchanged by the advice itself.

Optional rewrites are narrow: `I built REST APIs using Python, supporting 12 endpoints.` can become `Built REST APIs using Python, supporting 12 endpoints.` Only the first-person prefix is removed and the first letter capitalized. Tools, metrics, and remaining wording are preserved verbatim. Team statements beginning `We` are not turned into personal claims. Missing evidence never produces a fabricated rewrite. Broader AI rewrites are deferred until source facts can be validated.

Embedded document instructions remain ordinary text. No external model executes them. A gap means **not evidenced in this resume**, not that the candidate lacks a skill. Suggestions do not guarantee a score increase or hiring result.

## API

`POST /api/compare` returns the v1.1 report with populated `suggestions`: stable ID, kind, priority, relevant requirement IDs, rationale, action, nullable evidence, and nullable rewrite. IDs are tied to current inputs. Evidence decisions recalculate both matching and advice. The strict contract is `contracts/analysis-result-v1.1.schema.json`; the Phase 1 v1.0 schema remains unchanged.

There is no endpoint that trusts client-supplied gaps or scores. The server rebuilds requirements and findings first. Responses use `Cache-Control: no-store`.

## Setup and verification

Use [Phase 4 setup](phase-4.md) and [Phase 5 comparison notes](phase-5.md). API port: 8001. Frontend port: 5173. Start Vite with `BACKEND_URL=http://127.0.0.1:8001`.

```powershell
python -m pytest backend/tests -q
cd frontend
npm run build
```

Phase 6 regressions cover conditional advice, learning labels, priority ordering, evidence review, verbatim rewrites/metrics, team credit, stable IDs, edits, embedded instructions, qualification/readability advice, empty plans, and schema/API validation. Advice tests do not use reserved matching evaluation cases.

Limits: dictionary/rule coverage is bounded; advanced qualification equivalence and compound responsibility matches need review. Suggestions are rule-based, not a trained language model. No automatic resume editing, saved history, or export is included.

Verified in this workspace: 72 backend tests passed and the frontend production build passed. Browser checks passed for example comparison (57.5), six source-grounded suggestions, high-priority filtering, clearing results after edits, preserving and copying an existing 12-endpoint metric, and mobile layout without horizontal overflow. No browser errors were reported.
