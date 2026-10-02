"""Where the player is: the title card, a level being built or watched, the end.

The loop of the brief (§1): the spec and the board in the editor, Run, watch the run, back to the
editor to change the mechanism, or on to the next level once won (D-030). Around it (D-035,
D-054): the game opens on the first level under a title card; the Chapters drawer lists the
chapter's levels and the sandbox, each level opening once the one before it is won; after the
last level comes the end. A level opened from Chapters or by Next level comes up under its card,
which says what it asks. Each level keeps its board for the session, so going back finds it as
it was left, and the scores of its wins (D-028); nothing is kept after it. Pure Python, no
pygame: `main.py` turns the state into scenes.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from nektoids.graph.board import Board
from nektoids.levels.level import Level
from nektoids.levels.score import Score

CHAPTER = 1  # the jam's one chapter, light (D-028): its levels are LEVEL 1.1, LEVEL 1.2...
CHAPTER_NAME = "light"


def level_label(index: int) -> str:
    """How the level at `index` in the chapter is named on screen, before its title (D-034)."""
    return f"LEVEL {CHAPTER}.{index + 1}"


@dataclass(frozen=True)
class ChapterRow:
    """A place as the Chapters drawer shows it (D-054)."""

    index: int
    label: str  # "1.2", or "" for the sandbox
    title: str
    spec: str  # what it asks, for its info box
    state: str  # "won", "open", "locked", "sandbox"
    best: Score | None  # the fastest win this session
    current: bool  # the place open now


class Screen(Enum):
    TITLE = "title"  # the card over the first level, gone at the first click
    SPEC = "spec"  # a level's card: its name and what it asks, gone at the first click
    EDIT = "edit"  # a level's board in the editor
    RUN = "run"  # the level's board swimming in its arena
    END = "end"  # after the last level of the chapter


class Router:
    def __init__(self, levels: Sequence[Level], sandbox: Level | None = None) -> None:
        self.levels = list(levels)  # the chapter, in order
        self.sandbox = sandbox  # no objective; always open
        self.index = 0  # the open place: a level of the chapter, or `sandbox_index`
        self.screen = Screen.TITLE
        self.won: set[int] = set()  # the chapter's levels won this session
        self._boards: dict[int, Board] = {}
        self._scores: dict[int, set[Score]] = {}

    @property
    def sandbox_index(self) -> int:
        return len(self.levels)

    @property
    def in_sandbox(self) -> bool:
        return self.index == self.sandbox_index

    @property
    def level(self) -> Level:
        return self.sandbox if self.in_sandbox else self.levels[self.index]

    @property
    def board(self) -> Board:
        """The open level's board: its own, fresh the first time, then as the player left it."""
        if self.index not in self._boards:
            self._boards[self.index] = self.level.new_board()
        return self._boards[self.index]

    @property
    def label(self) -> str:
        return "SANDBOX" if self.in_sandbox else level_label(self.index)

    @property
    def has_next(self) -> bool:
        """A level of the chapter comes after the open one."""
        return not self.in_sandbox and self.index + 1 < len(self.levels)

    @property
    def is_last(self) -> bool:
        """The open level is the chapter's last: winning it leads to the end."""
        return not self.in_sandbox and self.index + 1 == len(self.levels)

    @property
    def scores(self) -> frozenset[Score]:
        """The open level's wins this session, each score once; none for the sandbox."""
        return frozenset(self._scores.get(self.index, ()))

    def best(self, index: int) -> Score | None:
        """The fastest of a level's wins this session, if it has any (D-054)."""
        scores = self._scores.get(index, ())
        return min(scores, key=lambda s: (s.ticks, s.parts)) if scores else None

    def state(self, index: int) -> str:
        """How Chapters shows a place: "won", "open", "locked", or "sandbox"."""
        if index == self.sandbox_index:
            return "sandbox"
        if index in self.won:
            return "won"
        return "open" if self.unlocked(index) else "locked"

    def rows(self) -> tuple[ChapterRow, ...]:
        """What Chapters shows: the chapter's levels, then the sandbox."""
        places = [*self.levels, self.sandbox] if self.sandbox is not None else list(self.levels)
        return tuple(
            ChapterRow(
                k,
                "" if k == self.sandbox_index else f"{CHAPTER}.{k + 1}",
                place.title,
                place.spec,
                self.state(k),
                self.best(k),
                k == self.index,
            )
            for k, place in enumerate(places)
        )

    def unlocked(self, index: int) -> bool:
        """The first level, any level after one won, and the sandbox are open."""
        return index == 0 or index == self.sandbox_index or index - 1 in self.won

    # Moving about

    def begin(self) -> None:
        """The card goes, the title card or a level's; the level stays."""
        self.screen = Screen.EDIT

    def open(self, index: int) -> None:
        """A place from Chapters, under its card; ValueError if it is still locked."""
        if not self.unlocked(index):
            raise ValueError(f"{level_label(index)} opens once the level before it is won")
        self.index = index
        self.screen = Screen.SPEC

    def run(self) -> None:
        self.screen = Screen.RUN

    def edit(self) -> None:
        self.screen = Screen.EDIT

    def reset(self, index: int) -> None:
        """The level at `index` back to its fresh board, the next time it opens (D-050)."""
        self._boards.pop(index, None)

    def mark_won(self) -> None:
        """The open level was won: the next one opens."""
        if not self.in_sandbox:
            self.won.add(self.index)

    def record(self, score: Score) -> None:
        """A win of the open level, scored; the sandbox, with no objective, keeps none."""
        if not self.in_sandbox:
            self._scores.setdefault(self.index, set()).add(score)

    def next(self) -> None:
        """On to the next level, under its card; ValueError after the last one."""
        if not self.has_next:
            raise ValueError("that was the last level")
        self.mark_won()
        self.index += 1
        self.screen = Screen.SPEC

    def finish(self) -> None:
        """After the last level: the end."""
        self.mark_won()
        self.screen = Screen.END
