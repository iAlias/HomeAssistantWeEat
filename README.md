# We Eat — the household menu for Home Assistant

**"What's for dinner?" solved by a sensor.** A random recipe from your own list, refreshed
automatically at **lunch (12:00)** and **dinner (19:00)**, with a card to change it on the spot.

[![Validate](https://github.com/iAlias/HomeAssistantWeEat/actions/workflows/validate.yml/badge.svg)](https://github.com/iAlias/HomeAssistantWeEat/actions/workflows/validate.yml)
[![HACS](https://img.shields.io/badge/HACS-Custom-41bdf5)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2023.0%2B-41bdf5)](https://www.home-assistant.io/)
[![Version](https://img.shields.io/badge/version-0.1.0-orange)](custom_components/we_eat/manifest.json)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

🇮🇹 [Leggi in italiano](README.it.md)

Stop arguing about what to cook: put your household's list of dishes into Home Assistant and let
the menu suggest itself. If a dish doesn't sound right, swap it with a single tap straight from the
card.

---

## Contents

- [What it does](#what-it-does)
- [Installation](#installation)
- [Configuration](#configuration)
- [Card](#card)
- [Services](#services)
- [Requirements](#requirements)
- [License](#license)

---

## What it does

- Picks a **random recipe** from a configurable list
- **Refreshes it twice a day**, at 12:00 and at 19:00
- Exposes the **`sensor.we_eat_menu`** sensor (state = today's dish, `recipes` attribute = the
  full list)
- Provides **services** to add, remove or replace recipes
- Ships a **Lovelace card** (`custom:we-eat-card`) with inline editing

---

## Installation

### With HACS (recommended)

1. Add this repository as a custom **Integration** in HACS
2. Install it, then restart Home Assistant

### Manually

1. Copy the `custom_components/we_eat` folder into `config/custom_components/`
2. Copy `we_eat_card.js` into your `www` folder and add it as a Lovelace resource
3. Restart Home Assistant

---

## Configuration

Add to `configuration.yaml`:

```yaml
we_eat:
  recipes:
    - Spaghetti
    - Pizza
    - Risotto
```

If you don't specify anything, the default list is *Spaghetti · Pizza · Risotto*.
After restarting you'll find the `sensor.we_eat_menu` entity.

---

## Card

```yaml
type: custom:we-eat-card
entity: sensor.we_eat_menu
editable: true
```

With `editable: true` you can add and remove recipes directly from the card.

---

## Services

| Service | Field | What it does |
|---|---|---|
| `we_eat.set_recipes` | `recipes` | Replaces the whole list |
| `we_eat.add_recipe` | `recipe` | Adds a dish |
| `we_eat.remove_recipe` | `recipe` | Removes a dish |

Example, from an automation:

```yaml
action:
  - service: we_eat.set_recipes
    data:
      recipes:
        - Lasagne
        - Minestrone
        - Pollo al forno
```

---

## Requirements

- Home Assistant **2023.0** or newer
- [HACS](https://hacs.xyz/) (optional, for one-click updates) or manual installation

## License

[MIT](LICENSE) © Antonino Di Stefano
