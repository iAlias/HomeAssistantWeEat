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
