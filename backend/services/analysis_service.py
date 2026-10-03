"""Rebuild and validate every comparison from current inputs."""
import hashlib
import json
from uuid import uuid4

from backend.services.evidence_matcher import match_evidence, rules
from backend.services.extraction_context import read_context
from backend.services.job_parser import extract_job_requirements
from backend.services.qualification_matcher import qualification_findings
from backend.services.scoring import calculate_scores, CATEGORY_COMPONENT
from backend.services.skill_extractor import CATALOG, skill_mentions
from backend.services.structured_profile import prepare_profile


def compare(text, job, corrections, mappings, decisions, context=None):
    current = extract_job_requirements(job)['requirements']
    if {r['id'] for r in current} != {c['requirement_id'] for c in corrections} or len(current) != len(corrections):
        raise ValueError('Confirm the full set of current requirement categories before comparison.')
    profile = prepare_profile(text, job, corrections)
    if profile['pending_review_count']:
        raise ValueError('Resolve unclear or conflicting requirement categories before comparison.')
    names = {s['name'] for s in json.loads(CATALOG.read_text(encoding='utf-8'))['skills']}
    mapping = {}
    for item in mappings:
        if item['requirement_id'] not in {r['id'] for r in current} or item['canonical_skill'] not in names or item['requirement_id'] in mapping:
            raise ValueError('Unknown or duplicate canonical skill mapping.')
        mapping[item['requirement_id']] = item['canonical_skill']
    requirements, seen = [], {}
    for item in profile['job_requirements']:
        canonical = None
        if item['category'] in {'required_skill', 'preferred_skill'}:
            mentions = skill_mentions(item['name'])
            canonical = mapping.get(item['id']) or (mentions[0]['name'] if len(mentions) == 1 else None)
            if not canonical:
                raise ValueError('Map unknown skill requirements to a dictionary skill or exclude them before comparison.')
        elif item['id'] in mapping:
            raise ValueError('Only required or preferred skills can have a canonical mapping.')
        included = item['category'] in CATEGORY_COMPONENT
        key = (item['category'], (canonical or item['name']).casefold().strip())
        if key in seen:
            seen[key]['sources'].extend(s for s in item['sources'] if s not in seen[key]['sources'])
            continue
        entry = {**item, 'canonical_skill': canonical, 'included_in_score': included, 'weight': 1 if included else 0}
        seen[key] = entry
        requirements.append(entry)
    required = {r['canonical_skill'] for r in requirements if r['category'] == 'required_skill'}
    preferred = {r['canonical_skill'] for r in requirements if r['category'] == 'preferred_skill'}
    if required & preferred:
        raise ValueError('A mapped skill is both required and preferred. Resolve its categories.')
    input_hash = hashlib.sha256(json.dumps([text, job], ensure_ascii=False).encode()).hexdigest()
    matches, possible = match_evidence(profile, requirements, input_hash, decisions)
    scores = calculate_scores(requirements, matches)
    credited = {m['requirement_id'] for m in matches}
    return {'schema_version': '1.1.0', 'analysis_id': str(uuid4()), 'input_hash': input_hash, 'scoring_policy_version': 'equal-weight-v1', 'taxonomy_version': profile['taxonomy_version'], 'rule_version': rules()['version'], 'status': 'complete' if scores['overall'] is not None else 'insufficient_requirements', 'resume_sections': profile['resume_sections'], 'requirements': requirements, 'matches': matches, 'possible_evidence': possible, 'requirements_not_evidenced': [r['id'] for r in requirements if r['included_in_score'] and r['id'] not in credited], 'qualifications': qualification_findings(profile['resume_sections'], requirements, input_hash), 'scores': scores, 'readability': read_context(context, text), 'suggestions': [], 'warnings': ['This is an estimated job match, not an employer ATS result or hiring probability.', 'Possible evidence earns no credit until confirmed. User confirmation records your interpretation, not independent verification.'], 'informational_requirement_count': sum(not r['included_in_score'] for r in requirements)}
