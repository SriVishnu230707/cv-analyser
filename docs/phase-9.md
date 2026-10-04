# Phase 9: alignment with the AI and NLP resume-analyser brief

| Original requirement | Implementation |
|---|---|
| Analyze resumes | PDF/DOCX extraction, local OCR, editable reviewed text, structured sections |
| Evaluate skills against job requirements | Canonical NLP skill recognition, versioned task rules, reviewed categories and evidence |
| Generate ATS scores | Estimated ATS alignment from explainable required/preferred/task coverage; extraction/readability reported separately |
| Identify missing skills | Requirements not evidenced, with verbatim evidence for credited matches |
| Intelligent improvement suggestions | Local actionable guidance plus optional OpenAI structured advice grounded in current requirements and resume excerpts |
| Understand related wording | OpenAI embedding-based ranking of positive responsibility evidence, always requiring human confirmation |

An ATS alignment estimate is the application's own measure. It cannot reproduce every employer's ATS, verify proficiency, or predict hiring. The model never supplies numeric scores or automatically gives credit to semantic similarity.

## Activate OpenAI

Copy `.env.example` to `.env` in the repository root. Set `OPENAI_API_KEY` privately in that file. Never put the key into frontend variables, a browser field, Git, or a chat message.

```dotenv
OPENAI_API_KEY=your-private-key
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

Install `backend/requirements.txt` (now includes python-dotenv), restart `python scripts/run_backend.py --port 8001`, and reload the frontend. The launcher reads `.env` without overriding existing environment variables. `/api/ai/status` reports configuration presence and model names without returning the key. Configuration presence does not verify account credit or model access.

Complete extraction, text review, requirement review, and local comparison. In **AI and semantic resume analysis**, check the cloud disclosure and click **Generate AI advice and semantic proposals**. Reviewed job wording, eligible resume excerpts, and local findings are sent to OpenAI; API charges may apply. Other steps remain local and do not call OpenAI automatically.

Review semantic proposals before confirming relevance. AI advice appears in the improvement plan. Downloading PDF or JSON includes the same advice and model provenance without repeating model calls. Use **Clear AI analysis and evidence confirmations** for a fresh comparison; this also clears previous manual evidence decisions.

## API and grounding

`POST /api/ai/analyze` accepts the reviewed comparison inputs plus `cloud_consent: true`. It returns `{report, ai_context}`. Include `ai_context` in subsequent comparison and export requests to retain enrichment. The signed, one-hour context binds the exact normalized input pair and requirement IDs/categories/canonical mappings. Editing inputs, changing mappings/categories, tampering with the token, or restarting the backend invalidates it. Local comparison without a context remains available.

The implementation uses [OpenAI embeddings](https://developers.openai.com/api/docs/guides/embeddings) and [structured outputs through the Responses API](https://developers.openai.com/api/docs/guides/structured-outputs). Generation uses `store: false`; this is not a promise about all provider data retention. No application database or report files are created.

Embedding analysis considers up to 80 eligible positive Projects/Experience lines and up to 40 reviewed requirements. It ranks missing responsibilities, adds at most three proposals per responsibility above cosine similarity 0.35, and records the model and token usage. This threshold is a proposal heuristic, not validated proficiency or an accuracy guarantee. Skills still require canonical evidence; related technologies are never inferred as equivalent. Oversized inputs fail before model calls.

Advice is constrained to known requirement/source IDs and validated response fields. It contains up to eight suggestions. Unknown references, invalid priorities, malformed responses, refusals, and incomplete output are rejected. Resume wording suggestions must be exact contiguous excerpts from their cited source. Free-form invented rewrites are discarded and counted. Generated explanations/actions remain AI advice for human review and should not be treated as verified facts. The source text and job wording are handled as untrusted data in the prompt.

The existing v1.1 contract adds optional `ats_assessment` and `ai_analysis` properties. Deterministic score weights and existing fields remain unchanged. Generation ID, model names, usage, and rejected-rewrite count provide provenance without exposing credentials.

## Verification and current limitation

The full 137-test backend suite and 7 frontend tests passed; four additional provider HTTP-error regressions also passed (141 backend cases in total). The frontend production build passed. AI regressions use controlled provider responses to check semantic confirmation, signed-context integrity, stale input rejection, invented rewrites, refusal/malformed-response handling, input limits, report-schema compatibility, and PDF/JSON exports.

No API key was configured in the workspace during implementation. Live OpenAI account/model behavior and semantic quality have **not** been verified. Configure the key and test with a synthetic resume before using real candidate data. Browser verification checks the local report and the missing-key state; neither a fake success message nor silently substituted local rules are presented as a live AI generation.
