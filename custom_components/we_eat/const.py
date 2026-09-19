"""Constants for We Eat (no Home Assistant imports, so they can be unit-tested)."""

DOMAIN = "we_eat"

CONF_PROVIDER = "provider"
CONF_API_KEY = "api_key"
CONF_MODEL = "model"
CONF_KCAL_TARGET = "kcal_target"
CONF_MEAL_TIMES = "meal_times"
CONF_RECIPES = "recipes"  # legacy YAML key, only used by the import

PROVIDER_NONE = "none"

DEFAULT_MEAL_TIMES = {
    "colazione": "07:30",
    "spuntino": "10:30",
    "pranzo": "12:30",
    "merenda": "16:30",
    "cena": "19:30",
}
MEALS = tuple(DEFAULT_MEAL_TIMES)
