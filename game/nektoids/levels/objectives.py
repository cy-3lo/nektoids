"""What a level asks of its swimmers, counted, and when a run is over (D-023).

A run remembers which lights each swimmer has touched, `visited` of shape (N, L): a swimmer
touches a light when their discs meet, and a visit counts once, whatever comes after. Each
objective counts what it asks from that, so many met out of so many needed (brief section 1:
countable win conditions). A run ends when every objective is met, or when its time is up.
Pure numbers, no pygame.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Protocol

import numpy as np

from nektoids.sim.arena import LIGHT_RADIUS, Arena

if TYPE_CHECKING:
    from nektoids.levels.arenas import Level


class Objective(Protocol):
    name: str

    def count(self, visited: np.ndarray) -> tuple[int, int]:
        """How many are met, out of how many needed; visited (N, L), see the module."""
        ...


class Outcome(Enum):
    WON = "won"
    TIME_UP = "time up"


def touching(arena: Arena, pos: np.ndarray, radius: np.ndarray) -> np.ndarray:
    """(N, L): whether each swimmer touches each light now; pos (N, 2) [u], radius (N,) [u]."""
    dx = arena.light_xy[None, :, 0] - pos[:, None, 0]
    dy = arena.light_xy[None, :, 1] - pos[:, None, 1]
    reach = LIGHT_RADIUS + np.asarray(radius, dtype=np.float64)[:, None]
    return dx * dx + dy * dy <= reach * reach


def met(objective: Objective, visited: np.ndarray) -> bool:
    done, needed = objective.count(visited)
    return done >= needed


def outcome(level: Level, visited: np.ndarray, tick: int, dt: float) -> Outcome | None:
    """How the run stands after `tick` ticks of `dt` [s]: won when the level has objectives and
    every one is met, else over when its time is up, else still running (None)."""
    if level.objectives and all(met(o, visited) for o in level.objectives):
        return Outcome.WON
    if tick >= round(level.time_limit / dt):
        return Outcome.TIME_UP
    return None


@dataclass(frozen=True)
class VisitLights:
    """Every swimmer touches every light of the arena, in any order."""

    name: str = "Visit every light"

    def count(self, visited: np.ndarray) -> tuple[int, int]:
        return int(visited.sum()), int(visited.size)
