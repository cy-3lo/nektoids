"""A level's proof (D-320): the board that won it, as its text (D-205), and its score, the parts
and the tick it was won at, the one to beat. A level is shared with its proof once its maker has
won it, as Mario Maker's courses are cleared by their makers; pasted, the proof is run again on
the level, headless, and the level counts as cleared if it wins again.

The run is deterministic on a platform (invariant 1), so a proof wins again where it won; across
platforms a run may differ in its last bit (D-004), so what is checked is the outcome, the win,
and not the tick. `Replay` runs the board a few ticks at a time, so that a long run never holds up
a frame: a run of 120 s takes some 2 s natively, more in a browser. Pure numbers, no pygame.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

from nektoids.graph.board import Board
from nektoids.graph.dynamics import initial_state
from nektoids.graph.network import Network
from nektoids.levels.level import Level, known
from nektoids.levels.objectives import Outcome, begin, follow, outcome
from nektoids.levels.score import Score
from nektoids.sim import world
from nektoids.sim.arena import BASE_RADIUS


@dataclass(frozen=True)
class Proof:
    """The board that won a level, as its text (D-205), and the score it won with."""

    board: str
    ticks: int  # the tick it was won at
    parts: int  # complexity(board) (D-045)

    def to_dict(self) -> dict:
        return {"board": self.board, "ticks": self.ticks, "parts": self.parts}

    @classmethod
    def from_dict(cls, data: Mapping) -> Proof:
        """ValueError for a key it does not know (D-201), or one missing."""
        known(data, ("board", "ticks", "parts"), "a proof")
        try:
            return cls(str(data["board"]), int(data["ticks"]), int(data["parts"]))
        except KeyError as missing:
            raise ValueError(f"a proof needs its {missing.args[0]!r}") from None


def to_beat(level: Level) -> Score | None:
    """The score of the level's proof, the one to beat, which Score shows as a cross (D-330);
    None for a level with no proof."""
    if level.proof is None:
        return None
    proof = Proof.from_dict(level.proof)
    return Score(proof.parts, proof.ticks)


class Replay:
    """`board` run on `level` from its start, as the run does, `advance`d a few ticks at a time
    until it is over: won, lost, or out of time."""

    def __init__(self, level: Level, board: Board, dt: float) -> None:
        self.level, self.dt = level, dt
        self.net = Network.from_board(board)
        x, y, heading = level.start
        self.pos = np.array([[x, y]])  # (1, 2) [u]
        self.heading = np.array([math.radians(heading)])  # (1,) [rad]
        self.radius = np.full(1, BASE_RADIUS)  # (1,) [u]
        self.state = initial_state(self.net, 1)
        self.kept = begin(level, self.pos, self.radius)
        self.tick = 0
        self.outcome: Outcome | None = None
        self.last = round(level.time_limit / dt)  # the tick its time is up at

    def advance(self, ticks: int) -> Outcome | None:
        """At most `ticks` more ticks, fewer if the run is over; how it ended, once it has."""
        arena = self.level.arena
        for _ in range(ticks):
            if self.outcome is not None:
                break
            self.pos, self.heading, self.state = world.step(
                arena, self.net, self.pos, self.heading, self.radius, self.state, self.dt
            )
            self.kept = follow(self.level, self.kept, self.pos, self.radius, self.dt)
            self.tick += 1
            self.outcome = outcome(self.level, self.kept, self.tick, self.dt)
        return self.outcome

    @property
    def progress(self) -> float:
        """How far through the level's time it has run, from 0 to 1."""
        return min(1.0, self.tick / self.last) if self.last else 1.0
