# We Eat 0.2.0 — piano del dietologo e conteggio calorie

Data: 2026-09-19 · Stato: bozza da approvare

## Obiettivo

Estendere l'integrazione `we_eat` perché mostri il **piano settimanale del dietologo** e conti le
**calorie** di ciò che l'utente mangia. Il menu casuale attuale viene sostituito dal piano.

## Decisioni prese

| Tema | Scelta |
|---|---|
| Ingresso del piano | Testo, PDF o foto, sempre tramite LLM, con conferma manuale |
| Diario pasti | "Fatto come da piano" con un tocco, più extra a testo libero stimati dall'LLM |
| LLM | Client **interno a We Eat**, senza dipendere da altre integrazioni, con API key propria |
| Provider | OpenAI, DeepSeek, Gemini, Claude |
| Menu casuale | Sostituito dal piano |
| Architettura | Config entry + `Store` + `DataUpdateCoordinator` |

## Dati e persistenza

**Config entry (UI):** provider, chiave API, modello, obiettivo kcal giornaliero (opzionale), fasce
dei pasti (default: colazione, spuntino, pranzo, merenda, cena). La chiave non compare mai negli
attributi delle entità.

**Storage** (`helpers.storage.Store`, chiave `we_eat`):

- *Piano:* 7 giorni × pasti. Ogni pasto è una lista di voci `{alimento, quantità, kcal, verificato}`;
  il totale del pasto è calcolato. Il piano ha stato `bozza` o `attivo`.
- *Diario:* eventi `{data, ora, pasto, origine: piano|extra, testo?, kcal, stimato}`. Le kcal di un
  pasto "come da piano" sono copiate dal piano al momento del segno e non cambiano se il piano
  viene modificato dopo.
- *Cache LLM:* stime degli extra indicizzate per testo normalizzato.
- *Piatti preferiti:* le ricette della vecchia configurazione YAML.

Dopo l'importazione il piano entra come **bozza** e diventa attivo solo alla conferma dell'utente.
Le kcal riportate nel documento sono usate così come sono; se mancano le stima l'LLM e le voci
sono marcate `stimato`.

## Livello LLM (`llm/`)

- Interfaccia unica `complete(prompt, immagine?) -> JSON`, con un adapter per provider.
- OpenAI e DeepSeek condividono l'adapter (API compatibile OpenAI, cambia il `base_url`). Gemini e
  Claude hanno un adapter ciascuno. Solo `aiohttp`, già presente in HA.
- Il config flow verifica la chiave con una chiamata di prova.
- Output forzato a JSON con schema; un solo tentativo di ripetizione se il JSON è invalido, poi
  errore esplicito all'utente.
- **Limite:** l'API DeepSeek è solo testo. Con DeepSeek attivo l'importazione da foto è disattivata
  con un messaggio chiaro; per le foto serve OpenAI, Gemini o Claude.

## Importazione

- **Testo:** incollato nella card, inviato all'LLM.
- **PDF:** testo estratto in locale; se il PDF è una scansione senza testo, è trattato come foto.
- **Foto:** inviata a un provider con visione.
- Tutti e tre producono la stessa bozza di piano, poi rivista e confermata dalla card.

## Servizi

`we_eat.import_plan` (`text` / `file`), `we_eat.confirm_plan`, `we_eat.log_plan_meal` (`meal`),
`we_eat.log_extra` (`text`, `meal`), `we_eat.remove_entry`.

I servizi `add_recipe`, `remove_recipe`, `set_recipes` vengono rimossi.

## Entità

Tutte lette dal coordinator, aggiornato a mezzanotte, a ogni scrittura del diario e agli orari
dei pasti.

- `sensor.we_eat_menu` — stato: pasto in corso o prossimo del piano di oggi; attributi: pasti del
  giorno con alimenti, quantità, kcal. Se non c'è un piano attivo lo stato è `unknown`.
- `sensor.we_eat_piano_settimana` — stato: `attivo` / `bozza` / `assente`; attributo: i 7 giorni.
- `sensor.we_eat_kcal_consumate` — totale di oggi, dettaglio per pasto negli attributi.
- `sensor.we_eat_kcal_rimanenti` — obiettivo meno consumate; creato solo se l'obiettivo è impostato.

## Card `custom:we-eat-card`

Tre schede: **Oggi** (pasti, "Fatto come da piano", campo extra, barra kcal), **Settimana** (griglia
7×pasti con giorno corrente evidenziato), **Importa** (testo/PDF/foto, bozza modificabile, conferma).
Le stime LLM portano l'etichetta "stimato"; in fondo un avviso: le stime sono approssimative e non
sono un parere medico.

## Migrazione e struttura

- `we_eat` passa a config entry (`config_flow: true`, versione 0.2.0). La vecchia sezione YAML è
  importata una volta, con avviso di deprecazione; le ricette diventano "piatti preferiti".
- File: `config_flow.py`, `coordinator.py`, `storage.py`, `llm/`, `const.py`, `strings.json`,
  `translations/it.json` (italiano primario), `brand/`.

## Errori e privacy

- Chiave API errata o provider irraggiungibile: errore nel config flow / notifica nella card, il
  diario manuale continua a funzionare.
- Le chiamate LLM inviano al provider il testo del piano e degli extra: va detto nel README.
- Ogni importazione o stima nuova è una chiamata a pagamento; la cache evita le ripetizioni.

## Test

`pytest` solo su logica pura (parsing/validazione del JSON dell'LLM, totali kcal, migrazione da
YAML), senza Home Assistant. Prima di scriverli va verificato che Python sia disponibile sul PC
(`where python`).

## Fuori scopo (YAGNI)

Macronutrienti, database alimentare/codici a barre, più utenti, sincronizzazione con app esterne.

## Precisazioni emerse dal piano di implementazione

Affinano lo spec senza cambiarne l'intento:

- **Pasti:** i nomi sono fissi (colazione, spuntino, pranzo, merenda, cena); si configurano solo gli orari, dalle opzioni.
- **Bozza separata:** `draft` è distinta dal piano attivo, così importare un nuovo piano non cancella quello in uso finché non lo confermi. Lo stato di `sensor.we_eat_piano_settimana` è `bozza` se esiste una bozza, altrimenti `attivo` o `assente`. Il flag `verificato` non serve: la conferma della bozza ne fa le veci; resta `estimated` per le kcal stimate.
- **Servizio in più:** `we_eat.save_draft` (`days`) salva le correzioni fatte alla bozza dalla card prima di `confirm_plan`.
- **`log_extra`** accetta `kcal` opzionale: se presente non chiama l'LLM.
- **Provider "nessuno":** l'integrazione funziona anche senza LLM (piano inserito a mano dalla card, kcal manuali). L'import YAML crea una voce con provider "nessuno".
- **PDF scansionati:** non supportati; l'utente riceve un messaggio che chiede una foto o il testo. I PDF con testo sono letti in locale con `pypdf` (nuova dipendenza).
- **File caricati:** la card li converte in base64 (le foto sono ridimensionate) e li passa a `import_plan` con `file_b64` e `mime_type`; limite pratico 3 MB.
- **Versione minima:** Home Assistant 2024.11 (`entry.runtime_data`).
- **`brand/`:** fuori scopo in questa versione.
