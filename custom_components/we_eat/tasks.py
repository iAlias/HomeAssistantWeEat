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
