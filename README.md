# CV Analyser

An evidence-based resume-to-job comparison tool. It extracts PDF/DOCX text with local English OCR, structures skills and job requirements for review, calculates explainable job-match estimates, and provides prioritized factual improvement suggestions.

## Run the Phase 8 application

See [Phase 8 matching coverage](docs/phase-8.md), [report-export instructions](docs/phase-7.md), and [Phase 4 setup](docs/phase-4.md). The current API uses port 8001 and the frontend uses 5173. Explore the searchable dictionary of 71 supported skills, extract and review the resume, confirm job requirement categories, then click **Compare with this role** for scores, evidence, and prioritized improvement suggestions. Download the reviewed report as PDF or JSON. No cloud model or API key is required.

## Phase 1 artifacts

- [MVP requirements and acceptance criteria](docs/phase-1/requirements.md)
- [Result contract and scoring rules](docs/phase-1/result-contract.md)
- [Machine-readable result schema](contracts/analysis-result.schema.json)
- [Synthetic dataset guide](data/phase-1/README.md)
- [Example completed report](data/phase-1/sample-report.json)
- [Labeled resume/job pairs](data/phase-1/cases)

Start by reading the requirements, then compare a case's `resume.txt` and `job-description.txt` against `labels.json`. The example report illustrates the output the future application must produce.

## Further improvements

Possible future work includes optional semantic evidence proposals and more extensive source-grounded rewrites. Current suggestions preserve documented facts and do not edit resumes automatically.

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
