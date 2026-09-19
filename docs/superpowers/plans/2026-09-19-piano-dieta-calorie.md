# We Eat 0.2.0 — piano del dietologo e calorie: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sostituire il menu casuale di `we_eat` con il piano settimanale del dietologo (import da testo/PDF/foto via LLM) e un diario che conta le calorie.

**Architecture:** Config entry + `Store` + `DataUpdateCoordinator`. Tutta la logica (piano, diario, snapshot dei sensori, client LLM, prompt) sta in moduli **senza import di Home Assistant**, testabili con `pytest` su Windows; `coordinator.py`, `config_flow.py`, `sensor.py`, `__init__.py`, `storage.py` sono strati sottili che li collegano a HA.

**Tech Stack:** Python 3.12+ (HA 2024.11+), `aiohttp` (già in HA), `pypdf`, `pytest`; card in JavaScript puro (Web Component, senza build).

**Spec:** `docs/superpowers/specs/2026-09-19-piano-dieta-calorie-design.md` (incluse le "Precisazioni emerse dal piano di implementazione", che prevalgono sul testo precedente).

## Global Constraints

- Lingua UI e messaggi d'errore: **italiano** con tutti gli accenti (`lunedì`, `già`, `è`); identificatori e chiavi JSON restano ASCII.
- Home Assistant minimo **2024.11.0** (`hacs.json` → `homeassistant`); `manifest.json` → `version` **0.2.0**, `config_flow: true`, `requirements: ["pypdf>=4"]`, `iot_class: "calculated"`.
- Pasti fissi: `colazione`, `spuntino`, `pranzo`, `merenda`, `cena`. Giorni: chiavi stringa `"0"`–`"6"` con `"0"` = lunedì (come `datetime.weekday()`).
- Voce del piano: `{"food": str, "quantity": str, "kcal": int, "estimated": bool}`.
- La **chiave API non compare mai** in attributi delle entità, log o messaggi d'errore.
- Moduli di logica (`const`, `model`, `diary`, `snapshot`, `tasks`, `pdf`, `llm/*`) **non importano `homeassistant`**.
- I servizi `add_recipe`, `remove_recipe`, `set_recipes` vengono rimossi.
- Test: solo `pytest` su logica pura, senza rete e senza Home Assistant; niente plugin asyncio (si usa `asyncio.run`).
- Prerequisito: `git config user.name` e `user.email` impostati nella repo, altrimenti ogni step "Commit" fallisce.

## File Structure

```
custom_components/we_eat/
  __init__.py        RISCRITTO  setup entry, import YAML, registrazione servizi
  const.py           NUOVO      costanti (nessun import HA)
  model.py           NUOVO      validazione piano, totali kcal, migrazione ricette
  diary.py           NUOVO      registrazione pasti/extra, totali del giorno
  snapshot.py        NUOVO      da (piano, bozza, diario, ora) a dati dei sensori
  tasks.py           NUOVO      import_plan e estimate_kcal (prompt + retry + cache)
  pdf.py             NUOVO      estrazione testo da PDF (pypdf)
  llm/__init__.py    NUOVO      PROVIDERS e create_client
  llm/base.py        NUOVO      LlmError, extract_json, post_json
  llm/openai_compat.py NUOVO    OpenAI + DeepSeek
  llm/gemini.py      NUOVO
  llm/claude.py      NUOVO
  storage.py         NUOVO      wrapper di helpers.storage.Store
  coordinator.py     NUOVO      DataUpdateCoordinator + operazioni dei servizi
  config_flow.py     NUOVO      flow utente, import YAML, opzioni
  sensor.py          RISCRITTO  4 sensori da coordinator
  services.yaml      RISCRITTO
  strings.json, translations/it.json, translations/en.json   NUOVI
  manifest.json      MODIFICATO
we_eat_card.js       RISCRITTO
tests/               conftest.py, test_*.py
pytest.ini, requirements_test.txt
.github/workflows/validate.yml   MODIFICATO (job pytest)
README.md, hacs.json             MODIFICATI
```

---

### Task 1: Scaffolding dei test, costanti e CI

**Files:**
- Create: `pytest.ini`, `requirements_test.txt`, `tests/conftest.py`, `tests/test_const.py`, `custom_components/we_eat/const.py`
- Modify: `.github/workflows/validate.yml`

**Interfaces:**
- Produces: `const.DOMAIN`, `CONF_PROVIDER`, `CONF_API_KEY`, `CONF_MODEL`, `CONF_KCAL_TARGET`, `CONF_MEAL_TIMES`, `CONF_RECIPES`, `PROVIDER_NONE`, `DEFAULT_MEAL_TIMES: dict[str,str]`, `MEALS: tuple[str,...]`; il `conftest.py` rende importabile `custom_components.we_eat.<modulo>` senza eseguire `__init__.py`.

- [ ] **Step 1: Crea i file di configurazione test**

`pytest.ini`:
```ini
[pytest]
testpaths = tests
```

`requirements_test.txt`:
```
pytest>=8
aiohttp>=3.9
pypdf>=4
```

`tests/conftest.py`:
```python
"""Rende importabili i moduli di logica di we_eat senza eseguire __init__.py (che importa HA)."""

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _stub_package(name: str, path: Path) -> None:
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    sys.modules[name] = module


_stub_package("custom_components", ROOT / "custom_components")
_stub_package("custom_components.we_eat", ROOT / "custom_components" / "we_eat")
```

- [ ] **Step 2: Scrivi il test che fallisce**

`tests/test_const.py`:
```python
from custom_components.we_eat.const import DEFAULT_MEAL_TIMES, DOMAIN, MEALS


def test_meals_follow_the_day_and_have_a_time():
    assert DOMAIN == "we_eat"
    assert MEALS == ("colazione", "spuntino", "pranzo", "merenda", "cena")
    assert set(DEFAULT_MEAL_TIMES) == set(MEALS)
    times = [DEFAULT_MEAL_TIMES[m] for m in MEALS]
    assert times == sorted(times)
```

- [ ] **Step 3: Verifica che fallisca**

Run: `python -m pip install -r requirements_test.txt && python -m pytest tests/test_const.py -q`
Expected: FAIL con `ModuleNotFoundError: ... const` (o `ImportError`).

- [ ] **Step 4: Implementa `const.py`**

```python
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
```

- [ ] **Step 5: Verifica che passi**

Run: `python -m pytest tests/test_const.py -q`
Expected: `1 passed`

- [ ] **Step 6: Aggiungi il job pytest alla CI**

In `.github/workflows/validate.yml`, dentro `jobs:` dopo il job `hacs`, aggiungi:
```yaml

  tests:
    name: pytest
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install -r requirements_test.txt
      - run: python -m pytest -q
```

- [ ] **Step 7: Commit**

```bash
git add pytest.ini requirements_test.txt tests/conftest.py tests/test_const.py custom_components/we_eat/const.py .github/workflows/validate.yml docs/superpowers
git commit -m "test: pytest scaffolding, constants module and CI job"
```

---

### Task 2: Modello del piano (validazione, totali, migrazione)

**Files:**
- Create: `custom_components/we_eat/model.py`, `tests/test_model.py`

**Interfaces:**
- Consumes: `const.MEALS`.
- Produces: `class PlanError(ValueError)`; `normalize_plan(raw: Any) -> {"days": {"0".."6": {meal: [item]}}}`; `meal_kcal(items: list[dict]) -> int`; `day_kcal(meals: dict[str, list[dict]]) -> int`; `migrate_recipes(conf: Any) -> list[str]`.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_model.py`:
```python
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
```

- [ ] **Step 2: Verifica che falliscano**

Run: `python -m pytest tests/test_model.py -q`
Expected: FAIL con `ModuleNotFoundError` su `model`.

- [ ] **Step 3: Implementa `model.py`**

```python
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
```

- [ ] **Step 4: Verifica che passino**

Run: `python -m pytest tests/test_model.py -q`
Expected: tutti i test passano.

- [ ] **Step 5: Commit**

```bash
git add custom_components/we_eat/model.py tests/test_model.py
git commit -m "feat: weekly plan model with validation and kcal totals"
```

---

### Task 3: Diario dei pasti

**Files:**
- Create: `custom_components/we_eat/diary.py`, `tests/test_diary.py`

**Interfaces:**
- Consumes: `const.MEALS`, `model.meal_kcal`.
- Produces: `normalize_text(text: str) -> str`; `log_plan_meal(diary: list[dict], plan: dict | None, meal: str, when: datetime, entry_id: str) -> dict`; `log_extra(diary, meal: str, text: str, kcal: int, estimated: bool, when: datetime, entry_id: str) -> dict`; `remove_entry(diary, entry_id: str) -> bool`; `day_totals(diary, date_iso: str) -> {"total": int, "by_meal": dict[str,int]}`. Le funzioni mutano `diary` in place e sollevano `ValueError` con messaggio italiano. Voce del diario: `{"id","date","time","meal","source": "plan"|"extra","text","kcal","estimated"}`.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_diary.py`:
```python
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
```

- [ ] **Step 2: Verifica che falliscano**

Run: `python -m pytest tests/test_diary.py -q`
Expected: FAIL con `ModuleNotFoundError` su `diary`.

- [ ] **Step 3: Implementa `diary.py`**

```python
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
```

- [ ] **Step 4: Verifica che passino**

Run: `python -m pytest tests/test_diary.py -q`
Expected: tutti i test passano.

- [ ] **Step 5: Commit**

```bash
git add custom_components/we_eat/diary.py tests/test_diary.py
git commit -m "feat: meal diary with plan and free-text entries"
```

---

### Task 4: Snapshot per i sensori

**Files:**
- Create: `custom_components/we_eat/snapshot.py`, `tests/test_snapshot.py`

**Interfaces:**
- Consumes: `const.MEALS`, `model.day_kcal`, `diary.day_totals`.
- Produces: `current_meal(today: dict, meal_times: dict[str,str], now: datetime) -> str | None`; `build_snapshot(plan, draft, diary, meal_times, kcal_target: int | None, now: datetime) -> dict` con chiavi `menu_state: str|None`, `menu_attrs: {"meal","today","kcal_planned"}`, `plan_status: "attivo"|"bozza"|"assente"`, `plan_days`, `draft_days`, `kcal_consumed: int`, `kcal_by_meal: dict`, `kcal_target: int|None`, `kcal_remaining: int|None`, `entries_today: list[dict]`.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_snapshot.py`:
```python
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
```

- [ ] **Step 2: Verifica che falliscano**

Run: `python -m pytest tests/test_snapshot.py -q`
Expected: FAIL con `ModuleNotFoundError` su `snapshot`.

- [ ] **Step 3: Implementa `snapshot.py`**

```python
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
```

- [ ] **Step 4: Verifica che passino**

Run: `python -m pytest tests/test_snapshot.py -q`
Expected: tutti i test passano.

- [ ] **Step 5: Commit**

```bash
git add custom_components/we_eat/snapshot.py tests/test_snapshot.py
git commit -m "feat: snapshot of today's menu, plan status and kcal totals"
```

---

### Task 5: Livello LLM (client interno, 4 provider)

**Files:**
- Create: `custom_components/we_eat/llm/__init__.py`, `llm/base.py`, `llm/openai_compat.py`, `llm/gemini.py`, `llm/claude.py`, `tests/test_llm.py`

**Interfaces:**
- Produces:
  - `base.LlmError(Exception)`; `base.extract_json(text: str) -> Any`; `base.post_json(session, url: str, *, headers: dict, body: dict) -> dict`.
  - Ogni client: attributo `supports_vision: bool` e `async complete(prompt: str, *, system: str | None = None, image: tuple[bytes, str] | None = None) -> str` (testo grezzo della risposta; `image` = `(byte, mime)`).
  - `llm.PROVIDERS: dict[str, Provider]` con `Provider(key, label, default_model, supports_vision)`; chiavi `openai`, `deepseek`, `gemini`, `claude`.
  - `llm.create_client(provider: str, api_key: str, model: str, session) -> client`; provider sconosciuto → `LlmError`.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_llm.py`:
```python
import asyncio
import json

import pytest

from custom_components.we_eat.llm import PROVIDERS, create_client
from custom_components.we_eat.llm.base import LlmError, extract_json


class FakeResponse:
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload

    async def json(self):
        return self._payload

    async def text(self):
        return json.dumps(self._payload)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeSession:
    def __init__(self, payload, status=200):
        self._payload = payload
        self._status = status
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(self._status, self._payload)


def run(coro):
    return asyncio.run(coro)


def test_extract_json_handles_fences_and_prose():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Ecco: {"a": {"b": 2}} fine') == {"a": {"b": 2}}


@pytest.mark.parametrize("text", ["niente json", "{rotto", ""])
def test_extract_json_rejects_garbage(text):
    with pytest.raises(LlmError):
        extract_json(text)


def test_providers_catalogue():
    assert set(PROVIDERS) == {"openai", "deepseek", "gemini", "claude"}
    assert PROVIDERS["deepseek"].supports_vision is False
    assert all(p.default_model for p in PROVIDERS.values())


def test_unknown_provider():
    with pytest.raises(LlmError, match="provider"):
        create_client("boh", "k", "m", FakeSession({}))


def test_openai_request_and_response():
    session = FakeSession({"choices": [{"message": {"content": '{"ok": true}'}}]})
    client = create_client("openai", "sk-secret", "gpt-x", session)
    assert run(client.complete("ciao", system="sys")) == '{"ok": true}'
    url, kwargs = session.calls[0]
    assert url == "https://api.openai.com/v1/chat/completions"
    assert kwargs["headers"]["Authorization"] == "Bearer sk-secret"
    body = kwargs["body"] if "body" in kwargs else kwargs["json"]
    assert body["model"] == "gpt-x"
    assert body["messages"][0] == {"role": "system", "content": "sys"}
    assert body["response_format"] == {"type": "json_object"}


def test_openai_sends_images_as_data_uri():
    session = FakeSession({"choices": [{"message": {"content": "{}"}}]})
    client = create_client("openai", "k", "m", session)
    run(client.complete("leggi", image=(b"\x01\x02", "image/jpeg")))
    content = session.calls[0][1]["json"]["messages"][-1]["content"]
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_deepseek_uses_its_own_url_and_rejects_images():
    session = FakeSession({"choices": [{"message": {"content": "{}"}}]})
    client = create_client("deepseek", "k", "deepseek-chat", session)
    assert client.supports_vision is False
    run(client.complete("ciao"))
    assert session.calls[0][0] == "https://api.deepseek.com/chat/completions"
    with pytest.raises(LlmError, match="immagini"):
        run(client.complete("leggi", image=(b"x", "image/png")))


def test_gemini_request_and_response():
    payload = {"candidates": [{"content": {"parts": [{"text": "{}"}]}}]}
    session = FakeSession(payload)
    client = create_client("gemini", "g-secret", "gemini-x", session)
    assert run(client.complete("ciao", system="sys", image=(b"\x01", "image/png"))) == "{}"
    url, kwargs = session.calls[0]
    assert url.endswith("/models/gemini-x:generateContent")
    assert kwargs["headers"]["x-goog-api-key"] == "g-secret"
    body = kwargs["json"]
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert body["systemInstruction"]["parts"][0]["text"] == "sys"
    assert body["contents"][0]["parts"][1]["inline_data"]["mime_type"] == "image/png"


def test_claude_request_and_response():
    session = FakeSession({"content": [{"type": "text", "text": "{}"}]})
    client = create_client("claude", "c-secret", "claude-x", session)
    assert run(client.complete("ciao", system="sys", image=(b"\x01", "image/png"))) == "{}"
    url, kwargs = session.calls[0]
    assert url == "https://api.anthropic.com/v1/messages"
    assert kwargs["headers"]["x-api-key"] == "c-secret"
    assert kwargs["headers"]["anthropic-version"] == "2023-06-01"
    body = kwargs["json"]
    assert body["system"] == "sys"
    assert body["messages"][0]["content"][0]["type"] == "image"


@pytest.mark.parametrize("provider", ["openai", "deepseek", "gemini", "claude"])
def test_http_errors_become_llm_errors_without_leaking_the_key(provider):
    client = create_client(provider, "sk-secret", "m", FakeSession({"error": "no"}, status=401))
    with pytest.raises(LlmError) as err:
        run(client.complete("ciao"))
    assert "401" in str(err.value)
    assert "sk-secret" not in str(err.value)


@pytest.mark.parametrize("provider", ["openai", "gemini", "claude"])
def test_unexpected_payload_becomes_llm_error(provider):
    client = create_client(provider, "k", "m", FakeSession({"boh": 1}))
    with pytest.raises(LlmError, match="risposta inattesa"):
        run(client.complete("ciao"))
```

- [ ] **Step 2: Verifica che falliscano**

Run: `python -m pytest tests/test_llm.py -q`
Expected: FAIL con `ModuleNotFoundError` su `llm`.

- [ ] **Step 3: Implementa `llm/base.py`**

```python
"""Shared pieces of the built-in LLM client."""

from __future__ import annotations

import json
from typing import Any, Protocol

import aiohttp


class LlmError(Exception):
    """The LLM call failed or returned something unusable."""


class LlmClient(Protocol):
    supports_vision: bool

    async def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        image: tuple[bytes, str] | None = None,
    ) -> str: ...


def extract_json(text: str) -> Any:
    """Parse the first JSON object in `text`, tolerating code fences and prose around it."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise LlmError("la risposta non contiene JSON")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as err:
        raise LlmError(f"JSON non valido: {err}") from err


async def post_json(session, url: str, *, headers: dict[str, str], body: dict[str, Any]) -> Any:
    """POST a JSON body; the error messages never include the headers (API keys)."""
    try:
        async with session.post(
            url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=90)
        ) as response:
            if response.status != 200:
                detail = (await response.text())[:200]
                raise LlmError(f"HTTP {response.status}: {detail}")
            return await response.json()
    except aiohttp.ClientError as err:
        raise LlmError(f"errore di rete: {err}") from err
    except TimeoutError as err:
        raise LlmError("timeout della richiesta") from err
```

- [ ] **Step 4: Implementa `llm/openai_compat.py`**

```python
"""OpenAI and DeepSeek (OpenAI-compatible chat completions)."""

from __future__ import annotations

import base64

from .base import LlmError, post_json


class OpenAICompatClient:
    def __init__(self, session, api_key: str, model: str, url: str, supports_vision: bool) -> None:
        self._session = session
        self._api_key = api_key
        self._model = model
        self._url = url
        self.supports_vision = supports_vision

    async def complete(self, prompt, *, system=None, image=None) -> str:
        content = prompt
        if image is not None:
            if not self.supports_vision:
                raise LlmError("questo provider non legge le immagini")
            data, mime = image
            encoded = base64.b64encode(data).decode()
            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}},
            ]
        messages = [{"role": "system", "content": system}] if system else []
        messages.append({"role": "user", "content": content})
        payload = await post_json(
            self._session,
            self._url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            body={
                "model": self._model,
                "messages": messages,
                "response_format": {"type": "json_object"},
            },
        )
        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as err:
            raise LlmError("risposta inattesa dal provider") from err
```

- [ ] **Step 5: Implementa `llm/gemini.py`**

```python
"""Google Gemini (generateContent)."""

from __future__ import annotations

import base64

from .base import LlmError, post_json

_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiClient:
    supports_vision = True

    def __init__(self, session, api_key: str, model: str) -> None:
        self._session = session
        self._api_key = api_key
        self._model = model

    async def complete(self, prompt, *, system=None, image=None) -> str:
        parts = [{"text": prompt}]
        if image is not None:
            data, mime = image
            parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode()}})
        body = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        payload = await post_json(
            self._session,
            _URL.format(model=self._model),
            headers={"x-goog-api-key": self._api_key},
            body=body,
        )
        try:
            return payload["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as err:
            raise LlmError("risposta inattesa dal provider") from err
```

- [ ] **Step 6: Implementa `llm/claude.py`**

```python
"""Anthropic Claude (messages API)."""

from __future__ import annotations

import base64

from .base import LlmError, post_json

_URL = "https://api.anthropic.com/v1/messages"


class ClaudeClient:
    supports_vision = True

    def __init__(self, session, api_key: str, model: str) -> None:
        self._session = session
        self._api_key = api_key
        self._model = model

    async def complete(self, prompt, *, system=None, image=None) -> str:
        content = []
        if image is not None:
            data, mime = image
            content.append(
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": mime, "data": base64.b64encode(data).decode()},
                }
            )
        content.append({"type": "text", "text": prompt})
        body = {"model": self._model, "max_tokens": 4096, "messages": [{"role": "user", "content": content}]}
        if system:
            body["system"] = system
        payload = await post_json(
            self._session,
            _URL,
            headers={"x-api-key": self._api_key, "anthropic-version": "2023-06-01"},
            body=body,
        )
        try:
            return payload["content"][0]["text"]
        except (KeyError, IndexError, TypeError) as err:
            raise LlmError("risposta inattesa dal provider") from err
```

- [ ] **Step 7: Implementa `llm/__init__.py`**

```python
"""Built-in LLM client used by We Eat (no dependency on other integrations)."""

from __future__ import annotations

from dataclasses import dataclass

from .base import LlmClient, LlmError
from .claude import ClaudeClient
from .gemini import GeminiClient
from .openai_compat import OpenAICompatClient

__all__ = ["LlmClient", "LlmError", "PROVIDERS", "Provider", "create_client"]


@dataclass(frozen=True)
class Provider:
    key: str
    label: str
    default_model: str
    supports_vision: bool


PROVIDERS = {
    p.key: p
    for p in (
        Provider("openai", "OpenAI", "gpt-4o-mini", True),
        Provider("deepseek", "DeepSeek (solo testo)", "deepseek-chat", False),
        Provider("gemini", "Google Gemini", "gemini-2.0-flash", True),
        Provider("claude", "Anthropic Claude", "claude-haiku-4-5-20251001", True),
    )
}

_OPENAI_URLS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "deepseek": "https://api.deepseek.com/chat/completions",
}


def create_client(provider: str, api_key: str, model: str, session) -> LlmClient:
    if provider in _OPENAI_URLS:
        return OpenAICompatClient(
            session, api_key, model, _OPENAI_URLS[provider], PROVIDERS[provider].supports_vision
        )
    if provider == "gemini":
        return GeminiClient(session, api_key, model)
    if provider == "claude":
        return ClaudeClient(session, api_key, model)
    raise LlmError(f"provider sconosciuto: {provider}")
```

- [ ] **Step 8: Verifica che passino**

Run: `python -m pytest tests/test_llm.py -q`
Expected: tutti i test passano. (Il test `test_openai_request_and_response` legge il body da `kwargs["json"]`: `post_json` passa `json=body`.)

- [ ] **Step 9: Commit**

```bash
git add custom_components/we_eat/llm tests/test_llm.py
git commit -m "feat: built-in LLM client for OpenAI, DeepSeek, Gemini and Claude"
```

---

### Task 6: Estrazione PDF e compiti AI (import piano, stima kcal)

**Files:**
- Create: `custom_components/we_eat/pdf.py`, `custom_components/we_eat/tasks.py`, `tests/test_pdf.py`, `tests/test_tasks.py`

**Interfaces:**
- Consumes: `llm.base.LlmError`, `llm.base.extract_json`, `model.normalize_plan`, `model.PlanError`, `diary.normalize_text`; un client con `supports_vision` e `complete(...)`.
- Produces: `pdf.extract_text(data: bytes) -> str` (solleva `LlmError` se illeggibile); `tasks.import_plan(client, *, text: str | None = None, data: bytes | None = None, mime: str | None = None) -> dict` (piano normalizzato; `LlmError` in ogni fallimento); `tasks.estimate_kcal(client, text: str, cache: dict[str,int]) -> tuple[int, bool]` (kcal, `True` se dalla cache; muta `cache`, max `MAX_CACHE = 500` voci).

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_pdf.py`:
```python
import io

import pytest
from pypdf import PdfWriter

from custom_components.we_eat.llm.base import LlmError
from custom_components.we_eat.pdf import extract_text


def _blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_blank_pdf_has_no_text():
    assert extract_text(_blank_pdf()).strip() == ""


def test_garbage_is_reported_as_llm_error():
    with pytest.raises(LlmError, match="PDF non leggibile"):
        extract_text(b"questo non e' un pdf")
```

`tests/test_tasks.py`:
```python
import asyncio
import io

import pytest
from pypdf import PdfWriter

from custom_components.we_eat.llm.base import LlmError
from custom_components.we_eat.tasks import MAX_CACHE, estimate_kcal, import_plan

GOOD = '{"days": {"0": {"pranzo": [{"food": "Pasta", "quantity": "80 g", "kcal": 280, "estimated": false}]}}}'


class FakeClient:
    def __init__(self, *responses, vision=True):
        self.supports_vision = vision
        self.responses = list(responses)
        self.prompts = []
        self.images = []

    async def complete(self, prompt, *, system=None, image=None):
        self.prompts.append(prompt)
        self.images.append(image)
        return self.responses.pop(0)


def run(coro):
    return asyncio.run(coro)


def test_import_from_text():
    client = FakeClient(GOOD)
    plan = run(import_plan(client, text="Lunedì pranzo pasta 80 g"))
    assert plan["days"]["0"]["pranzo"][0]["food"] == "Pasta"
    assert "Lunedì pranzo pasta 80 g" in client.prompts[0]
    assert client.images == [None]


def test_import_retries_once_with_the_error_in_the_prompt():
    client = FakeClient("non è json", GOOD)
    plan = run(import_plan(client, text="piano"))
    assert plan["days"]["0"]["pranzo"]
    assert "risposta precedente era errata" in client.prompts[1]
    assert "la risposta non contiene JSON" in client.prompts[1]


def test_import_retries_on_invalid_plan_then_gives_up():
    client = FakeClient('{"days": {"0": {"brunch": []}}}', '{"days": {}}')
    with pytest.raises(LlmError, match="Importazione non riuscita"):
        run(import_plan(client, text="piano"))
    assert len(client.prompts) == 2


def test_import_from_image_needs_vision():
    with pytest.raises(LlmError, match="immagini"):
        run(import_plan(FakeClient(GOOD, vision=False), data=b"x", mime="image/jpeg"))


def test_import_from_image_passes_the_bytes():
    client = FakeClient(GOOD)
    run(import_plan(client, data=b"\x01\x02", mime="image/jpeg"))
    assert client.images == [(b"\x01\x02", "image/jpeg")]


def test_import_from_pdf_without_text_is_refused():
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buffer = io.BytesIO()
    writer.write(buffer)
    with pytest.raises(LlmError, match="scansione"):
        run(import_plan(FakeClient(GOOD), data=buffer.getvalue(), mime="application/pdf"))


def test_import_rejects_missing_or_unsupported_input():
    with pytest.raises(LlmError, match="Formato non supportato"):
        run(import_plan(FakeClient(GOOD), data=b"x", mime="text/csv"))
    with pytest.raises(LlmError, match="Formato non supportato"):
        run(import_plan(FakeClient(GOOD)))


def test_estimate_kcal_uses_and_fills_the_cache():
    cache = {}
    client = FakeClient('{"kcal": 520}')
    assert run(estimate_kcal(client, "2 Fette di pizza", cache)) == (520, False)
    assert cache == {"2 fette di pizza": 520}
    assert run(estimate_kcal(client, "  2 fette  di PIZZA", cache)) == (520, True)
    assert len(client.prompts) == 1


def test_estimate_kcal_retries_then_validates():
    assert run(estimate_kcal(FakeClient("boh", '{"kcal": 90.4}'), "mela", {})) == (90, False)
    with pytest.raises(LlmError, match="Stima non riuscita"):
        run(estimate_kcal(FakeClient('{"kcal": -5}', '{"kcal": "molte"}'), "mela", {}))


def test_estimate_cache_is_capped():
    cache = {f"k{i}": i for i in range(MAX_CACHE)}
    run(estimate_kcal(FakeClient('{"kcal": 10}'), "nuovo", cache))
    assert len(cache) == MAX_CACHE
    assert "k0" not in cache and cache["nuovo"] == 10
```

- [ ] **Step 2: Verifica che falliscano**

Run: `python -m pytest tests/test_pdf.py tests/test_tasks.py -q`
Expected: FAIL con `ModuleNotFoundError` su `pdf` / `tasks`.

- [ ] **Step 3: Implementa `pdf.py`**

```python
"""Local text extraction from PDF files."""

from __future__ import annotations

import io

from .llm.base import LlmError


def extract_text(data: bytes) -> str:
    """Return the text of all pages ("" for a scan without a text layer)."""
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as err:  # pypdf raises many unrelated error types on bad input
        raise LlmError(f"PDF non leggibile: {err}") from err
```

- [ ] **Step 4: Implementa `tasks.py`**

```python
"""AI tasks: turning a diet document into a plan, and estimating the kcal of an extra."""

from __future__ import annotations

import asyncio
from typing import Any

from .diary import normalize_text
from .llm.base import LlmError, extract_json
from .model import PlanError, normalize_plan
from .pdf import extract_text

MAX_CACHE = 500
MAX_KCAL = 10000

SYSTEM = "Sei un assistente nutrizionale. Rispondi SOLO con un oggetto JSON valido, senza altro testo."

PLAN_PROMPT = """Trascrivi il piano alimentare settimanale che segue in JSON, con questo formato:
{"days": {"0": {"pranzo": [{"food": "Pasta integrale", "quantity": "80 g", "kcal": 280, "estimated": false}]}}}
Regole:
- Chiavi dei giorni: "0" = lunedì, "1" = martedì, ... "6" = domenica.
- Pasti ammessi, in minuscolo: colazione, spuntino, pranzo, merenda, cena. Ignora ogni altro pasto.
- Se il documento riporta le kcal usale con "estimated": false; altrimenti stimale con buon senso e metti "estimated": true.
- Se sono offerte alternative ("oppure"), trascrivi solo la prima.
- Se il piano non distingue i giorni, ripeti gli stessi pasti per tutti e sette.
- "quantity" è una stringa (es. "80 g", "1 porzione"); usa "" se non indicata.
"""

EXTRA_PROMPT = """Stima le kcal totali di quanto è stato mangiato, descritto qui sotto. Se le porzioni non sono indicate assumi porzioni tipiche italiane.
Rispondi SOLO con {"kcal": <intero>}.

Descrizione: """

NOT_SUPPORTED = "Formato non supportato: usa testo, PDF o immagine."


async def _ask_json(client, prompt: str, image, parse, failure: str):
    """Ask the LLM, validate with `parse`, retry once telling it what was wrong."""
    last: Exception | None = None
    for _ in range(2):
        hint = ""
        if last is not None:
            hint = f"\n\nLa risposta precedente era errata ({last}). Correggi e rispondi solo con il JSON."
        try:
            return parse(extract_json(await client.complete(prompt + hint, system=SYSTEM, image=image)))
        except (LlmError, PlanError, ValueError) as err:
            last = err
    raise LlmError(f"{failure}: {last}")


async def import_plan(client, *, text=None, data=None, mime=None) -> dict[str, Any]:
    image = None
    if text is None:
        if data is None:
            raise LlmError(NOT_SUPPORTED)
        if mime == "application/pdf":
            text = await asyncio.to_thread(extract_text, data)
            if not text.strip():
                raise LlmError(
                    "Il PDF non contiene testo (è una scansione?): carica una foto o incolla il testo."
                )
        elif mime and mime.startswith("image/"):
            if not client.supports_vision:
                raise LlmError(
                    "Questo provider non legge le immagini: incolla il testo o scegli OpenAI, Gemini o Claude."
                )
            image = (data, mime)
            text = "(vedi l'immagine allegata)"
        else:
            raise LlmError(NOT_SUPPORTED)
    return await _ask_json(
        client, f"{PLAN_PROMPT}\nPIANO:\n{text}", image, normalize_plan, "Importazione non riuscita"
    )


def _parse_kcal(raw: Any) -> int:
    kcal = raw.get("kcal") if isinstance(raw, dict) else None
    if isinstance(kcal, bool) or not isinstance(kcal, (int, float)) or not 0 <= kcal <= MAX_KCAL:
        raise ValueError("kcal mancanti o fuori scala")
    return round(kcal)


async def estimate_kcal(client, text: str, cache: dict[str, int]) -> tuple[int, bool]:
    """Return (kcal, from_cache); a repeated description costs no LLM call."""
    key = normalize_text(text)
    if key in cache:
        return cache[key], True
    kcal = await _ask_json(client, EXTRA_PROMPT + text.strip(), None, _parse_kcal, "Stima non riuscita")
    cache[key] = kcal
    while len(cache) > MAX_CACHE:
        del cache[next(iter(cache))]
    return kcal, False
```

- [ ] **Step 5: Verifica che passino**

Run: `python -m pytest -q`
Expected: tutti i test (Task 1–6) passano.

- [ ] **Step 6: Commit**

```bash
git add custom_components/we_eat/pdf.py custom_components/we_eat/tasks.py tests/test_pdf.py tests/test_tasks.py
git commit -m "feat: plan import (text/PDF/photo) and kcal estimation tasks"
```

---

### Task 7: Storage e coordinator (strato HA)

**Files:**
- Create: `custom_components/we_eat/storage.py`, `custom_components/we_eat/coordinator.py`

**Interfaces:**
- Consumes: tutto ciò che producono i Task 1–6.
- Produces:
  - `storage.WeEatStore(hass)`: `async_load() -> dict` (chiavi `plan`, `draft`, `diary`, `cache`, `favorites`) e `async_save(data: dict) -> None`.
  - `coordinator.WeEatCoordinator(hass, entry)` con: `async_setup()`, proprietà `meal_times`, `kcal_target`, `favorites`; operazioni `async_import_plan(*, text=None, data=None, mime=None)`, `async_save_draft(days: dict)`, `async_confirm_plan()`, `async_log_plan_meal(meal: str)`, `async_log_extra(text: str, meal: str, kcal: int | None = None)`, `async_remove_entry(entry_id: str)`. `coordinator.data` è il dict di `build_snapshot`. Errori utente → `ServiceValidationError`; errori LLM → `HomeAssistantError`.

Questo strato non ha test unitari (dipende da HA, e i test HA richiedono Linux): si verifica con `py_compile` qui e con lo smoke test del Task 11.

- [ ] **Step 1: Scrivi `storage.py`**

```python
"""Persistent storage for the plan, the diary and the LLM cache."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORAGE_VERSION = 1


def _empty() -> dict[str, Any]:
    return {"plan": None, "draft": None, "diary": [], "cache": {}, "favorites": []}


class WeEatStore:
    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, DOMAIN)

    async def async_load(self) -> dict[str, Any]:
        return {**_empty(), **(await self._store.async_load() or {})}

    async def async_save(self, data: dict[str, Any]) -> None:
        await self._store.async_save(data)
```

- [ ] **Step 2: Scrivi `coordinator.py`**

```python
"""Coordinator: keeps the stored data, recomputes the snapshot and runs the service operations."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_API_KEY,
    CONF_KCAL_TARGET,
    CONF_MEAL_TIMES,
    CONF_MODEL,
    CONF_PROVIDER,
    DEFAULT_MEAL_TIMES,
    DOMAIN,
    PROVIDER_NONE,
)
from .diary import log_extra, log_plan_meal, remove_entry
from .llm import PROVIDERS, LlmError, create_client
from .model import PlanError, normalize_plan
from .snapshot import build_snapshot
from .storage import WeEatStore
from .tasks import estimate_kcal, import_plan

_LOGGER = logging.getLogger(__name__)


class WeEatCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """No polling: refreshed at midnight, at each meal time and after every write."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry)
        self._entry = entry
        self._store = WeEatStore(hass)
        self._data: dict[str, Any] = {}

    @property
    def meal_times(self) -> dict[str, str]:
        return {**DEFAULT_MEAL_TIMES, **self._entry.options.get(CONF_MEAL_TIMES, {})}

    @property
    def kcal_target(self) -> int | None:
        return self._entry.options.get(CONF_KCAL_TARGET)

    @property
    def favorites(self) -> list[str]:
        return list(self._data.get("favorites", []))

    async def async_setup(self) -> None:
        self._data = await self._store.async_load()
        legacy = self._entry.data.get("favorites")
        if legacy and not self._data["favorites"]:
            self._data["favorites"] = list(legacy)
            await self._store.async_save(self._data)
        times = [(0, 0)] + [tuple(int(p) for p in t.split(":")[:2]) for t in self.meal_times.values()]
        for hour, minute in times:
            self._entry.async_on_unload(
                async_track_time_change(self.hass, self._tick, hour=hour, minute=minute, second=0)
            )

    @callback
    def _tick(self, now: datetime) -> None:
        self.hass.async_create_task(self.async_refresh())

    async def _async_update_data(self) -> dict[str, Any]:
        return build_snapshot(
            self._data["plan"],
            self._data["draft"],
            self._data["diary"],
            self.meal_times,
            self.kcal_target,
            dt_util.now(),
        )

    async def _commit(self) -> None:
        await self._store.async_save(self._data)
        await self.async_refresh()

    def _client(self):
        data = self._entry.data
        provider = data.get(CONF_PROVIDER, PROVIDER_NONE)
        if provider == PROVIDER_NONE:
            raise ServiceValidationError(
                "Nessun provider AI configurato: sceglilo nelle opzioni di We Eat oppure inserisci i dati a mano."
            )
        model = data.get(CONF_MODEL) or PROVIDERS[provider].default_model
        return create_client(provider, data[CONF_API_KEY], model, async_get_clientsession(self.hass))

    async def async_import_plan(self, *, text=None, data=None, mime=None) -> None:
        client = self._client()
        try:
            self._data["draft"] = await import_plan(client, text=text, data=data, mime=mime)
        except LlmError as err:
            raise HomeAssistantError(str(err)) from err
        await self._commit()

    async def async_save_draft(self, days: dict[str, Any]) -> None:
        try:
            self._data["draft"] = normalize_plan({"days": days})
        except PlanError as err:
            raise ServiceValidationError(str(err)) from err
        await self._commit()

    async def async_confirm_plan(self) -> None:
        if not self._data["draft"]:
            raise ServiceValidationError("Nessuna bozza da confermare.")
        self._data["plan"], self._data["draft"] = self._data["draft"], None
        await self._commit()

    async def async_log_plan_meal(self, meal: str) -> None:
        try:
            log_plan_meal(self._data["diary"], self._data["plan"], meal, dt_util.now(), uuid4().hex)
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        await self._commit()

    async def async_log_extra(self, text: str, meal: str, kcal: int | None = None) -> None:
        estimated = kcal is None
        if estimated:
            try:
                kcal, _ = await estimate_kcal(self._client(), text, self._data["cache"])
            except LlmError as err:
                raise HomeAssistantError(str(err)) from err
        try:
            log_extra(self._data["diary"], meal, text, kcal, estimated, dt_util.now(), uuid4().hex)
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        await self._commit()

    async def async_remove_entry(self, entry_id: str) -> None:
        if not remove_entry(self._data["diary"], entry_id):
            raise ServiceValidationError("Voce del diario non trovata.")
        await self._commit()
```

- [ ] **Step 3: Verifica la sintassi**

Run: `python -m py_compile custom_components/we_eat/storage.py custom_components/we_eat/coordinator.py`
Expected: nessun output, exit code 0.

- [ ] **Step 4: Commit**

```bash
git add custom_components/we_eat/storage.py custom_components/we_eat/coordinator.py
git commit -m "feat: storage and coordinator wiring the logic modules to Home Assistant"
```

---

### Task 8: Config flow, setup, servizi, manifest e traduzioni

**Files:**
- Create: `custom_components/we_eat/config_flow.py`, `custom_components/we_eat/strings.json`, `custom_components/we_eat/translations/it.json`, `custom_components/we_eat/translations/en.json`
- Modify (riscrittura completa): `custom_components/we_eat/__init__.py`, `custom_components/we_eat/services.yaml`, `custom_components/we_eat/manifest.json`

**Interfaces:**
- Consumes: `WeEatCoordinator` (Task 7), `PROVIDERS`/`create_client` (Task 5), `migrate_recipes` (Task 2), costanti.
- Produces: config entry con `data = {provider, api_key, model}` (+ `favorites` se importata da YAML) e `options = {kcal_target?, meal_times}`; `entry.runtime_data` = `WeEatCoordinator`; servizi `we_eat.import_plan|save_draft|confirm_plan|log_plan_meal|log_extra|remove_entry`.

- [ ] **Step 1: Sostituisci `manifest.json`**

```json
{
  "domain": "we_eat",
  "name": "We Eat Menu",
  "codeowners": ["@iAlias"],
  "config_flow": true,
  "dependencies": [],
  "documentation": "https://github.com/iAlias/HomeAssistantWeEat",
  "iot_class": "calculated",
  "issue_tracker": "https://github.com/iAlias/HomeAssistantWeEat/issues",
  "requirements": ["pypdf>=4"],
  "single_config_entry": true,
  "version": "0.2.0"
}
```

- [ ] **Step 2: Scrivi `config_flow.py`**

```python
"""Config flow: provider and key, YAML import, and options (target kcal, meal times)."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
    TimeSelector,
)

from .const import (
    CONF_API_KEY,
    CONF_KCAL_TARGET,
    CONF_MEAL_TIMES,
    CONF_MODEL,
    CONF_PROVIDER,
    DEFAULT_MEAL_TIMES,
    DOMAIN,
    MEALS,
    PROVIDER_NONE,
)
from .llm import PROVIDERS, LlmError, create_client
from .model import migrate_recipes

_PROVIDER_LABELS = [SelectOptionDict(value=PROVIDER_NONE, label="Nessuno (solo inserimento manuale)")] + [
    SelectOptionDict(value=p.key, label=p.label) for p in PROVIDERS.values()
]


def _provider_fields(defaults: dict[str, Any]) -> dict[Any, Any]:
    return {
        vol.Required(CONF_PROVIDER, default=defaults.get(CONF_PROVIDER, PROVIDER_NONE)): SelectSelector(
            SelectSelectorConfig(options=_PROVIDER_LABELS, mode=SelectSelectorMode.DROPDOWN)
        ),
        vol.Optional(CONF_API_KEY, default=defaults.get(CONF_API_KEY, "")): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Optional(CONF_MODEL, default=defaults.get(CONF_MODEL, "")): str,
    }


async def _validate(hass, data: dict[str, Any]) -> dict[str, str]:
    provider = data[CONF_PROVIDER]
    if provider == PROVIDER_NONE:
        return {}
    if not data.get(CONF_API_KEY):
        return {CONF_API_KEY: "api_key_required"}
    model = data.get(CONF_MODEL) or PROVIDERS[provider].default_model
    client = create_client(provider, data[CONF_API_KEY], model, async_get_clientsession(hass))
    try:
        await client.complete('Rispondi con {"ok": true}', system="Rispondi solo con JSON.")
    except LlmError:
        return {"base": "cannot_connect"}
    return {}


class WeEatConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = await _validate(self.hass, user_input)
            if not errors:
                return self.async_create_entry(title="We Eat", data=user_input)
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(_provider_fields(user_input or {})), errors=errors
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        return self.async_create_entry(
            title="We Eat",
            data={CONF_PROVIDER: PROVIDER_NONE, "favorites": migrate_recipes(import_data)},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return WeEatOptionsFlow(config_entry)


class WeEatOptionsFlow(OptionsFlow):
    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            provider_data = {k: user_input.get(k, "") for k in (CONF_PROVIDER, CONF_API_KEY, CONF_MODEL)}
            errors = await _validate(self.hass, provider_data)
            if not errors:
                self.hass.config_entries.async_update_entry(
                    self._entry, data={**self._entry.data, **provider_data}
                )
                options: dict[str, Any] = {
                    CONF_MEAL_TIMES: {
                        meal: _hhmm(user_input.get(f"time_{meal}"), DEFAULT_MEAL_TIMES[meal]) for meal in MEALS
                    }
                }
                if user_input.get(CONF_KCAL_TARGET):
                    options[CONF_KCAL_TARGET] = int(user_input[CONF_KCAL_TARGET])
                return self.async_create_entry(data=options)
        current = user_input or {**self._entry.data}
        times = {**DEFAULT_MEAL_TIMES, **self._entry.options.get(CONF_MEAL_TIMES, {})}
        fields = _provider_fields(current)
        fields[
            vol.Optional(
                CONF_KCAL_TARGET, description={"suggested_value": self._entry.options.get(CONF_KCAL_TARGET)}
            )
        ] = NumberSelector(NumberSelectorConfig(min=500, max=10000, step=50, mode=NumberSelectorMode.BOX))
        for meal in MEALS:
            fields[vol.Optional(f"time_{meal}", description={"suggested_value": f"{times[meal]}:00"})] = TimeSelector()
        return self.async_show_form(step_id="init", data_schema=vol.Schema(fields), errors=errors)


def _hhmm(value: str | None, default: str) -> str:
    match = re.match(r"^(\d{2}:\d{2})", value or "")
    return match.group(1) if match else default
```

- [ ] **Step 3: Riscrivi `__init__.py`**

```python
"""We Eat: the dietitian's weekly plan and a kcal diary, as a Home Assistant integration."""

from __future__ import annotations

import base64
import binascii

import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.typing import ConfigType

from .const import CONF_RECIPES, DOMAIN, MEALS
from .coordinator import WeEatCoordinator

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


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
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
```

- [ ] **Step 4: Riscrivi `services.yaml`**

```yaml
import_plan:
  fields:
    text:
      selector:
        text:
          multiline: true
    file_b64:
      selector:
        text:
    mime_type:
      example: "application/pdf"
      selector:
        text:
save_draft:
  fields:
    days:
      required: true
      selector:
        object:
confirm_plan:
log_plan_meal:
  fields:
    meal:
      required: true
      selector:
        select:
          options: [colazione, spuntino, pranzo, merenda, cena]
log_extra:
  fields:
    text:
      required: true
      example: "2 fette di pizza"
      selector:
        text:
    meal:
      required: true
      selector:
        select:
          options: [colazione, spuntino, pranzo, merenda, cena]
    kcal:
      selector:
        number:
          min: 0
          max: 10000
          mode: box
remove_entry:
  fields:
    entry_id:
      required: true
      selector:
        text:
```

- [ ] **Step 5: Scrivi `strings.json`**

```json
{
  "config": {
    "step": {
      "user": {
        "title": "We Eat",
        "description": "Scegli il provider AI per importare il piano e stimare le calorie, oppure \"Nessuno\" per inserire tutto a mano. La chiave resta in questo Home Assistant; le richieste inviano al provider il testo del piano e degli extra.",
        "data": {
          "provider": "Provider AI",
          "api_key": "Chiave API",
          "model": "Modello (vuoto = predefinito)"
        }
      }
    },
    "error": {
      "cannot_connect": "Il provider non risponde o la chiave non è valida.",
      "api_key_required": "Serve la chiave API per questo provider."
    },
    "abort": {
      "single_instance_allowed": "We Eat è già configurato."
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "Opzioni di We Eat",
        "data": {
          "provider": "Provider AI",
          "api_key": "Chiave API",
          "model": "Modello (vuoto = predefinito)",
          "kcal_target": "Obiettivo kcal giornaliero (facoltativo)",
          "time_colazione": "Inizio colazione",
          "time_spuntino": "Inizio spuntino",
          "time_pranzo": "Inizio pranzo",
          "time_merenda": "Inizio merenda",
          "time_cena": "Inizio cena"
        }
      }
    },
    "error": {
      "cannot_connect": "Il provider non risponde o la chiave non è valida.",
      "api_key_required": "Serve la chiave API per questo provider."
    }
  },
  "issues": {
    "yaml_deprecated": {
      "title": "La configurazione YAML di We Eat è obsoleta",
      "description": "Le ricette sono state importate come piatti preferiti. Rimuovi la sezione `we_eat:` da configuration.yaml e configura il provider AI da Impostazioni → Dispositivi e servizi."
    }
  },
  "services": {
    "import_plan": {
      "name": "Importa piano",
      "description": "Crea una bozza del piano settimanale da testo, PDF o foto.",
      "fields": {
        "text": {"name": "Testo", "description": "Il piano incollato come testo."},
        "file_b64": {"name": "File (base64)", "description": "PDF o immagine codificati in base64 (max 3 MB)."},
        "mime_type": {"name": "Tipo del file", "description": "Per esempio application/pdf o image/jpeg."}
      }
    },
    "save_draft": {
      "name": "Salva bozza",
      "description": "Salva le correzioni fatte alla bozza del piano.",
      "fields": {"days": {"name": "Giorni", "description": "Giorni da 0 (lunedì) a 6 (domenica) con i pasti e gli alimenti."}}
    },
    "confirm_plan": {"name": "Conferma piano", "description": "Rende attivo il piano in bozza."},
    "log_plan_meal": {
      "name": "Segna pasto come da piano",
      "description": "Registra nel diario il pasto previsto oggi dal piano.",
      "fields": {"meal": {"name": "Pasto", "description": "Il pasto da registrare."}}
    },
    "log_extra": {
      "name": "Aggiungi extra",
      "description": "Registra nel diario qualcosa che hai mangiato fuori piano.",
      "fields": {
        "text": {"name": "Descrizione", "description": "Cosa hai mangiato."},
        "meal": {"name": "Pasto", "description": "A quale pasto associarlo."},
        "kcal": {"name": "Kcal", "description": "Se le indichi non viene chiamata l'AI."}
      }
    },
    "remove_entry": {
      "name": "Rimuovi voce",
      "description": "Elimina una voce dal diario.",
      "fields": {"entry_id": {"name": "ID voce", "description": "L'identificativo della voce."}}
    }
  }
}
```

- [ ] **Step 6: Copia in `translations/it.json` e scrivi `translations/en.json`**

Run: `mkdir -p custom_components/we_eat/translations && cp custom_components/we_eat/strings.json custom_components/we_eat/translations/it.json`

`custom_components/we_eat/translations/en.json`:
```json
{
  "config": {
    "step": {
      "user": {
        "title": "We Eat",
        "description": "Pick the AI provider used to import the plan and estimate calories, or \"None\" to enter everything by hand. The key stays in this Home Assistant; requests send the plan and extras text to the provider.",
        "data": {"provider": "AI provider", "api_key": "API key", "model": "Model (empty = default)"}
      }
    },
    "error": {
      "cannot_connect": "The provider does not answer or the key is invalid.",
      "api_key_required": "This provider needs an API key."
    },
    "abort": {"single_instance_allowed": "We Eat is already configured."}
  },
  "options": {
    "step": {
      "init": {
        "title": "We Eat options",
        "data": {
          "provider": "AI provider",
          "api_key": "API key",
          "model": "Model (empty = default)",
          "kcal_target": "Daily kcal target (optional)",
          "time_colazione": "Breakfast starts",
          "time_spuntino": "Snack starts",
          "time_pranzo": "Lunch starts",
          "time_merenda": "Afternoon snack starts",
          "time_cena": "Dinner starts"
        }
      }
    },
    "error": {
      "cannot_connect": "The provider does not answer or the key is invalid.",
      "api_key_required": "This provider needs an API key."
    }
  },
  "issues": {
    "yaml_deprecated": {
      "title": "We Eat YAML configuration is deprecated",
      "description": "Your recipes were imported as favourite dishes. Remove the `we_eat:` section from configuration.yaml and set up the AI provider in Settings → Devices & services."
    }
  },
  "services": {
    "import_plan": {
      "name": "Import plan",
      "description": "Create a draft of the weekly plan from text, PDF or photo.",
      "fields": {
        "text": {"name": "Text", "description": "The plan pasted as text."},
        "file_b64": {"name": "File (base64)", "description": "PDF or image encoded in base64 (max 3 MB)."},
        "mime_type": {"name": "File type", "description": "For example application/pdf or image/jpeg."}
      }
    },
    "save_draft": {
      "name": "Save draft",
      "description": "Save the edits made to the draft plan.",
      "fields": {"days": {"name": "Days", "description": "Days 0 (Monday) to 6 (Sunday) with meals and foods."}}
    },
    "confirm_plan": {"name": "Confirm plan", "description": "Make the draft plan the active one."},
    "log_plan_meal": {
      "name": "Log meal as planned",
      "description": "Record today's planned meal in the diary.",
      "fields": {"meal": {"name": "Meal", "description": "The meal to record."}}
    },
    "log_extra": {
      "name": "Add extra",
      "description": "Record something you ate outside the plan.",
      "fields": {
        "text": {"name": "Description", "description": "What you ate."},
        "meal": {"name": "Meal", "description": "Which meal to attach it to."},
        "kcal": {"name": "Kcal", "description": "If given, the AI is not called."}
      }
    },
    "remove_entry": {
      "name": "Remove entry",
      "description": "Delete a diary entry.",
      "fields": {"entry_id": {"name": "Entry ID", "description": "The entry identifier."}}
    }
  }
}
```

- [ ] **Step 7: Verifica sintassi e JSON**

Run:
```bash
python -m py_compile custom_components/we_eat/__init__.py custom_components/we_eat/config_flow.py
python -c "import json; [json.load(open(f, encoding='utf-8')) for f in ('custom_components/we_eat/manifest.json','custom_components/we_eat/strings.json','custom_components/we_eat/translations/it.json','custom_components/we_eat/translations/en.json')]; print('json ok')"
python -c "import yaml; yaml.safe_load(open('custom_components/we_eat/services.yaml', encoding='utf-8')); print('yaml ok')"
```
Expected: `json ok` e `yaml ok` (se `yaml` manca: `pip install pyyaml`).

- [ ] **Step 8: Commit**

```bash
git add custom_components/we_eat/__init__.py custom_components/we_eat/config_flow.py custom_components/we_eat/services.yaml custom_components/we_eat/manifest.json custom_components/we_eat/strings.json custom_components/we_eat/translations
git commit -m "feat: config entry, options flow, YAML import and services"
```

---

### Task 9: Sensori

**Files:**
- Modify (riscrittura completa): `custom_components/we_eat/sensor.py`

**Interfaces:**
- Consumes: `entry.runtime_data` (`WeEatCoordinator`, con `.data` = snapshot del Task 4, `.favorites`, `.kcal_target`).
- Produces: `sensor.we_eat_menu` (stato = `menu_state`; attributi `meal`, `today`, `kcal_planned`, `favorites`), `sensor.we_eat_piano_settimana` (stato = `plan_status`; attributi `days`, `draft_days`), `sensor.we_eat_kcal_consumate` (stato kcal; attributi `by_meal`, `entries`, `target`), `sensor.we_eat_kcal_rimanenti` (solo se c'è l'obiettivo). Il menu mantiene `unique_id = "we_eat_menu"` così conserva l'entity_id di prima.

- [ ] **Step 1: Riscrivi `sensor.py`**

```python
"""Sensors of We Eat, all read from the coordinator snapshot."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import WeEatConfigEntry
from .const import DOMAIN
from .coordinator import WeEatCoordinator

DEVICE = DeviceInfo(identifiers={(DOMAIN, "we_eat")}, name="We Eat", manufacturer="We Eat")


async def async_setup_entry(hass, entry: WeEatConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    entities: list[WeEatSensor] = [
        MenuSensor(coordinator),
        PlanSensor(coordinator),
        ConsumedSensor(coordinator),
    ]
    if coordinator.kcal_target is not None:
        entities.append(RemainingSensor(coordinator))
    async_add_entities(entities)


class WeEatSensor(CoordinatorEntity[WeEatCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_device_info = DEVICE

    def __init__(self, coordinator: WeEatCoordinator, key: str, name: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"we_eat_{key}"
        self._attr_name = name


class MenuSensor(WeEatSensor):
    def __init__(self, coordinator: WeEatCoordinator) -> None:
        super().__init__(coordinator, "menu", "Menu")

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data["menu_state"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {**self.coordinator.data["menu_attrs"], "favorites": self.coordinator.favorites}


class PlanSensor(WeEatSensor):
    _unrecorded_attributes = frozenset({"days", "draft_days"})

    def __init__(self, coordinator: WeEatCoordinator) -> None:
        super().__init__(coordinator, "piano_settimana", "Piano settimana")

    @property
    def native_value(self) -> str:
        return self.coordinator.data["plan_status"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        return {"days": data["plan_days"], "draft_days": data["draft_days"]}


class ConsumedSensor(WeEatSensor):
    _attr_native_unit_of_measurement = "kcal"
    _unrecorded_attributes = frozenset({"entries"})

    def __init__(self, coordinator: WeEatCoordinator) -> None:
        super().__init__(coordinator, "kcal_consumate", "Kcal consumate")

    @property
    def native_value(self) -> int:
        return self.coordinator.data["kcal_consumed"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        return {
            "by_meal": data["kcal_by_meal"],
            "entries": data["entries_today"],
            "target": data["kcal_target"],
        }


class RemainingSensor(WeEatSensor):
    _attr_native_unit_of_measurement = "kcal"

    def __init__(self, coordinator: WeEatCoordinator) -> None:
        super().__init__(coordinator, "kcal_rimanenti", "Kcal rimanenti")

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data["kcal_remaining"]
```

- [ ] **Step 2: Verifica la sintassi**

Run: `python -m py_compile custom_components/we_eat/sensor.py`
Expected: nessun output, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add custom_components/we_eat/sensor.py
git commit -m "feat: menu, weekly plan and kcal sensors backed by the coordinator"
```

---

### Task 10: Card Lovelace

**Files:**
- Modify (riscrittura completa): `we_eat_card.js`

**Interfaces:**
- Consumes: entità `sensor.we_eat_menu` (attributi `meal`, `today`), `sensor.we_eat_piano_settimana` (`days`, `draft_days`), `sensor.we_eat_kcal_consumate` (`by_meal`, `entries`, `target`); servizi `we_eat.log_plan_meal|log_extra|remove_entry|import_plan|save_draft|confirm_plan`.
- Config card: `entity` (menu, default `sensor.we_eat_menu`), `plan_entity`, `kcal_entity` (default derivati dai nomi standard). Il vecchio `editable` viene ignorato.

Il testo che arriva dall'LLM viene sempre inserito con `textContent`/`document.createTextNode`, mai come HTML.

- [ ] **Step 1: Riscrivi `we_eat_card.js`**

```javascript
const DAYS = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"];
const MEALS = ["colazione", "spuntino", "pranzo", "merenda", "cena"];
const MAX_FILE_BYTES = 3 * 1024 * 1024;
const DISCLAIMER = "Le calorie stimate dall'AI sono approssimative e non sono un parere medico.";

function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") el.className = value;
    else if (key.startsWith("on")) el.addEventListener(key.slice(2), value);
    else if (value !== undefined && value !== null && value !== false) el.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return el;
}

const cap = (text) => text.charAt(0).toUpperCase() + text.slice(1);
const mealKcal = (items) => items.reduce((sum, item) => sum + item.kcal, 0);

function readAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1]);
    reader.onerror = () => reject(new Error("Lettura del file non riuscita"));
    reader.readAsDataURL(file);
  });
}

async function shrinkImage(file) {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
  return { file_b64: dataUrl.split(",")[1], mime_type: "image/jpeg" };
}

class WeEatCard extends HTMLElement {
  setConfig(config) {
    this.config = {
      entity: "sensor.we_eat_menu",
      plan_entity: "sensor.we_eat_piano_settimana",
      kcal_entity: "sensor.we_eat_kcal_consumate",
      ...config,
    };
    this._tab = this._tab || "oggi";
    this._message = "";
  }

  getCardSize() {
    return 6;
  }

  set hass(hass) {
    this._hass = hass;
    const menu = hass.states[this.config.entity];
    const plan = hass.states[this.config.plan_entity];
    const kcal = hass.states[this.config.kcal_entity];
    if (!menu || !plan || !kcal) {
      this.replaceChildren(h("ha-card", { header: "We Eat" }, h("div", { class: "card-content" }, "Entità di We Eat non trovate.")));
      return;
    }
    const signature = [menu, plan, kcal].map((s) => s.last_updated).join("|");
    const typing = this.contains(document.activeElement) && document.activeElement.matches("input, textarea");
    if (signature === this._signature || typing) return;
    if (!this._signature || plan.attributes.draft_days !== this._plan?.attributes.draft_days) this._draft = null;
    this._signature = signature;
    this._menu = menu;
    this._plan = plan;
    this._kcal = kcal;
    this._render();
  }

  _call(service, data, success) {
    this._message = "…";
    this._render();
    return this._hass
      .callService("we_eat", service, data)
      .then(() => {
        this._message = success || "";
        this._signature = null;
      })
      .catch((err) => {
        this._message = err.message || "Operazione non riuscita";
      })
      .finally(() => this._render());
  }

  _setTab(tab) {
    this._tab = tab;
    this._render();
  }

  _render() {
    if (!this._menu) return;
    const tabs = [["oggi", "Oggi"], ["settimana", "Settimana"], ["importa", "Importa"]];
    const body = { oggi: () => this._today(), settimana: () => this._week(), importa: () => this._import() }[this._tab]();
    this.replaceChildren(
      h(
        "ha-card",
        { header: "We Eat" },
        h(
          "div",
          { class: "card-content" },
          h("div", {}, ...tabs.map(([id, label]) =>
            h("button", { onclick: () => this._setTab(id), disabled: this._tab === id }, label))),
          this._message && h("p", {}, this._message),
          body,
          h("p", { style: "opacity:.6;font-size:.8em" }, DISCLAIMER),
        ),
      ),
    );
  }

  _today() {
    const today = this._menu.attributes.today || {};
    const entries = this._kcal.attributes.entries || [];
    const target = this._kcal.attributes.target;
    const total = Number(this._kcal.state) || 0;
    const rows = MEALS.filter((meal) => (today[meal] || []).length).map((meal) => {
      const done = entries.some((e) => e.meal === meal && e.source === "plan");
      const items = today[meal];
      return h(
        "div",
        { style: this._menu.attributes.meal === meal ? "font-weight:600" : "" },
        `${cap(meal)} (${mealKcal(items)} kcal): `,
        items.map((i) => `${i.food}${i.quantity ? " " + i.quantity : ""}${i.estimated ? " (stimato)" : ""}`).join(", "),
        " ",
        h("button", { disabled: done, onclick: () => this._call("log_plan_meal", { meal }) }, done ? "Fatto ✓" : "Fatto come da piano"),
      );
    });
    const mealSelect = h("select", {}, ...MEALS.map((m) => h("option", { value: m }, cap(m))));
    const text = h("input", { type: "text", placeholder: "Extra (es. 2 fette di pizza)" });
    const kcal = h("input", { type: "number", min: "0", placeholder: "kcal (facoltative)", style: "width:9em" });
    const add = () => {
      if (!text.value.trim()) return;
      const data = { text: text.value.trim(), meal: mealSelect.value };
      if (kcal.value !== "") data.kcal = Number(kcal.value);
      this._call("log_extra", data);
    };
    return h(
      "div",
      {},
      h("p", {}, `Consumate: ${total} kcal` + (target ? ` su ${target}` : "")),
      target && h("progress", { max: target, value: Math.min(total, target), style: "width:100%" }),
      rows.length ? rows : h("p", {}, "Nessun pasto previsto oggi dal piano."),
      h("div", {}, text, mealSelect, kcal, h("button", { onclick: add }, "Aggiungi")),
      h("ul", {}, ...entries.map((e) =>
        h("li", {}, `${e.time} ${cap(e.meal)}: ${e.text || "come da piano"} — ${e.kcal} kcal${e.estimated ? " (stimato)" : ""} `,
          h("button", { onclick: () => this._call("remove_entry", { entry_id: e.id }) }, "×")))),
    );
  }

  _week() {
    const days = this._plan.attributes.days || {};
    if (!Object.keys(days).length) return h("p", {}, "Nessun piano attivo: importalo dalla scheda Importa.");
    const todayIndex = (new Date().getDay() + 6) % 7;
    const cell = (items) => (items || []).map((i) => `${i.food} (${i.kcal})`).join(", ");
    return h(
      "table",
      { style: "width:100%;border-collapse:collapse" },
      h("tr", {}, h("th", {}), ...MEALS.map((m) => h("th", {}, cap(m)))),
      ...DAYS.map((name, index) =>
        h("tr", { style: index === todayIndex ? "font-weight:600;background:rgba(127,127,127,.15)" : "" },
          h("td", {}, name),
          ...MEALS.map((meal) => h("td", { style: "vertical-align:top;font-size:.85em" }, cell((days[index] || {})[meal])))),
      ),
    );
  }

  _import() {
    const draftDays = this._plan.attributes.draft_days || {};
    const hasDraft = this._plan.state === "bozza" && Object.keys(draftDays).length;
    const textarea = h("textarea", { rows: "5", style: "width:100%", placeholder: "Incolla qui il piano del dietologo" });
    const file = h("input", { type: "file", accept: "application/pdf,image/*" });
    const send = async () => {
      try {
        if (file.files[0]) {
          const chosen = file.files[0];
          if (chosen.size > MAX_FILE_BYTES && chosen.type === "application/pdf") throw new Error("Il PDF supera i 3 MB");
          const payload = chosen.type === "application/pdf"
            ? { file_b64: await readAsBase64(chosen), mime_type: chosen.type }
            : await shrinkImage(chosen);
          await this._call("import_plan", payload, "Bozza creata: controllala qui sotto.");
        } else if (textarea.value.trim()) {
          await this._call("import_plan", { text: textarea.value.trim() }, "Bozza creata: controllala qui sotto.");
        }
      } catch (err) {
        this._message = err.message;
        this._render();
      }
    };
    return h(
      "div",
      {},
      h("p", {}, "Importa il piano da testo, PDF o foto. Dovrai controllarlo prima di attivarlo."),
      textarea,
      h("div", {}, file, h("button", { onclick: send }, "Importa")),
      hasDraft && this._draftEditor(draftDays),
    );
  }

  _draftEditor(draftDays) {
    if (!this._draft) this._draft = JSON.parse(JSON.stringify(draftDays));
    const draft = this._draft;
    const input = (item, key, type, width) =>
      h("input", {
        type, value: item[key], style: `width:${width}`,
        oninput: (ev) => { item[key] = type === "number" ? Number(ev.target.value) : ev.target.value; item.estimated = key === "kcal" ? false : item.estimated; },
      });
    const blocks = DAYS.flatMap((name, index) =>
      MEALS.filter((meal) => ((draft[index] || {})[meal] || []).length || false).map((meal) => {
        const items = draft[index][meal];
        return h("div", { style: "margin:.5em 0" },
          h("strong", {}, `${name} — ${cap(meal)}`),
          ...items.map((item, pos) => h("div", {},
            input(item, "food", "text", "40%"), input(item, "quantity", "text", "20%"), input(item, "kcal", "number", "6em"),
            item.estimated ? " (stimato) " : " ",
            h("button", { onclick: () => { items.splice(pos, 1); this._render(); } }, "×"))),
          h("button", { onclick: () => { items.push({ food: "", quantity: "", kcal: 0, estimated: false }); this._render(); } }, "+ alimento"));
      }));
    const save = () => this._call("save_draft", { days: this._draft }, "Bozza salvata.");
    const confirm = async () => {
      await this._call("save_draft", { days: this._draft });
      if (!this._message) await this._call("confirm_plan", {}, "Piano attivato.");
    };
    return h("div", {}, h("h3", {}, "Bozza da controllare"), ...blocks,
      h("button", { onclick: save }, "Salva bozza"), h("button", { onclick: confirm }, "Conferma e attiva"));
  }

  static getConfigElement() {
    return document.createElement("hui-entities-card-editor");
  }

  static getStubConfig() {
    return { entity: "sensor.we_eat_menu" };
  }
}
customElements.define("we-eat-card", WeEatCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "we-eat-card",
  name: "We Eat Card",
  description: "Piano settimanale del dietologo, diario dei pasti e conteggio calorie.",
});
```

- [ ] **Step 2: Verifica la sintassi JavaScript**

Run: `node --check we_eat_card.js`
Expected: nessun output, exit code 0. (Se `node` manca, salta: il controllo reale è lo smoke test del Task 11.)

- [ ] **Step 3: Commit**

```bash
git add we_eat_card.js
git commit -m "feat: card with today, week and import tabs (draft editor included)"
```

---

### Task 11: README, hacs.json e verifica finale

**Files:**
- Modify: `README.md`, `hacs.json`

- [ ] **Step 1: Aggiorna `hacs.json`**

```json
{
  "name": "We Eat Menu",
  "content_in_root": false,
  "homeassistant": "2024.11.0",
  "render_readme": true
}
```

- [ ] **Step 2: Riscrivi `README.md`**

```markdown
# We Eat — il piano del dietologo e le calorie, in Home Assistant

**Il piano settimanale del dietologo sempre sotto mano, e un diario che conta le calorie di quello che mangi.**
Importi il piano da testo, PDF o foto; ogni giorno vedi cosa mangiare, segni "fatto" con un tocco e aggiungi gli extra
scrivendo cosa hai mangiato.

---

## Cosa fa

- **Importa il piano** da testo incollato, PDF (con testo) o foto, con un LLM. Il risultato è una *bozza* che controlli e correggi prima di attivarla.
- **Mostra il piano della settimana** e il pasto del momento (`sensor.we_eat_menu`).
- **Conta le calorie**: "Fatto come da piano" copia le kcal del piano; per gli extra scrivi (es. "2 fette di pizza") e l'AI stima le kcal.
- **Obiettivo giornaliero** facoltativo, con le kcal rimanenti.
- **Card Lovelace** con tre schede: Oggi, Settimana, Importa.

> Le calorie stimate dall'AI sono approssimative e non sono un parere medico: segui sempre le indicazioni del tuo dietologo.

---

## Installazione

### Con HACS (consigliato)

1. Aggiungi questo repository come **Integrazione** personalizzata in HACS.
2. Installa e riavvia Home Assistant.
3. **Impostazioni → Dispositivi e servizi → Aggiungi integrazione → We Eat**.

### A mano

1. Copia `custom_components/we_eat` in `config/custom_components/`.
2. Copia `we_eat_card.js` in `config/www/` e aggiungilo come risorsa Lovelace (`/local/we_eat_card.js`, tipo *modulo JavaScript*).
3. Riavvia Home Assistant.

---

## Configurazione

Dalla procedura guidata scegli il **provider AI** e inserisci la **chiave API**:

| Provider | Legge le foto | Note |
|---|---|---|
| OpenAI | sì | |
| Google Gemini | sì | |
| Anthropic Claude | sì | |
| DeepSeek | no | solo testo e PDF con testo |
| Nessuno | — | piano e kcal inseriti a mano |

Il campo *Modello* può restare vuoto (si usa quello predefinito). Nelle **opzioni** puoi impostare l'obiettivo di kcal
giornaliero e gli orari di inizio dei pasti (colazione, spuntino, pranzo, merenda, cena).

**Privacy e costi:** con un provider AI attivo, il testo (o la foto) del piano e la descrizione degli extra vengono
inviati a quel provider, e ogni importazione o stima nuova è una chiamata a pagamento. Le stime già fatte vengono
ricordate e non si pagano due volte. La chiave resta in Home Assistant.

**Aggiornamento dalla 0.1:** la sezione `we_eat:` di `configuration.yaml` viene importata una volta (le ricette diventano
"piatti preferiti", attributo `favorites` del menu) e puoi poi rimuoverla. Il menu casuale non esiste più: lo sostituisce il piano.

---

## Entità

| Entità | Stato |
|---|---|
| `sensor.we_eat_menu` | pasto in corso (o prossimo) del piano di oggi |
| `sensor.we_eat_piano_settimana` | `attivo`, `bozza` o `assente`; attributo `days` con la settimana |
| `sensor.we_eat_kcal_consumate` | kcal di oggi; attributi `by_meal`, `entries` |
| `sensor.we_eat_kcal_rimanenti` | obiettivo meno consumate (solo se impostato) |

## Card

```yaml
type: custom:we-eat-card
entity: sensor.we_eat_menu
```

## Servizi

| Servizio | Campi | Cosa fa |
|---|---|---|
| `we_eat.import_plan` | `text` oppure `file_b64` + `mime_type` | Crea la bozza del piano |
| `we_eat.save_draft` | `days` | Salva le correzioni alla bozza |
| `we_eat.confirm_plan` | — | Rende attiva la bozza |
| `we_eat.log_plan_meal` | `meal` | Segna il pasto come da piano |
| `we_eat.log_extra` | `text`, `meal`, `kcal` (facoltativo) | Aggiunge un extra; senza `kcal` le stima l'AI |
| `we_eat.remove_entry` | `entry_id` | Elimina una voce del diario |

---

## Licenza

[MIT](LICENSE) © Antonino Di Stefano
```

- [ ] **Step 3: Esegui tutta la suite e i controlli statici**

Run:
```bash
python -m pytest -q
python -m py_compile custom_components/we_eat/*.py custom_components/we_eat/llm/*.py
grep -rn "api_key" custom_components/we_eat/sensor.py custom_components/we_eat/snapshot.py || echo "nessuna chiave nei sensori"
```
Expected: tutti i test passano; nessun errore di compilazione; `nessuna chiave nei sensori`.

- [ ] **Step 4: Smoke test manuale in una Home Assistant di prova (2024.11+)**

Copia `custom_components/we_eat` e `we_eat_card.js`, riavvia, poi verifica:
1. **Aggiungi integrazione → We Eat** con provider *Nessuno*: si crea la voce; compaiono `sensor.we_eat_menu`, `_piano_settimana` (`assente`), `_kcal_consumate` (0).
2. Da *Strumenti per sviluppatori → Azioni*: `we_eat.save_draft` con `days: {"0": {"pranzo": [{"food": "Pasta", "kcal": 300}]}}` → `piano_settimana` diventa `bozza`; poi `we_eat.confirm_plan` → `attivo`; se oggi è lunedì `sensor.we_eat_menu` mostra "Pranzo: Pasta".
3. `we_eat.log_plan_meal` con `meal: pranzo` → kcal consumate = 300; ripeterlo dà l'errore "già registrato oggi".
4. `we_eat.log_extra` con `kcal: 120` → 420. Senza `kcal` e con provider *Nessuno* → errore "Nessun provider AI configurato".
5. Opzioni: imposta un obiettivo kcal → compare `sensor.we_eat_kcal_rimanenti`.
6. Con una chiave vera (es. DeepSeek): incolla un piano di prova dalla scheda *Importa* → bozza modificabile → *Conferma e attiva*; prova un extra a testo libero. Con DeepSeek una foto deve dare il messaggio "non legge le immagini".
7. Aggiungi la card (`type: custom:we-eat-card`) e controlla le tre schede; riavvia HA e verifica che piano e diario siano ancora lì.
8. CI: dopo il push, i job hassfest, HACS e pytest devono essere verdi (se hassfest segnala chiavi di traduzione mancanti, allinea `strings.json` e `translations/it.json`).

- [ ] **Step 5: Commit**

```bash
git add README.md hacs.json
git commit -m "docs: README for the dietitian plan and calorie tracking, min HA 2024.11"
```
