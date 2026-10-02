"""Guards on the layout: model code stays headless so it can be tested without a display, and
every colour comes from the palette (D-047)."""

import re
from pathlib import Path

HEADLESS_PACKAGES = ["sim", "graph"]
ROOT = Path(__file__).resolve().parents[1] / "game" / "nektoids"


def test_model_packages_do_not_import_pygame():
    offenders = [
        str(path.relative_to(ROOT))
        for package in HEADLESS_PACKAGES
        for path in (ROOT / package).rglob("*.py")
        if "import pygame" in path.read_text() or "from pygame" in path.read_text()
    ]
    assert offenders == [], f"pygame imported in headless code: {offenders}"


COLOUR = re.compile(r"\(\s*\d{1,3}(\s*,\s*\d{1,3}){2,3}\s*\)|#[0-9A-Fa-f]{6}\b|Color\(")


def test_colours_are_named_by_their_job_in_the_palette_and_nowhere_else():
    offenders = [
        f"{path.relative_to(ROOT)}:{n}"
        for path in [*(ROOT / "editor").glob("*.py"), ROOT.parent / "main.py"]
        if path.name != "palette.py"
        for n, line in enumerate(path.read_text().splitlines(), start=1)
        if COLOUR.search(line) and ": Rect" not in line  # a Rect is four numbers too
    ]
    assert offenders == [], f"a colour outside editor/palette.py: {offenders}"
