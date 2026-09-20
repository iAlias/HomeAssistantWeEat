# We Eat — dietitian's plan and calorie diary

**Your dietitian's weekly plan inside Home Assistant, and a diary that counts the calories of what you actually eat.**

[![Validate](https://github.com/iAlias/HomeAssistantWeEat/actions/workflows/validate.yml/badge.svg)](https://github.com/iAlias/HomeAssistantWeEat/actions/workflows/validate.yml)
[![HACS](https://img.shields.io/badge/HACS-Custom-41bdf5)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.11%2B-41bdf5)](https://www.home-assistant.io/)
[![Version](https://img.shields.io/badge/version-0.2.4-orange)](custom_components/we_eat/manifest.json)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

🇮🇹 [Leggi in italiano](README.it.md)

Photograph the sheet your dietitian gave you, or paste its text, and an LLM turns it into a
structured weekly plan — which **you review and correct before it becomes active**, because a diet
plan is not something a model should be trusted to transcribe unsupervised. From then on the card
shows what to eat today, you tick each meal off with one tap, and anything eaten off-plan is logged
by simply typing it ("two slices of pizza").

> ⚠️ Calories estimated by the AI are approximate and are **not medical advice**. Always follow your
> dietitian's own instructions.

---

## Contents

- [What it does](#what-it-does)
- [Requirements](#requirements)
- [Installation](#installation)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [What you get in Home Assistant](#what-you-get-in-home-assistant)
- [The card](#the-card)
- [Services](#services)
- [How it works](#how-it-works)
- [Things worth knowing](#things-worth-knowing)
- [Development](#development)
- [Issues and contributions](#issues-and-contributions)
- [License](#license)

---

## What it does

- **Imports the plan** from pasted text, a PDF with a text layer, or a photo, using the LLM provider
  of your choice. The result is a **draft** you edit and confirm — it never activates by itself.
- **Shows today's meal and the whole week**, with foods, quantities and kcal per meal.
- **Counts calories**: "Done as planned" copies the kcal straight from the plan; for extras you type
  what you ate and the AI estimates the kcal.
- Optional **daily kcal target**, with a progress bar and the remaining kcal as their own sensor.
- Ships a **Lovelace card** with three tabs — Today, Week, Import — including the draft editor, and a
  ready-to-use **"We Eat" sidebar panel** that appears by itself, nothing to add by hand.
- **Works without any AI too**: pick provider *None* and enter the plan and the kcal by hand.

---

## Requirements

- Home Assistant **2024.11.0** or newer
- [HACS](https://hacs.xyz/) (optional, for one-click updates) or manual installation
- An API key from OpenAI, Google Gemini, Anthropic or DeepSeek — **optional**, see the table below

---

## Installation

### Via HACS (recommended)

This integration is not in the HACS default store; add it as a custom repository:

1. HACS → Integrations → ⋮ menu → **Custom repositories**
2. Add `https://github.com/iAlias/HomeAssistantWeEat` with category **Integration**
3. Install it, then restart Home Assistant
4. **Settings → Devices & services → Add integration → We Eat**

### Manually

1. Copy `custom_components/we_eat` into `config/custom_components/`
2. Restart Home Assistant, then add the integration as in step 4 above

**The card installs itself**, together with a **"We Eat" sidebar panel**: the integration serves and
loads both automatically, so there is no file to copy into `www/`, no Lovelace resource to register
and no dashboard to create. If you added `/local/we_eat_card.js` by hand in an earlier version,
remove that resource: it is no longer needed.

---

## Getting started

1. **Pick your provider** in the setup wizard and paste the API key. The key is checked with a test
   call before the entry is created. Choosing *None* is fine — everything still works by hand.
2. **Open the "We Eat" panel** from the sidebar — it is already there, card included. Alternatively
   add the card to any dashboard — Edit dashboard → Add card → search **We Eat**, or paste:
   ```yaml
   type: custom:we-eat-card
   entity: sensor.we_eat_menu
   ```
3. **Import the plan** from the *Import* tab: paste the text, or upload the PDF or a photo of the
   sheet, and press **Importa**.
4. **Review the draft.** Every food, quantity and kcal value is editable; values the AI had to guess
   are flagged *(stimato)*. Add or delete rows, then press **Conferma e attiva**.
5. **Use it daily** from the *Today* tab: press **Fatto come da piano** for each meal you ate as
   planned, and type anything extra into the text box.
6. Optionally set a **daily kcal target** in the integration options to get the progress bar and the
   `sensor.we_eat_kcal_rimanenti` entity.

---

## Configuration

Everything is configured through the UI. Provider and key are set in the wizard and can be changed
later in **Configure**, together with the target and the meal times.

| Provider | Reads photos | Default model |
|---|---|---|
| OpenAI | yes | `gpt-4o-mini` |
| Google Gemini | yes | `gemini-2.0-flash` |
| Anthropic Claude | yes | `claude-haiku-4-5-20251001` |
| DeepSeek | **no** — text and text-layer PDFs only | `deepseek-chat` |
| None | — | plan and kcal entered by hand |

Leave *Model* empty to use the default, or type any model name the provider accepts.

The five meals — **breakfast, snack, lunch, afternoon snack, dinner** — are fixed; their **start
times** (07:30, 10:30, 12:30, 16:30, 19:30 by default) are configurable and decide which meal
`sensor.we_eat_menu` shows at any moment.

**Privacy and cost.** With an AI provider enabled, the text or photo of the plan and the description
of each extra are sent to that provider, and every import or *new* estimate is a billed API call.
Estimates are cached by description, so "two slices of pizza" is paid for once and reused afterwards.
The key never leaves Home Assistant and never appears in entity attributes or logs.

**Upgrading from 0.1.** The `we_eat:` section of `configuration.yaml` is imported once — the recipes
become "favourite dishes" in the `favorites` attribute of the menu sensor — and a repair issue tells
you to remove it. The random menu and the `add_recipe` / `remove_recipe` / `set_recipes` services are
gone: the plan replaces them.

---

## What you get in Home Assistant

| Entity | State | Attributes |
|---|---|---|
| `sensor.we_eat_menu` | current (or next) meal of today's plan, e.g. `Pranzo: Pasta, Insalata` | `meal`, `today` (all of today's meals), `kcal_planned`, `favorites` |
| `sensor.we_eat_piano_settimana` | `attivo`, `bozza` or `assente` | `days` (the whole week), `draft_days` |
| `sensor.we_eat_kcal_consumate` | kcal eaten today | `by_meal`, `entries` (today's diary), `target` |
| `sensor.we_eat_kcal_rimanenti` | target minus consumed | — (created only when a target is set) |

All four are backed by one coordinator and update at midnight, at every meal time, and immediately
after any change to the plan or the diary.

---

## The card

The **We Eat** sidebar panel is this same card, already mounted for you. The standalone card is only
for when you prefer it inside one of your own dashboards.

```yaml
type: custom:we-eat-card
entity: sensor.we_eat_menu
```

| Option | Default | What it is |
|---|---|---|
| `entity` | `sensor.we_eat_menu` | the menu sensor |
| `plan_entity` | `sensor.we_eat_piano_settimana` | the weekly plan sensor |
| `kcal_entity` | `sensor.we_eat_kcal_consumate` | the calorie sensor |

Renaming the device renames its entities, so these ids may not match on your system. You rarely need
to set them: when an id doesn't resolve, the card recognises each of its three sensors by the
attributes only that sensor has.

- **Today** — each planned meal with its foods and kcal, a *Fatto come da piano* button per meal, a
  free-text box for extras (with an optional kcal field that skips the AI call), the kcal progress
  bar and today's diary, each row deletable.
- **Week** — the 7 × 5 grid of the active plan, today's row highlighted.
- **Import** — paste text or upload a PDF/photo, then the draft editor.

Photos are resized in the browser before upload; the service accepts files up to 3 MB.

---

## Services

| Service | Fields | What it does |
|---|---|---|
| `we_eat.import_plan` | `text`, or `file_b64` + `mime_type` | Builds a draft plan with the LLM |
| `we_eat.save_draft` | `days` | Saves corrections to the draft |
| `we_eat.confirm_plan` | — | Makes the draft the active plan |
| `we_eat.log_plan_meal` | `meal` | Logs the meal as planned, copying its kcal |
| `we_eat.log_extra` | `text`, `meal`, `kcal` *(optional)* | Logs an extra; without `kcal` the AI estimates it |
| `we_eat.remove_entry` | `entry_id` | Deletes a diary entry |

Example, from an automation:

```yaml
action:
  - action: we_eat.log_extra
    data:
      text: Un caffè macchiato
      meal: spuntino
      kcal: 35
```

---

## How it works

- **The plan is data, not a prompt.** The LLM is asked for strict JSON, which is then validated
  against the integration's own schema: unknown meals, unparseable days, missing foods or negative
  kcal are rejected. If validation fails, the model is asked once more with the error quoted back to
  it — then the import gives up with a readable message instead of storing garbage.
- **A draft is never the plan.** Imports write to a separate draft slot, so re-importing never
  destroys the plan you are currently following until you confirm the new one.
- **Logged kcal are frozen.** "Done as planned" copies the meal's kcal into the diary at that moment;
  editing the plan afterwards never rewrites your history. The same meal cannot be logged twice in
  one day.
- **The AI is called twice at most.** Once per import, once per *unseen* extra description. Everything
  else — totals, which meal is current, remaining kcal — is computed locally.
- **Storage** lives in `.storage/we_eat` (plan, draft, diary, estimate cache, favourites) and survives
  restarts. The estimate cache holds the 500 most recent descriptions.

---

## Things worth knowing

- **The estimates are guesses, and so is part of the transcription.** Whenever the source sheet
  doesn't state calories, the model invents a plausible number and the entry is flagged *stimato*.
  Review the draft properly — that step exists for a reason.
- **DeepSeek cannot read photos.** Its API is text-only; a photo import with DeepSeek selected fails
  with an explicit message. Use text, a text-layer PDF, or one of the other three providers.
- **Scanned PDFs are not supported.** There is no OCR: a PDF without a text layer is refused, with a
  message asking for a photo or the text instead. Photos of paper sheets work — send the photo, not a
  scan wrapped in a PDF.
- **Every import and every new extra costs money** on your provider account. Repeated descriptions are
  served from the cache and cost nothing.
- **One instance only.** The integration is `single_config_entry`, and the diary is a single household
  diary — there is no per-person tracking.
- **No macronutrients and no food database.** Protein, carbs, fat, barcodes and packaged-product
  lookups are deliberately out of scope for this version.
- **This is not a medical device.** It is a convenience for following a plan a professional gave you.

---

## Development

```bash
pip install -r requirements_test.txt
pytest -q
```

64 tests cover the parts that can break silently — plan validation, diary and kcal totals, the sensor
snapshot, all four LLM clients against fake HTTP responses, PDF extraction and the import/estimate
retry logic. They import no Home Assistant code, so they run on any OS with just `pytest` installed.

The Home Assistant layer (coordinator, config flow, sensors) and the card are not unit-tested: CI
validates them with **hassfest** and **HACS** on every push, and the rest is verified by loading the
integration in a test instance.

---

## Issues and contributions

Found a bug, or a plan the importer gets wrong? Open an issue at
[github.com/iAlias/HomeAssistantWeEat/issues](https://github.com/iAlias/HomeAssistantWeEat/issues).
When reporting an import problem, include the text you fed it — never your API key.

---

## License

[MIT](LICENSE) © Antonino Di Stefano
