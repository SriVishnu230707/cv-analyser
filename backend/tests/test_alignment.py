import json
import pymupdf
from jsonschema import Draft202012Validator

from backend.main import ROOT
from backend.services.resume_quality import assess_quality
from backend.services.resume_sections import parse_sections
from backend.tests.test_phase5 import RESUME, JOB, result, corrections, client
from scripts.evaluate_alignment import evaluate
import pytest


def test_cross_role_skill_evaluation():
    outcome = evaluate()
    assert outcome['case_count'] == 12
    assert outcome['counts']['false_positive'] == outcome['counts']['false_negative'] == 0
    assert outcome['counts']['true_positive'] == 25


def test_quality_findings_are_actionable_and_do_not_change_score():
    before = result()
    text = 'candidate@example.test\n' + RESUME
    after = result(text)
    assert after['scores'] == before['scores']
    assert after['resume_quality']['review_count'] < before['resume_quality']['review_count']
    for check in before['resume_quality']['checks']:
        assert bool(check['action']) == (check['status'] == 'review')
    assert 'candidate@example.test' not in json.dumps(after['resume_quality'])


def test_entry_level_projects_satisfy_example_check():
    text = 'candidate@example.test\nProjects\nBuilt a classifier using Python.\nSkills\nPython'
    assessment = assess_quality(text, parse_sections(text))
    assert assessment['review_count'] == 0
    assert all(check['status'] == 'pass' for check in assessment['checks'])


@pytest.mark.parametrize('line', ['Never built Python tools.', 'Learning to develop tools; used Python in a tutorial.', 'No experience with Docker; deployed nothing.'])
def test_learning_and_negated_action_wording_needs_review(line):
    text = 'Projects\n' + line
    assessment = assess_quality(text, parse_sections(text))
    contribution = next(c for c in assessment['checks'] if c['id'] == 'contribution')
    assert contribution['status'] == 'review'


def test_long_description_and_missing_headings_need_review():
    text = 'Projects\nBuilt ' + 'a useful tool ' * 20
    checks = {c['id']: c for c in assess_quality(text, parse_sections(text))['checks']}
    assert checks['conciseness']['status'] == 'review'
    assert checks['contact']['status'] == 'review'
    unstructured = assess_quality('Python developer with coursework.', parse_sections('Python developer with coursework.'))
    assert next(c for c in unstructured['checks'] if c['id'] == 'sections')['status'] == 'review'


def test_quality_is_schema_valid_and_in_json_and_pdf_exports():
    payload = {'resume_text': RESUME, 'job_description': JOB, 'requirements_confirmed': True, 'category_corrections': corrections()}
    report = client.post('/api/report/export', json={**payload, 'format': 'json'}).json()
    Draft202012Validator(json.loads((ROOT / 'contracts/analysis-result-v1.1.schema.json').read_text(encoding='utf-8'))).validate(report)
    assert report['resume_quality']['checks']
    response = client.post('/api/report/export', json={**payload, 'format': 'pdf'})
    assert response.status_code == 200
    with pymupdf.open(stream=response.content, filetype='pdf') as document:
        extracted = ''.join(page.get_text() for page in document)
    assert 'Resume quality and editing checks' in extracted
    assert 'Contact email' in extracted
