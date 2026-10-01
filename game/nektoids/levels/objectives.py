"""What a level asks of its swimmers, counted, and when a run is over (D-023).

A run remembers which lights each swimmer has reached, `visited` of shape (N, L): a swimmer
reaches a light when their centres come within REACH times the sum of their radii, a little
short of touching (D-029), and a visit counts once, whatever comes after. Each
objective counts what it asks from that, so many met out of so many needed (brief section 1:
countable win conditions). A run ends when every objective is met, or when its time is up.
In a level's data an objective is its `kind` and its settings (D-028). Pure numbers, no pygame.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from enum import Enum
from typing import TYPE_CHECKING, ClassVar, Protocol

import numpy as np

from nektoids.sim.arena import LIGHT_RADIUS, Arena

REACH = 1.2  # a light counts as reached this many times its touching distance away (D-029)

if TYPE_CHECKING:
    from nektoids.levels.level import Level


class Objective(Protocol):
    kind: ClassVar[str]  # how a level's data names it; stays put if `name` is reworded
    name: str  # as the player reads it

    def count(self, visited: np.ndarray) -> tuple[int, int]:
        """How many are met, out of how many needed; visited (N, L), see the module."""
        ...


class Outcome(Enum):
    WON = "won"
    TIME_UP = "time up"


def reaching(arena: Arena, pos: np.ndarray, radius: np.ndarray) -> np.ndarray:
    """(N, L): whether each swimmer reaches each light now: centres within REACH (R + r), 2.4 u
    for a base body, 1.2 diameters. pos (N, 2) [u], radius (N,) [u]."""
    dx = arena.light_xy[None, :, 0] - pos[:, None, 0]
    dy = arena.light_xy[None, :, 1] - pos[:, None, 1]
    reach = REACH * (LIGHT_RADIUS + np.asarray(radius, dtype=np.float64)[:, None])
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

    kind: ClassVar[str] = "visit lights"
    name: str = "Visit every light"

    def count(self, visited: np.ndarray) -> tuple[int, int]:
        return int(visited.sum()), int(visited.size)


OBJECTIVES: dict[str, type] = {VisitLights.kind: VisitLights}


def objective_to_dict(objective: Objective) -> dict:
    """Its kind and its settings, as a level's data holds it; the name is the code's."""
    settings = {f.name: getattr(objective, f.name) for f in fields(objective) if f.name != "name"}
    return {"kind": objective.kind, **settings}


def objective_from_dict(data: Mapping) -> Objective:
    if data["kind"] not in OBJECTIVES:
        raise ValueError(f"no objective is called {data['kind']!r}")
    return OBJECTIVES[data["kind"]](**{k: v for k, v in data.items() if k != "kind"})
