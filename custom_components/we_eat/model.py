"""Weekly plan model: validation of LLM/user data and kcal totals."""

from __future__ import annotations

import unicodedata
from typing import Any

from .const import MEALS

_DAY_PREFIXES = ("lun", "mar", "mer", "gio", "ven", "sab", "dom")


class PlanError(ValueError):
    """The plan data is not valid."""


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.strip().lower())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def _day_key(key: Any) -> str:
    raw = _fold(str(key))
    if raw in {str(i) for i in range(7)}:
        return raw
    for index, prefix in enumerate(_DAY_PREFIXES):
        if raw.startswith(prefix):
            return str(index)
    raise PlanError(f"giorno non riconosciuto: {key!r}")


def _item(raw: Any, where: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise PlanError(f"{where}: voce non valida")
    food = str(raw.get("food", "")).strip()
    if not food:
        raise PlanError(f"{where}: alimento mancante")
    kcal = raw.get("kcal")
    if isinstance(kcal, bool) or not isinstance(kcal, (int, float)) or kcal < 0:
        raise PlanError(f"{where}: kcal non valide per {food!r}")
    return {
        "food": food,
        "quantity": str(raw.get("quantity", "")).strip(),
        "kcal": round(kcal),
        "estimated": bool(raw.get("estimated", False)),
    }


def normalize_plan(raw: Any) -> dict[str, Any]:
    """Validate raw plan data and return it with all seven days present."""
    if not isinstance(raw, dict) or not isinstance(raw.get("days"), dict):
        raise PlanError("manca la chiave 'days'")
    days: dict[str, dict[str, list[dict[str, Any]]]] = {str(i): {} for i in range(7)}
    for day_raw, meals_raw in raw["days"].items():
        day = _day_key(day_raw)
        if not isinstance(meals_raw, dict):
            raise PlanError(f"giorno {day_raw!r}: pasti non validi")
        for meal_raw, items_raw in meals_raw.items():
            meal = _fold(str(meal_raw))
            if meal not in MEALS:
                raise PlanError(f"pasto sconosciuto: {meal_raw!r}")
            if not isinstance(items_raw, list):
                raise PlanError(f"{day_raw}/{meal_raw}: serve una lista di alimenti")
            days[day][meal] = [_item(i, f"{day_raw}/{meal_raw}") for i in items_raw]
    if not any(items for meals in days.values() for items in meals.values()):
        raise PlanError("il piano è vuoto")
    return {"days": days}


def meal_kcal(items: list[dict[str, Any]]) -> int:
    return sum(item["kcal"] for item in items)


def day_kcal(meals: dict[str, list[dict[str, Any]]]) -> int:
    return sum(meal_kcal(items) for items in meals.values())


def migrate_recipes(conf: Any) -> list[str]:
    """Turn the legacy YAML `recipes` list into a clean list of favourite dishes."""
    recipes = conf.get("recipes") if isinstance(conf, dict) else None
    if not isinstance(recipes, list):
        return []
    favourites: list[str] = []
    for recipe in recipes:
        name = str(recipe).strip()
        if name and name not in favourites:
            favourites.append(name)
    return favourites
