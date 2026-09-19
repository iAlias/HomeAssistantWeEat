"""Rende importabili i moduli di logica di we_eat senza eseguire __init__.py (che importa HA)."""

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _stub_package(name: str, path: Path) -> None:
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    sys.modules[name] = module


_stub_package("custom_components", ROOT / "custom_components")
_stub_package("custom_components.we_eat", ROOT / "custom_components" / "we_eat")
