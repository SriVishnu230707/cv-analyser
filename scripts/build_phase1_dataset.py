"""Build authored synthetic Phase 1 fixtures; this is not an analyzer."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "phase-1"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


ROLES = {
    "backend": {
        "skills": ["Python", "SQL", "Flask", "Docker"],
        "preferred": ["Redis", "AWS"],
        "bullets": ["Built REST APIs using Python and Flask.", "Queried application data using SQL and packaged the service using Docker."],
        "responsibilities": ["Build REST APIs.", "Query application data and package services for deployment."],
        "alias": "python, sql, flask, docker, redis, Amazon Web Services",
    },
    "frontend": {
        "skills": ["JavaScript", "React", "CSS", "Git"],
        "preferred": ["TypeScript", "Jest"],
        "bullets": ["Built interactive interfaces using JavaScript and React.", "Styled responsive pages using CSS and tracked changes using Git."],
        "responsibilities": ["Build interactive user interfaces.", "Style responsive pages and track code changes."],
        "alias": "JS, React.js, Cascading Style Sheets, git, TS, jest",
    },
    "fullstack": {
        "skills": ["JavaScript", "Node.js", "PostgreSQL", "React"],
        "preferred": ["Docker", "TypeScript"],
        "bullets": ["Built server endpoints using JavaScript and Node.js.", "Built database-backed interfaces using PostgreSQL and React."],
        "responsibilities": ["Build server endpoints.", "Build database-backed user interfaces."],
        "alias": "JS, NodeJS, postgres, React.js, docker, TS",
    },
}
SCENARIOS = ["full_coverage", "partial_coverage", "listed_only", "aliases", "negated", "unrelated", "required_only", "sparse_evidence"]


def build():
    manifest = []
    for role, spec in ROLES.items():
        for index, scenario in enumerate(SCENARIOS, 1):
            case_id = f"{role}-{index:02d}"
            folder = DATA / "cases" / case_id
            folder.mkdir(parents=True, exist_ok=True)
            required = spec["skills"]
            preferred = spec["preferred"]
            if scenario == "full_coverage":
                skill_line, bullets = ", ".join(required + preferred), spec["bullets"]
                req_indices, pref_indices, resp_indices = list(range(4)), [0, 1], [0, 1]
            elif scenario == "partial_coverage":
                skill_line, bullets = ", ".join(required[:3]), [spec["bullets"][0]]
                req_indices, pref_indices, resp_indices = [0, 1, 2], [], [0]
            elif scenario == "listed_only":
                skill_line, bullets = ", ".join(required + preferred), ["Coordinated study sessions for a fictional student club."]
                req_indices, pref_indices, resp_indices = list(range(4)), [0, 1], []
            elif scenario == "aliases":
                skill_line, bullets = spec["alias"], ["Maintained meeting notes for a fictional student club."]
                req_indices, pref_indices, resp_indices = list(range(4)), [0, 1], []
            elif scenario == "negated":
                skill_line = "No experience with " + ", ".join(required + preferred) + "."
                bullets = ["Organized a fictional campus event."]
                req_indices, pref_indices, resp_indices = [], [], []
            elif scenario == "unrelated":
                skill_line, bullets = "Java, spreadsheet editing", ["Built a Java desktop calculator."]
                req_indices, pref_indices, resp_indices = [], [], []
            elif scenario == "required_only":
                skill_line, bullets = ", ".join(required), spec["bullets"]
                req_indices, pref_indices, resp_indices = list(range(4)), [], [0, 1]
            else:
                skill_line = required[0]
                bullets = [f"Practiced {required[0]} in small introductory exercises."]
                req_indices, pref_indices, resp_indices = [0], [], []
            resume = "\n".join([f"Synthetic Candidate {case_id}", "Summary", "Entry-level software-development candidate.", "Skills", skill_line, "Projects", *bullets, "Education", "Completed a fictional introductory programming course.", ""])
            requirements = []
            for i, skill in enumerate(required):
                requirements.append({"id": f"req-{i+1}", "category": "required_skill", "name": skill, "weight": [3, 3, 2, 2][i], "source": f"Required: {skill}."})
            for i, skill in enumerate(preferred):
                requirements.append({"id": f"pref-{i+1}", "category": "preferred_skill", "name": skill, "weight": 1, "source": f"Preferred: {skill}."})
            for i, sentence in enumerate(spec["responsibilities"]):
                requirements.append({"id": f"resp-{i+1}", "category": "responsibility", "name": sentence.rstrip("."), "weight": 1, "source": sentence})
            qualification = {"id": "qual-1", "category": "mandatory_qualification", "name": "Computer science degree or equivalent practical experience", "weight": 0, "source": "Mandatory qualification: a computer science degree or equivalent practical experience."}
            requirements.append(qualification)
            job = "\n".join([f"Fictional {role} developer opening", "This synthetic role supports a fictional internal application.", *[r["source"] for r in requirements], ""])
            matches = []
            for category, indices, prefix in [("required_skill", req_indices, "req"), ("preferred_skill", pref_indices, "pref")]:
                for i in indices:
                    skill = required[i] if category == "required_skill" else preferred[i]
                    evidence = next((b for b in bullets if skill in b), None)
                    matches.append({"requirement_id": f"{prefix}-{i+1}", "status": "demonstrated" if evidence else "listed", "method": "alias" if scenario == "aliases" else "exact", "evidence": {"text": evidence or skill_line, "section": "Projects" if evidence else "Skills"}})
            for i in resp_indices:
                matches.append({"requirement_id": f"resp-{i+1}", "status": "demonstrated", "method": "semantic", "evidence": {"text": spec["bullets"][i], "section": "Projects"}})
            matched_ids = {m["requirement_id"] for m in matches}
            components = {
                "required_skills": {"score": float(sum([3, 3, 2, 2][i] for i in req_indices) * 10), "base_weight": 0.6, "effective_weight": 0.6},
                "preferred_skills": {"score": float(len(pref_indices) * 50), "base_weight": 0.15, "effective_weight": 0.15},
                "responsibilities": {"score": float(len(resp_indices) * 50), "base_weight": 0.25, "effective_weight": 0.25},
            }
            labels = {
                "case_id": case_id, "scenario": scenario, "annotation_origin": "authored_synthetic_reference",
                "requirements": requirements, "matches": matches,
                "requirements_not_evidenced": [r["id"] for r in requirements if r["category"] != "mandatory_qualification" and r["id"] not in matched_ids],
                "qualifications": [{"requirement_id": "qual-1", "status": "uncertain", "evidence": None, "reason": "No degree is stated; equivalence of practical experience requires review."}],
                "scores": {"overall": round(sum(c["score"] * c["effective_weight"] for c in components.values()), 1), "components": components},
                "readability": {"status": "not_assessed", "issues": []},
            }
            (folder / "resume.txt").write_text(resume, encoding="utf-8")
            (folder / "job-description.txt").write_text(job, encoding="utf-8")
            write_json(folder / "labels.json", labels)
            manifest.append({"case_id": case_id, "role": role, "scenario": scenario, "split": "development" if index <= 6 else "evaluation", "directory": f"cases/{case_id}"})
            if case_id == "backend-02":
                report = {"schema_version": "1.0.0", "analysis_id": "sample-backend-02", "status": "complete", "resume_sections": [{"name": "Skills", "text": skill_line}, {"name": "Projects", "text": "\n".join(bullets)}, {"name": "Education", "text": "Completed a fictional introductory programming course."}], **{k: labels[k] for k in ["requirements", "matches", "requirements_not_evidenced", "qualifications", "scores", "readability"]}, "suggestions": [
                    {"priority": "high", "requirement_ids": ["req-4"], "rationale": "Docker is required but no resume evidence was found.", "action": "If you have used Docker, describe a specific project and what you containerized. Otherwise, consider learning it; do not add it as an existing skill.", "rewrite": None},
                    {"priority": "medium", "requirement_ids": ["req-2"], "rationale": "SQL is listed without a supporting project example.", "action": "If accurate, describe where you used SQL and the purpose of the queries.", "rewrite": None},
                    {"priority": "medium", "requirement_ids": ["resp-1"], "rationale": "The API project is relevant and can be made easier to scan.", "action": "Use a concise action-led bullet without inventing an outcome.", "rewrite": "Built REST APIs with Python and Flask."}
                ], "warnings": ["Illustrative application estimate; not an employer ATS score or a proficiency assessment."]}
                write_json(DATA / "sample-report.json", report)
    write_json(DATA / "manifest.json", {"dataset_version": "1.0.0", "synthetic": True, "cases": manifest})


if __name__ == "__main__":
    build()
    print("Built 24 synthetic pairs (18 development, 6 evaluation) and sample report.")
