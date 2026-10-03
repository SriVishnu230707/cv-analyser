"""Dictionary phrase matching with explicit source evidence, not proficiency inference."""
import json
import re
from functools import lru_cache
from pathlib import Path

import spacy
from spacy.matcher import PhraseMatcher

CATALOG = Path(__file__).resolve().parents[1] / "data/skills.json"
NEGATION = re.compile(r"\b(?:no (?:experience|knowledge|exposure)(?:\s+(?:with|in|of|to))?|(?:not|never) (?:used|worked with|experienced in|familiar with)|haven't used|don't know|without (?:experience|knowledge)(?:\s+(?:of|in|with))?|lack(?:ing)? (?:experience|knowledge)(?:\s+(?:with|of|in))?)\b", re.I)
LEARNING = re.compile(r"\b(?:learning|studying|plan(?:ning)? to learn|want to learn)\b", re.I)
ACTION = re.compile(r"\b(?:built|developed|implemented|used|deployed|maintained|queried|tested|designed|created|integrated|packaged|styled|tracked|automated|optimized)\b", re.I)


@lru_cache(maxsize=1)
def matcher_bundle():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    aliases = set()
    for skill in catalog["skills"]:
        for alias in skill["aliases"]:
            if alias.casefold() in aliases:
                raise ValueError("Duplicate skill alias in taxonomy")
            aliases.add(alias.casefold())
        matcher.add(skill["name"], [nlp.make_doc(alias) for alias in skill["aliases"]])
    return nlp, matcher, catalog["version"]


def skill_mentions(text: str):
    nlp, matcher, _ = matcher_bundle()
    document = nlp.make_doc(text)
    candidates = []
    for key, start, end in matcher(document):
        span = document[start:end]
        # Tokenization plus character boundaries avoid embedded/compound near-matches.
        if span.start_char and (text[span.start_char - 1].isalnum() or text[span.start_char - 1] == "_"):
            continue
        if span.end_char < len(text) and (text[span.end_char].isalnum() or text[span.end_char] in "_+#"):
            continue
        candidates.append({"name": nlp.vocab.strings[key], "matched_text": span.text, "start": span.start_char, "end": span.end_char})
    selected = []
    for item in sorted(candidates, key=lambda item: (-(item["end"] - item["start"]), item["start"])):
        if not any(item["start"] < other["end"] and other["start"] < item["end"] for other in selected):
            selected.append(item)
    return sorted(selected, key=lambda item: item["start"])


def assertion(text: str, start: int, end: int):
    # Negation scopes across lists but stops at sentence/clause boundaries and contrast.
    prefix = re.split(r"[;!?]|\.(?=\s|$)|\b(?:but|however|although)\b", text[:start], flags=re.I)[-1]
    suffix = re.split(r"[;!?]|\.(?=\s|$)|\b(?:but|however|although)\b", text[end:], flags=re.I)[0]
    if NEGATION.search(prefix) or re.search(r"\bno\s+$", prefix, re.I) or re.match(r"\s+(?:is |experience is )?(?:not|isn't) (?:required|needed|necessary)\b", suffix, re.I):
        return "negated"
    if LEARNING.search(prefix):
        return "learning"
    return "positive"


def extract_resume_skills(sections: list[dict]):
    found = {}
    for section in sections:
        for line in section["text"].splitlines():
            for mention in skill_mentions(line):
                state = assertion(line, mention["start"], mention["end"])
                level = state if state != "positive" else "listed" if section["name"] == "Skills" else "demonstrated" if section["name"] in {"Experience", "Projects"} and ACTION.search(line) else "mentioned"
                evidence = {"text": line, "section": section["name"], "matched_text": mention["matched_text"], "start": mention["start"], "end": mention["end"], "assertion": state, "level": level}
                entry = found.setdefault(mention["name"], {"name": mention["name"], "evidence": []})
                if evidence not in entry["evidence"]:
                    entry["evidence"].append(evidence)
    return sorted(found.values(), key=lambda entry: entry["name"].casefold())
