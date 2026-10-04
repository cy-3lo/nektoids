"""Levels to try a swimmer in, until the tutorials and the real level exist (D-019, D-028).

Each is a JSON file in `data/` (`level.py` says what it holds), read once at startup. Lengths
in u, the base body radius, in an open plane; what each holds fits in 40 x 38 u. The swimmer
runs whatever board is in the editor, and each level says what it asks (`objectives.py`).
"""

from __future__ import annotations

from pathlib import Path

from nektoids.levels.level import Level, load

DATA = Path(__file__).resolve().parent / "data"
ORDER = (
    "fear",
    "aggression",
    "love",
    "orbit",
    "shadows",
    "greed",
    "patience",
)  # the route's files, in the order the levels come: Braitenberg's 2a, 2b, 3a, the brief's
# orbit (D-097), then the levels with obstacles and more lights, the real level last (D-098)
SANDBOX = "sandbox"  # no objective: the old "Two lights, four obstacles" (D-035)


def arenas() -> list[Level]:
    return [load(DATA / f"{name}.json") for name in ORDER]


def sandbox() -> Level:
    return load(DATA / f"{SANDBOX}.json")
