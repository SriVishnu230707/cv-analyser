import pytest
from backend.services import ai_enrichment as ai
from backend.tests.test_phase9 import body, fake_provider, client, provider


@pytest.mark.parametrize('output', [[None], [42], [{'type': 'message', 'content': None}], [{'type': 'message', 'content': [None]}], [{'type': 'message', 'content': [{'type': 'output_text', 'text': 42}]}]])
def test_malformed_provider_envelopes_return_actionable_errors(provider, monkeypatch, output):
    def malformed(path, payload):
        response = fake_provider(path, payload)
        if path == 'responses': response['output'] = output
        return response
    monkeypatch.setattr(ai, 'post_openai', malformed)
    response = client.post('/api/ai/analyze', json=body())
    assert response.status_code == 502
    assert response.json()['code'] == 'ai_invalid_response'
    assert client.post('/api/compare', json=body()).status_code == 200


@pytest.mark.parametrize('source,rewrite', [('Monitored 150 logs.', '50 logs.'), ('Built helper scripts while a teammate deployed AWS.', 'deployed AWS.'), ('Built Python tools using SQL.', 'Python tools')])
def test_source_fragments_cannot_change_metrics_or_ownership(source, rewrite):
    assert rewrite in source  # These slipped through the previous guard.
    assert not ai.source_sentence(rewrite, {'text': source})


def test_complete_source_sentences_are_allowed_with_dotted_technologies():
    source = {'text': 'Built .NET services. Monitored 150 logs.'}
    assert ai.source_sentence('Built .NET services.', source)
    assert ai.source_sentence('Monitored 150 logs.', source)
    assert not ai.source_sentence('Monitored 50 logs.', source)


@pytest.mark.parametrize('left,right', [([True, 0], [1, 0]), ([0, 0], [1, 0]), ([float('inf')], [1]), (None, [1]), ([1], [1, 0])])
def test_invalid_vectors_fail_cleanly(left, right):
    with pytest.raises(ai.AIError, match='embedding response was invalid'):
        ai.cosine(left, right)


def test_large_finite_vectors_have_stable_similarity():
    assert ai.cosine([1e200, 0], [1e200, 0]) == pytest.approx(1)


def test_oversized_integer_vectors_return_controlled_error():
    with pytest.raises(ai.AIError):
        ai.cosine([10**400, 1], [1, 0])


def test_boolean_embedding_indices_are_rejected(provider, monkeypatch):
    def malformed(path, payload):
        response = fake_provider(path, payload)
        if path == 'embeddings':
            response['data'][0]['index'] = False
        return response
    monkeypatch.setattr(ai, 'post_openai', malformed)
    response = client.post('/api/ai/analyze', json=body())
    assert response.status_code == 502
    assert response.json()['code'] == 'ai_invalid_response'
