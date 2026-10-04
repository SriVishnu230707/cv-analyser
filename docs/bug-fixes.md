# Matching and request-error fixes

This review found and corrected the following reproducible issues:

- An action in another sentence or clause could turn an unrelated skill mention into demonstrated evidence. For example, `Built JavaScript applications. Python.` now leaves Python as a mention requiring review instead of automatically scoring it.
- Responsibility rules could combine an action, object, and tools from separate clauses. `Built REST APIs. Java.` no longer automatically satisfies `Build REST APIs using Java.`
- Learning wording after a skill, such as `Python (learning)`, was credited as a listed skill. It now receives no automatic or confirmable positive credit.
- Degree checks used substring matching, so `Masterclass in computer science` or an unfinished master's degree could satisfy a master's requirement. Checks now use whole words, recognize grammatical variants of the same degree type, and reject explicit unfinished wording.
- Comparison and export requests tried to parse HTML proxy failures as JSON. Shared request handling now preserves useful API errors, supplies readable fallback errors, and combines caller cancellation with the request timeout.

Verification: 97 backend tests, 4 frontend request-handling tests, and the production frontend build passed. Browser checks covered extraction, requirement review, comparison, simulated HTML failures for comparison and export, and a successful JSON download after retry. The browser reported no uncaught errors.

```powershell
python -m pytest backend/tests -q
cd frontend
npm test
npm run build
```

Scoring weights are unchanged. Automatic coverage may decrease where an old rule incorrectly credited unrelated or learning evidence; users can review eligible positive mentions explicitly.

## Phase 8 follow-up review

Responsibility rules previously treated different objects within a task family as interchangeable. Monitoring metrics could automatically satisfy monitoring logs or service health; build/deployment/CI/CD pipelines and data/ETL pipelines had the same issue. Rule version **1.1.1** now distinguishes these targets, supports singular/plural pipeline wording, and sends multi-target or mismatched cases through evidence review. JSON exports use the same corrected matching results. Taxonomy version remains 1.1.0.

A successful but malformed `/api/skills` response, such as `{"version":"bad","skills":null}`, could crash the page. The dictionary and comparison mapping controls now share runtime validation of catalog entries and aliases. Invalid data produces a readable error and the dictionary can retry without losing the page.

Follow-up validation: **129 backend tests**, **7 frontend tests**, and the production build passed. Browser checks verified malformed-dictionary recovery and the corrected monitoring requirement workflow.

## Phase 9 follow-up review

- Malformed OpenAI output items or message content could raise an unhandled exception. Explicit envelope/content validation now returns `ai_invalid_response` rather than an internal error. Invalid, zero, boolean, and non-finite embedding vectors also fail cleanly; large finite vectors use stable cosine arithmetic.
- The substring rewrite guard accepted a fragment such as `50 logs.` from `Monitored 150 logs.`, or a fragment that removed a teammate's subject. Only complete source sentences are now accepted. Metrics and subjects cannot be clipped by selecting part of a sentence.
- Successful but malformed comparison/AI responses could replace the visible report with invalid data or crash rendering. The frontend now validates the shared report schema with Ajv before updating state, checks AI metadata/context and the current input hash, and keeps the previous report on failure. AI metadata is explicitly defined in the shared contract.

Validation: **156 backend tests**, **10 frontend tests**, and the production build passed. Browser fault injection confirmed that malformed AI and local-comparison responses show errors, preserve the original report, and allow a successful local retry without uncaught browser errors. Provider tests remain controlled; no live OpenAI generation was performed.

## Phase 10 reliability review

- Extraction, preparation, requirement review, and example loading previously trusted successful response bodies. Malformed nested data could crash rendering or replace usable state. The frontend now validates the existing extraction/profile contracts, checks returned profile inputs against the current normalized text and job, and validates the synthetic example before updating form state. Errors remain visible and can be retried. Real API fixtures cover schema compatibility and legitimate text normalization.
- Learning and negated action wording no longer passes the contribution editing check. It uses the existing positive-action policy and does not affect job-match scores.
- Extremely large integer embedding components now return a controlled invalid-provider error. Boolean embedding indices are rejected rather than accepted as integer indices.
- API health and frontend/backend version metadata now consistently identify Phase 10 / version 0.10.0.

Validation: **166 backend tests**, **15 frontend tests**, and the production build passed. Browser fault injection verified malformed extraction, preparation, and requirement-review responses show controlled errors, preserve usable state, and allow retries through a valid comparison at 57.5%, without uncaught browser errors. No live OpenAI calls were made. Passing these checks does not establish universal accuracy or prove the absence of all bugs.

## Qualification and release verification review

Degree matching could combine a bachelor's computer-science subject with a master's literature credential on the same line. Degree type and subject must now refer to one credential in one clause; mixed credentials do not receive automatic credit. A completed degree can still match when an unrelated incomplete credential appears in a separate clause.

Pydantic's literal-true handling accepted numeric `1` as confirmation. Requirement confirmation and cloud consent now require the actual JSON boolean `true`. Invalid confirmations fail before provider calls.

Added a GitHub Actions workflow for backend/frontend tests, the synthetic skill evaluation, and the production build. Added `scripts/verify_live_ai.py` for explicit synthetic live verification through a local backend, including signed-context JSON/PDF exports and unchanged scores before semantic confirmation. No paid call runs without `--run-live`; missing configuration is never reported as a pass.

Validation: **188 backend tests passed**. The verification command reported the current missing-key limitation without making a cloud call. Its complete flow passed with the controlled provider in regression tests. Frontend source is unchanged from the previous passing 15-test/build/browser verification. The new hosted CI workflow has not yet been verified on GitHub.
