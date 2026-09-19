"""Persistent storage for the plan, the diary and the LLM cache."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORAGE_VERSION = 1


def _empty() -> dict[str, Any]:
    return {"plan": None, "draft": None, "diary": [], "cache": {}, "favorites": []}


class WeEatStore:
    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, DOMAIN)

    async def async_load(self) -> dict[str, Any]:
        return {**_empty(), **(await self._store.async_load() or {})}

    async def async_save(self, data: dict[str, Any]) -> None:
        await self._store.async_save(data)
