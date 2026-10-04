import pytest

from backend.services.qualification_matcher import qualification_findings
from backend.services import ai_enrichment as ai
from backend.tests.test_phase9 import body, client, provider
from scripts.verify_live_ai import verify


@pytest.mark.parametrize('education', [
    "Bachelor's degree in computer science. Master's degree in literature.",
    "Bachelor's degree in computer science; Master's degree in literature.",
    "Bachelor's degree in computer science and Master's degree in literature.",
    "Master's degree in literature. Computer science course.",
])
def test_degree_type_and_subject_cannot_cross_credentials(education):
    requirements = [{'id': 'degree', 'category': 'qualification', 'name': "Master's degree in computer science required."}]
    finding = qualification_findings([{'name': 'Education', 'text': education}], requirements, 'hash')[0]
    assert finding['status'] != 'met'
    assert finding['evidence'] is None


def test_completed_degree_can_follow_an_unrelated_incomplete_degree():
    requirements = [{'id': 'degree', 'category': 'qualification', 'name': "Bachelor's degree in computer science required."}]
    education = "Pursuing Master's degree in literature. Completed Bachelor's degree in computer science."
    finding = qualification_findings([{'name': 'Education', 'text': education}], requirements, 'hash')[0]
    assert finding['status'] == 'met'
    assert finding['evidence']['text'] == education


@pytest.mark.parametrize('value', [1, 1.0, 'true', 'yes', False, None])
def test_cloud_consent_requires_actual_boolean_true(provider, monkeypatch, value):
    monkeypatch.setattr(ai, 'post_openai', lambda *_: pytest.fail('Consent rejection must happen before a paid call'))
    response = client.post('/api/ai/analyze', json={**body(), 'cloud_consent': value})
    assert response.status_code == 422


@pytest.mark.parametrize('value', [1, 1.0, 'true', False])
def test_requirement_confirmation_requires_actual_boolean_true(value):
    response = client.post('/api/compare', json={**body(), 'requirements_confirmed': value})
    assert response.status_code == 422


def local_api(_base, path, payload=None):
    response = client.get(path) if payload is None else client.post(path, json=payload)
    assert response.status_code == 200
    return response.content if path == '/api/report/export' and payload['format'] == 'pdf' else response.json()


def test_live_verifier_checks_signed_json_pdf_flow_with_controlled_provider(provider):
    outcome = verify('http://127.0.0.1:8001', True, local_api)
    assert outcome['status'] == 'passed'
    assert outcome['score_preserved'] and outcome['json_export'] and outcome['pdf_export']


def test_verifier_does_not_call_ai_without_explicit_live_flag():
    calls = []
    def request(_base, path, payload=None):
        calls.append(path)
        return {'configured': True}
    assert verify('http://localhost:8001', False, request)['status'] == 'not_run'
    assert calls == ['/api/ai/status']


def test_verifier_missing_key_is_not_a_fake_pass():
    with pytest.raises(ValueError, match='still unverified'):
        verify('http://localhost:8001', True, lambda *_: {'configured': False})


@pytest.mark.parametrize('url', ['https://example.com', 'http://localhost:8001/api', 'http://user:secret@localhost:8001', 'http://localhost:8001?redirect=example.com'])
def test_verifier_rejects_nonlocal_or_credential_urls(url):
    with pytest.raises(ValueError, match='local backend'):
        verify(url, True, lambda *_: pytest.fail('Do not send verification requests to this URL'))
