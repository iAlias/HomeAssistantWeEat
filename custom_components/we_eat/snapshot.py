"""Pure computation of what the sensors show, from stored data and the current time."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .const import MEALS
from .diary import day_totals
from .model import day_kcal


def _minutes(hhmm: str) -> int:
    hours, minutes = hhmm.split(":")[:2]
    return int(hours) * 60 + int(minutes)


def current_meal(today: dict, meal_times: dict[str, str], now: datetime) -> str | None:
    """The last planned meal already started, or the first one if none has started."""
    planned = sorted((m for m in MEALS if today.get(m)), key=lambda m: _minutes(meal_times[m]))
    if not planned:
        return None
    minutes = now.hour * 60 + now.minute
    started = [m for m in planned if _minutes(meal_times[m]) <= minutes]
    return started[-1] if started else planned[0]


def build_snapshot(plan, draft, diary, meal_times, kcal_target, now: datetime) -> dict[str, Any]:
    today = plan["days"][str(now.weekday())] if plan else {}
    meal = current_meal(today, meal_times, now)
    menu_state = None
    if meal:
        foods = ", ".join(item["food"] for item in today[meal])
        menu_state = f"{meal.capitalize()}: {foods}"[:255]
    date = now.date().isoformat()
    totals = day_totals(diary, date)
    return {
        "menu_state": menu_state,
        "menu_attrs": {"meal": meal, "today": today, "kcal_planned": day_kcal(today)},
        "plan_status": "bozza" if draft else "attivo" if plan else "assente",
        "plan_days": plan["days"] if plan else {},
        "draft_days": draft["days"] if draft else {},
        "kcal_consumed": totals["total"],
        "kcal_by_meal": totals["by_meal"],
        "kcal_target": kcal_target,
        "kcal_remaining": None if kcal_target is None else kcal_target - totals["total"],
        "entries_today": [e for e in diary if e["date"] == date],
    }
