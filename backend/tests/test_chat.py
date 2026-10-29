import json
from urllib.error import HTTPError, URLError
import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app import chat


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'test-only-placeholder')
    monkeypatch.setenv('CHAT_DAILY_LIMIT', '100')
    with TestClient(create_app()) as c:
        yield c


@pytest.mark.parametrize('payload', [{}, {'message':''}, {'message':'   '}, {'message':'x'*1201}, {'message':123}, {'message':'fraud','model':'expensive'}])
def test_invalid_chat(client, payload):
    assert client.post('/api/chat', json=payload).status_code == 422


def test_missing_key(client, monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY')
    assert client.post('/api/chat', json={'message':'What is fraud detection?'}).status_code == 503


def test_provider_contract(client, monkeypatch):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size):
            return json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'in_scope':True,'answer':'The model uses synthetic data.'})}}]}).encode()
    def fake(req, timeout):
        payload = json.loads(req.data)
        assert req.full_url == 'https://api.groq.com/openai/v1/chat/completions'
        assert payload['model'] == 'openai/gpt-oss-20b'
        assert 'provider' not in payload
        assert payload['max_tokens'] == 800
        assert payload['messages'][0]['role'] == 'system'
        assert len(payload['messages']) == 2
        assert timeout == 25
        return Response()
    monkeypatch.setattr(chat, 'urlopen', fake)
    assert client.post('/api/chat', json={'message':'Which dataset is used?'}).json() == {'answer':'The model uses synthetic data.'}


def test_refusal_discards_provider_answer(client, monkeypatch):
    monkeypatch.setattr(chat, 'completion', lambda *args: chat.ChatOutput(in_scope=False, answer='Unrelated content'))
    assert client.post('/api/chat', json={'message':'Tell me a joke'}).json() == {'answer':chat.REFUSAL}


def test_upstream_failure_is_sanitized(client, monkeypatch):
    def fail(*args): raise URLError('secret provider details')
    monkeypatch.setattr(chat, 'completion', fail)
    result = client.post('/api/chat', json={'message':'Explain fraud'})
    assert result.status_code == 502
    assert 'secret' not in result.text


@pytest.mark.parametrize('status,expected,message', [
    (429,503,'rate-limiting'), (401,503,'authentication'),
    (403,503,'authentication'), (402,503,'credits'), (500,502,'service error')])
def test_provider_http_errors_are_actionable(client, monkeypatch, status, expected, message):
    def fail(*args):
        raise HTTPError('https://api.groq.com/openai/v1/chat/completions', status, 'private provider details', {}, None)
    monkeypatch.setattr(chat, 'completion', fail)
    result = client.post('/api/chat', json={'message':'Hello'})
    assert result.status_code == expected
    assert message in result.json()['error']['message']
    assert 'private provider details' not in result.text
    if status == 429:
        assert result.headers['retry-after'] == '60'


def test_chat_budget(client, monkeypatch):
    monkeypatch.setenv('CHAT_DAILY_LIMIT', '1')
    monkeypatch.setattr(chat, 'completion', lambda *args: chat.ChatOutput(in_scope=True, answer='Educational answer'))
    assert client.post('/api/chat', json={'message':'Explain fraud'}).status_code == 200
    assert client.post('/api/chat', json={'message':'Explain fraud'}).status_code == 429


@pytest.mark.parametrize('raw', [b'not json', b'{}',
    json.dumps({'choices':[{'finish_reason':'length','message':{'content':'{}'}}]}).encode(),
    json.dumps({'choices':[{'finish_reason':'stop','message':{'content':'{"in_scope":"true","answer":"x"}'}}]}).encode(),
    b'x'*65537], ids=['invalid-json','missing-choices','truncated','wrong-type','oversized'])
def test_malformed_provider_response(client, monkeypatch, raw):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size): return raw
    monkeypatch.setattr(chat, 'urlopen', lambda *args, **kwargs: Response())
    assert client.post('/api/chat', json={'message':'Explain fraud'}).status_code == 502
