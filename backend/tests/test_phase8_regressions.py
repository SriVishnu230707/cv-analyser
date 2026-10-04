import pytest
from backend.services.evidence_matcher import rule_match
from backend.tests.test_phase5 import client, corrections


@pytest.mark.parametrize('requirement,evidence', [
    ('Monitor logs.', 'Monitored metrics.'),
    ('Monitor service health.', 'Monitored logs.'),
    ('Monitor metrics.', 'Monitored service health.'),
    ('Automate deployment pipelines.', 'Automated build pipelines.'),
    ('Automate CI/CD pipelines.', 'Automated deployment pipelines.'),
    ('Build ETL pipelines.', 'Built data pipelines.'),
    ('Build data pipelines.', 'Built ETL pipelines.'),
    ('Monitor logs, metrics.', 'Monitored logs.'),
])
def test_distinct_task_targets_are_not_interchangeable(requirement, evidence):
    assert not rule_match(requirement, evidence)


@pytest.mark.parametrize('requirement,evidence', [
    ('Monitor logs.', 'Monitored logs.'),
    ('Monitor metrics.', 'Monitored metrics.'),
    ('Monitor service health.', 'Monitored service health.'),
    ('Automate deployment pipelines.', 'Automated deployment pipeline.'),
    ('Automate CI/CD pipelines.', 'Automated CI/CD pipeline.'),
    ('Build ETL pipelines.', 'Built ETL pipeline.'),
    ('Build data pipelines.', 'Built data pipelines.'),
])
def test_same_task_targets_and_singular_variants_still_match(requirement, evidence):
    assert rule_match(requirement, evidence)


def test_mismatched_target_needs_confirmation_in_comparison_and_export():
    job = ('Monitor logs. ' + 'Our team creates useful customer tools. ' * 3).strip()
    resume = 'Projects\nMonitored metrics.\nEducation\nCompleted an introductory course.'
    body = {'resume_text': resume, 'job_description': job, 'requirements_confirmed': True, 'category_corrections': corrections(job)}
    response = client.post('/api/compare', json=body)
    assert response.status_code == 200
    report = response.json()
    assert report['scores']['overall'] == 0
    assert report['matches'] == []
    assert report['rule_version'] == '1.1.1'
    candidate = report['possible_evidence'][0]
    exported = client.post('/api/report/export', json={**body, 'format': 'json'})
    assert exported.json()['scores']['overall'] == 0
    decision = {'requirement_id': candidate['requirement_id'], 'evidence_id': candidate['evidence']['id'], 'decision': 'accept'}
    confirmed = client.post('/api/compare', json={**body, 'evidence_decisions': [decision]}).json()
    assert confirmed['scores']['overall'] == 100
    assert confirmed['matches'][0]['method'] == 'user_confirmed'
