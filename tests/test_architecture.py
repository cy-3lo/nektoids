"""Guards on the layout: model code stays headless so it can be tested without a display."""

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
