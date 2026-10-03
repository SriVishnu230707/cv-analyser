"""Qualification equivalence and experience duration are not inferred."""
import re
from backend.services.evidence_matcher import excerpts, identify


def qualification_findings(sections, requirements, input_hash):
    lines = list(excerpts(sections))
    results = []
    for requirement in requirements:
        if requirement['category'] not in {'mandatory_qualification', 'qualification', 'experience_requirement'}:
            continue
        name = requirement['name']
        # Only exact explicit degree type + field can qualify automatically.
        degree = re.search(r"\b(bachelor'?s?|master'?s?|phd|doctorate)\b", name, re.I)
        field = re.search(r'\b(computer science|software engineering|information technology)\b', name, re.I)
        evidence = None
        status = 'uncertain'
        reason = 'This requirement needs manual review; equivalence and years of experience are not inferred.'
        if degree and field and not re.search(r'\b(?:equivalent|or|not)\b', name, re.I):
            evidence = next((line for line in lines if line['section'] == 'Education' and degree.group().casefold() in line['text'].casefold() and field.group().casefold() in line['text'].casefold() and not re.search(r'\b(?:no|not|incomplete|pursuing|expected)\b', line['text'], re.I)), None)
            status = 'met' if evidence else 'not_evidenced'
            reason = 'Explicit degree and subject wording found.' if evidence else 'No completed degree with this explicit type and subject is stated.'
        results.append({'requirement_id': requirement['id'], 'status': status, 'reason': reason, 'evidence': identify(evidence, requirement['id'], input_hash) if evidence else None})
    return results
