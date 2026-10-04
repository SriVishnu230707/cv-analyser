# Phase 7: downloadable analysis reports

Phase 7 adds **Download PDF** and **Download JSON** to the comparison report. Report export was the next enhancement listed in the README after the completed Phase 6 improvement plan.

## Workflow

1. Upload or load a sample resume, review its text, and confirm job requirement categories.
2. Click **Compare with this role**.
3. Use **Save your report** above the match summary. PDF is a readable report; JSON is the complete machine-readable v1.1 result.
4. Review possible evidence if appropriate, then download again to include the latest decisions.

PDF includes the score breakdown, job wording, credited and possible evidence, all qualification/informational/excluded requirements, readability findings, prioritized suggestions, optional factual rewrites, report notes, and page numbering. JSON additionally includes the reviewed resume sections and exact evidence offsets. Review downloaded files before sharing them; source excerpts and JSON resume sections can contain personal information.

Editing the inputs or changing requirement categories clears the report and download controls. An in-progress export is aborted when the report panel is removed, preventing a late download from the previous inputs. Downloaded files are snapshots and do not change after later edits.

## API

`POST /api/report/export` accepts the same reviewed inputs, canonical mappings, and evidence decisions as `/api/compare`, plus `format: "pdf" | "json"`.

The backend shares comparison validation and rebuilds the report from current request text. It never trusts submitted scores, suggestions, or positive-match flags. Unreviewed categories, invalid/expired extraction context, and stale evidence decisions produce the existing 422 error envelope. Each export has a fresh analysis ID; its input hash correlates it with the same reviewed text pair.

Successful responses have the appropriate PDF/JSON content type, an attachment filename, `Cache-Control: no-store`, and `X-Content-Type-Options: nosniff`. Filenames contain an analysis ID, not a candidate name. Application exports are generated in memory and returned directly; no database or server-side report file is created.

## PDF rendering

`backend/services/report_export.py` uses the existing PyMuPDF dependency and [Story layout](https://pymupdf.readthedocs.io/en/latest/recipes-stories.html) for multi-page text. All source text is escaped before HTML layout; markup is printed as text, not treated as active content. No external fonts, images, links, or network resources are loaded. Headers/footers use an embedded font for consistent rendering.

Long tokens receive soft wrapping; JSON retains the original exact strings. PDF output is capped at 100 pages. An oversized PDF returns a useful error and recommends JSON or shorter inputs; it does not silently omit findings.

## Setup and verification

Dependencies and startup commands remain the same as [Phase 4](phase-4.md). Run the API on port 8001 and Vite on 5173 with `BACKEND_URL=http://127.0.0.1:8001`.

```powershell
python -m pytest backend/tests -q
cd frontend
npm run build
```

Backend regressions cover JSON schema/score integrity, valid PDF content, repeated headers/footers, Unicode accents and skill symbols, source markup escaping, invalid inputs, confirmed evidence, stale edits, multi-page long content, and the page limit. The four-page synthetic PDF was rendered with bundled Poppler and visually inspected. QA files under `.logs/phase7` are ignored by Git and contain synthetic data only.

Export does not alter the matching/scoring policy or introduce accounts, saved history, cloud models, or automatic resume edits.

Verification completed: all 83 backend tests passed, the production frontend build passed, and browser downloads were opened and checked for PDF/JSON content. Mobile download controls fit without horizontal overflow; editing the resume clears the previous report and its download controls.
