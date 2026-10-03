import json
import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from backend.main import app, ROOT
from backend.services.analysis_service import compare
from backend.services.extraction_context import sign_context, read_context
from backend.services.job_parser import extract_job_requirements
from backend.services.scoring import calculate_scores
from backend.services.skill_extractor import assertion, skill_mentions

client = TestClient(app)
RESUME = 'Candidate\nSkills\nPython, SQL, Flask\nProjects\nBuilt REST APIs using Python and Flask.\nEducation\nCompleted an introductory course.'
JOB = 'Required: Python.\nRequired: SQL.\nRequired: Flask.\nRequired: Docker.\nPreferred: Redis.\nPreferred: AWS.\nBuild REST APIs.\nQuery data and package services.\nMandatory qualification: computer science degree or equivalent experience.'


def corrections(job=JOB):
    return [{'requirement_id': r['id'], 'category': 'excluded' if r['category'] == 'unclassified_skill' else r['category']} for r in extract_job_requirements(job)['requirements']]


def result(resume=RESUME, job=JOB, decisions=None):
    return compare(resume, job, corrections(job), [], decisions or [])


def test_real_score_and_schema():
    report = result()
    assert report['scores']['overall'] == 57.5
    assert report['scores']['components']['required_skills']['score'] == 75
    assert report['scores']['components']['responsibilities']['score'] == 50
    schema = json.loads((ROOT / 'contracts/analysis-result-v1.1.schema.json').read_text(encoding='utf-8'))
    Draft202012Validator(schema).validate(report)
    for match in report['matches']:
        evidence = match['evidence']
        source = report['resume_sections'][evidence['section_index']]
        assert source['name'] == evidence['section']
        assert source['text'][evidence['start']:evidence['end']] == evidence['text']


def test_weighted_arithmetic_and_normalization():
    requirements = [{'id': str(i), 'category': c, 'included_in_score': True, 'weight': w} for i, (c, w) in enumerate([('required_skill', 3), ('required_skill', 3), ('required_skill', 2), ('required_skill', 2), ('preferred_skill', 1), ('preferred_skill', 1), ('responsibility', 1), ('responsibility', 1)])]
    assert calculate_scores(requirements, [{'requirement_id': str(i)} for i in [0, 1, 2, 6]])['overall'] == 60.5
    only = calculate_scores(requirements[:4], [{'requirement_id': '0'}])
    assert only['overall'] == 30
    assert only['components']['required_skills']['effective_weight'] == 1
    assert only['components']['preferred_skills']['score'] is None
    assert calculate_scores([], [])['overall'] is None


@pytest.mark.parametrize('text', ['No Python or Docker experience.', 'Never built Python services.', 'Learning Python and Docker.', "I don't know Python.", 'Python not used.'])
def test_negative_and_learning_do_not_earn_credit(text):
    job = 'Required: Python. ' + 'Build reliable customer applications. ' * 3
    report = result('Summary\n' + text + '\nEducation\nCompleted an introductory course.', job)
    assert not report['matches']


def test_aliases_deduplication_and_related_languages():
    job = 'Required: Java. Required: PostgreSQL. ' + 'We operate a friendly distributed team. ' * 3
    resume = 'Skills\nJavaScript, postgres, postgres\nProjects\nBuilt JavaScript applications.'
    report = result(resume, job)
    assert [m['method'] for m in report['matches']] == ['alias']
    assert report['scores']['overall'] == 50
    duplicate = result(resume + '\npostgres postgres', job + '\nRequired: postgres.')
    assert duplicate['scores'] == report['scores']


def test_manual_decision_and_stale_or_fabricated_evidence():
    report = result()
    candidate = report['possible_evidence'][0]
    decision = {'requirement_id': candidate['requirement_id'], 'evidence_id': candidate['evidence']['id'], 'decision': 'accept'}
    accepted = result(decisions=[decision])
    assert accepted['scores']['overall'] == 70
    assert accepted['matches'][-1]['method'] == 'user_confirmed'
    rejected = result(decisions=[{**decision, 'decision': 'reject'}])
    assert rejected['scores'] == report['scores']
    with pytest.raises(ValueError, match='stale'):
        result(RESUME + '\nSkills\nDocker', decisions=[decision])
    with pytest.raises(ValueError):
        result(decisions=[{**decision, 'evidence_id': 'invented'}])
    with pytest.raises(ValueError):
        result(decisions=[decision, decision])


def test_responsibility_is_not_technology_overlap():
    job = 'Build REST APIs using Java. ' + 'Work alongside our experienced product team. ' * 3
    report = result(RESUME, job)
    assert not report['matches']
    assert report['possible_evidence']


def test_mapping_review_gates_and_empty_score():
    with pytest.raises(ValueError, match='full set'):
        compare(RESUME, JOB, [], [], [])
    job = 'Required: Svelte. ' + 'We work collaboratively on reliable tools. ' * 3
    review = corrections(job)
    review[0]['category'] = 'required_skill'
    with pytest.raises(ValueError, match='Map unknown'):
        compare(RESUME, job, review, [], [])
    mapped = compare(RESUME, job, review, [{'requirement_id': review[0]['requirement_id'], 'canonical_skill': 'Vue'}], [])
    assert mapped['scores']['overall'] == 0
    info = compare(RESUME, job, corrections(job), [], [])
    assert info['scores']['overall'] is None
    assert info['status'] == 'insufficient_requirements'


def test_qualification_and_readability_separate_from_score():
    job = "Required: Python. Bachelor's degree in computer science required. " + 'We are a collaborative team. ' * 3
    resume = RESUME + "\nEducation\nBachelor's degree in computer science."
    report = result(resume, job)
    assert report['qualifications'][0]['status'] == 'met'
    assert report['scores']['overall'] == 100
    assert result(RESUME, job)['qualifications'][0]['status'] == 'not_evidenced'
    assert result()['qualifications'][0]['status'] == 'uncertain'
    token = sign_context({'text': resume, 'readability': {'status': 'readable', 'issues': []}, 'warnings': ['Check the original columns.']})
    assert read_context(token, resume)['status'] == 'readable'
    assert read_context(token, resume + ' edit')['status'] == 'needs_review'
    with pytest.raises(ValueError):
        read_context(token + 'x', resume)
    assert read_context(None, resume)['status'] == 'not_assessed'


def test_compare_api_current_inputs_and_validation():
    body = {'resume_text': RESUME, 'job_description': JOB, 'requirements_confirmed': True, 'category_corrections': corrections()}
    response = client.post('/api/compare', json=body)
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    assert response.json()['scores']['overall'] == 57.5
    assert client.post('/api/compare', json={**body, 'requirements_confirmed': False}).status_code == 422
    assert client.post('/api/compare', json={**body, 'category_corrections': []}).status_code == 422
    assert client.post('/api/compare', json={**body, 'extraction_context': 'invalid'}).status_code == 422
