"""The game's levels, in chapters, and the sandbox (D-019, D-028, D-325).

Each is a JSON file in `data/` (`level.py` says what it holds), a chapter's in its own folder,
read once at startup. Lengths in u, the base body radius, in an open plane; what each holds fits
in 40 x 38 u. The swimmer runs whatever board is on the Board, and each level says what it asks
(`objectives.py`). The chapters make one route: `arenas()` is its levels in order, and a level's
place on it, its index, is all the rest of the game needs; `locate` gives its chapter.

A level made in the Editor ships from Share level (D-320, D-328): its text, with its proof, saved
in its chapter's folder and named in its chapter below; its passkey, hints and tutorial, which
the Editor does not set, written in the file by hand; then
`PYTHONPATH=game python -m nektoids.levels.level FILE` writes the file as the game does, which
the tests ask. Every shipped level carries its proof, and the tests run it again.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nektoids.levels.level import Level, load

DATA = Path(__file__).resolve().parent / "data"


@dataclass(frozen=True)
class Chapter:
    number: int | None  # None: no real chapter, the levels made by users (D-510)
    title: str
    folder: str  # under `data/`
    names: tuple[str, ...]  # its levels' files, in the order they come
    all_open: bool = False  # every level open from the start, not one after another (D-335)
    hints: bool = True  # its levels' hints, from their proofs, in the Hints drawer (D-353)

    @property
    def heading(self) -> str:
        """Its title in Chapters and in the Editor's Files: "1. Braitenberg" (D-420); its title
        alone if it has no number."""
        return self.title if self.number is None else f"{self.number}. {self.title}"


CHAPTERS = (
    Chapter(
        0,
        "Tutorials",
        "0-tutorials",
        ("wiring", "turning", "eyes", "half", "minus", "diagnostic"),
        all_open=True,
    ),  # the board and the parts, one thing a level, any in any order (D-325, D-335, D-335)
    Chapter(1, "Braitenberg", "1-braitenberg", ("fear", "aggression", "love", "orbit")),
    Chapter(2, "Obstacles", "2-obstacles", ("shadows",)),
    Chapter(3, "Many lights", "3-many-lights", ("greed", "patience", "two-lights")),
    Chapter(4, "Colour", "4-colour", ("violet", "two-colours", "crossed-colours")),
    Chapter(5, "Memory", "5-memory", ("latch",)),
    Chapter(
        None,
        "Made by users",
        "made-by-users",
        ("dragster", "dragster-ii"),
        all_open=True,
        hints=False,
    ),
)  # Braitenberg's 2a, 2b, 3a and the brief's orbit (D-097); obstacles; then more lights, the
# real level (D-098) and "Two lights, four obstacles", once too hard for level 2 (D-032), last
# (D-324); colour and memory (D-510); levels made in the Editor, the physicist's Dragster first
# (D-332), every one open, as they come in no order (D-348), and no chapter of their own, so
# unnumbered (D-510). A chapter with no level yet is not listed.
ORDER = tuple(f"{chapter.folder}/{name}" for chapter in CHAPTERS for name in chapter.names)
SANDBOX = "sandbox"  # no objective: the old "Two lights, four obstacles" (D-035)
EVERY_LEVEL = "VEHICLES"  # the word for every level, once all are won: Braitenberg's (D-355)


def locate(index: int) -> tuple[Chapter, int]:
    """The chapter of the route's level at `index`, and the level's place in it, from 0;
    IndexError past the route's end."""
    if index >= 0:
        for chapter in CHAPTERS:
            if index < len(chapter.names):
                return chapter, index
            index -= len(chapter.names)
    raise IndexError("no level there on the route")


def arenas() -> list[Level]:
    return [load(DATA / f"{name}.json") for name in ORDER]


def sandbox() -> Level:
    return load(DATA / f"{SANDBOX}.json")
