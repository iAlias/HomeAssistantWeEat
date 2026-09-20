"""Constants for We Eat (no Home Assistant imports, so they can be unit-tested)."""

DOMAIN = "we_eat"

CONF_PROVIDER = "provider"
CONF_API_KEY = "api_key"
CONF_MODEL = "model"
CONF_KCAL_TARGET = "kcal_target"
CONF_MEAL_TIMES = "meal_times"
CONF_RECIPES = "recipes"  # legacy YAML key, only used by the import

PROVIDER_NONE = "none"

# The card is served by the integration itself, so there is no Lovelace resource to add by hand.
STATIC_URL = "/we_eat_static"
CARD_FILENAME = "we-eat-card.js"
PANEL_FILENAME = "we-eat-panel.js"
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
