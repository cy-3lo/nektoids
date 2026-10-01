"""Which level the player is on, and whether they are building its board or watching it run.

The loop of the brief (§1): the spec and the board in the editor, Run, watch the run, back to the
editor to change the mechanism, or on to the next level once won. Each level keeps its board
for the session, so going back finds it as it was left. Pure Python, no pygame: `main.py` turns
the state into scenes.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum

from nektoids.graph.board import Board
from nektoids.levels.level import Level


class Screen(Enum):
    EDIT = "edit"  # the level's board in the editor
    RUN = "run"  # the level's board swimming in its arena


class Router:
    def __init__(self, levels: Sequence[Level]) -> None:
        self.levels = list(levels)
        self.index = 0
        self.screen = Screen.EDIT
        self._boards: dict[int, Board] = {}

    @property
    def level(self) -> Level:
        return self.levels[self.index]

    @property
    def board(self) -> Board:
        """The current level's board: its own, fresh the first time, then as the player left it."""
        if self.index not in self._boards:
            self._boards[self.index] = self.level.new_board()
        return self._boards[self.index]

    @property
    def has_next(self) -> bool:
        return self.index + 1 < len(self.levels)

    def run(self) -> None:
        self.screen = Screen.RUN

    def edit(self) -> None:
        self.screen = Screen.EDIT

    def next(self) -> None:
        """On to the next level's editor; ValueError after the last one."""
        if not self.has_next:
            raise ValueError("that was the last level")
        self.index += 1
        self.screen = Screen.EDIT
