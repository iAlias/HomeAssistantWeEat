# We Eat — il menu di casa per Home Assistant

**"Cosa si mangia oggi?" risolto da un sensore.** Una ricetta a caso dalla tua lista, rinnovata
automaticamente a **pranzo (12:00)** e **cena (19:00)**, con una card per cambiarla al volo.

Smetti di discutere su cosa cucinare: metti in Home Assistant la lista dei piatti di casa e lascia
che il menu si proponga da solo. Se un piatto non va bene, lo cambi con un tocco direttamente dalla
card.

---

## Cosa fa

- Sceglie una **ricetta casuale** da una lista configurabile
- La **rinnova due volte al giorno**, alle 12:00 e alle 19:00
- Espone il sensore **`sensor.we_eat_menu`** (stato = piatto del giorno, attributo `recipes` = lista)
- Offre **servizi** per aggiungere, rimuovere o sostituire le ricette
- Include una **Lovelace card** (`custom:we-eat-card`) con modifica inline

---

## Installazione

### Con HACS (consigliato)

1. Aggiungi questo repository come **Integrazione** personalizzata in HACS
2. Installa e riavvia Home Assistant

### A mano

1. Copia la cartella `custom_components/we_eat` in `config/custom_components/`
2. Copia `we_eat_card.js` nella cartella `www` e aggiungilo come risorsa Lovelace
3. Riavvia Home Assistant

---

## Configurazione

Aggiungi a `configuration.yaml`:

```yaml
we_eat:
  recipes:
    - Spaghetti
    - Pizza
    - Risotto
```

Se non specifichi nulla, la lista predefinita è *Spaghetti · Pizza · Risotto*.
Dopo il riavvio trovi il sensore `sensor.we_eat_menu`.

---

## Card

```yaml
type: custom:we-eat-card
entity: sensor.we_eat_menu
editable: true
```

Con `editable: true` puoi aggiungere e rimuovere ricette direttamente dalla card.

---

## Servizi

| Servizio | Campo | Cosa fa |
|---|---|---|
| `we_eat.set_recipes` | `recipes` | Sostituisce l'intera lista |
| `we_eat.add_recipe` | `recipe` | Aggiunge un piatto |
| `we_eat.remove_recipe` | `recipe` | Rimuove un piatto |

Esempio in un'automazione:

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

## Licenza

[MIT](LICENSE) © Antonino Di Stefano
