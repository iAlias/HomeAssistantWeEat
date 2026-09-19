"""Anthropic Claude (messages API)."""

from __future__ import annotations

import base64

from .base import LlmError, post_json

_URL = "https://api.anthropic.com/v1/messages"


class ClaudeClient:
    supports_vision = True

    def __init__(self, session, api_key: str, model: str) -> None:
        self._session = session
        self._api_key = api_key
        self._model = model

    async def complete(self, prompt, *, system=None, image=None) -> str:
        content = []
        if image is not None:
            data, mime = image
            content.append(
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": mime, "data": base64.b64encode(data).decode()},
                }
            )
        content.append({"type": "text", "text": prompt})
        body = {"model": self._model, "max_tokens": 4096, "messages": [{"role": "user", "content": content}]}
        if system:
            body["system"] = system
        payload = await post_json(
            self._session,
            _URL,
            headers={"x-api-key": self._api_key, "anthropic-version": "2023-06-01"},
            body=body,
        )
        try:
            return payload["content"][0]["text"]
        except (KeyError, IndexError, TypeError) as err:
            raise LlmError("risposta inattesa dal provider") from err
