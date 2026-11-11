import httpx
import pytest

import extractor
from extractor import GatewayLLM, LLMError

SECRET = "sk-test-secret-key"


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def llm():
    return GatewayLLM("http://gateway.test/", SECRET, "chat-primary")


def test_a_successful_call_returns_the_message_text(monkeypatch):
    seen = {}

    def fake_post(url, headers, json, timeout):
        seen.update(url=url, headers=headers, json=json)
        return FakeResponse(200, {"choices": [{"message": {"content": "hello"}}]})

    monkeypatch.setattr(extractor.httpx, "post", fake_post)
    assert llm().complete("system text", "user text") == "hello"
    assert seen["url"] == "http://gateway.test/v1/chat/completions"
    assert seen["headers"] == {"Authorization": f"Bearer {SECRET}"}
    assert seen["json"]["model"] == "chat-primary"
    assert "temperature" not in seen["json"]
    assert seen["json"]["messages"][0] == {"role": "system", "content": "system text"}


def test_a_gateway_error_status_is_an_llm_error_without_the_key(monkeypatch):
    monkeypatch.setattr(extractor.httpx, "post", lambda *a, **k: FakeResponse(422))
    with pytest.raises(LLMError) as error:
        llm().complete("s", "u")
    assert "422" in str(error.value)
    assert SECRET not in str(error.value)


def test_an_unreachable_gateway_is_an_llm_error_without_the_key(monkeypatch):
    def refuse(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(extractor.httpx, "post", refuse)
    with pytest.raises(LLMError) as error:
        llm().complete("s", "u")
    assert SECRET not in str(error.value)


def test_a_malformed_gateway_answer_is_an_llm_error(monkeypatch):
    monkeypatch.setattr(extractor.httpx, "post", lambda *a, **k: FakeResponse(200, {"oops": 1}))
    with pytest.raises(LLMError):
        llm().complete("s", "u")


def test_no_client_is_made_without_an_api_key(monkeypatch):
    monkeypatch.delenv("GATEWAY_API_KEY", raising=False)
    assert extractor.make_llm() is None


def test_a_client_is_made_from_the_environment(monkeypatch):
    monkeypatch.setenv("GATEWAY_API_KEY", SECRET)
    monkeypatch.setenv("GATEWAY_URL", "http://example.test:4000")
    made = extractor.make_llm()
    assert made.url == "http://example.test:4000"
    assert made.model == "chat-primary"
