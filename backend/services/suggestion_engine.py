"""Factual, deterministic guidance. No invented skills, metrics, or experience."""
import hashlib
import re

VERSION = '1.0.0'
PRIORITY = {'high': 0, 'medium': 1, 'low': 2}


def build_suggestions(report, profile):
    suggestions = []
    requirements = {r['id']: r for r in report['requirements']}
    matches = {m['requirement_id']: m for m in report['matches']}
    pending = {p['requirement_id'] for p in report['possible_evidence'] if p['decision'] == 'pending' and p['requirement_id'] not in matches}
    skills = {s['name']: s for s in profile['resume_skills']}

    def add(kind, priority, ids, rationale, action, evidence=None, rewrite=None):
        # Stable within the same input pair; no suggestion carries factual text from another report.
        key = '|'.join([report['input_hash'], kind, *ids])
        suggestions.append({'id': 'suggestion-' + hashlib.sha256(key.encode()).hexdigest()[:16], 'kind': kind, 'priority': priority, 'requirement_ids': ids, 'rationale': rationale, 'action': action, 'evidence': evidence, 'rewrite': rewrite})

    for identifier in report['requirements_not_evidenced']:
        requirement = requirements[identifier]
        priority = 'high' if requirement['category'] == 'required_skill' else 'medium'
        name = requirement['canonical_skill'] or requirement['name']
        if identifier in pending:
            add('evidence_review', priority, [identifier], f'Possible evidence for “{name}” has not been confirmed and earns no credit.', 'Review the suggested excerpt. Confirm it only if it actually documents this requirement; otherwise reject it or add a truthful example.')
        elif requirement['canonical_skill']:
            assertions = {e['assertion'] for e in skills.get(name, {'evidence': []})['evidence']}
            action = f'If you have used {name}, add a specific project or work example describing what you did. Otherwise, leave it out of your skill claims.'
            if 'learning' in assertions:
                action = f'Keep {name} labeled as learning. If you later complete a relevant project, describe what you actually built; do not claim proficiency from study alone.'
            add('missing_skill', priority, [identifier], f'“{name}” is {"required" if priority == "high" else "preferred"} but has no eligible positive evidence in this resume.', action)
        else:
            add('responsibility_gap', 'medium', [identifier], f'The responsibility “{name}” is not evidenced in this resume.', 'If you have performed this task, add a concrete example of your own contribution, tools, and outcome. Include metrics only when you can substantiate them.')

    for identifier, match in matches.items():
        requirement = requirements[identifier]
        if requirement['canonical_skill'] and match['status'] == 'listed':
            add('listed_skill', 'medium', [identifier], f'“{requirement["canonical_skill"]}” is listed but demonstrated use is not documented by the credited excerpt.', 'If you have used this skill, add a truthful example under Projects or Experience explaining the task and your contribution. A stronger description may improve clarity without increasing this coverage score.', match['evidence'])
        if match['method'] == 'user_confirmed':
            add('confirmed_evidence', 'low', [identifier], 'This match depends on your confirmation rather than an automatic rule.', 'Check that the wording clearly connects your actual contribution to the job requirement. Keep team contributions and personal contributions distinct.', match['evidence'])

    for qualification in report['qualifications']:
        if qualification['status'] != 'met':
            requirement = requirements[qualification['requirement_id']]
            priority = 'high' if requirement['category'] == 'mandatory_qualification' else 'medium'
            add('qualification_review', priority, [requirement['id']], qualification['reason'], 'Review the original qualification requirement. If you meet it, state the exact credential or relevant experience truthfully. Do not invent a degree, certification, duration, or equivalence.', qualification['evidence'])

    if report['readability']['status'] == 'needs_review':
        add('readability', 'high', [], 'The extraction or edited text needs a completeness and reading-order check.', 'Compare the preview with your original file, correct omissions and reading order, and rerun. If OCR is unclear, export a searchable PDF or use a clearer scan.')

    # Optional rewrite: only simplify the existing first-person bullet prefix.
    # Everything after the prefix is copied verbatim, including tools and metrics.
    seen = set()
    for match in report['matches']:
        evidence = match['evidence']
        text = evidence['text']
        if evidence['section'] not in {'Projects', 'Experience'} or text in seen:
            continue
        seen.add(text)
        rewrite = re.sub(r'^([-•*]\s*)?I\s+(?=(?:built|developed|implemented|used|deployed|maintained|queried|tested|designed|created|integrated|packaged|automated)\b)', '', text, flags=re.I)
        if rewrite != text:
            rewrite = rewrite[:1].upper() + rewrite[1:]
            related = [m['requirement_id'] for m in report['matches'] if m['evidence']['text'] == text]
            add('bullet_clarity', 'low', related, 'This existing first-person sentence can be presented as a concise resume bullet.', 'Consider this wording only if the original statement is accurate. It removes the first-person prefix and preserves your documented facts.', evidence, rewrite)

    return sorted(suggestions, key=lambda item: (PRIORITY[item['priority']], item['kind'], item['id']))
