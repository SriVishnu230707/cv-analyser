import asyncio

from fastapi.testclient import TestClient

from backend.main import app
from backend.security import MAX_REQUEST_BYTES, SecurityMiddleware


def test_token_protects_analysis_before_validation(monkeypatch):
    monkeypatch.setenv('CV_API_TOKEN', 't' * 43)
    client = TestClient(app)
    assert client.get('/health').status_code == 200
    assert client.post('/api/ai/analyze', json={}).status_code == 401
    assert client.get('/api/demo/job', headers={'Authorization': 'Bearer wrong'}).status_code == 401
    response = client.get('/api/demo/job', headers={'Authorization': 'Bearer ' + 't' * 43})
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'


def test_foreign_browser_cannot_spend_local_ai_budget(monkeypatch):
    monkeypatch.delenv('CV_API_TOKEN', raising=False)
    client = TestClient(app)
    assert client.post('/api/ai/analyze', json={}, headers={'Origin': 'https://evil.example'}).status_code == 403
    assert client.get('/api/demo/job', headers={'Origin': 'http://127.0.0.1:5173'}).status_code == 200


def test_declared_oversized_upload_rejected_before_parser(monkeypatch):
    monkeypatch.delenv('CV_API_TOKEN', raising=False)
    response = TestClient(app).post('/api/extract', content=b'x', headers={'Content-Length': str(MAX_REQUEST_BYTES + 1)})
    assert response.status_code == 413


def test_chunked_limit_and_remote_fail_closed(monkeypatch):
    monkeypatch.delenv('CV_API_TOKEN', raising=False)

    async def run(peer, chunks, headers=()):
        called, sent = [], []
        async def downstream(*args):
            called.append(True)
        async def receive():
            return chunks.pop(0)
        async def send(message):
            sent.append(message)
        await SecurityMiddleware(downstream)({'type': 'http', 'path': '/api/extract', 'client': (peer, 1), 'headers': headers}, receive, send)
        assert not called
        return sent[0]['status']

    assert asyncio.run(run('192.168.0.10', [], [(b'x-forwarded-for', b'127.0.0.1')])) == 503
    chunks = [{'type': 'http.request', 'body': b'x' * MAX_REQUEST_BYTES, 'more_body': True},
              {'type': 'http.request', 'body': b'y', 'more_body': False}]
    assert asyncio.run(run('127.0.0.1', chunks)) == 413
