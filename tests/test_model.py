import pytest

from custom_components.we_eat.model import (
    PlanError,
    day_kcal,
    meal_kcal,
    migrate_recipes,
    normalize_plan,
)

ITEM = {"food": "Pasta", "quantity": "80 g", "kcal": 280}


def raw(**meals):
    return {"days": {"0": meals}}


def test_normalize_fills_all_seven_days():
    plan = normalize_plan(raw(pranzo=[ITEM]))
    assert sorted(plan["days"]) == ["0", "1", "2", "3", "4", "5", "6"]
    assert plan["days"]["0"]["pranzo"] == [
        {"food": "Pasta", "quantity": "80 g", "kcal": 280, "estimated": False}
    ]
    assert plan["days"]["1"] == {}


def test_day_and_meal_names_are_folded():
    plan = normalize_plan({"days": {"Lunedì": {"Pranzo": [ITEM]}, "sab": {"cena": [ITEM]}}})
    assert plan["days"]["0"]["pranzo"]
    assert plan["days"]["5"]["cena"]


def test_kcal_is_rounded_and_estimated_flag_kept():
    item = {"food": "Mela", "kcal": 52.6, "estimated": True}
    plan = normalize_plan(raw(spuntino=[item]))
    assert plan["days"]["0"]["spuntino"][0] == {
        "food": "Mela", "quantity": "", "kcal": 53, "estimated": True,
    }


@pytest.mark.parametrize(
    "bad, message",
    [
        ({"giorni": {}}, "days"),
        ({"days": {"0": {"brunch": [ITEM]}}}, "pasto sconosciuto"),
        ({"days": {"xyz": {"pranzo": [ITEM]}}}, "giorno non riconosciuto"),
        ({"days": {"0": {"pranzo": [{"food": "", "kcal": 10}]}}}, "alimento mancante"),
        ({"days": {"0": {"pranzo": [{"food": "A", "kcal": -1}]}}}, "kcal non valide"),
        ({"days": {"0": {"pranzo": [{"food": "A", "kcal": True}]}}}, "kcal non valide"),
        ({"days": {"0": {"pranzo": [{"food": "A"}]}}}, "kcal non valide"),
        ({"days": {"0": {"pranzo": []}}}, "vuoto"),
    ],
)
def test_invalid_plans_are_rejected(bad, message):
    with pytest.raises(PlanError, match=message):
        normalize_plan(bad)


def test_non_dict_is_rejected():
    with pytest.raises(PlanError):
        normalize_plan(["days"])


def test_totals():
    items = [{"kcal": 100}, {"kcal": 250}]
    assert meal_kcal(items) == 350
    assert day_kcal({"pranzo": items, "cena": [{"kcal": 50}]}) == 400
    assert day_kcal({}) == 0


def test_migrate_recipes_dedupes_and_strips():
    assert migrate_recipes({"recipes": [" Pizza ", "Pizza", "", "Risotto"]}) == ["Pizza", "Risotto"]
    assert migrate_recipes({"recipes": "Pizza"}) == []
    assert migrate_recipes(None) == []
