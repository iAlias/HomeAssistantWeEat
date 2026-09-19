"""Local text extraction from PDF files."""

from __future__ import annotations

import io

from .llm.base import LlmError


def extract_text(data: bytes) -> str:
    """Return the text of all pages ("" for a scan without a text layer)."""
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as err:  # pypdf raises many unrelated error types on bad input
        raise LlmError(f"PDF non leggibile: {err}") from err
