"""Levels to try a swimmer in, until the tutorials and the real level exist (D-019, D-028).

Each is a JSON file in `data/` (`level.py` says what it holds), read once at startup. Lengths
in u, the base body radius, in an open plane; what each holds fits in 40 x 38 u. For now the
swimmer runs whatever board is in the editor, and each level asks it to visit every light
within its time (D-023).
"""

from __future__ import annotations

from pathlib import Path

from nektoids.levels.level import Level, load

DATA = Path(__file__).resolve().parent / "data"
ORDER = ("one-light", "two-lights")  # the files, in the order the levels come


def arenas() -> list[Level]:
    return [load(DATA / f"{name}.json") for name in ORDER]
