"""Constants for We Eat (no Home Assistant imports, so they can be unit-tested)."""

from pathlib import Path

DOMAIN = "we_eat"

CONF_PROVIDER = "provider"
CONF_API_KEY = "api_key"
CONF_MODEL = "model"
CONF_KCAL_TARGET = "kcal_target"
CONF_MEAL_TIMES = "meal_times"
CONF_RECIPES = "recipes"  # legacy YAML key, only used by the import

PROVIDER_NONE = "none"

# The card is served by the integration itself, so there is no Lovelace resource to add by hand.
# The files live in the integration folder rather than in a subfolder: HACS does not always
# download nested directories, and a missing static directory fails silently in Home Assistant.
STATIC_URL = "/we_eat_static"
CARD_FILENAME = "we-eat-card.js"
PANEL_FILENAME = "we-eat-panel.js"
PANEL_URL_PATH = "we-eat"
# Resolved here, next to the files themselves, so a test can check they are really there.
INTEGRATION_DIR = Path(__file__).parent
FRONTEND_FILES = (CARD_FILENAME, PANEL_FILENAME)
KEY_STATIC_PATH = f"{DOMAIN}_static_path"
KEY_CARD_URL = f"{DOMAIN}_card_url"
KEY_PANEL = f"{DOMAIN}_panel"

DEFAULT_MEAL_TIMES = {
    "colazione": "07:30",
    "spuntino": "10:30",
    "pranzo": "12:30",
    "merenda": "16:30",
    "cena": "19:30",
}
MEALS = tuple(DEFAULT_MEAL_TIMES)
