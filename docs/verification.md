# Verification and release checks

## Repeatable local checks

From the repository root, install `backend/requirements-dev.txt`, then run:

```text
python -m pytest backend/tests -q
python scripts/evaluate_alignment.py
cd frontend
npm ci
npm test
npm run build
```

The GitHub workflow runs backend/frontend tests, the synthetic skill evaluation, and the production build on pushes and pull requests. OCR tests are skipped when English Tesseract data is unavailable; install it and set `TESSDATA_PREFIX` to run them. Live OpenAI calls are never part of automatic CI.

## Live OpenAI verification

Set `OPENAI_API_KEY` privately in the repository-root `.env`, following [AI setup](phase-9.md), and restart the backend on port 8001. This command checks configuration without paid calls and exits nonzero because it is not a live verification:

```text
python scripts/verify_live_ai.py
```

To explicitly authorize a live check with the built-in fictional resume/job pair:

```text
python scripts/verify_live_ai.py --run-live
```

The live check verifies requirement review, local scoring, AI analysis, signed context retention, and JSON/PDF exports. It checks that semantic proposals do not change scores without confirmation. It sends synthetic data to OpenAI through the local backend; API charges may apply. The script never requests, displays, or transmits your key itself. Do not substitute candidate data into this script.

Missing credentials, provider errors, malformed results, and failed checks exit nonzero. Configuration presence and controlled provider tests are never reported as a successful live verification.

## Accuracy limits

The authored evaluation cases test skill matching regressions, not universal accuracy. Real-world evaluation needs an independently labeled, authorized resume/job dataset, including negation, learning, aliases, ambiguous qualifications, and semantic relevance. Keep that data out of Git. A passing synthetic live workflow confirms connectivity and report contracts, not the quality of every AI suggestion or an employer's ATS score.
