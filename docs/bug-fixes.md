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
