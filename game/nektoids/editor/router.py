"""Where the player is: the title card, the map, a level being built or watched, the end.

The loop of the brief (§1): the spec and the board in the editor, Run, watch the run, back to the
editor to change the mechanism, or on to the next level once won (D-030). Around it (D-035): the
game opens on the first level under a title card; the map lists the route's levels and the
sandbox, each level opening once the one before it is won; after the last level comes the end.
Each level keeps its board for the session, so going back finds it as it was left; nothing is
kept after it. Pure Python, no pygame: `main.py` turns the state into scenes.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum

from nektoids.graph.board import Board
from nektoids.levels.level import Level

ROUTE = 1  # the jam's one route, light (D-028): its levels are LEVEL 1.1, LEVEL 1.2...
ROUTE_NAME = "light"


def level_label(index: int) -> str:
    """How the level at `index` in the route is named on screen, before its title (D-034)."""
    return f"LEVEL {ROUTE}.{index + 1}"


class Screen(Enum):
    TITLE = "title"  # the card over the first level, gone at the first click
    MAP = "map"  # the route's levels and the sandbox
    EDIT = "edit"  # a level's board in the editor
    RUN = "run"  # the level's board swimming in its arena
    END = "end"  # after the last level of the route


class Router:
    def __init__(self, levels: Sequence[Level], sandbox: Level | None = None) -> None:
        self.levels = list(levels)  # the route, in order
        self.sandbox = sandbox  # no objective; always open
        self.index = 0  # the open place: a level of the route, or `sandbox_index`
        self.screen = Screen.TITLE
        self.won: set[int] = set()  # the route's levels won this session
        self._boards: dict[int, Board] = {}

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
        """A level of the route comes after the open one."""
        return not self.in_sandbox and self.index + 1 < len(self.levels)

    @property
    def is_last(self) -> bool:
        """The open level is the route's last: winning it leads to the end."""
        return not self.in_sandbox and self.index + 1 == len(self.levels)

    def unlocked(self, index: int) -> bool:
        """The first level, any level after one won, and the sandbox are open."""
        return index == 0 or index == self.sandbox_index or index - 1 in self.won

    # Moving about

    def begin(self) -> None:
        """The title card goes; the first level stays."""
        self.screen = Screen.EDIT

    def open_map(self) -> None:
        self.screen = Screen.MAP

    def open(self, index: int) -> None:
        """A place from the map, in the editor; ValueError if it is still locked."""
        if not self.unlocked(index):
            raise ValueError(f"{level_label(index)} opens once the level before it is won")
        self.index = index
        self.screen = Screen.EDIT

    def run(self) -> None:
        self.screen = Screen.RUN

    def edit(self) -> None:
        self.screen = Screen.EDIT

    def mark_won(self) -> None:
        """The open level was won: the next one opens."""
        if not self.in_sandbox:
            self.won.add(self.index)

    def next(self) -> None:
        """On to the next level's editor; ValueError after the last one."""
        if not self.has_next:
            raise ValueError("that was the last level")
        self.mark_won()
        self.index += 1
        self.screen = Screen.EDIT

    def finish(self) -> None:
        """After the last level: the end."""
        self.mark_won()
        self.screen = Screen.END
