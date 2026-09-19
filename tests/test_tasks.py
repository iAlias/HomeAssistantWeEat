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
