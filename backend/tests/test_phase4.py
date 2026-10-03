"""Phase 4 extraction/review regressions; held-out evaluation cases remain unused."""
import json

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from backend.main import ROOT, app
from backend.services.job_parser import extract_job_requirements
from backend.services.resume_sections import parse_sections
from backend.services.skill_extractor import assertion, extract_resume_skills, skill_mentions
from backend.services.structured_profile import prepare_profile

client = TestClient(app)
RESUME = "Summary\nBackend developer building dependable applications.\nSkills\nPython, postgres\nProjects\nBuilt services using Python and PostgreSQL."
JOB = "Required skills:\nPython and SQL\nPreferred:\nDocker\nResponsibilities:\nBuild REST APIs and maintain services.\nMinimum qualifications:\nBachelor's degree required.\n3+ years of experience."


def test_aliases_and_distinct_languages():
    names = [item['name'] for item in skill_mentions('JS, TypeScript, JavaScript, Java, C++, C#, Node.js. React.js postgres k8s golang')]
    assert names == ['JavaScript', 'TypeScript', 'JavaScript', 'Java', 'C++', 'C#', 'Node.js', 'React', 'PostgreSQL', 'Kubernetes', 'Go']
    assert [item['name'] for item in skill_mentions('AngularJS and Angular')] == ['AngularJS', 'Angular']


@pytest.mark.parametrize('text', ['JavaScript', 'myPythonTool', 'Pythonista', 'SQLAlchemy', 'Go to the office', 'express your ideas'])
def test_no_embedded_or_ambiguous_aliases(text):
    names = {item['name'] for item in skill_mentions(text)}
    if text == 'JavaScript':
        assert names == {'JavaScript'}
    else:
        assert not names


def test_source_offsets_and_canonical_deduplication():
    skills = extract_resume_skills(parse_sections(RESUME))
    assert [item['name'] for item in skills] == ['PostgreSQL', 'Python']
    for skill in skills:
        assert {item['level'] for item in skill['evidence']} == {'listed', 'demonstrated'}
        for evidence in skill['evidence']:
            assert evidence['text'][evidence['start']:evidence['end']] == evidence['matched_text']
            assert evidence['text'] in RESUME
    repeated = extract_resume_skills([{'name': 'Skills', 'text': 'Python\nPython'}])
    assert len(repeated) == len(repeated[0]['evidence']) == 1


def test_negation_learning_and_dotted_names():
    text = 'No experience with Node.js or Docker, but built Python services. Learning Rust.'
    states = {item['name']: assertion(text, item['start'], item['end']) for item in skill_mentions(text)}
    assert states == {'Node.js': 'negated', 'Docker': 'negated', 'Python': 'positive', 'Rust': 'learning'}
    evidence = extract_resume_skills([{'name': 'Summary', 'text': text}])
    assert next(item for item in evidence if item['name'] == 'Rust')['evidence'][0]['level'] == 'learning'
    assert assertion('No Docker', 3, 9) == 'negated'


def test_heading_categories_and_traceable_requirements():
    result = extract_job_requirements(JOB)
    pairs = {(item['name'], item['category']) for item in result['requirements']}
    assert {('Python', 'required_skill'), ('SQL', 'required_skill'), ('Docker', 'preferred_skill'), ('REST APIs', 'unclassified_skill'), ("Bachelor's degree required", 'mandatory_qualification'), ('3+ years of experience', 'experience_requirement'), ('Build REST APIs and maintain services', 'responsibility')} <= pairs
    for item in result['requirements']:
        for source in item['sources']:
            assert source['text'] in JOB.splitlines()[source['line_number'] - 1]


def test_mixed_categories_require_review_and_semicolons_scope_clauses():
    unclear = extract_job_requirements('Python required and Docker preferred.')['requirements']
    assert len(unclear) == 2
    assert all(item['category'] == 'unclassified_skill' and item['needs_review'] for item in unclear)
    clear = extract_job_requirements('Python required; Docker preferred.')['requirements']
    assert [(item['name'], item['category']) for item in clear] == [('Python', 'required_skill'), ('Docker', 'preferred_skill')]


def test_negated_requirement_does_not_exclude_other_skills():
    result = extract_job_requirements('Python required and Docker not required.')
    assert [(item['name'], item['category']) for item in result['requirements']] == [('Python', 'required_skill')]
    assert [item['name'] for item in result['excluded_mentions']] == ['Docker']
    assert not extract_job_requirements('No degree required.')['requirements']


def test_duplicates_keep_sources_and_conflicts_need_review():
    result = extract_job_requirements('Python required.\nPython is mandatory.\nPython preferred.')
    assert len(result['requirements']) == 2
    assert all(item['needs_review'] for item in result['requirements'])
    assert len(result['requirements'][0]['sources']) == 2
    assert extract_job_requirements('Python required.')['requirements'][0]['id'] == result['requirements'][0]['id']


def test_unknown_requirement_is_preserved_and_benefits_ignored():
    result = extract_job_requirements('Svelte required.\nBenefits:\nPython workshops available.')
    assert len(result['requirements']) == 1
    assert result['requirements'][0]['name'] == 'Svelte required'
    assert result['requirements'][0]['category'] == 'other_requirement'
    assert result['requirements'][0]['needs_review']


def test_preview_contract_and_edits_recompute_profile():
    response = client.post('/api/preview', json={'resume_text': RESUME, 'job_description': JOB})
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    result = response.json()
    schema = json.loads((ROOT / 'contracts/structured-profile.schema.json').read_text(encoding='utf-8'))
    Draft202012Validator(schema).validate(result)
    assert result['pending_review_count'] == 1
    assert not result['analysis_available']
    assert 'scores' not in result and 'matches' not in result
    edited = client.post('/api/preview', json={'resume_text': RESUME + '\nUsed Docker to package services.', 'job_description': JOB}).json()
    assert 'Docker' in {skill['name'] for skill in edited['resume_skills']}
    assert edited['preparation_id'] != result['preparation_id']


def test_review_confirm_and_changed_text_validation():
    profile = prepare_profile(RESUME, JOB)
    corrections = [{'requirement_id': item['id'], 'category': 'required_skill' if item['category'] == 'unclassified_skill' else item['category']} for item in profile['job_requirements']]
    response = client.post('/api/requirements/review', json={'resume_text': RESUME, 'job_description': JOB, 'corrections': corrections})
    assert response.status_code == 200
    reviewed = response.json()
    assert reviewed['review_status'] == 'confirmed'
    assert reviewed['pending_review_count'] == 0
    assert all(item['classification_method'] == 'user' for item in reviewed['job_requirements'])
    assert 'scores' not in reviewed
    changed_job = 'Required: Kubernetes. ' + ('Build cloud services and support customer applications. ' * 2)
    invalid = client.post('/api/requirements/review', json={'resume_text': RESUME, 'job_description': changed_job, 'corrections': corrections})
    assert invalid.status_code == 422
    assert invalid.json()['code'] == 'invalid_review'


def test_invalid_review_and_conflicting_categories():
    profile = prepare_profile(RESUME, JOB)
    correction = {'requirement_id': profile['job_requirements'][0]['id'], 'category': 'required_skill'}
    duplicate = client.post('/api/requirements/review', json={'resume_text': RESUME, 'job_description': JOB, 'corrections': [correction, correction]})
    assert duplicate.status_code == 422
    bad_category = client.post('/api/requirements/review', json={'resume_text': RESUME, 'job_description': JOB, 'corrections': [{**correction, 'category': 'invented'}]})
    assert bad_category.status_code == 422
    conflicted_job = 'Python required. Python preferred. ' + 'Build dependable customer applications. ' * 3
    conflict = prepare_profile(RESUME, conflicted_job)
    same = [{'requirement_id': item['id'], 'category': item['category']} for item in conflict['job_requirements']]
    assert prepare_profile(RESUME, conflicted_job, same)['review_status'] == 'needs_review'
    assert prepare_profile(RESUME, 'Welcome to our friendly organization.', [])['review_status'] == 'needs_review'


def test_development_skill_categories_match_authored_labels():
    manifest = json.loads((ROOT / 'data/phase-1/manifest.json').read_text(encoding='utf-8'))
    cases = [item for item in manifest['cases'] if item['split'] == 'development']
    assert len(cases) == 18
    for case in cases:
        directory = ROOT / 'data/phase-1' / case['directory']
        job = (directory / 'job-description.txt').read_text(encoding='utf-8')
        labels = json.loads((directory / 'labels.json').read_text(encoding='utf-8'))
        expected = {(item['name'], item['category']) for item in labels['requirements'] if item['category'] in {'required_skill', 'preferred_skill'}}
        actual = {(item['name'], item['category']) for item in extract_job_requirements(job)['requirements'] if item['category'] in {'required_skill', 'preferred_skill'}}
        assert actual == expected, case['case_id']
