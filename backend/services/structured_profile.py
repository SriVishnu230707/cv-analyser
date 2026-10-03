from uuid import uuid4
from backend.services.job_parser import extract_job_requirements, review_requirements
from backend.services.resume_sections import parse_sections
from backend.services.skill_extractor import extract_resume_skills, matcher_bundle


def prepare_profile(text, job, corrections=None):
    sections = parse_sections(text)
    parsed = extract_job_requirements(job)
    requirements = parsed["requirements"]
    if corrections is not None:
        requirements = review_requirements(requirements, corrections)
    pending = sum(item["needs_review"] for item in requirements)
    review_status = "needs_review" if pending or not requirements else "confirmed" if corrections is not None else "not_confirmed"
    return {"status": "ready_for_matching", "preparation_id": str(uuid4()), "resume_text": text, "resume_sections": sections, "job_description": job, "analysis_available": False, "taxonomy_version": matcher_bundle()[2], "resume_skills": extract_resume_skills(sections), "job_requirements": requirements, "excluded_job_mentions": parsed["excluded_mentions"], "review_status": review_status, "pending_review_count": pending, "warnings": (["Review the unclear requirement categories before matching."] if pending else []) + (["No assessable job requirements were found. Add explicit job requirements."] if not requirements else []) + ["Skill mentions describe resume evidence, not verified proficiency. Confirm requirement categories before comparison."]}
