# We Eat — your dietitian's plan and calorie diary for Home Assistant

**Your dietitian's weekly plan always at hand, and a diary that counts the calories of what you eat.**
Import the plan from text, PDF or photo; every day you see what to eat, tick meals off with one tap and add
extras by simply typing what you ate.

[![Validate](https://github.com/iAlias/HomeAssistantWeEat/actions/workflows/validate.yml/badge.svg)](https://github.com/iAlias/HomeAssistantWeEat/actions/workflows/validate.yml)
[![HACS](https://img.shields.io/badge/HACS-Custom-41bdf5)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.11%2B-41bdf5)](https://www.home-assistant.io/)
[![Version](https://img.shields.io/badge/version-0.2.0-orange)](custom_components/we_eat/manifest.json)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

🇮🇹 [Leggi in italiano](README.it.md)

---

## Contents

- [What it does](#what-it-does)
- [Installation](#installation)
- [Configuration](#configuration)
- [Entities](#entities)
- [Card](#card)
- [Services](#services)
- [Requirements](#requirements)
- [License](#license)

---

## What it does

- **Imports the plan** from pasted text, a PDF (with a text layer) or a photo, using an LLM. The result is a *draft* you
  review and correct before activating it.
- **Shows the weekly plan** and the current meal (`sensor.we_eat_menu`).
- **Counts calories**: "Done as planned" copies the plan's kcal; for extras you type what you ate (e.g. "2 slices of
  pizza") and the AI estimates the kcal.
- Optional **daily target**, with the remaining kcal.
- **Lovelace card** with three tabs: Today, Week, Import.

> Calories estimated by the AI are approximate and are not medical advice: always follow your dietitian's guidance.

---

## Installation

### With HACS (recommended)

1. Add this repository as a custom **Integration** in HACS
2. Install it, then restart Home Assistant
3. **Settings → Devices & services → Add integration → We Eat**

### Manually

1. Copy `custom_components/we_eat` into `config/custom_components/`
2. Copy `we_eat_card.js` into `config/www/` and add it as a Lovelace resource (`/local/we_eat_card.js`, type
   *JavaScript module*)
3. Restart Home Assistant

---

## Configuration

In the setup wizard pick the **AI provider** and enter the **API key**:

| Provider | Reads photos | Notes |
|---|---|---|
| OpenAI | yes | |
| Google Gemini | yes | |
| Anthropic Claude | yes | |
| DeepSeek | no | text and text-layer PDFs only |
| None | — | plan and kcal entered by hand |

The *Model* field can stay empty (the default is used). In the **options** you can set the daily kcal target and the
start time of each meal (breakfast, snack, lunch, afternoon snack, dinner).

**Privacy and cost:** with an AI provider enabled, the text (or photo) of the plan and the description of extras are sent
to that provider, and every new import or estimate is a paid call. Estimates already made are remembered and never paid
for twice. The key stays in Home Assistant.

**Upgrading from 0.1:** the `we_eat:` section of `configuration.yaml` is imported once (the recipes become "favourite
dishes", the `favorites` attribute of the menu) and you can then remove it. The random menu is gone: the plan replaces it.

---

## Entities

| Entity | State |
|---|---|
| `sensor.we_eat_menu` | current (or next) meal of today's plan |
| `sensor.we_eat_piano_settimana` | `attivo`, `bozza` or `assente`; the `days` attribute holds the week |
| `sensor.we_eat_kcal_consumate` | today's kcal; attributes `by_meal`, `entries` |
| `sensor.we_eat_kcal_rimanenti` | target minus consumed (only when a target is set) |

---

## Card

```yaml
type: custom:we-eat-card
entity: sensor.we_eat_menu
```

---

## Services

| Service | Fields | What it does |
|---|---|---|
| `we_eat.import_plan` | `text` or `file_b64` + `mime_type` | Creates the draft plan |
| `we_eat.save_draft` | `days` | Saves the edits made to the draft |
| `we_eat.confirm_plan` | — | Makes the draft the active plan |
| `we_eat.log_plan_meal` | `meal` | Logs the meal as planned |
| `we_eat.log_extra` | `text`, `meal`, `kcal` (optional) | Adds an extra; without `kcal` the AI estimates it |
| `we_eat.remove_entry` | `entry_id` | Deletes a diary entry |

---

## Requirements

- Home Assistant **2024.11** or newer
- [HACS](https://hacs.xyz/) (optional, for one-click updates) or manual installation
- An API key from OpenAI, Google Gemini, Anthropic or DeepSeek (optional: without one, plan and kcal are entered by hand)

## License

[MIT](LICENSE) © Antonino Di Stefano
