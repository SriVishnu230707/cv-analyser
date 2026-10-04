"""Reproducible skill coverage evaluation; labels are never runtime inputs."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
for folder in ('nlp', 'backend'):
    path = ROOT / '.tools' / folder
    if path.is_dir():
        sys.path.insert(0, str(path))

from backend.services.analysis_service import compare
from backend.services.job_parser import extract_job_requirements


def evaluate():
    cases = json.loads((ROOT / 'data/alignment-evaluation/cases.json').read_text(encoding='utf-8'))
    totals = {'true_positive': 0, 'false_positive': 0, 'false_negative': 0}
    results = []
    for case in cases:
        job = 'Required: ' + ', '.join(case['skills']) + '.'
        categories = [{'requirement_id': r['id'], 'category': r['category']} for r in extract_job_requirements(job)['requirements']]
        report = compare(case['resume'], job, categories, [], [])
        names = {r['id']: r['canonical_skill'] for r in report['requirements']}
        predicted = {names[m['requirement_id']] for m in report['matches'] if names[m['requirement_id']]}
        expected = set(case['expected'])
        counts = {'true_positive': len(predicted & expected), 'false_positive': len(predicted - expected), 'false_negative': len(expected - predicted)}
        for key in totals:
            totals[key] += counts[key]
        results.append({'id': case['id'], **counts, 'expected': sorted(expected), 'predicted': sorted(predicted)})
    tp, fp, fn = totals.values()
    return {'taxonomy_version': report['taxonomy_version'], 'case_count': len(cases), 'counts': totals, 'precision': tp / (tp + fp) if tp + fp else None, 'recall': tp / (tp + fn) if tp + fn else None, 'cases': results, 'limits': 'Authored synthetic regression cases across six job families. Not an independent held-out dataset, real-world accuracy estimate, or evaluation of live AI semantic proposals.'}


if __name__ == '__main__':
    print(json.dumps(evaluate(), indent=2))
