"""Google Gemini (generateContent)."""

from __future__ import annotations

import base64

from .base import LlmError, post_json

_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiClient:
    supports_vision = True

    def __init__(self, session, api_key: str, model: str) -> None:
        self._session = session
        self._api_key = api_key
        self._model = model

    async def complete(self, prompt, *, system=None, image=None) -> str:
        parts = [{"text": prompt}]
        if image is not None:
            data, mime = image
            parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode()}})
        body = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        payload = await post_json(
            self._session,
            _URL.format(model=self._model),
            headers={"x-goog-api-key": self._api_key},
            body=body,
        )
        try:
            return payload["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as err:
            raise LlmError("risposta inattesa dal provider") from err
