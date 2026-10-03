"""Evaluate frozen automatic skill matches; labels never enter the runtime service."""
import argparse
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
for folder in ('nlp', 'backend'):
    path = root / '.tools' / folder
    if path.is_dir():
        sys.path.insert(0, str(path))
from backend.services.analysis_service import compare
from backend.services.job_parser import extract_job_requirements

parser = argparse.ArgumentParser()
parser.add_argument('--split', choices=['development', 'evaluation'], default='development')
args = parser.parse_args()
manifest = json.loads((root / 'data/phase-1/manifest.json').read_text(encoding='utf-8'))
counts = {'true_positive': 0, 'false_positive': 0, 'false_negative': 0}
cases = []
for case in manifest['cases']:
    if case['split'] != args.split:
        continue
    directory = root / 'data/phase-1' / case['directory']
    text = (directory / 'resume.txt').read_text(encoding='utf-8')
    job = (directory / 'job-description.txt').read_text(encoding='utf-8')
    corrections = [{'requirement_id': r['id'], 'category': 'excluded' if r['category'] == 'unclassified_skill' else r['category']} for r in extract_job_requirements(job)['requirements']]
    report = compare(text, job, corrections, [], [])
    scored = {r['id']: (r['canonical_skill'], r['category']) for r in report['requirements'] if r['canonical_skill']}
    predicted = {scored[m['requirement_id']] for m in report['matches'] if m['requirement_id'] in scored}
    labels = json.loads((directory / 'labels.json').read_text(encoding='utf-8'))
    refs = {r['id']: (r['name'], r['category']) for r in labels['requirements'] if r['category'] in {'required_skill', 'preferred_skill'}}
    expected = {refs[m['requirement_id']] for m in labels['matches'] if m['requirement_id'] in refs and m['status'] in {'listed', 'demonstrated'}}
    local = {'true_positive': len(predicted & expected), 'false_positive': len(predicted - expected), 'false_negative': len(expected - predicted)}
    for key in counts:
        counts[key] += local[key]
    cases.append({'case_id': case['case_id'], **local})
tp, fp, fn = counts.values()
print(json.dumps({'split': args.split, 'rule_version': '1.0.0', 'scoring_policy': 'equal-weight-v1', 'counts': counts, 'precision': tp / (tp + fp) if tp + fp else None, 'recall': tp / (tp + fn) if tp + fn else None, 'cases': cases, 'limits': 'Small authored synthetic dataset. Automatic skill matches only; no responsibility accuracy or real-world accuracy claim. Unclassified extra skill mentions are excluded as a fixed review policy.'}, indent=2))
