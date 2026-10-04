"""Conservative local matching; possible evidence is never automatic credit."""
import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

from backend.services.skill_extractor import ACTION, NEGATION, LEARNING, skill_mentions


@lru_cache(maxsize=1)
def rules():
    return json.loads((Path(__file__).resolve().parents[1] / 'data/responsibility_rules.json').read_text(encoding='utf-8'))


def excerpts(sections):
    for index, section in enumerate(sections):
        offset = 0
        for line in section['text'].splitlines(keepends=True):
            text = line.rstrip('\r\n')
            if text.strip():
                yield {"text": text, "section": section['name'], "section_index": index, "start": offset, "end": offset + len(text)}
            offset += len(line)


def identify(evidence, requirement_id, input_hash):
    key = f"{input_hash}|{requirement_id}|{evidence['section_index']}|{evidence['start']}|{evidence['end']}"
    return {**evidence, 'id': 'evidence-' + hashlib.sha256(key.encode()).hexdigest()[:20]}


def positive_action(text):
    return bool(ACTION.search(text)) and not (NEGATION.search(text) or LEARNING.search(text) or re.search(r"\b(?:no|not|never|didn't|cannot|can't)\b", text, re.I))


def rule_match(requirement, text):
    matched = [rule for rule in rules()['rules'] if re.search(rule['action'], requirement, re.I) and re.search(rule['object'], requirement, re.I)]
    # Multi-task and unknown task wording is always reviewed rather than partially credited.
    if not matched or len(matched) != 1 or re.search(r'\b(?:and|or|also)\b', requirement, re.I):
        return False
    rule = matched[0]
    object_pattern = rule['object']
    if 'object_groups' in rule:
        targets = [pattern for pattern in rule['object_groups'] if re.search(pattern, requirement, re.I)]
        if len(targets) != 1:
            return False
        object_pattern = targets[0]
    required_skills = {m['name'] for m in skill_mentions(requirement)}
    # An action and its object/tools must belong to the same assertion.
    clauses = re.split(r"[;!?]|\.(?=\s|$)|\b(?:but|however|although)\b", text, flags=re.I)
    return any(positive_action(clause) and re.search(rule['action'], clause, re.I) and re.search(object_pattern, clause, re.I) and not required_skills - {m['name'] for m in skill_mentions(clause)} for clause in clauses)


def match_evidence(profile, requirements, input_hash, decisions, extra_possible=()):
    lines = list(excerpts(profile['resume_sections']))
    skills = {skill['name']: skill for skill in profile['resume_skills']}
    matches, possible = [], []
    for requirement in requirements:
        if not requirement['included_in_score']:
            continue
        identifier = requirement['id']
        if requirement['canonical_skill']:
            skill = skills.get(requirement['canonical_skill'], {'evidence': []})
            eligible = [e for e in skill['evidence'] if e['assertion'] == 'positive']
            eligible.sort(key=lambda e: {'demonstrated': 0, 'listed': 1, 'mentioned': 2}[e['level']])
            for item in eligible:
                source = next(line for line in lines if line['section'] == item['section'] and line['text'] == item['text'])
                evidence = identify(source, identifier, input_hash)
                if item['level'] == 'mentioned':
                    possible.append({'requirement_id': identifier, 'evidence': evidence, 'reason': 'Positive mention outside a skills list or demonstrated use; confirm its relevance.'})
                else:
                    method = 'exact' if item['matched_text'].casefold() == requirement['canonical_skill'].casefold() else 'alias'
                    matches.append({'requirement_id': identifier, 'status': item['level'], 'method': method, 'evidence': evidence})
                    break
        else:
            candidates = [line for line in lines if line['section'] in {'Projects', 'Experience'} and positive_action(line['text'])]
            direct = next((line for line in candidates if rule_match(requirement['name'], line['text'])), None)
            if direct:
                matches.append({'requirement_id': identifier, 'status': 'demonstrated', 'method': 'rule', 'evidence': identify(direct, identifier, input_hash)})
            else:
                # A candidate selects relevance; these excerpts earn zero automatic points.
                possible.extend({'requirement_id': identifier, 'evidence': identify(line, identifier, input_hash), 'reason': 'Action wording found; relevance to this responsibility needs your confirmation.'} for line in candidates[:8])
    credited = {item['requirement_id'] for item in matches}
    combined = {}
    for item in [*extra_possible, *possible]:
        combined.setdefault((item['requirement_id'], item['evidence']['id']), item)
    possible = list(combined.values())
    possible = [item for item in possible if item['requirement_id'] not in credited]
    known = {(item['requirement_id'], item['evidence']['id']): item for item in possible}
    seen, accepted = set(), set()
    for decision in decisions:
        key = (decision['requirement_id'], decision['evidence_id'])
        if key not in known or key in seen:
            raise ValueError('Unknown, duplicate, or stale evidence decision. Compare the current text again.')
        seen.add(key)
        if decision['decision'] == 'accept':
            if key[0] in accepted:
                raise ValueError('Accept only one excerpt per requirement.')
            accepted.add(key[0])
            item = known[key]
            matches.append({'requirement_id': key[0], 'status': 'demonstrated' if item['evidence']['section'] in {'Projects', 'Experience'} else 'listed', 'method': 'user_confirmed', 'evidence': item['evidence']})
    for item in possible:
        key = (item['requirement_id'], item['evidence']['id'])
        item['decision'] = next((d['decision'] for d in decisions if (d['requirement_id'], d['evidence_id']) == key), 'pending')
    return matches, possible
