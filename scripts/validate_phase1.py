"""Validate authored artifacts, not the accuracy of a future analyzer."""
import json
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "phase-1"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check(condition, message):
    if not condition:
        raise ValueError(message)


def validate():
    schema = read(ROOT / "contracts" / "analysis-result.schema.json")
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    manifest = read(DATA / "manifest.json")["cases"]
    check(len(manifest) == 24, "Expected 24 cases")
    check(len({c["case_id"] for c in manifest}) == 24, "Duplicate case IDs")
    check(sum(c["split"] == "development" for c in manifest) == 18, "Expected 18 development cases")
    check(sum(c["split"] == "evaluation" for c in manifest) == 6, "Expected 6 evaluation cases")
    for case in manifest:
        folder = DATA / case["directory"]
        labels = read(folder / "labels.json")
        resume = (folder / "resume.txt").read_text(encoding="utf-8")
        job = (folder / "job-description.txt").read_text(encoding="utf-8")
        check(labels["case_id"] == case["case_id"], "Case ID mismatch")
        check(100 <= len(job) <= 20000, "Job description outside input bounds")
        requirements = {r["id"]: r for r in labels["requirements"]}
        check(len(requirements) == len(labels["requirements"]), "Duplicate requirement IDs")
        for requirement in requirements.values():
            check(requirement["source"] in job, "Requirement source absent from job")
        matched = set()
        for match in labels["matches"]:
            check(match["requirement_id"] in requirements, "Unknown match requirement")
            check(match["requirement_id"] not in matched, "Duplicate match")
            matched.add(match["requirement_id"])
            check(match["evidence"]["text"] in resume, "Evidence absent from resume")
        expected_gaps = {r["id"] for r in requirements.values() if r["category"] != "mandatory_qualification"} - matched
        check(expected_gaps == set(labels["requirements_not_evidenced"]), "Gap labels inconsistent")
        components = labels["scores"]["components"]
        for name, category in [("required_skills", "required_skill"), ("preferred_skills", "preferred_skill"), ("responsibilities", "responsibility")]:
            subset = [r for r in requirements.values() if r["category"] == category]
            expected = 100 * sum(r["weight"] for r in subset if r["id"] in matched) / sum(r["weight"] for r in subset)
            check(round(expected, 1) == components[name]["score"], "Component arithmetic mismatch")
        check(abs(sum(c["effective_weight"] for c in components.values()) - 1) < 1e-9, "Weights must sum to one")
        expected_total = round(sum(c["score"] * c["effective_weight"] for c in components.values()), 1)
        check(expected_total == labels["scores"]["overall"], "Overall arithmetic mismatch")
        report = {"schema_version": "1.0.0", "analysis_id": case["case_id"], "status": "complete", "resume_sections": [], **{k: labels[k] for k in ["requirements", "matches", "requirements_not_evidenced", "qualifications", "scores", "readability"]}, "suggestions": [], "warnings": []}
        validator.validate(report)
    sample = read(DATA / "sample-report.json")
    validator.validate(sample)
    backend_labels = read(DATA / "cases" / "backend-02" / "labels.json")
    for key in ["requirements", "matches", "requirements_not_evidenced", "qualifications", "scores", "readability"]:
        check(sample[key] == backend_labels[key], f"Sample report disagrees with fixture: {key}")
    known_ids = {r["id"] for r in sample["requirements"]}
    for suggestion in sample["suggestions"]:
        check(set(suggestion["requirement_ids"]) <= known_ids, "Unknown suggestion requirement")
    print("PASS: 24 pairs, split integrity, source/evidence references, score arithmetic, JSON Schema, and sample report.")


if __name__ == "__main__":
    validate()
