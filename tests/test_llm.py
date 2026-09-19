import asyncio
import json

import pytest

from custom_components.we_eat.llm import PROVIDERS, create_client
from custom_components.we_eat.llm.base import LlmError, extract_json


class FakeResponse:
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload

    async def json(self):
        return self._payload

    async def text(self):
        return json.dumps(self._payload)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeSession:
    def __init__(self, payload, status=200):
        self._payload = payload
        self._status = status
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(self._status, self._payload)


def run(coro):
    return asyncio.run(coro)


def test_extract_json_handles_fences_and_prose():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Ecco: {"a": {"b": 2}} fine') == {"a": {"b": 2}}


@pytest.mark.parametrize("text", ["niente json", "{rotto", ""])
def test_extract_json_rejects_garbage(text):
    with pytest.raises(LlmError):
        extract_json(text)


def test_providers_catalogue():
    assert set(PROVIDERS) == {"openai", "deepseek", "gemini", "claude"}
    assert PROVIDERS["deepseek"].supports_vision is False
    assert all(p.default_model for p in PROVIDERS.values())


def test_unknown_provider():
    with pytest.raises(LlmError, match="provider"):
        create_client("boh", "k", "m", FakeSession({}))


def test_openai_request_and_response():
    session = FakeSession({"choices": [{"message": {"content": '{"ok": true}'}}]})
    client = create_client("openai", "sk-secret", "gpt-x", session)
    assert run(client.complete("ciao", system="sys")) == '{"ok": true}'
    url, kwargs = session.calls[0]
    assert url == "https://api.openai.com/v1/chat/completions"
    assert kwargs["headers"]["Authorization"] == "Bearer sk-secret"
    body = kwargs["json"]
    assert body["model"] == "gpt-x"
    assert body["messages"][0] == {"role": "system", "content": "sys"}
    assert body["response_format"] == {"type": "json_object"}


def test_openai_sends_images_as_data_uri():
    session = FakeSession({"choices": [{"message": {"content": "{}"}}]})
    client = create_client("openai", "k", "m", session)
    run(client.complete("leggi", image=(b"\x01\x02", "image/jpeg")))
    content = session.calls[0][1]["json"]["messages"][-1]["content"]
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_deepseek_uses_its_own_url_and_rejects_images():
    session = FakeSession({"choices": [{"message": {"content": "{}"}}]})
    client = create_client("deepseek", "k", "deepseek-chat", session)
    assert client.supports_vision is False
    run(client.complete("ciao"))
    assert session.calls[0][0] == "https://api.deepseek.com/chat/completions"
    with pytest.raises(LlmError, match="immagini"):
        run(client.complete("leggi", image=(b"x", "image/png")))


def test_gemini_request_and_response():
    payload = {"candidates": [{"content": {"parts": [{"text": "{}"}]}}]}
    session = FakeSession(payload)
    client = create_client("gemini", "g-secret", "gemini-x", session)
    assert run(client.complete("ciao", system="sys", image=(b"\x01", "image/png"))) == "{}"
    url, kwargs = session.calls[0]
    assert url.endswith("/models/gemini-x:generateContent")
    assert kwargs["headers"]["x-goog-api-key"] == "g-secret"
    body = kwargs["json"]
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert body["systemInstruction"]["parts"][0]["text"] == "sys"
    assert body["contents"][0]["parts"][1]["inline_data"]["mime_type"] == "image/png"


def test_claude_request_and_response():
    session = FakeSession({"content": [{"type": "text", "text": "{}"}]})
    client = create_client("claude", "c-secret", "claude-x", session)
    assert run(client.complete("ciao", system="sys", image=(b"\x01", "image/png"))) == "{}"
    url, kwargs = session.calls[0]
    assert url == "https://api.anthropic.com/v1/messages"
    assert kwargs["headers"]["x-api-key"] == "c-secret"
    assert kwargs["headers"]["anthropic-version"] == "2023-06-01"
    body = kwargs["json"]
    assert body["system"] == "sys"
    assert body["messages"][0]["content"][0]["type"] == "image"


@pytest.mark.parametrize("provider", ["openai", "deepseek", "gemini", "claude"])
def test_http_errors_become_llm_errors_without_leaking_the_key(provider):
    client = create_client(provider, "sk-secret", "m", FakeSession({"error": "no"}, status=401))
    with pytest.raises(LlmError) as err:
        run(client.complete("ciao"))
    assert "401" in str(err.value)
    assert "sk-secret" not in str(err.value)


@pytest.mark.parametrize("provider", ["openai", "gemini", "claude"])
def test_unexpected_payload_becomes_llm_error(provider):
    client = create_client(provider, "k", "m", FakeSession({"boh": 1}))
    with pytest.raises(LlmError, match="risposta inattesa"):
        run(client.complete("ciao"))
