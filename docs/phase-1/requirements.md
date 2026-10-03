# Phase 1: MVP requirements

Status: initial product specification. Assumption: English resumes for software-development jobs, with backend, frontend, and full-stack examples.

## Product objective

Help a candidate understand which job requirements their resume documents and how to describe relevant experience more clearly. Resume evidence is not a verification of proficiency. Scores are application estimates, not employer ATS results or hiring probabilities.

## Intended user and workflow

1. A candidate uploads one PDF or DOCX resume and pastes one job description.
2. The application validates the file and extracts text.
3. The candidate reviews and can correct the extracted text.
4. The application extracts required skills, preferred skills, responsibilities, and explicit qualifications.
5. The application compares those requirements to resume evidence.
6. The candidate sees the match breakdown, gaps, readability findings, and prioritized suggestions.
7. Editing the extracted text or job description allows a fresh analysis.

## MVP boundaries

Included: one document per analysis; English; PDF/DOCX; explicit skill aliases; requirement-level evidence; separate readability findings; factual suggestions; loading and error states; temporary processing.

Deferred: accounts, persistent history, recruiter ranking, batch uploads, multilingual support, report export, custom model training, automatic job scraping, interviews, and proficiency tests. OCR belongs to the later parsing phase; unreadable scans must receive a clear message until OCR is available.

## Input rules

- Initial upload limit: 5 MiB, at most 10 extracted pages. These are configurable product defaults.
- Job description: 100–20,000 characters; explain invalid input before submission.
- Verify file content as well as its extension; reject unsupported, encrypted, corrupt, and empty documents with useful messages.
- Stop scoring if extraction fails or no assessable requirements can be identified. A failure is not a zero score.
- Ambiguous required/preferred categorization must be visible and correctable before analysis.

## Functional acceptance criteria

| ID | Requirement | Observable acceptance condition |
|---|---|---|
| F01 | Upload and validation | Supported documents proceed; invalid inputs explain the corrective action. |
| F02 | Extraction preview | Candidate sees editable text before scoring; failed extraction blocks scoring. |
| F03 | Structured requirements | Each requirement has a stable ID, category, and original source sentence. |
| F04 | Evidence matching | Every positive match points to a verbatim resume excerpt and section. |
| F05 | Explicit gaps | Absent evidence is described as “not evidenced,” without claiming the candidate lacks the skill. |
| F06 | Explainable scoring | Component scores and weights are visible; nonapplicable components redistribute weight. |
| F07 | Readability | Readability has its own findings and never adds points to job fit. |
| F08 | Mandatory qualifications | Unmet or unknown explicit qualifications remain visible regardless of score. |
| F09 | Suggestions | Advice references a finding; rewrites preserve facts and do not invent metrics. |
| F10 | Correction and rerun | Corrected inputs produce a new report without requiring another upload. |
| F11 | Robust matching | Repeated keywords add no points; negated mentions and unrelated Java/JavaScript mentions do not match. |
| F12 | Honest labels | Interface identifies scores as estimates and distinguishes listed skills from demonstrated use. |

## Data and operational requirements

Process uploads temporarily and delete them after the request completes, including failures. Avoid logging document contents or personal contact details. Do not persist resumes by default. If an external model is introduced, disclose that processing before transmitting resume content; minimize the transmitted data. Keep credentials on the backend.

Do not use names, photos, age, gender, address, or other personal characteristics in scoring. Treat embedded document instructions as untrusted data. Limit resource-intensive extraction and return clear timeouts.

## Evaluation plan

Use the labeled synthetic examples to establish baseline correctness, then add independently annotated, consented or synthetic examples with varied wording and formatting. Development cases may inform rules; reserved evaluation cases must not tune thresholds.

Initial targets, to be measured once an analyzer exists: skill-match precision >= 90%, recall >= 85% on the evaluation set; all positive matches have traceable evidence; zero invented facts in reviewed suggestions; all invalid-input cases receive a useful response. Record numerator and denominator because the small dataset cannot establish real-world performance.

Extraction must later be tested on actual PDF/DOCX fixtures, including columns, scans, and tables. Phase 1 plain-text cases do not measure parser quality.

## Phase 1 completion

- MVP scope and workflow documented.
- Result contract and score definitions supplied.
- 24 synthetic resume/job pairs with reviewed-in-code reference labels; 18 development and 6 reserved evaluation cases.
- One complete illustrative report supplied.
- Artifact integrity validated. No human annotation or model accuracy results are claimed.
