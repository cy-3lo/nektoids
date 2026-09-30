"""Bundled assets are present, with their licence, and small enough for the web build."""

from pathlib import Path

FONT_DIR = Path(__file__).resolve().parents[1] / "game" / "nektoids" / "assets" / "fontawesome"


def test_icon_font_ships_with_its_licence():
    font = FONT_DIR / "fa-solid-900.ttf"
    assert font.is_file() and font.stat().st_size < 500_000
    licence = (FONT_DIR / "LICENSE.txt").read_text()
    assert "SIL OFL 1.1" in licence and 'Reserved Font Name: "Font Awesome"' in licence
