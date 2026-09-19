# We Eat — il piano del dietologo e le calorie, in Home Assistant

**Il piano settimanale del dietologo sempre sotto mano, e un diario che conta le calorie di quello che mangi.**
Importi il piano da testo, PDF o foto; ogni giorno vedi cosa mangiare, segni "fatto" con un tocco e aggiungi gli extra
scrivendo cosa hai mangiato.

[![Validate](https://github.com/iAlias/HomeAssistantWeEat/actions/workflows/validate.yml/badge.svg)](https://github.com/iAlias/HomeAssistantWeEat/actions/workflows/validate.yml)
[![HACS](https://img.shields.io/badge/HACS-Custom-41bdf5)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.11%2B-41bdf5)](https://www.home-assistant.io/)
[![Versione](https://img.shields.io/badge/versione-0.2.0-orange)](custom_components/we_eat/manifest.json)
[![Licenza](https://img.shields.io/badge/licenza-MIT-green)](LICENSE)

🇬🇧 [Read in English](README.md)

---

## Indice

- [Cosa fa](#cosa-fa)
- [Installazione](#installazione)
- [Configurazione](#configurazione)
- [Entità](#entità)
- [Card](#card)
- [Servizi](#servizi)
- [Requisiti](#requisiti)
- [Licenza](#licenza)

---

## Cosa fa

- **Importa il piano** da testo incollato, PDF (con testo) o foto, con un LLM. Il risultato è una *bozza* che controlli e
  correggi prima di attivarla.
- **Mostra il piano della settimana** e il pasto del momento (`sensor.we_eat_menu`).
- **Conta le calorie**: "Fatto come da piano" copia le kcal del piano; per gli extra scrivi (es. "2 fette di pizza") e
  l'AI stima le kcal.
- **Obiettivo giornaliero** facoltativo, con le kcal rimanenti.
- **Card Lovelace** con tre schede: Oggi, Settimana, Importa.

> Le calorie stimate dall'AI sono approssimative e non sono un parere medico: segui sempre le indicazioni del tuo dietologo.

---

## Installazione

### Con HACS (consigliato)

1. Aggiungi questo repository come **Integrazione** personalizzata in HACS
2. Installa e riavvia Home Assistant
3. **Impostazioni → Dispositivi e servizi → Aggiungi integrazione → We Eat**

### A mano

1. Copia `custom_components/we_eat` in `config/custom_components/`
2. Copia `we_eat_card.js` in `config/www/` e aggiungilo come risorsa Lovelace (`/local/we_eat_card.js`, tipo
   *modulo JavaScript*)
3. Riavvia Home Assistant

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
"piatti preferiti", attributo `favorites` del menu) e puoi poi rimuoverla. Il menu casuale non esiste più: lo sostituisce
il piano.

---

## Entità

| Entità | Stato |
|---|---|
| `sensor.we_eat_menu` | pasto in corso (o prossimo) del piano di oggi |
| `sensor.we_eat_piano_settimana` | `attivo`, `bozza` o `assente`; attributo `days` con la settimana |
| `sensor.we_eat_kcal_consumate` | kcal di oggi; attributi `by_meal`, `entries` |
| `sensor.we_eat_kcal_rimanenti` | obiettivo meno consumate (solo se impostato) |

---

## Card

```yaml
type: custom:we-eat-card
entity: sensor.we_eat_menu
```

---

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

## Requisiti

- Home Assistant **2024.11** o successivo
- [HACS](https://hacs.xyz/) (facoltativo, per gli aggiornamenti con un clic) oppure installazione manuale
- Una chiave API di OpenAI, Google Gemini, Anthropic o DeepSeek (facoltativa: senza, piano e kcal si inseriscono a mano)

## Licenza

[MIT](LICENSE) © Antonino Di Stefano
