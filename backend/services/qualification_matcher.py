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
            degree_type = degree.group().casefold()
            degree_pattern = r"\bbachelor'?s?\b" if degree_type.startswith('bachelor') else r"\bmaster'?s?\b" if degree_type.startswith('master') else r'\b(?:phd|doctorate)\b'
            unfinished = r'\b(?:no|not|incomplete|unfinished|pursuing|expected|studying|candidate|in progress|working (?:toward|towards|on))\b'
            def documents_degree(line):
                if line['section'] != 'Education':
                    return False
                # Type and subject must describe one credential in one clause.
                # Mixed credentials need review rather than borrowing another degree's subject.
                clauses = re.split(r'[;!?]|\.(?=\s|$)|\b(?:but|however)\b', line['text'], flags=re.I)
                for clause in clauses:
                    types = re.findall(r"\b(?:bachelor'?s?|master'?s?|phd|doctorate)\b", clause, re.I)
                    subjects = re.findall(r'\b(?:computer science|software engineering|information technology)\b', clause, re.I)
                    if len(types) == len(subjects) == 1 and re.search(degree_pattern, clause, re.I) and re.search(r'\b' + re.escape(field.group()) + r'\b', clause, re.I) and not re.search(unfinished, clause, re.I):
                        return True
                return False

            evidence = next((line for line in lines if documents_degree(line)), None)
            status = 'met' if evidence else 'not_evidenced'
            reason = 'Explicit degree and subject wording found.' if evidence else 'No completed degree with this explicit type and subject is stated.'
        results.append({'requirement_id': requirement['id'], 'status': status, 'reason': reason, 'evidence': identify(evidence, requirement['id'], input_hash) if evidence else None})
    return results
