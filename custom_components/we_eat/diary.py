"""Food diary: what was actually eaten, with kcal frozen at logging time."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .const import MEALS
from .model import meal_kcal


def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def _entry(entry_id, when, meal, source, text, kcal, estimated) -> dict[str, Any]:
    return {
        "id": entry_id,
        "date": when.date().isoformat(),
        "time": when.strftime("%H:%M"),
        "meal": meal,
        "source": source,
        "text": text,
        "kcal": kcal,
        "estimated": estimated,
    }


def _check_meal(meal: str) -> None:
    if meal not in MEALS:
        raise ValueError(f"pasto non valido: {meal!r}")


def log_plan_meal(diary, plan, meal, when: datetime, entry_id: str) -> dict[str, Any]:
    _check_meal(meal)
    if plan is None:
        raise ValueError("nessun piano attivo")
    items = plan["days"][str(when.weekday())].get(meal, [])
    if not items:
        raise ValueError(f"il piano di oggi non prevede {meal}")
    date = when.date().isoformat()
    if any(e["date"] == date and e["meal"] == meal and e["source"] == "plan" for e in diary):
        raise ValueError(f"{meal} già registrato oggi")
    entry = _entry(
        entry_id, when, meal, "plan", None, meal_kcal(items), any(i["estimated"] for i in items)
    )
    diary.append(entry)
    return entry


def log_extra(diary, meal, text, kcal, estimated, when: datetime, entry_id: str) -> dict[str, Any]:
    _check_meal(meal)
    text = text.strip()
    if not text:
        raise ValueError("serve una descrizione")
    if kcal < 0:
        raise ValueError("le kcal non possono essere negative")
    entry = _entry(entry_id, when, meal, "extra", text, round(kcal), estimated)
    diary.append(entry)
    return entry


def remove_entry(diary, entry_id: str) -> bool:
    for index, entry in enumerate(diary):
        if entry["id"] == entry_id:
            del diary[index]
            return True
    return False


def day_totals(diary, date_iso: str) -> dict[str, Any]:
    by_meal: dict[str, int] = {}
    for entry in diary:
        if entry["date"] == date_iso:
            by_meal[entry["meal"]] = by_meal.get(entry["meal"], 0) + entry["kcal"]
    return {"total": sum(by_meal.values()), "by_meal": by_meal}
