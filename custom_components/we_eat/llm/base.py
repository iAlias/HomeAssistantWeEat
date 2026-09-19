"""Shared pieces of the built-in LLM client."""

from __future__ import annotations

import json
from typing import Any, Protocol

import aiohttp


class LlmError(Exception):
    """The LLM call failed or returned something unusable."""


class LlmClient(Protocol):
    supports_vision: bool

    async def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        image: tuple[bytes, str] | None = None,
    ) -> str: ...


def extract_json(text: str) -> Any:
    """Parse the first JSON object in `text`, tolerating code fences and prose around it."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise LlmError("la risposta non contiene JSON")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as err:
        raise LlmError(f"JSON non valido: {err}") from err


async def post_json(session, url: str, *, headers: dict[str, str], body: dict[str, Any]) -> Any:
    """POST a JSON body; the error messages never include the headers (API keys)."""
    try:
        async with session.post(
            url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=90)
        ) as response:
            if response.status != 200:
                detail = (await response.text())[:200]
                raise LlmError(f"HTTP {response.status}: {detail}")
            return await response.json()
    except aiohttp.ClientError as err:
        raise LlmError(f"errore di rete: {err}") from err
    except TimeoutError as err:
        raise LlmError("timeout della richiesta") from err
