# CV Analyser

Phase 1 defines an evidence-based resume-to-job comparison tool. This checkpoint contains the MVP specification, output contract, synthetic labeled examples, and validation scripts.

## Artifacts

- [MVP requirements](docs/phase-1/requirements.md)
- [Result contract and scoring policy](docs/phase-1/result-contract.md)
- [JSON result schema](contracts/analysis-result.schema.json)
- [24 labeled synthetic pairs](data/phase-1/README.md)
- [Example report](data/phase-1/sample-report.json)

## Verify

~~~text
python -m pip install -r scripts/requirements.txt
python scripts/build_phase1_dataset.py
python scripts/validate_phase1.py
~~~

18 examples are for development and 6 are reserved for evaluation. These authored synthetic references are sanity checks, not independently annotated accuracy benchmarks.

## Next phase

Build a React upload form and FastAPI backend that return the fixed example report. Parsing and personalized scoring follow in later phases.

## Phase 2 application

React/Vite upload form and FastAPI API now return a clearly marked fixed sample report. See [setup instructions](docs/phase-2.md). Real extraction comes in Phase 3.
