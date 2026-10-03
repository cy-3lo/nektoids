"""A level's hints, asked for one after another in the Hints drawer (D-078): an idea, a bit
cryptic; the parts one solution takes; the shadow of that solution, its parts and wires drawn
faintly, in a picture in the drawer and on the editor's board.

A level's data says the idea and the shadow, whose ghosts and ghost wires are written as a
tutorial's are (D-074). The parts are counted from the shadow, so the second hint and the third
cannot disagree. Taken hints last the session, level by level, and never show on the score.
Pure Python, no pygame.
"""

from __future__ import annotations

import textwrap
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field

from nektoids.editor.layout import DRAWER_WIDTH, MARGIN, MENU_GROUPS
from nektoids.editor.parts import NAME
from nektoids.editor.tutorial import Ghost, ghost_wires_from, ghosts_from
from nektoids.graph.board import Board, Refused
from nektoids.graph.hexgrid import Cell

NAMES = ("Hint 1", "Hint 2", "Hint 3")  # the drawer's rows: the idea, the parts, the shadow
IDEA, PARTS, SHADOW = range(3)
ADVANCE = 9  # a letter of Plex Mono at 15 px, the drawer's text: 0.6 em [px]
CHARS = (DRAWER_WIDTH - 2 * MARGIN) // ADVANCE  # a line of a hint, in the drawer [characters]
NUMBERS = ("one", "two", "three", "four", "five", "six")


@dataclass(frozen=True)
class Hints:
    idea: str
    ghosts: tuple[Ghost, ...]  # the shadow's parts, where they go and the way they face
    ghost_wires: tuple[tuple[Cell, Cell], ...]  # ... and its wires, from a cell to a cell

    @classmethod
    def from_dict(cls, data: Mapping) -> Hints:
        shadow = data["shadow"]
        return cls(data["idea"], ghosts_from(shadow), ghost_wires_from(shadow))

    def says(self, index: int) -> tuple[str, ...]:
        """Hint `index`'s lines, as the drawer shows them under its row; the shadow's are none:
        its picture says it."""
        text = (self.idea, parts_line(self.ghosts), "")[index]
        return tuple(textwrap.wrap(text, CHARS))

    def build(self, board: Board) -> Board:
        """The shadow, made for real on `board`, the level's own and fresh: its parts placed,
        then its wires made in order, as a player would make them. Returns `board`."""
        for ghost in self.ghosts:
            placed = board.place(ghost.kind, ghost.cell, facing=ghost.facing)
            if isinstance(placed, Refused):
                raise ValueError(f"a shadow's {ghost.kind.value} at {ghost.cell}: {placed.reason}")
        for start, end in self.ghost_wires:
            a, b = board.node_at(start), board.node_at(end)
            made = board.connect(a.id, b.id) if a and b else Refused("no part at an end")
            if isinstance(made, Refused):
                raise ValueError(f"a shadow's wire {start} to {end}: {made.reason}")
        return board


def parts_line(ghosts: tuple[Ghost, ...]) -> str:
    """The parts the shadow takes, counted, in Parts' order, each name as Parts writes it:
    "One Eye, one Source, one Thruster, one Diff." """
    counts = Counter(ghost.kind for ghost in ghosts)
    named = [
        f"{_number(n)} {NAME[kind]}{'s' if n > 1 else ''}"
        for _, group in MENU_GROUPS
        for kind in group
        if (n := counts[kind])
    ]
    line = ", ".join(named) + "."
    return line[0].upper() + line[1:]


def _number(n: int) -> str:
    return NUMBERS[n - 1] if n <= len(NUMBERS) else str(n)


@dataclass(frozen=True)
class HintView:
    """What the Hints drawer shows of the open level's hints; main.py's, every frame."""

    lines: tuple[tuple[str, ...], ...]  # each hint taken, its lines under its row, in order
    locked: bool  # a tutorial leads: no hint may be taken yet
    shadow: bool  # the shadow shows, in its picture and on the editor's board
    board: Board | None = field(default=None, compare=False)  # the shadow built, for the picture


def hint_view(hints: Hints, taken: Taken, locked: bool, shadow: Board) -> HintView:
    """What the drawer shows: the hints `taken`, and `shadow`, the shadow built (`build`), once
    it is taken."""
    lines = tuple(hints.says(k) for k in range(taken.count))
    return HintView(lines, locked, taken.shown, shadow if taken.count > SHADOW else None)


@dataclass
class Taken:
    """What the player has taken of a level's hints this session: how many, the first ones, and
    whether the shadow shows."""

    count: int = 0
    shown: bool = False

    def take(self, index: int) -> str | None:
        """A click on hint `index`'s row. The next one is taken, the shadow shown with it; the
        shadow taken, a click shows or hides it; one taken already stays. Returns why not, if a
        hint before it is still to take."""
        if index > self.count:
            return f"take {NAMES[self.count]} first"
        if index == self.count:
            self.count += 1
            self.shown = self.shown or index == SHADOW
        elif index == SHADOW:
            self.shown = not self.shown
        return None
