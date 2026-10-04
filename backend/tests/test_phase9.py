import json
import pytest
from jsonschema import Draft202012Validator
from backend.main import ROOT
from backend.services import ai_enrichment as ai
from backend.tests.test_phase5 import client, corrections

RESUME = 'Projects\nTracked application events using Python.\nEducation\nCompleted an introductory programming course.'
JOB = ('Monitor logs. ' + 'This fictional team creates reliable tools for internal customers. ' * 2).strip()


def body():
    return {'resume_text': RESUME, 'job_description': JOB, 'requirements_confirmed': True, 'category_corrections': corrections(JOB), 'cloud_consent': True}


def fake_provider(path, payload):
    if path == 'embeddings':
        return {'data': [{'index': i, 'embedding': [1, 0]} for i in range(len(payload['input']))], 'usage': {'total_tokens': 20}}
    data = json.loads(payload['input'])
    requirement = data['requirements'][0]['id']
    output = {'suggestions': [{'requirement_id': requirement, 'evidence_id': 'source-0', 'priority': 'medium', 'rationale': 'The existing excerpt needs a clearer connection to the task.', 'action': 'If you monitored logs, describe that contribution truthfully.', 'rewrite': RESUME.splitlines()[1]}]}
    return {'status': 'completed', 'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(output)}]}], 'usage': {'input_tokens': 100, 'output_tokens': 60}}


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic-key')
    monkeypatch.setattr(ai, 'post_openai', fake_provider)


def test_missing_key_and_consent_do_not_affect_local_report(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    assert client.get('/api/ai/status').json()['configured'] is False
    assert client.post('/api/ai/analyze', json=body()).status_code == 503
    assert client.post('/api/ai/analyze', json={**body(), 'cloud_consent': False}).status_code == 422
    local = client.post('/api/compare', json=body()).json()
    assert local['ats_assessment']['score'] == local['scores']['overall'] == 0
    assert 'ai_analysis' not in local


def test_enrichment_is_reviewable_schema_valid_and_exportable(provider):
    response = client.post('/api/ai/analyze', json=body())
    assert response.status_code == 200
    enhanced = response.json()
    report = enhanced['report']
    assert report['scores']['overall'] == 0
    assert report['ai_analysis']['provider'] == 'OpenAI'
    assert any('Semantic proposal' in p['reason'] for p in report['possible_evidence'])
    assert report['suggestions'][-1]['rewrite'] == RESUME.splitlines()[1]
    Draft202012Validator(json.loads((ROOT / 'contracts/analysis-result-v1.1.schema.json').read_text(encoding='utf-8'))).validate(report)
    candidate = report['possible_evidence'][0]
    decision = {'requirement_id': candidate['requirement_id'], 'evidence_id': candidate['evidence']['id'], 'decision': 'accept'}
    accepted = client.post('/api/compare', json={**body(), 'ai_context': enhanced['ai_context'], 'evidence_decisions': [decision]}).json()
    assert accepted['scores']['overall'] == 100
    assert accepted['matches'][0]['method'] == 'user_confirmed'
    exported = client.post('/api/report/export', json={**body(), 'ai_context': enhanced['ai_context'], 'format': 'json'}).json()
    assert exported['ai_analysis']['generation_id'] == report['ai_analysis']['generation_id']
    assert exported['suggestions'][-1]['rewrite'] == report['suggestions'][-1]['rewrite']
    pdf = client.post('/api/report/export', json={**body(), 'ai_context': enhanced['ai_context'], 'format': 'pdf'})
    assert pdf.status_code == 200 and pdf.content.startswith(b'%PDF-')


def test_signed_advice_rejects_tampering_edits_and_category_changes(provider):
    token = client.post('/api/ai/analyze', json=body()).json()['ai_context']
    for change in [{'ai_context': token+'x'}, {'resume_text': RESUME+'\nExtra reviewed source text.'}, {'category_corrections': [{**corrections(JOB)[0], 'category': 'excluded'}]}]:
        assert client.post('/api/compare', json={**body(), 'ai_context': token, **change}).status_code == 422
    assert client.post('/api/ai/analyze', json={**body(), 'ai_context': token}).status_code == 422


def test_invented_rewrites_are_discarded(provider, monkeypatch):
    def invented(path, payload):
        response = fake_provider(path, payload)
        if path == 'responses':
            output = json.loads(response['output'][0]['content'][0]['text'])
            output['suggestions'][0]['rewrite'] = 'Improved revenue by 50% using AWS.'
            response['output'][0]['content'][0]['text'] = json.dumps(output)
        return response
    monkeypatch.setattr(ai, 'post_openai', invented)
    report = client.post('/api/ai/analyze', json=body()).json()['report']
    assert report['suggestions'][-1]['rewrite'] is None
    assert report['ai_analysis']['discarded_rewrites'] == 1


@pytest.mark.parametrize('failure', ['refusal', 'bad_id', 'bad_vectors'])
def test_malformed_ai_results_fail_without_replacing_local_analysis(provider, monkeypatch, failure):
    def broken(path, payload):
        response = fake_provider(path, payload)
        if failure == 'bad_vectors' and path == 'embeddings':
            response['data'][0]['embedding'] = [float('nan'), 0]
        if path == 'responses':
            if failure == 'refusal': return {'status': 'incomplete', 'output': []}
            if failure == 'bad_id':
                data = json.loads(response['output'][0]['content'][0]['text']);data['suggestions'][0]['requirement_id'] = 'invented'
                response['output'][0]['content'][0]['text'] = json.dumps(data)
        return response
    monkeypatch.setattr(ai, 'post_openai', broken)
    assert client.post('/api/ai/analyze', json=body()).status_code == 502


def test_large_inputs_fail_before_paid_calls(provider, monkeypatch):
    monkeypatch.setattr(ai, 'post_openai', lambda *_args: pytest.fail('Should not call provider'))
    too_long = 'Projects\nTracked logs ' + 'x'*2200
    assert client.post('/api/ai/analyze', json={**body(), 'resume_text': too_long}).status_code == 422


@pytest.mark.parametrize('status,code', [(401, 'ai_access_error'), (403, 'ai_access_error'), (429, 'ai_rate_limited'), (500, 'ai_provider_error')])
def test_provider_http_errors_are_actionable_without_exposing_credentials(monkeypatch, status, code):
    from urllib.error import HTTPError
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic-secret')
    def rejected(request, timeout):
        assert request.full_url == 'https://api.openai.com/v1/responses'
        raise HTTPError(request.full_url, status, 'private provider details', {}, None)
    monkeypatch.setattr(ai, 'urlopen', rejected)
    with pytest.raises(ai.AIError) as raised:
        ai.post_openai('responses', {'store': False})
    assert raised.value.code == code
    assert 'synthetic-secret' not in str(raised.value)
    assert 'private provider details' not in str(raised.value)
