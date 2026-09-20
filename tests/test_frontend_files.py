"""The card is only served if these files really sit where the integration looks for them.

Home Assistant registers nothing, and reports nothing, for a static path that does not exist, so
getting this wrong is invisible until the card refuses to load in a browser.
"""

from custom_components.we_eat.const import (
    CARD_FILENAME,
    FRONTEND_FILES,
    INTEGRATION_DIR,
    PANEL_FILENAME,
)


def test_integration_dir_is_the_integration_itself():
    assert (INTEGRATION_DIR / "manifest.json").is_file()
    assert (INTEGRATION_DIR / "__init__.py").is_file()


def test_every_frontend_file_exists_where_it_is_served_from():
    for name in FRONTEND_FILES:
        assert (INTEGRATION_DIR / name).is_file(), f"{name} manca in {INTEGRATION_DIR}"


def test_frontend_files_are_javascript_modules():
    assert FRONTEND_FILES == (CARD_FILENAME, PANEL_FILENAME)
    for name in FRONTEND_FILES:
        assert name.endswith(".js")
        assert (INTEGRATION_DIR / name).read_text(encoding="utf-8").strip()


def test_the_files_are_shipped_by_hacs():
    """HACS downloads the integration folder; it did not download a frontend/ subfolder."""
    assert not (INTEGRATION_DIR / "frontend").exists()
