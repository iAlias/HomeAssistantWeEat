from datetime import datetime

from custom_components.we_eat.const import DEFAULT_MEAL_TIMES
from custom_components.we_eat.diary import log_extra
from custom_components.we_eat.model import normalize_plan
from custom_components.we_eat.snapshot import build_snapshot, current_meal

MONDAY = datetime(2026, 9, 21, 13, 0)
PLAN = normalize_plan(
    {
        "days": {
            "0": {
                "colazione": [{"food": "Latte", "kcal": 100}],
                "pranzo": [{"food": "Pasta", "kcal": 300}, {"food": "Insalata", "kcal": 50}],
                "cena": [{"food": "Pesce", "kcal": 250}],
            }
        }
    }
)


def at(hour, minute=0):
    return MONDAY.replace(hour=hour, minute=minute)


def test_monday_fixture():
    assert MONDAY.weekday() == 0


def test_current_meal_is_the_last_one_started():
    today = PLAN["days"]["0"]
    assert current_meal(today, DEFAULT_MEAL_TIMES, at(13)) == "pranzo"
    assert current_meal(today, DEFAULT_MEAL_TIMES, at(20)) == "cena"


def test_current_meal_before_the_first_is_the_first():
    assert current_meal(PLAN["days"]["0"], DEFAULT_MEAL_TIMES, at(5)) == "colazione"


def test_current_meal_none_when_the_day_is_empty():
    assert current_meal({}, DEFAULT_MEAL_TIMES, at(13)) is None


def test_snapshot_with_active_plan_and_target():
    diary = []
    log_extra(diary, "merenda", "biscotti", 200, True, at(11), "a1")
    snap = build_snapshot(PLAN, None, diary, DEFAULT_MEAL_TIMES, 1800, MONDAY)
    assert snap["menu_state"] == "Pranzo: Pasta, Insalata"
    assert snap["menu_attrs"]["meal"] == "pranzo"
    assert snap["menu_attrs"]["kcal_planned"] == 700
    assert snap["plan_status"] == "attivo"
    assert snap["kcal_consumed"] == 200
    assert snap["kcal_remaining"] == 1600
    assert [e["id"] for e in snap["entries_today"]] == ["a1"]


def test_snapshot_without_plan_or_target():
    snap = build_snapshot(None, None, [], DEFAULT_MEAL_TIMES, None, MONDAY)
    assert snap["menu_state"] is None
    assert snap["plan_status"] == "assente"
    assert snap["plan_days"] == {}
    assert snap["kcal_remaining"] is None


def test_draft_status_wins_but_menu_still_uses_the_active_plan():
    snap = build_snapshot(PLAN, PLAN, [], DEFAULT_MEAL_TIMES, None, MONDAY)
    assert snap["plan_status"] == "bozza"
    assert snap["draft_days"]
    assert snap["menu_state"].startswith("Pranzo")


def test_menu_state_is_capped_at_255_characters():
    long_plan = normalize_plan({"days": {"0": {"pranzo": [{"food": "x" * 300, "kcal": 1}]}}})
    assert len(build_snapshot(long_plan, None, [], DEFAULT_MEAL_TIMES, None, MONDAY)["menu_state"]) == 255
