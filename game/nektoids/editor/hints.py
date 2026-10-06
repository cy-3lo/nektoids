"""A level's hints, asked for one after another in the Hints drawer (D-078): an idea, a bit
cryptic; the parts one solution takes; the shadow of that solution, its parts and wires drawn
faintly, in a picture in the drawer and on the editor's board.

A level's data says the idea; the solution is its proof, the board that won it (D-320, D-329),
put on the level's own board over the parts the level places. The parts the player adds are
counted from it, so the second hint and the third cannot disagree. Only the levels of chapters
0 and 1 have hints. Taken hints last the session, level by level, and never show on the score.
Pure Python, no pygame.
"""

from __future__ import annotations

import textwrap
from collections import Counter
from dataclasses import dataclass, field

from nektoids.editor.boardfield import load
from nektoids.editor.layout import DRAWER_WIDTH, MARGIN, MENU_GROUPS
from nektoids.editor.parts import NAME
from nektoids.editor.tutorial import Ghost
from nektoids.graph.board import Board
from nektoids.graph.hexgrid import Cell
from nektoids.levels.level import Level, known
from nektoids.levels.proof import Proof

NAMES = ("Hint 1", "Hint 2", "Hint 3")  # the drawer's rows: the idea, the parts, the shadow
IDEA, PARTS, SHADOW = range(3)
ADVANCE = 9  # a letter of Plex Mono at 15 px, the drawer's text: 0.6 em [px]
CHARS = (DRAWER_WIDTH - 2 * MARGIN) // ADVANCE  # a line of a hint, in the drawer [characters]
NUMBERS = ("one", "two", "three", "four", "five", "six")


@dataclass(frozen=True)
class Hints:
    idea: str
    ghosts: tuple[Ghost, ...]  # the parts the shadow adds, where they go and the way they face
    ghost_wires: tuple[tuple[Cell, Cell], ...]  # ... and its wires, from a cell to a cell
    board: Board = field(compare=False)  # the shadow, built: the level's board, the proof's on it

    @classmethod
    def of(cls, level: Level) -> Hints:
        """The hints of `level`, which has some and a proof: its idea, and its proof's board on
        its blank board, the parts it places locked under it (D-329). ValueError for a key the
        hints do not know, or a proof that does not fit the level."""
        known(level.hints, ("idea",), "a level's hints")
        board = level.blank_board()
        fits, why = load(board, Proof.from_dict(level.proof).board)
        if not fits:
            raise ValueError(f"{level.title}'s proof: {why}")
        nodes = [board.nodes[k] for k in sorted(board.nodes)]
        ghosts = tuple(Ghost(n.kind, n.cell, n.facing) for n in nodes if not n.locked)
        cells = tuple((board.nodes[w.source].cell, board.nodes[w.target].cell) for w in board.wires)
        return cls(level.hints["idea"], ghosts, cells, board)

    def says(self, index: int) -> tuple[str, ...]:
        """Hint `index`'s lines, as the drawer shows them under its row; the shadow's are none:
        its picture says it."""
        text = (self.idea, parts_line(self.ghosts), "")[index]
        return tuple(textwrap.wrap(text, CHARS))


def parts_line(ghosts: tuple[Ghost, ...]) -> str:
    """The parts the shadow adds, counted, in Parts' order, each name as Parts writes it:
    "One Eye, one Source, one Thruster, one Diff."; with none, the wires alone."""
    if not ghosts:
        return "No part to add: only wires."
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
