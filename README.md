# CV Analyser

An evidence-based resume-to-job comparison tool. It extracts PDF/DOCX text with local English OCR, structures skills and job requirements for review, calculates explainable job-match estimates, and provides prioritized factual improvement suggestions.

## Run the Phase 10 application

See [Phase 10 matching and resume improvement](docs/phase-10.md), [Phase 9 AI setup](docs/phase-9.md), and [Phase 4 setup](docs/phase-4.md). The API uses port 8001 and the frontend uses 5173. Explore the dictionary of 128 supported skills, review the resume and job categories, then compare for estimated ATS alignment, missing skills, resume quality checks, and improvement suggestions. PDF/JSON downloads include reviewed findings. Local analysis needs no key; OpenAI semantic proposals and generative advice require a backend API key and an explicit cloud-analysis action.

## Phase 1 artifacts

- [MVP requirements and acceptance criteria](docs/phase-1/requirements.md)
- [Result contract and scoring rules](docs/phase-1/result-contract.md)
- [Machine-readable result schema](contracts/analysis-result.schema.json)
- [Synthetic dataset guide](data/phase-1/README.md)
- [Example completed report](data/phase-1/sample-report.json)
- [Labeled resume/job pairs](data/phase-1/cases)

Start by reading the requirements, then compare a case's `resume.txt` and `job-description.txt` against `labels.json`. The example report illustrates the output the future application must produce.

## Further improvements

Possible future work includes evaluation of semantic proposal quality on a fresh held-out dataset and richer rewrites with stronger factual verification. Current AI wording suggestions are source excerpts and never edit resumes automatically.

See the [bug-fix review and regression checks](docs/bug-fixes.md) for corrected matching edge cases and frontend error handling. Run `npm test` inside `frontend` for request-error regressions.

See the [Phase 5 design](docs/phase-5-design.md) and [implementation notes](docs/phase-5.md) for matching rules, score calculation, API/report changes, UI flow, and evaluation results.

## Dataset maintenance

`scripts/build_phase1_dataset.py` regenerates the synthetic fixtures deterministically. It overwrites files only inside `data/phase-1`. `scripts/validate_phase1.py` checks fixture integrity and the sample report contract.

```text
python -m pip install -r scripts/requirements.txt
python scripts/build_phase1_dataset.py
python scripts/validate_phase1.py
```

Project repository: [cv-analyser](https://github.com/SriVishnu230707/cv-analyser).
