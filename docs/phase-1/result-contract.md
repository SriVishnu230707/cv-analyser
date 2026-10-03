# Analysis result contract

The canonical output shape is `contracts/analysis-result.schema.json` (JSON Schema Draft 2020-12). Schema version starts at `1.0.0`. Phase 2 can return the sample report unchanged.

## Evidence semantics

Each match references a requirement ID and an exact resume excerpt. `listed` means the candidate lists a skill; `demonstrated` means an experience/project describes its use. Neither proves proficiency. `possible` semantic evidence is shown for review and earns no points until confirmed. Explicitly negated mentions earn no points.

Exact or canonical-alias listed skills count toward skill coverage in this initial policy, but the interface must distinguish them from demonstrated use. Responsibility alignment requires demonstrated evidence. Skill repetition never increases coverage. Related technologies are not automatic aliases.

Mandatory qualifications have `met`, `not_evidenced`, or `uncertain` status, with supporting text when available. They remain independent of the numeric score. Do not infer qualifications from personal characteristics.

## Proposed scoring, not a validated ATS standard

- Required skills: base weight 0.60.
- Preferred skills: base weight 0.15.
- Responsibilities: base weight 0.25.
- Component score = 100 × matched requirement weight / total applicable requirement weight.
- A confirmed requirement is counted once. A component with no requirements has score `null` and effective weight zero.
- Normalize remaining base weights to sum to one. If no components apply, return `insufficient_requirements`, a null overall score, and all effective weights zero.
- Keep full precision during calculations; round component display and final score to one decimal place.
- `scores.overall` is the weighted job match. Readability never contributes to it.

Example: required coverage 80, preferred coverage 0, responsibility coverage 50 gives `0.60 × 80 + 0.15 × 0 + 0.25 × 50 = 60.5`.

## Readability and errors

Phase 1 specifies readability findings, not an arbitrary numeric readability formula. `not_assessed` is appropriate for plain-text synthetic examples. Later parsing reports `readable`, `needs_review`, or `failed` with specific issues. Failed extraction returns `extraction_failed` with null job score and no matches, rather than inventing gaps from unreadable input.

## Suggestions

Each suggestion has priority, relevant requirement IDs, rationale, and a concrete action. An optional rewrite may only use documented facts. Advice for absent skills must be conditional: “If you have used Docker, add a specific example.” No automatic addition of missing skills.

## API planned for Phase 2

`POST /api/analyze`: multipart `resume` file and `job_description` text. Successful analysis returns this contract. Invalid upload/input uses an HTTP 4xx error envelope (`code`, `message`, `field`); unexpected processing failures use a generic message without document content. The editable-text rerun interface will be finalized in Phase 2.
