"""Coverage arithmetic. Readability and personal attributes never earn points."""
BASE = {"required_skills": .60, "preferred_skills": .15, "responsibilities": .25}
CATEGORY_COMPONENT = {"required_skill": "required_skills", "preferred_skill": "preferred_skills", "responsibility": "responsibilities"}


def calculate_scores(requirements, matches):
    credited = {item["requirement_id"] for item in matches}
    totals = {key: 0 for key in BASE}
    hits = {key: 0 for key in BASE}
    for item in requirements:
        component = CATEGORY_COMPONENT.get(item["category"])
        if component and item["included_in_score"]:
            totals[component] += item["weight"]
            if item["id"] in credited:
                hits[component] += item["weight"]
    applicable = sum(BASE[key] for key in BASE if totals[key])
    components, overall = {}, 0
    for key, base in BASE.items():
        raw = 100 * hits[key] / totals[key] if totals[key] else None
        effective = base / applicable if totals[key] else 0
        components[key] = {"score": round(raw, 1) if raw is not None else None, "base_weight": base, "effective_weight": effective, "credited_weight": hits[key], "total_weight": totals[key]}
        overall += (raw or 0) * effective
    return {"overall": round(overall, 1) if applicable else None, "components": components}
