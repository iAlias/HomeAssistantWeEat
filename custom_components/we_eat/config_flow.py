"""Config flow: provider and key, YAML import, and options (target kcal, meal times)."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
    TimeSelector,
)

from .const import (
    CONF_API_KEY,
    CONF_KCAL_TARGET,
    CONF_MEAL_TIMES,
    CONF_MODEL,
    CONF_PROVIDER,
    DEFAULT_MEAL_TIMES,
    DOMAIN,
    MEALS,
    PROVIDER_NONE,
)
from .llm import PROVIDERS, LlmError, create_client
from .model import migrate_recipes

_PROVIDER_LABELS = [SelectOptionDict(value=PROVIDER_NONE, label="Nessuno (solo inserimento manuale)")] + [
    SelectOptionDict(value=p.key, label=p.label) for p in PROVIDERS.values()
]


def _provider_fields(defaults: dict[str, Any]) -> dict[Any, Any]:
    return {
        vol.Required(CONF_PROVIDER, default=defaults.get(CONF_PROVIDER, PROVIDER_NONE)): SelectSelector(
            SelectSelectorConfig(options=_PROVIDER_LABELS, mode=SelectSelectorMode.DROPDOWN)
        ),
        vol.Optional(CONF_API_KEY, default=defaults.get(CONF_API_KEY, "")): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Optional(CONF_MODEL, default=defaults.get(CONF_MODEL, "")): str,
    }


async def _validate(hass, data: dict[str, Any]) -> dict[str, str]:
    provider = data[CONF_PROVIDER]
    if provider == PROVIDER_NONE:
        return {}
    if not data.get(CONF_API_KEY):
        return {CONF_API_KEY: "api_key_required"}
    model = data.get(CONF_MODEL) or PROVIDERS[provider].default_model
    client = create_client(provider, data[CONF_API_KEY], model, async_get_clientsession(hass))
    try:
        await client.complete('Rispondi con {"ok": true}', system="Rispondi solo con JSON.")
    except LlmError:
        return {"base": "cannot_connect"}
    return {}


def _hhmm(value: str | None, default: str) -> str:
    match = re.match(r"^(\d{2}:\d{2})", value or "")
    return match.group(1) if match else default


class WeEatConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = await _validate(self.hass, user_input)
            if not errors:
                return self.async_create_entry(title="We Eat", data=user_input)
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(_provider_fields(user_input or {})), errors=errors
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        return self.async_create_entry(
            title="We Eat",
            data={CONF_PROVIDER: PROVIDER_NONE, "favorites": migrate_recipes(import_data)},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return WeEatOptionsFlow(config_entry)


class WeEatOptionsFlow(OptionsFlow):
    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            provider_data = {k: user_input.get(k, "") for k in (CONF_PROVIDER, CONF_API_KEY, CONF_MODEL)}
            errors = await _validate(self.hass, provider_data)
            if not errors:
                self.hass.config_entries.async_update_entry(
                    self._entry, data={**self._entry.data, **provider_data}
                )
                options: dict[str, Any] = {
                    CONF_MEAL_TIMES: {
                        meal: _hhmm(user_input.get(f"time_{meal}"), DEFAULT_MEAL_TIMES[meal]) for meal in MEALS
                    }
                }
                if user_input.get(CONF_KCAL_TARGET):
                    options[CONF_KCAL_TARGET] = int(user_input[CONF_KCAL_TARGET])
                return self.async_create_entry(data=options)
        current = user_input or {**self._entry.data}
        times = {**DEFAULT_MEAL_TIMES, **self._entry.options.get(CONF_MEAL_TIMES, {})}
        fields = _provider_fields(current)
        fields[
            vol.Optional(
                CONF_KCAL_TARGET, description={"suggested_value": self._entry.options.get(CONF_KCAL_TARGET)}
            )
        ] = NumberSelector(NumberSelectorConfig(min=500, max=10000, step=50, mode=NumberSelectorMode.BOX))
        for meal in MEALS:
            fields[vol.Optional(f"time_{meal}", description={"suggested_value": f"{times[meal]}:00"})] = TimeSelector()
        return self.async_show_form(step_id="init", data_schema=vol.Schema(fields), errors=errors)
