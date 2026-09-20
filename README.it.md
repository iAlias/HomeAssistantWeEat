# We Eat — il piano del dietologo e il diario delle calorie

**Il piano settimanale del dietologo dentro Home Assistant, e un diario che conta le calorie di quello che mangi davvero.**

[![Validate](https://github.com/iAlias/HomeAssistantWeEat/actions/workflows/validate.yml/badge.svg)](https://github.com/iAlias/HomeAssistantWeEat/actions/workflows/validate.yml)
[![HACS](https://img.shields.io/badge/HACS-Custom-41bdf5)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.11%2B-41bdf5)](https://www.home-assistant.io/)
[![Versione](https://img.shields.io/badge/versione-0.2.4-orange)](custom_components/we_eat/manifest.json)
[![Licenza](https://img.shields.io/badge/licenza-MIT-green)](LICENSE)

🇬🇧 [Read in English](README.md)

Fotografa il foglio che ti ha dato il dietologo, oppure incollane il testo, e un LLM lo trasforma in
un piano settimanale strutturato — che **controlli e correggi prima che diventi attivo**, perché la
trascrizione di una dieta non è una cosa da lasciare a un modello senza supervisione. Da lì in poi la
card mostra cosa mangiare oggi, segni ogni pasto con un tocco e quello che mangi fuori piano lo
registri semplicemente scrivendolo ("due fette di pizza").

> ⚠️ Le calorie stimate dall'AI sono approssimative e **non sono un parere medico**. Segui sempre le
> indicazioni del tuo dietologo.

---

## Indice

- [Cosa fa](#cosa-fa)
- [Requisiti](#requisiti)
- [Installazione](#installazione)
- [Primi passi](#primi-passi)
- [Configurazione](#configurazione)
- [Cosa trovi in Home Assistant](#cosa-trovi-in-home-assistant)
- [La card](#la-card)
- [Servizi](#servizi)
- [Come funziona](#come-funziona)
- [Cose da sapere prima di fidarsi](#cose-da-sapere-prima-di-fidarsi)
- [Sviluppo](#sviluppo)
- [Segnalazioni e contributi](#segnalazioni-e-contributi)
- [Licenza](#licenza)

---

## Cosa fa

- **Importa il piano** da testo incollato, da un PDF con testo o da una foto, con il provider LLM che
  preferisci. Il risultato è una **bozza** che modifichi e confermi: non si attiva mai da sola.
- **Mostra il pasto di oggi e tutta la settimana**, con alimenti, quantità e kcal per ogni pasto.
- **Conta le calorie**: "Fatto come da piano" copia le kcal direttamente dal piano; per gli extra
  scrivi cosa hai mangiato e l'AI stima le kcal.
- **Obiettivo kcal giornaliero** facoltativo, con barra di avanzamento e le kcal rimanenti come
  sensore a sé.
- Include una **card Lovelace** con tre schede — Oggi, Settimana, Importa — editor della bozza compreso,
  e un **pannello laterale "We Eat"** già pronto: appare da solo, senza aggiungere nulla a mano.
- **Funziona anche senza AI**: scegli provider *Nessuno* e inserisci piano e kcal a mano.

---

## Requisiti

- Home Assistant **2024.11.0** o successivo
- [HACS](https://hacs.xyz/) (facoltativo, per gli aggiornamenti con un clic) oppure installazione manuale
- Una chiave API di OpenAI, Google Gemini, Anthropic o DeepSeek — **facoltativa**, vedi la tabella sotto

---

## Installazione

### Con HACS (consigliato)

L'integrazione non è nello store predefinito di HACS: aggiungila come repository personalizzato.

1. HACS → Integrazioni → menu ⋮ → **Repository personalizzati**
2. Aggiungi `https://github.com/iAlias/HomeAssistantWeEat` con categoria **Integration**
3. Installa e riavvia Home Assistant
4. **Impostazioni → Dispositivi e servizi → Aggiungi integrazione → We Eat**

### A mano

1. Copia `custom_components/we_eat` in `config/custom_components/`
2. Riavvia Home Assistant e aggiungi l'integrazione come al punto 4 qui sopra

**La card si installa da sola**, e con lei un **pannello "We Eat" nella barra laterale**: l'integrazione
serve e carica entrambi in automatico, quindi non c'è nessun file da copiare in `www/`, nessuna
risorsa Lovelace da registrare e nessuna dashboard da creare. Se in una versione precedente avevi
aggiunto a mano `/local/we_eat_card.js`, rimuovi quella risorsa: non serve più.

---

## Primi passi

1. **Scegli il provider** nella procedura guidata e incolla la chiave API. La chiave viene verificata
   con una chiamata di prova prima di creare la voce. Puoi anche scegliere *Nessuno*: tutto continua a
   funzionare a mano.
2. **Apri il pannello "We Eat"** dalla barra laterale: è già pronto, con la card dentro. In alternativa
   puoi aggiungere la card a una dashboard qualsiasi — Modifica dashboard → Aggiungi card → cerca
   **We Eat**, oppure incolla:
   ```yaml
   type: custom:we-eat-card
   entity: sensor.we_eat_menu
   ```
3. **Importa il piano** dalla scheda *Importa*: incolla il testo, oppure carica il PDF o una foto del
   foglio, e premi **Importa**.
4. **Controlla la bozza.** Alimenti, quantità e kcal sono tutti modificabili; i valori che l'AI ha
   dovuto indovinare sono marcati *(stimato)*. Aggiungi o togli righe, poi premi **Conferma e attiva**.
5. **Usala ogni giorno** dalla scheda *Oggi*: premi **Fatto come da piano** per i pasti che hai fatto
   come previsto e scrivi gli extra nella casella di testo.
6. Se vuoi, imposta l'**obiettivo kcal giornaliero** nelle opzioni per avere la barra di avanzamento e
   l'entità `sensor.we_eat_kcal_rimanenti`.

---

## Configurazione

Si configura tutto dall'interfaccia. Provider e chiave si impostano nella procedura guidata e si
cambiano poi da **Configura**, insieme all'obiettivo e agli orari dei pasti.

| Provider | Legge le foto | Modello predefinito |
|---|---|---|
| OpenAI | sì | `gpt-4o-mini` |
| Google Gemini | sì | `gemini-2.0-flash` |
| Anthropic Claude | sì | `claude-haiku-4-5-20251001` |
| DeepSeek | **no** — solo testo e PDF con testo | `deepseek-chat` |
| Nessuno | — | piano e kcal inseriti a mano |

Lascia vuoto il campo *Modello* per usare quello predefinito, oppure scrivi il nome di un qualsiasi
modello accettato dal provider.

I cinque pasti — **colazione, spuntino, pranzo, merenda, cena** — sono fissi; i loro **orari di
inizio** (07:30, 10:30, 12:30, 16:30, 19:30 di default) sono configurabili e decidono quale pasto
mostra `sensor.we_eat_menu` in ogni momento.

**Privacy e costi.** Con un provider AI attivo, il testo o la foto del piano e la descrizione di ogni
extra vengono inviati a quel provider, e ogni importazione o stima *nuova* è una chiamata API a
pagamento. Le stime sono messe in cache per descrizione, quindi "due fette di pizza" si paga una volta
sola e poi viene riusata. La chiave non esce mai da Home Assistant e non compare né negli attributi
delle entità né nei log.

**Aggiornamento dalla 0.1.** La sezione `we_eat:` di `configuration.yaml` viene importata una volta —
le ricette diventano "piatti preferiti" nell'attributo `favorites` del sensore menu — e una
segnalazione di riparazione ti invita a rimuoverla. Il menu casuale e i servizi `add_recipe`,
`remove_recipe` e `set_recipes` non ci sono più: li sostituisce il piano.

---

## Cosa trovi in Home Assistant

| Entità | Stato | Attributi |
|---|---|---|
| `sensor.we_eat_menu` | pasto in corso (o prossimo) del piano di oggi, es. `Pranzo: Pasta, Insalata` | `meal`, `today` (tutti i pasti di oggi), `kcal_planned`, `favorites` |
| `sensor.we_eat_piano_settimana` | `attivo`, `bozza` o `assente` | `days` (tutta la settimana), `draft_days` |
| `sensor.we_eat_kcal_consumate` | kcal mangiate oggi | `by_meal`, `entries` (il diario di oggi), `target` |
| `sensor.we_eat_kcal_rimanenti` | obiettivo meno consumate | — (creata solo se l'obiettivo è impostato) |

Tutte e quattro sono alimentate da un unico coordinator e si aggiornano a mezzanotte, agli orari dei
pasti e subito dopo ogni modifica al piano o al diario.

---

## La card

Il pannello laterale **We Eat** è questa stessa card, già montata per te. La card singola serve solo
se preferisci averla dentro una tua dashboard.

```yaml
type: custom:we-eat-card
entity: sensor.we_eat_menu
```

| Opzione | Predefinito | Cos'è |
|---|---|---|
| `entity` | `sensor.we_eat_menu` | il sensore del menu |
| `plan_entity` | `sensor.we_eat_piano_settimana` | il sensore del piano settimanale |
| `kcal_entity` | `sensor.we_eat_kcal_consumate` | il sensore delle calorie |

Se rinomini il dispositivo cambiano anche gli ID delle sue entità, quindi questi potrebbero non
corrispondere ai tuoi. Raramente serve impostarli: quando un ID non esiste, la card riconosce
ciascuno dei suoi tre sensori dagli attributi che solo quel sensore ha.

- **Oggi** — ogni pasto previsto con alimenti e kcal, un pulsante *Fatto come da piano* per pasto, una
  casella di testo libero per gli extra (con un campo kcal facoltativo che evita la chiamata all'AI),
  la barra delle kcal e il diario di oggi, con ogni riga eliminabile.
- **Settimana** — la griglia 7 × 5 del piano attivo, con la riga di oggi evidenziata.
- **Importa** — incolli il testo o carichi un PDF/foto, poi l'editor della bozza.

Le foto vengono ridimensionate nel browser prima dell'invio; il servizio accetta file fino a 3 MB.

---

## Servizi

| Servizio | Campi | Cosa fa |
|---|---|---|
| `we_eat.import_plan` | `text`, oppure `file_b64` + `mime_type` | Costruisce la bozza del piano con l'LLM |
| `we_eat.save_draft` | `days` | Salva le correzioni fatte alla bozza |
| `we_eat.confirm_plan` | — | Rende attiva la bozza |
| `we_eat.log_plan_meal` | `meal` | Registra il pasto come da piano, copiandone le kcal |
| `we_eat.log_extra` | `text`, `meal`, `kcal` *(facoltativo)* | Registra un extra; senza `kcal` le stima l'AI |
| `we_eat.remove_entry` | `entry_id` | Elimina una voce del diario |

Esempio, da un'automazione:

```yaml
action:
  - action: we_eat.log_extra
    data:
      text: Un caffè macchiato
      meal: spuntino
      kcal: 35
```

---

## Come funziona

- **Il piano è un dato, non un prompt.** All'LLM viene chiesto JSON rigoroso, che poi è validato
  contro lo schema dell'integrazione: pasti sconosciuti, giorni illeggibili, alimenti mancanti o kcal
  negative vengono rifiutati. Se la validazione fallisce, al modello viene chiesto ancora una volta
  citandogli l'errore, e poi l'importazione si arrende con un messaggio comprensibile invece di
  salvare dati sbagliati.
- **Una bozza non è mai il piano.** L'importazione scrive in uno spazio separato, così re-importare non
  distrugge il piano che stai seguendo finché non confermi quello nuovo.
- **Le kcal registrate sono congelate.** "Fatto come da piano" copia le kcal del pasto nel diario in
  quel momento; modificare il piano dopo non riscrive la tua storia. Lo stesso pasto non può essere
  registrato due volte nello stesso giorno.
- **L'AI viene chiamata al massimo due volte.** Una per importazione, una per ogni descrizione di
  extra *mai vista prima*. Tutto il resto — totali, quale pasto è in corso, kcal rimanenti — è
  calcolato in locale.
- **I dati** stanno in `.storage/we_eat` (piano, bozza, diario, cache delle stime, preferiti) e
  sopravvivono ai riavvii. La cache conserva le 500 descrizioni più recenti.

---

## Cose da sapere prima di fidarsi

- **Le stime sono ipotesi, e lo è anche parte della trascrizione.** Quando il foglio non riporta le
  calorie, il modello inventa un numero plausibile e la voce viene marcata *stimato*. Controlla la
  bozza sul serio: quel passaggio esiste per questo.
- **DeepSeek non legge le foto.** La sua API è solo testo; un'importazione da foto con DeepSeek
  selezionato fallisce con un messaggio esplicito. Usa il testo, un PDF con testo o uno degli altri
  tre provider.
- **I PDF scansionati non sono supportati.** Non c'è OCR: un PDF senza testo viene rifiutato, con un
  messaggio che chiede una foto o il testo. Le foto dei fogli di carta funzionano: manda la foto, non
  una scansione dentro un PDF.
- **Ogni importazione e ogni extra nuovo costano** sul tuo account del provider. Le descrizioni già
  viste arrivano dalla cache e non costano nulla.
- **Una sola istanza.** L'integrazione è `single_config_entry` e il diario è unico per la casa: non
  c'è il conteggio per singola persona.
- **Niente macronutrienti e niente database alimentare.** Proteine, carboidrati, grassi, codici a
  barre e ricerca dei prodotti confezionati sono volutamente fuori dallo scopo di questa versione.
- **Non è un dispositivo medico.** È una comodità per seguire un piano che ti ha dato un professionista.

---

## Sviluppo

```bash
pip install -r requirements_test.txt
pytest -q
```

64 test coprono le parti che possono rompersi in silenzio: validazione del piano, diario e totali
kcal, snapshot dei sensori, tutti e quattro i client LLM contro risposte HTTP finte, estrazione dal
PDF e la logica di ritentativo di importazione e stima. Non importano codice di Home Assistant,
quindi girano su qualunque sistema operativo con il solo `pytest` installato.

Lo strato Home Assistant (coordinator, config flow, sensori) e la card non hanno test unitari: la CI
li valida con **hassfest** e **HACS** a ogni push, e il resto si verifica caricando l'integrazione in
un'istanza di prova.

---

## Segnalazioni e contributi

Hai trovato un bug, o un piano che l'importazione sbaglia? Apri una issue su
[github.com/iAlias/HomeAssistantWeEat/issues](https://github.com/iAlias/HomeAssistantWeEat/issues).
Se segnali un problema di importazione, allega il testo che gli hai dato — mai la tua chiave API.

---

## Licenza

[MIT](LICENSE) © Antonino Di Stefano
