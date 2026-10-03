# Phase 5: comparison implementation

The reviewed profile can now be compared through `POST /api/compare`. See [the design](phase-5-design.md) for the policy. Phase 4 upload/text review/category review remains available. After confirming categories, click **Compare with this role**.

Implemented: canonical exact/alias skill matching; conservative action/object responsibility rules; possible-evidence confirmation/rejection; equal-weight coverage and component normalization; qualification findings; signed extraction context; stale-decision rejection; unknown-skill mapping; report cards, filters, and desktop/mobile evidence views.

Each scored requirement defaults to one point. Required, preferred, and responsibility components have base weights 60%, 15%, and 25%. Missing components redistribute their weight. No assessable components means no score. The example is 57.5 with equal weights. Unknown/informational and qualification rows remain visible in the count and are not scored.

Qualification matching is deliberately narrow: explicit degree type and supported field can match Education wording; equivalence, certifications, and years of experience require review. Responsibility rules support one complete action/object family; compound or unsupported tasks require user confirmation. This is local deterministic matching, not an embedding model. User confirmation records interpretation, not independent verification.

The new strict contract is `contracts/analysis-result-v1.1.schema.json`; Phase 1 fixtures and their v1.0 schema remain unchanged. `/api/compare` requires current text, the complete category-correction set, `requirements_confirmed: true`, optional canonical mappings, and optional evidence decisions. Decisions reference backend-generated evidence IDs tied to both texts and excerpt offsets. Editing input invalidates them. Readability context arrives through the extraction response's `X-Extraction-Context` header, is signed for one hour, and is invalidated by an API restart. Missing context reports `not_assessed`. Edited text adds a review warning.

Setup follows Phase 4 with the same dependencies. Run `python -m pytest backend/tests -q`, `npm run build` in `frontend`, and `python scripts/evaluate_phase5.py --split evaluation` after freezing rules. Evaluation measures automatic skills separately from responsibility review and reports raw counts; it does not read labels during runtime analysis. Suggestions are empty in the Phase 5 commit and added by Phase 6.

Verification: 64 backend tests and the frontend build passed. The browser example produced 57.5. Frozen rules on the six reserved synthetic cases yielded 15 true positives, 0 false positives, and 0 false negatives for automatic skill matching (precision 15/15, recall 15/15). This small authored dataset does not establish real-world accuracy or responsibility-match accuracy.
