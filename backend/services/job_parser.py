"""Explicit/heading rules with reviewable ambiguity; no inferred proficiency or scores."""
import hashlib
import re

from backend.services.skill_extractor import assertion, matcher_bundle, skill_mentions

CATEGORIES = {"required_skill", "preferred_skill", "unclassified_skill", "responsibility", "mandatory_qualification", "qualification", "experience_requirement", "other_requirement", "excluded"}
HEADINGS = {
    "required": "required", "required skills": "required", "requirements": "required", "must have": "required", "must-have": "required", "essential skills": "required", "minimum qualifications": "required", "what you bring": "required",
    "preferred": "preferred", "preferred skills": "preferred", "nice to have": "preferred", "nice-to-have": "preferred", "bonus": "preferred", "desirable skills": "preferred",
    "responsibilities": "responsibility", "duties": "responsibility", "what you'll do": "responsibility", "what you will do": "responsibility",
    "qualifications": None, "skills": None, "about us": None, "about the company": None, "benefits": "ignore", "equal opportunity": "ignore",
}
REQUIRED = re.compile(r"\b(?:required|mandatory|must|essential|minimum|need(?:ed)?|shall)\b", re.I)
PREFERRED = re.compile(r"\b(?:preferred|preferably|desirable|optional|bonus|nice[- ]to[- ]have|a plus)\b", re.I)
QUALIFICATION = re.compile(r"\b(?:degree|bachelor'?s?|master'?s?|doctorate|phd|certification|certified|diploma)\b", re.I)
EXPERIENCE = re.compile(r"\b\d+(?:\s*[-–]\s*\d+)?\s*\+?\s*(?:years?|yrs?)\b", re.I)
RESPONSIBILITY = re.compile(r"^(?:(?:you (?:will|would)|you'll|responsibilities?)\s*[:\-]?\s*)?(?:build|develop|design|maintain|implement|collaborate|write|test|deploy|manage|optimi[sz]e|automate|create|support|monitor|query|style|track|deliver|work)\b", re.I)
NOT_REQUIRED = re.compile(r"\b(?:not|isn't) (?:required|needed|necessary)\b|\bno (?:degree|certification) (?:is )?required\b", re.I)


def source_units(job: str):
    nlp, _, _ = matcher_bundle()
    context = None
    for number, original in enumerate(job.splitlines(), 1):
        line = re.sub(r"^\s*[-•*#]+\s*", "", original).strip()
        if not line:
            continue
        key = line.rstrip(":").casefold()
        if key in HEADINGS:
            context = HEADINGS[key]
            continue
        # Sentence segmentation preserves dotted technology names. Semicolons scope mixed categories.
        for clause in line.split(";"):
            for sentence in nlp(clause).sents:
                text = sentence.text.strip()
                if text:
                    yield text, number, context


def extract_job_requirements(job: str):
    entries, excluded = {}, []

    def add(name, category, source, line, method, needs_review=False, reason=""):
        key = (name.casefold(), category)
        if key not in entries:
            identifier = hashlib.sha256((category + "|" + name.casefold()).encode()).hexdigest()[:12]
            entries[key] = {"id": "job-" + identifier, "category": category, "name": name, "source": source, "sources": [], "weight": 0 if category in {"mandatory_qualification", "qualification", "experience_requirement"} else 1, "classification_method": method, "needs_review": needs_review, "review_reason": reason}
        entry = entries[key]
        evidence = {"text": source, "line_number": line}
        if evidence not in entry["sources"]:
            entry["sources"].append(evidence)

    for source, line, context in source_units(job):
        mentions = skill_mentions(source)
        if context == "ignore":
            continue
        explicit_required, explicit_preferred = bool(REQUIRED.search(source)), bool(PREFERRED.search(source))
        ambiguous = explicit_required and explicit_preferred
        category = "unclassified_skill"
        method = "inferred"
        if not ambiguous:
            if explicit_preferred or (not explicit_required and context == "preferred"):
                category = "preferred_skill"
            elif explicit_required or context == "required":
                category = "required_skill"
            method = "explicit" if explicit_required or explicit_preferred else "heading" if context in {"required", "preferred"} else "inferred"
        for item in mentions:
            if assertion(source, item["start"], item["end"]) == "negated":
                excluded.append({"name": item["name"], "source": source, "reason": "Negated mention."})
                continue
            add(item["name"], category, source, line, method, category == "unclassified_skill", "Required/preferred wording is mixed in this sentence." if ambiguous else "No explicit required/preferred classification." if category == "unclassified_skill" else "")
        if QUALIFICATION.search(source) and not NOT_REQUIRED.search(source):
            mandatory = (explicit_required or context == "required") and not explicit_preferred and not ambiguous
            add(source.rstrip("."), "mandatory_qualification" if mandatory else "qualification", source, line, "explicit" if explicit_required or explicit_preferred else "heading" if context else "inferred", ambiguous, "Mixed mandatory/preferred wording." if ambiguous else "")
        if EXPERIENCE.search(source):
            add(source.rstrip("."), "experience_requirement", source, line, "explicit")
        if context == "responsibility" or RESPONSIBILITY.search(source):
            add(source.rstrip("."), "responsibility", source, line, "heading" if context == "responsibility" else "inferred")
        if not mentions and not QUALIFICATION.search(source) and not EXPERIENCE.search(source) and not RESPONSIBILITY.search(source) and context != "responsibility" and (explicit_required or explicit_preferred or context in {"required", "preferred"}):
            add(source.rstrip("."), "other_requirement", source, line, method, True, "No dictionary skill was recognized. Review this requirement or extend the skill dictionary.")
    requirements = list(entries.values())
    mark_conflicts(requirements)
    warnings = []
    if not requirements:
        warnings.append("No assessable job requirements were found. Add explicit skills, responsibilities, or qualifications.")
    if any(entry["needs_review"] for entry in requirements):
        warnings.append("Some requirements need category review before matching.")
    return {"requirements": requirements, "excluded_mentions": excluded, "warnings": warnings}


def mark_conflicts(requirements):
    required = {r["name"] for r in requirements if r["category"] == "required_skill"}
    preferred = {r["name"] for r in requirements if r["category"] == "preferred_skill"}
    for entry in requirements:
        if entry["name"] in required & preferred and entry["category"] in {"required_skill", "preferred_skill"}:
            entry["needs_review"] = True
            entry["review_reason"] = "This skill is described as both required and preferred. Resolve the categories or exclude a duplicate."


def review_requirements(requirements, corrections):
    known = {entry["id"]: entry for entry in requirements}
    seen = set()
    for correction in corrections:
        identifier, category = correction["requirement_id"], correction["category"]
        if identifier not in known or identifier in seen:
            raise ValueError("Unknown or duplicate requirement ID. Extract the current text again before reviewing.")
        if category not in CATEGORIES:
            raise ValueError("Unknown requirement category.")
        seen.add(identifier)
        entry = known[identifier]
        entry["category"] = category
        entry["classification_method"] = "user"
        entry["needs_review"] = category == "unclassified_skill"
        entry["review_reason"] = "Choose required, preferred, or excluded for this skill." if entry["needs_review"] else ""
        entry["weight"] = 0 if category in {"mandatory_qualification", "qualification", "experience_requirement", "excluded"} else 1
    mark_conflicts(requirements)
    return requirements
