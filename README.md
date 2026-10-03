# CV Analyser

An evidence-based resume-to-job comparison tool. Phase 1 defines the product and evaluation examples. Phase 2 established the React/FastAPI application. Phase 3 extracts actual PDF/DOCX text and supports local English OCR. Phase 4 extracts canonical skills with resume evidence and structures job requirements for category review.

## Run the Phase 5 application

See [Phase 5 comparison instructions](docs/phase-5.md) and [Phase 4 setup](docs/phase-4.md). The current API uses port 8001 and the frontend uses 5173. Extract and review the resume, confirm job requirement categories, then click **Compare with this role** for evidence and an estimated job-match score.

## Phase 1 artifacts

- [MVP requirements and acceptance criteria](docs/phase-1/requirements.md)
- [Result contract and scoring rules](docs/phase-1/result-contract.md)
- [Machine-readable result schema](contracts/analysis-result.schema.json)
- [Synthetic dataset guide](data/phase-1/README.md)
- [Example completed report](data/phase-1/sample-report.json)
- [Labeled resume/job pairs](data/phase-1/cases)

Start by reading the requirements, then compare a case's `resume.txt` and `job-description.txt` against `labels.json`. The example report illustrates the output the future application must produce.

## Next implementation step: Phase 6

Generate factual improvement suggestions from missing evidence, listed skills, uncertain qualifications, and extraction issues. The current application requires no accounts, cloud services, API keys, or model training.

See the [Phase 5 design](docs/phase-5-design.md) and [implementation notes](docs/phase-5.md) for matching rules, score calculation, API/report changes, UI flow, and evaluation results.

## Dataset maintenance

`scripts/build_phase1_dataset.py` regenerates the synthetic fixtures deterministically. It overwrites files only inside `data/phase-1`. `scripts/validate_phase1.py` checks fixture integrity and the sample report contract.

```text
python -m pip install -r scripts/requirements.txt
python scripts/build_phase1_dataset.py
python scripts/validate_phase1.py
```

Project repository: [cv-analyser](https://github.com/SriVishnu230707/cv-analyser).
