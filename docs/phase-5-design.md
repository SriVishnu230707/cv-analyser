# Phase 5 design: evidence matching and explainable scores

Status: design only. Phase 4 remains the running application. Implement the milestones below as a separate Phase 5 change.

## Outcome and scope

A candidate confirms the extracted job requirements, compares them with their reviewed resume, and receives an estimated job-match score with a requirement-by-requirement explanation. The report separates documented skills, demonstrated use, unconfirmed evidence, and requirements not evidenced in the resume.

Included: canonical skill matching, conservative responsibility matching, evidence review, explicit gaps, three score components, separate qualification findings, extraction warnings, and reruns after text edits.

Deferred to Phase 6: personalized improvement suggestions, generated rewrites, and optional semantic matching with embeddings. Accounts, saved history, export, recruiter ranking, and cloud model calls remain outside this phase. Return an empty suggestions array until suggestions are implemented.

## Candidate workflow and report layout

1. Complete the existing upload, text review, and requirement-category review.
2. Click **Compare with this role**. Block comparison while requirement categories are unresolved. Offer a useful explanation when there are no scored requirements.
3. Show **Estimated job match**, followed by required-skill coverage, preferred-skill coverage, and responsibility alignment. Each component shows matched weight, total weight, and its effective contribution.
4. Show a requirements table with category, requirement, outcome, and expandable verbatim evidence. Provide filters for All, Evidenced, Needs review, and Not evidenced.
5. Show unconfirmed responsibility candidates in a review panel. The candidate can accept a specific excerpt or reject it. Accepting evidence recalculates the report; label those matches as user-confirmed.
6. Show mandatory qualifications and experience requirements separately. They do not change the score.
7. Keep extraction/readability warnings visible. Editing either input clears the report and its evidence confirmations; reclassifying requirements also clears the report.

Desktop: a summary row, three component cards, a wide evidence table, then qualification and readability panels. Mobile: stack the cards and render requirement rows as expandable cards. Use textual outcome labels alongside colors. Loading, errors, empty results, and review states must be accessible without relying on color or hover.

Use **Not evidenced in this resume**, rather than claiming the candidate lacks a skill. Present the score as an application estimate, not an employer ATS result or hiring probability. A confirmed report can still contain missing requirements and uncertain qualifications.

## Matching policy

### Skills

Match only the same canonical skill in the reviewed requirement and resume profile. Approved aliases count; related technologies do not. Java and JavaScript, Angular and AngularJS, and SQL and PostgreSQL remain distinct.

| Resume evidence | Skill outcome | Score credit |
|---|---|---|
| Positive listed evidence | Listed | Full requirement weight |
| Positive demonstrated use | Demonstrated | Full requirement weight |
| Positive mention outside Skills/Projects/Experience | Needs review | None until accepted as relevant evidence |
| Learning or negated mention only | Not evidenced | None |
| No canonical mention | Not evidenced | None |

Choose demonstrated evidence before listed evidence. Keep other excerpts available for inspection. Repeated keywords or additional excerpts never add points. Learning and negated excerpts can be shown as context but cannot be accepted for score credit. A skill with both negated and positive excerpts uses its positive evidence and displays the conflicting context for review.

User classification alone does not make an unknown requirement matchable. A requirement changed to a skill category must resolve to one canonical dictionary skill; otherwise require dictionary mapping or exclude it before scoring. Do not silently drop an unknown skill from the denominator. Mapping support can initially be a canonical-skill selector; creating new dictionary entries is deferred.

### Responsibilities

Use a small, versioned set of action/object rules, not a whole-document similarity percentage. Initial rule families can cover building APIs, querying data, packaging/deploying services, testing, and developing user interfaces.

Automatic credit requires a positive Projects/Experience excerpt with a supported action and matching task/object. Normalize only explicitly approved action variants, such as build/built and query/queried. Technology overlap alone is insufficient: listing React does not demonstrate building an interface, and using Docker does not prove managing production deployments.

When an excerpt is related but does not satisfy a complete rule, present it as **Possible evidence** and give no credit. Unsupported responsibility wording produces no automatic match. Allow the candidate to select a positive Projects/Experience excerpt and confirm its relevance. Preserve that excerpt and mark the result user-confirmed. This records the candidate's interpretation; it does not verify the claim independently.

No embeddings are needed for the initial Phase 5 release. Later semantic models can propose evidence, but must use this same review gate unless independently validated for automatic credit.

### Qualifications and experience

Keep these outside the numeric score:

- An explicit mandatory qualification gets met, not_evidenced, or uncertain with a reason and supporting excerpt when available.
- Automatically mark met only for supported, explicit degree/certification wording in Education/Certifications. Degree-equivalence clauses require review. Do not infer equivalence from a project or job title.
- Years-of-experience requirements are displayed separately. Do not add overlapping job durations or infer years from graduation dates in this phase; use uncertain unless an explicit relevant duration can be established.
- Optional qualifications remain visible as informational findings. Unknown qualification wording stays uncertain.

## Scoring policy

Keep the Phase 1 component weights:

| Component | Base weight |
|---|---:|
| Required skills | 0.60 |
| Preferred skills | 0.15 |
| Responsibilities | 0.25 |

Within each component, every unique requirement defaults to weight 1. Phase 4 weights are provisional; validate and rebuild them on the backend. Custom importance weights are deferred. Qualifications, experience requirements, excluded rows, and informational rows have weight 0.

For each component:

```text
coverage = 100 × credited_requirement_weight / applicable_requirement_weight
effective_weight = base_weight / sum(base_weights_of_applicable_components)
overall = sum(unrounded_coverage × effective_weight)
```

Credit each requirement once. A component with no requirements has score null and effective weight 0. If none apply, return insufficient_requirements with overall null. A failed extraction is not a zero score. Keep full precision until display rounding to one decimal place. Readability never contributes points.

Example with equal requirement weights: three of four required skills, zero of two preferred skills, and one of two responsibilities gives `0.60 × 75 + 0.15 × 0 + 0.25 × 50 = 57.5`. The Phase 1 illustrative 60.5 report uses unequal authored requirement weights; it is not the expected score for this default equal-weight policy. Tests of the generic score calculator may use those explicit weights to verify the original 60.5 arithmetic, without loading labels into the runtime matcher.

Duplicate canonical skills in the same category merge their source excerpts. If a skill remains both required and preferred, block scoring until the category conflict is resolved. Deduplicate responsibility statements after conservative whitespace/case normalization; avoid automatically merging different tasks through fuzzy similarity.

Other requirements must be explicitly resolved, mapped, or acknowledged as informational before comparison. Show the number of informational/excluded requirements beside the score so omission is visible. A role with only those requirements receives insufficient_requirements.

## Backend architecture

Reuse Phase 4 section parsing, skill extraction, and validated category corrections. Add separate services:

| File | Responsibility |
|---|---|
| `backend/services/evidence_matcher.py` | Canonical skill matches, evidence eligibility, deterministic responsibility rules, possible evidence |
| `backend/services/qualification_matcher.py` | Conservative qualification/experience findings |
| `backend/services/scoring.py` | Pure weighted coverage calculation and component normalization |
| `backend/services/analysis_service.py` | Recompute profile, validate review, deduplicate requirements, assemble report |
| `backend/data/responsibility_rules.json` | Versioned actions, objects, and rule descriptions |
| `backend/tests/test_phase5.py` | Matcher, scoring, review, and report regressions |
| `scripts/evaluate_phase5.py` | Split-aware evaluation with explicit counts and metrics |

Keep `/api/extract`, `/api/preview`, and `/api/requirements/review` working. Add `POST /api/compare` for JSON input rather than changing the existing legacy multipart `/api/analyze` behavior.

Proposed request fields:

```text
resume_text
job_description
category_corrections: [{requirement_id, category}]
skill_mappings: [{requirement_id, canonical_skill}]
requirements_confirmed: true
evidence_decisions: [{requirement_id, evidence_id, decision: accept | reject}]
extraction_context: signed token, if available
```

Recompute all extracted requirements and evidence from current text on every request. Require a full, unique category-correction list for the current extracted requirement set before scoring; validate all mappings. Never accept client-calculated scores, weights, positive-match flags, or free-form excerpts as authoritative data.

Evidence IDs hash the current resume text, current job description, requirement ID, section, and exact excerpt offsets. Accept decisions only for eligible evidence rebuilt from those inputs. An edit therefore invalidates previous evidence decisions. Stable Phase 4 requirement IDs alone cannot detect changes to source wording.

For readability, issue a short-lived backend-signed extraction-context token from `/api/extract` containing the original text hash and extraction findings, without document contents. Keep the signing key on the server. `/api/compare` validates this context and marks text as edited when its hash differs. If context is absent, return readability not_assessed; never manufacture readable status or treat browser-supplied findings as verified. Tokens and resumes need no database. Restarting a local process may invalidate outstanding context tokens; re-extraction restores them.

Errors retain the existing `{code, message, field}` envelope. Examples: review_required, invalid_evidence_decision, stale_review, invalid_skill_mapping. Comparison responses use `Cache-Control: no-store`; no document contents are logged.

## Report contract changes

Design a new `analysis-result-v1.1.schema.json`; leave the Phase 1 schema and fixtures unchanged. The old strict schema cannot represent all Phase 4 categories, explicit match review, or rule-based methods accurately.

The new schema should retain sections, requirements, matches, gaps, qualifications, scores, readability, suggestions, and warnings, and add:

- schema_version 1.1.0 and scoring_policy_version equal-weight-v1.
- taxonomy/rule versions and a hash of the analyzed text pair.
- All reviewed Phase 4 requirement categories, canonical skill mappings, and included_in_score flags.
- Explicit possible-evidence entries and review decisions, separate from credited matches.
- Match methods exact, alias, rule, and user_confirmed. Do not call a rule match semantic.
- Evidence IDs, exact excerpt offsets, section names, and eligibility information.
- Component credited/total weights and counts, in addition to scores/base/effective weights.
- Informational qualification/experience findings and the count of excluded/informational requirements.

Validate report cross-references and calculations in service tests as well as JSON Schema. A confirmed match must reference a current requirement and an eligible verbatim excerpt. No component may score above 100. All credited matches must be traceable. A report with outstanding possible evidence remains usable, but receives no points for that evidence and visibly identifies pending review.

## Implementation milestones

| Order | Deliverable | Completion check |
|---|---|---|
| 5.1 | Finalize v1.1 contract, default weights, mapping and review gates | Sample reports for complete, pending review, and insufficient requirements validate |
| 5.2 | Build skill matcher and conservative responsibility/qualification rules | Independent positive, negative, alias, learning, and responsibility tests pass |
| 5.3 | Implement scoring and `/api/compare` | Formula, normalization, duplicate handling, invalid decisions, and stale edits pass API tests |
| 5.4 | Build report cards, evidence table, and review interaction | Full browser flow passes; edits clear results; mobile fits; errors recover |
| 5.5 | Freeze rules and evaluate the held-out split | Record precision/recall with numerator/denominator, limitations, and rule version |

Commit the completed Phase 5 implementation separately from this design. Keep matching, API, UI, and evaluation changes reviewable within that phase.

## Acceptance and evaluation

- Exact/alias positive skill evidence earns credit; learning and negated mentions do not.
- Repeated resume keywords and duplicate job requirements cannot inflate the score.
- Responsibility credit requires eligible action/object evidence or explicit user confirmation. Possible evidence never earns automatic points.
- Unresolved categories/mappings block comparison; edited inputs reject stale evidence decisions.
- The score arithmetic, missing-component normalization, and null-score behavior follow the formulas above. Scores depend only on documented requirements and evidence, never personal attributes.
- Every positive match has a verbatim excerpt and section. Qualifications/readability are independent of the score. Unknown qualification equivalence remains visible.
- Backend schema/API tests, existing extraction/OCR tests, frontend production build, and desktop/mobile browser verification pass.
- Develop rules on the 18 development cases plus independently authored regressions. Freeze them before running the six reserved cases. Do not load authored labels or reference matches into runtime analysis.
- Measure automatic skill-match precision/recall against the Phase 1 targets (90%/85%), reporting raw counts and the small dataset limitation. Evaluate responsibility proposals separately; do not blend user-confirmed decisions into automatic accuracy. Record any mismatch caused by the deliberate equal-weight policy separately from matcher errors.
- If held-out failures motivate rule changes, report those cases as development evidence and create a fresh held-out set before claiming a new evaluation result.

Phase 5 is complete when the user can compare current, reviewed inputs, explain every credited point, inspect missing evidence, and rerun safely after edits. Phase 6 then adds factual suggestions based on these findings.
