from datetime import datetime

import pytest

from custom_components.we_eat.diary import (
    day_totals,
    log_extra,
    log_plan_meal,
    normalize_text,
    remove_entry,
)
from custom_components.we_eat.model import normalize_plan

MONDAY_NOON = datetime(2026, 9, 21, 12, 40)
PLAN = normalize_plan(
    {"days": {"0": {"pranzo": [{"food": "Pasta", "kcal": 300}, {"food": "Insalata", "kcal": 50}]}}}
)


def test_the_monday_fixture_is_a_monday():
    assert MONDAY_NOON.weekday() == 0


def test_normalize_text():
    assert normalize_text("  2 Fette   di PIZZA ") == "2 fette di pizza"


def test_log_plan_meal_copies_kcal_from_the_plan():
    diary = []
    entry = log_plan_meal(diary, PLAN, "pranzo", MONDAY_NOON, "a1")
    assert diary == [entry]
    assert entry == {
        "id": "a1", "date": "2026-09-21", "time": "12:40", "meal": "pranzo",
        "source": "plan", "text": None, "kcal": 350, "estimated": False,
    }


def test_log_plan_meal_marks_estimated_when_any_item_is_estimated():
    plan = normalize_plan({"days": {"0": {"cena": [{"food": "Pesce", "kcal": 200, "estimated": True}]}}})
    assert log_plan_meal([], plan, "cena", MONDAY_NOON, "x")["estimated"] is True


@pytest.mark.parametrize(
    "plan, meal, message",
    [
        (None, "pranzo", "nessun piano"),
        (PLAN, "cena", "non prevede"),
        (PLAN, "brunch", "pasto non valido"),
    ],
)
def test_log_plan_meal_rejects_bad_requests(plan, meal, message):
    with pytest.raises(ValueError, match=message):
        log_plan_meal([], plan, meal, MONDAY_NOON, "x")


def test_plan_meal_cannot_be_logged_twice_on_the_same_day():
    diary = []
    log_plan_meal(diary, PLAN, "pranzo", MONDAY_NOON, "a1")
    with pytest.raises(ValueError, match="già registrato"):
        log_plan_meal(diary, PLAN, "pranzo", MONDAY_NOON, "a2")


def test_log_extra_and_totals():
    diary = []
    log_plan_meal(diary, PLAN, "pranzo", MONDAY_NOON, "a1")
    log_extra(diary, "merenda", "2 fette di pizza", 500, True, MONDAY_NOON, "a2")
    log_extra(diary, "merenda", "caffè", 5, False, datetime(2026, 9, 20, 9, 0), "old")
    assert day_totals(diary, "2026-09-21") == {"total": 850, "by_meal": {"pranzo": 350, "merenda": 500}}
    assert day_totals(diary, "2026-09-22") == {"total": 0, "by_meal": {}}


def test_log_extra_validates_input():
    with pytest.raises(ValueError, match="pasto non valido"):
        log_extra([], "brunch", "x", 10, False, MONDAY_NOON, "x")
    with pytest.raises(ValueError, match="descrizione"):
        log_extra([], "cena", "  ", 10, False, MONDAY_NOON, "x")
    with pytest.raises(ValueError, match="kcal"):
        log_extra([], "cena", "x", -5, False, MONDAY_NOON, "x")


def test_remove_entry():
    diary = []
    log_extra(diary, "cena", "x", 10, False, MONDAY_NOON, "a1")
    assert remove_entry(diary, "nope") is False
    assert remove_entry(diary, "a1") is True
    assert diary == []
