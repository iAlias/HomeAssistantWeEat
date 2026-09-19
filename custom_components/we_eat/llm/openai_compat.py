"""OpenAI and DeepSeek (OpenAI-compatible chat completions)."""

from __future__ import annotations

import base64

from .base import LlmError, post_json


class OpenAICompatClient:
    def __init__(self, session, api_key: str, model: str, url: str, supports_vision: bool) -> None:
        self._session = session
        self._api_key = api_key
        self._model = model
        self._url = url
        self.supports_vision = supports_vision

    async def complete(self, prompt, *, system=None, image=None) -> str:
        content = prompt
        if image is not None:
            if not self.supports_vision:
                raise LlmError("questo provider non legge le immagini")
            data, mime = image
            encoded = base64.b64encode(data).decode()
            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}},
            ]
        messages = [{"role": "system", "content": system}] if system else []
        messages.append({"role": "user", "content": content})
        payload = await post_json(
            self._session,
            self._url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            body={
                "model": self._model,
                "messages": messages,
                "response_format": {"type": "json_object"},
            },
        )
        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as err:
            raise LlmError("risposta inattesa dal provider") from err
