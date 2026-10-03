# Synthetic evaluation fixtures

24 fictional resume–job pairs: 18 development cases and 6 reserved evaluation cases. `manifest.json` records each split and scenario. Each case contains `resume.txt`, `job-description.txt`, and `labels.json` with explicit requirement sources, match evidence, gaps, and reference component scores.

There are three roles (backend, frontend, full-stack) and eight scenarios per role: full coverage, partial coverage, listed-only skills, aliases, negated mentions, unrelated experience, required-only coverage, and sparse relevant experience. The last two scenarios for each role are reserved for evaluation.

These are authored synthetic labels, not annotations by independent human reviewers. Reference scores use the proposed Phase 1 policy. Shared templates across splits make this a sanity-check set, not an unbiased benchmark. Add independently written held-out examples before claiming accuracy or selecting semantic thresholds.

The fixtures are text-level examples. They do not test PDF/DOCX formatting, OCR, extraction order, malware handling, or proficiency. No real personal information is used.

`sample-report.json` is a fully populated report for `backend-02` and illustrates evidence, gaps, mandatory qualification status, and factual suggestions.
