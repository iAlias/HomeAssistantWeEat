"""Coordinator: keeps the stored data, recomputes the snapshot and runs the service operations."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_API_KEY,
    CONF_KCAL_TARGET,
    CONF_MEAL_TIMES,
    CONF_MODEL,
    CONF_PROVIDER,
    DEFAULT_MEAL_TIMES,
    DOMAIN,
    PROVIDER_NONE,
)
from .diary import log_extra, log_plan_meal, remove_entry
from .llm import PROVIDERS, LlmError, create_client
from .model import PlanError, normalize_plan
from .snapshot import build_snapshot
from .storage import WeEatStore
from .tasks import estimate_kcal, import_plan

_LOGGER = logging.getLogger(__name__)


class WeEatCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """No polling: refreshed at midnight, at each meal time and after every write."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry)
        self._entry = entry
        self._store = WeEatStore(hass)
        self._data: dict[str, Any] = {}

    @property
    def meal_times(self) -> dict[str, str]:
        return {**DEFAULT_MEAL_TIMES, **self._entry.options.get(CONF_MEAL_TIMES, {})}

    @property
    def kcal_target(self) -> int | None:
        return self._entry.options.get(CONF_KCAL_TARGET)

    @property
    def favorites(self) -> list[str]:
        return list(self._data.get("favorites", []))

    async def async_setup(self) -> None:
        self._data = await self._store.async_load()
        legacy = self._entry.data.get("favorites")
        if legacy and not self._data["favorites"]:
            self._data["favorites"] = list(legacy)
            await self._store.async_save(self._data)
        times = [(0, 0)] + [tuple(int(p) for p in t.split(":")[:2]) for t in self.meal_times.values()]
        for hour, minute in times:
            self._entry.async_on_unload(
                async_track_time_change(self.hass, self._tick, hour=hour, minute=minute, second=0)
            )

    @callback
    def _tick(self, now: datetime) -> None:
        self.hass.async_create_task(self.async_refresh())

    async def _async_update_data(self) -> dict[str, Any]:
        return build_snapshot(
            self._data["plan"],
            self._data["draft"],
            self._data["diary"],
            self.meal_times,
            self.kcal_target,
            dt_util.now(),
        )

    async def _commit(self) -> None:
        await self._store.async_save(self._data)
        await self.async_refresh()

    def _client(self):
        data = self._entry.data
        provider = data.get(CONF_PROVIDER, PROVIDER_NONE)
        if provider == PROVIDER_NONE:
            raise ServiceValidationError(
                "Nessun provider AI configurato: sceglilo nelle opzioni di We Eat oppure inserisci i dati a mano."
            )
        model = data.get(CONF_MODEL) or PROVIDERS[provider].default_model
        return create_client(provider, data[CONF_API_KEY], model, async_get_clientsession(self.hass))

    async def async_import_plan(self, *, text=None, data=None, mime=None) -> None:
        client = self._client()
        try:
            self._data["draft"] = await import_plan(client, text=text, data=data, mime=mime)
        except LlmError as err:
            raise HomeAssistantError(str(err)) from err
        await self._commit()

    async def async_save_draft(self, days: dict[str, Any]) -> None:
        try:
            self._data["draft"] = normalize_plan({"days": days})
        except PlanError as err:
            raise ServiceValidationError(str(err)) from err
        await self._commit()

    async def async_confirm_plan(self) -> None:
        if not self._data["draft"]:
            raise ServiceValidationError("Nessuna bozza da confermare.")
        self._data["plan"], self._data["draft"] = self._data["draft"], None
        await self._commit()

    async def async_log_plan_meal(self, meal: str) -> None:
        try:
            log_plan_meal(self._data["diary"], self._data["plan"], meal, dt_util.now(), uuid4().hex)
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        await self._commit()

    async def async_log_extra(self, text: str, meal: str, kcal: int | None = None) -> None:
        estimated = kcal is None
        if estimated:
            try:
                kcal, _ = await estimate_kcal(self._client(), text, self._data["cache"])
            except LlmError as err:
                raise HomeAssistantError(str(err)) from err
        try:
            log_extra(self._data["diary"], meal, text, kcal, estimated, dt_util.now(), uuid4().hex)
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        await self._commit()

    async def async_remove_entry(self, entry_id: str) -> None:
        if not remove_entry(self._data["diary"], entry_id):
            raise ServiceValidationError("Voce del diario non trovata.")
        await self._commit()
