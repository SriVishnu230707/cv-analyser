# Phase 10: broader matching and resume improvement

The application covers the original workflow: extract and review PDF/DOCX resumes, recognize skills with NLP, compare reviewed job requirements, generate explainable estimated ATS alignment scores, show missing evidence, and provide local or optional OpenAI improvement advice.

## Changes

- Dictionary version 1.2.0 supports 128 canonical skills, up from 71. It adds mobile, analytics, ML, design, security, operations, and business tools. Exact aliases retain source offsets; learning, negated, and embedded near-matches retain the existing credit restrictions. Related tools are separate skills.
- Resume quality checks now identify contact email, recognizable headings, experience/project examples, action wording, and descriptions longer than 45 words. Review findings include concrete editing instructions. Entry-level projects satisfy the example check. These text checks do not evaluate proficiency, original visual layout, or affect job coverage scores. Contact values are not repeated in the check output.
- UI, JSON, and PDF reports include the same editing checks. The shared schema validates the optional `resume_quality` object before the UI updates.
- Twelve synthetic regression cases cover six job families, with positive, learning, negated, and near-match wording. Run `python scripts/evaluate_alignment.py` for reproducible per-case precision/recall results. This dataset is authored and is not a held-out real-world accuracy benchmark.

## Remaining verification

Validation passed: 161 backend tests, 10 frontend tests, and the frontend production build. The cross-role set reported 25 true positives, zero false positives, and zero false negatives across 36 skill decisions. Browser verification covered extraction, review, comparison, and the new quality findings while preserving the sample's 57.5% coverage score. The PDF quality-check page was rendered and visually inspected; JSON/PDF export regressions passed. No live OpenAI calls were made.

Configure `OPENAI_API_KEY` privately in the backend `.env`, restart the API, and run the explicit AI analysis action with a synthetic resume to verify account/model access. Existing controlled-provider tests cover response validation, grounding, context integrity, and semantic confirmation. Live OpenAI calls and broader independently labeled accuracy evaluation remain unverified. The app's ATS alignment estimate is not an employer's proprietary score.
