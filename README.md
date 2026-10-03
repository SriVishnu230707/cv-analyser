# CV Analyser

An evidence-based resume-to-job comparison tool. Phase 1 defines the product and evaluation examples. Phase 2 established the React/FastAPI application. Phase 3 extracts actual PDF/DOCX text, supports local English OCR for PDF scans, and lets candidates review and correct text before future matching.

## Run the Phase 3 application

See [Phase 3 setup and verification instructions](docs/phase-3.md). The current API uses port 8001 and the frontend uses 5173. Click **Load example**, **Extract resume text**, review the text, then **Prepare for matching**. No score is generated yet.

## Phase 1 artifacts

- [MVP requirements and acceptance criteria](docs/phase-1/requirements.md)
- [Result contract and scoring rules](docs/phase-1/result-contract.md)
- [Machine-readable result schema](contracts/analysis-result.schema.json)
- [Synthetic dataset guide](data/phase-1/README.md)
- [Example completed report](data/phase-1/sample-report.json)
- [Labeled resume/job pairs](data/phase-1/cases)

Start by reading the requirements, then compare a case's `resume.txt` and `job-description.txt` against `labels.json`. The example report illustrates the output the future application must produce.

## Next implementation step: Phase 4

Extract canonical skills and required/preferred job requirements with traceable source sentences. Matching and personalized scoring follow in later phases. The current application requires no accounts, cloud services, API keys, or model training.

## Dataset maintenance

`scripts/build_phase1_dataset.py` regenerates the synthetic fixtures deterministically. It overwrites files only inside `data/phase-1`. `scripts/validate_phase1.py` checks fixture integrity and the sample report contract.

```text
python -m pip install -r scripts/requirements.txt
python scripts/build_phase1_dataset.py
python scripts/validate_phase1.py
```

Project repository: [cv-analyser](https://github.com/SriVishnu230707/cv-analyser).
