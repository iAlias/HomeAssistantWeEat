"""We Eat: the dietitian's weekly plan and a kcal diary, as a Home Assistant integration."""

from __future__ import annotations

import base64
import binascii
from pathlib import Path

import voluptuous as vol

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .const import (
    CARD_FILENAME,
    CONF_RECIPES,
    DOMAIN,
    KEY_CARD_URL,
    KEY_STATIC_PATH,
    MEALS,
    STATIC_URL,
)
from .coordinator import WeEatCoordinator

FRONTEND_DIR = Path(__file__).parent / "frontend"

PLATFORMS = ["sensor"]
MAX_FILE_BYTES = 3 * 1024 * 1024

type WeEatConfigEntry = ConfigEntry[WeEatCoordinator]

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({vol.Optional(CONF_RECIPES): [cv.string]})}, extra=vol.ALLOW_EXTRA
)

MEAL = vol.In(MEALS)
IMPORT_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Optional("text"): cv.string,
            vol.Optional("file_b64"): cv.string,
            vol.Optional("mime_type"): cv.string,
        }
    ),
    cv.has_at_least_one_key("text", "file_b64"),
)
SAVE_DRAFT_SCHEMA = vol.Schema({vol.Required("days"): dict})
MEAL_SCHEMA = vol.Schema({vol.Required("meal"): MEAL})
EXTRA_SCHEMA = vol.Schema(
    {
        vol.Required("text"): cv.string,
        vol.Required("meal"): MEAL,
        vol.Optional("kcal"): vol.All(vol.Coerce(int), vol.Range(min=0, max=10000)),
    }
)
REMOVE_SCHEMA = vol.Schema({vol.Required("entry_id"): cv.string})


def _coordinator(hass: HomeAssistant) -> WeEatCoordinator:
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        raise ServiceValidationError("We Eat non è configurato.")
    return entries[0].runtime_data


async def _async_serve_card(hass: HomeAssistant) -> None:
    """Serve the card and load it in the UI, so there is no resource to add by hand.

    Safe to call repeatedly: each half is flagged only once it has actually succeeded, so a
    failure — or a frontend that is not up yet — is retried on the next call instead of being
    silently skipped forever.
    """
    if not hass.data.get(KEY_STATIC_PATH):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(FRONTEND_DIR), True)]
        )
        hass.data[KEY_STATIC_PATH] = True

    if hass.data.get(KEY_CARD_URL) or "frontend" not in hass.config.components:
        return
    # Imported here: the frontend package is absent in the test environment.
    from homeassistant.components.frontend import add_extra_js_url  # noqa: PLC0415

    integration = await async_get_integration(hass, DOMAIN)
    add_extra_js_url(hass, f"{STATIC_URL}/{CARD_FILENAME}?v={integration.version}")
    hass.data[KEY_CARD_URL] = True


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    await _async_serve_card(hass)

    if DOMAIN in config:
        ir.async_create_issue(
            hass,
            DOMAIN,
            "yaml_deprecated",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="yaml_deprecated",
        )
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=config[DOMAIN]
            )
        )

    async def import_plan(call: ServiceCall) -> None:
        data = mime = None
        if "file_b64" in call.data:
            try:
                data = base64.b64decode(call.data["file_b64"], validate=True)
            except (binascii.Error, ValueError) as err:
                raise ServiceValidationError("file_b64 non è base64 valido.") from err
            if len(data) > MAX_FILE_BYTES:
                raise ServiceValidationError("Il file supera i 3 MB.")
            mime = call.data.get("mime_type")
        await _coordinator(hass).async_import_plan(text=call.data.get("text"), data=data, mime=mime)

    async def save_draft(call: ServiceCall) -> None:
        await _coordinator(hass).async_save_draft(call.data["days"])

    async def confirm_plan(call: ServiceCall) -> None:
        await _coordinator(hass).async_confirm_plan()

    async def log_plan_meal(call: ServiceCall) -> None:
        await _coordinator(hass).async_log_plan_meal(call.data["meal"])

    async def log_extra(call: ServiceCall) -> None:
        await _coordinator(hass).async_log_extra(call.data["text"], call.data["meal"], call.data.get("kcal"))

    async def remove_entry(call: ServiceCall) -> None:
        await _coordinator(hass).async_remove_entry(call.data["entry_id"])

    for name, handler, schema in (
        ("import_plan", import_plan, IMPORT_SCHEMA),
        ("save_draft", save_draft, SAVE_DRAFT_SCHEMA),
        ("confirm_plan", confirm_plan, vol.Schema({})),
        ("log_plan_meal", log_plan_meal, MEAL_SCHEMA),
        ("log_extra", log_extra, EXTRA_SCHEMA),
        ("remove_entry", remove_entry, REMOVE_SCHEMA),
    ):
        hass.services.async_register(DOMAIN, name, handler, schema=schema)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: WeEatConfigEntry) -> bool:
    # Also here, not only in async_setup: by now the frontend is certainly up.
    await _async_serve_card(hass)

    coordinator = WeEatCoordinator(hass, entry)
    await coordinator.async_setup()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def _reload(hass: HomeAssistant, entry: WeEatConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: WeEatConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
