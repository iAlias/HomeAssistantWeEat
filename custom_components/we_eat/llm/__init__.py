"""Built-in LLM client used by We Eat (no dependency on other integrations)."""

from __future__ import annotations

from dataclasses import dataclass

from .base import LlmClient, LlmError
from .claude import ClaudeClient
from .gemini import GeminiClient
from .openai_compat import OpenAICompatClient

__all__ = ["LlmClient", "LlmError", "PROVIDERS", "Provider", "create_client"]


@dataclass(frozen=True)
class Provider:
    key: str
    label: str
    default_model: str
    supports_vision: bool


PROVIDERS = {
    p.key: p
    for p in (
        Provider("openai", "OpenAI", "gpt-4o-mini", True),
        Provider("deepseek", "DeepSeek (solo testo)", "deepseek-chat", False),
        Provider("gemini", "Google Gemini", "gemini-2.0-flash", True),
        Provider("claude", "Anthropic Claude", "claude-haiku-4-5-20251001", True),
    )
}

_OPENAI_URLS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "deepseek": "https://api.deepseek.com/chat/completions",
}


def create_client(provider: str, api_key: str, model: str, session) -> LlmClient:
    if provider in _OPENAI_URLS:
        return OpenAICompatClient(
            session, api_key, model, _OPENAI_URLS[provider], PROVIDERS[provider].supports_vision
        )
    if provider == "gemini":
        return GeminiClient(session, api_key, model)
    if provider == "claude":
        return ClaudeClient(session, api_key, model)
    raise LlmError(f"provider sconosciuto: {provider}")
