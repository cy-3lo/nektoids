"""What a level asks of its swimmers, counted, and when a run is over (D-023, D-038).

Each objective says what counts at a tick, `marks`, a boolean array (N, K): which lights each
swimmer reaches (`VisitLights`: a light is reached when their centres come within REACH times the
sum of their radii, a little short of touching, D-029), or whether it is out of the ring round
the light (`LeaveRing`). The run keeps one such array per objective and ORs each tick's into it,
`latch`, so a mark counts once, whatever comes after. Each objective then counts what it asks
from its marks, so many met out of so many needed (brief section 1: countable win conditions). A
run ends when every objective is met, or when its time is up. In a level's data an objective is
its `kind` and its settings (D-028). Pure numbers, no pygame.
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

Marks = tuple[np.ndarray, ...]  # the run's latched marks, one (N, K) array per objective


class Objective(Protocol):
    kind: ClassVar[str]  # how a level's data names it; stays put if `name` is reworded
    name: str  # as the player reads it

    def marks(self, arena: Arena, pos: np.ndarray, radius: np.ndarray) -> np.ndarray:
        """(N, K): what counts now, for swimmers at pos (N, 2) [u] of radius (N,) [u]."""
        ...

    def count(self, marked: np.ndarray) -> tuple[int, int]:
        """How many are met, out of how many needed, from the run's latched marks."""
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


def marks(level: Level, pos: np.ndarray, radius: np.ndarray) -> Marks:
    """What counts now for each of the level's objectives."""
    return tuple(o.marks(level.arena, pos, radius) for o in level.objectives)


def latch(marked: Marks, now: Marks) -> Marks:
    """The run's marks with this tick's added: once marked, always marked."""
    return tuple(before | new for before, new in zip(marked, now, strict=True))


def met(objective: Objective, marked: np.ndarray) -> bool:
    done, needed = objective.count(marked)
    return done >= needed


def outcome(level: Level, marked: Marks, tick: int, dt: float) -> Outcome | None:
    """How the run stands after `tick` ticks of `dt` [s]: won when the level has objectives and
    every one is met, else over when its time is up, else still running (None)."""
    pairs = zip(level.objectives, marked, strict=True)
    if level.objectives and all(met(o, m) for o, m in pairs):
        return Outcome.WON
    if tick >= round(level.time_limit / dt):
        return Outcome.TIME_UP
    return None


@dataclass(frozen=True)
class VisitLights:
    """Every swimmer reaches every light of the arena, in any order."""

    kind: ClassVar[str] = "visit lights"
    name: str = "Visit every light"

    def marks(self, arena: Arena, pos: np.ndarray, radius: np.ndarray) -> np.ndarray:
        return reaching(arena, pos, radius)  # (N, L)

    def count(self, marked: np.ndarray) -> tuple[int, int]:
        return int(marked.sum()), int(marked.size)


@dataclass(frozen=True, kw_only=True)  # LeaveRing(radius=12.0), never by position
class LeaveRing:
    """Every swimmer gets out of the ring of `radius` round every light: fear (D-038)."""

    kind: ClassVar[str] = "leave ring"
    name: str = "Leave the ring"
    radius: float = 12.0  # [u], from the light's centre to the swimmer's

    def marks(self, arena: Arena, pos: np.ndarray, radius: np.ndarray) -> np.ndarray:
        dx = arena.light_xy[None, :, 0] - pos[:, None, 0]
        dy = arena.light_xy[None, :, 1] - pos[:, None, 1]
        return (dx * dx + dy * dy > self.radius * self.radius).all(axis=1)[:, None]  # (N, 1)

    def count(self, marked: np.ndarray) -> tuple[int, int]:
        return int(marked.sum()), int(marked.size)


OBJECTIVES: dict[str, type] = {VisitLights.kind: VisitLights, LeaveRing.kind: LeaveRing}


def objective_to_dict(objective: Objective) -> dict:
    """Its kind and its settings, as a level's data holds it; the name is the code's."""
    settings = {f.name: getattr(objective, f.name) for f in fields(objective) if f.name != "name"}
    return {"kind": objective.kind, **settings}


def objective_from_dict(data: Mapping) -> Objective:
    if data["kind"] not in OBJECTIVES:
        raise ValueError(f"no objective is called {data['kind']!r}")
    return OBJECTIVES[data["kind"]](**{k: v for k, v in data.items() if k != "kind"})
