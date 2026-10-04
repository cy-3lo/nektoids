"""What a level asks of its swimmers, counted, and when a run is over (D-023, D-038, D-040).

Each objective says what counts at a tick, `marks`, an array (N, K): which lights each swimmer
reaches (a light is reached when their centres come within REACH times the sum of their radii, a
little short of touching, D-029), whether it is out of the ring round the light, or in the ring
it must stay in; for `CircleLight`, the angle at which each light sees it. The run keeps
something for each objective, from `start` and then `keep` at every tick: latched marks for most
(once marked, always marked), the time spent in the ring for `StayNear`, the angle swept round
each light for `CircleLight` (D-097). Each objective counts what it asks from what was kept, so
many met out of so many needed (brief section 1: countable win conditions), and may lose the run
(`KeepOff`: a light touched). A run is lost as soon as an objective loses it, won when every
objective is met, over when its time is up. In a level's data an objective is its `kind` and its
settings (D-028). Pure numbers, no pygame.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from enum import Enum
from typing import TYPE_CHECKING, ClassVar, Protocol

import numpy as np

from nektoids.sim.arena import LIGHT_RADIUS, Arena

REACH = 1.05  # a light counts as reached this many times its touching distance away (D-043)

if TYPE_CHECKING:
    from nektoids.levels.level import Level

Kept = tuple[np.ndarray, ...]  # what the run keeps for each objective, one array apiece
EPS = 1e-9  # a timer this close to its seconds has reached them


class Objective(Protocol):
    kind: ClassVar[str]  # how a level's data names it; stays put if `name` is reworded
    name: str  # as the player reads it
    broken: ClassVar[str]  # what the run's end says if it loses the run

    def marks(self, arena: Arena, pos: np.ndarray, radius: np.ndarray) -> np.ndarray:
        """(N, K): what counts now, for swimmers at pos (N, 2) [u] of radius (N,) [u]."""
        ...

    def start(self, now: np.ndarray) -> np.ndarray:
        """What the run keeps for it at t = 0, from what counts then."""
        ...

    def keep(self, kept: np.ndarray, now: np.ndarray, dt: float) -> np.ndarray:
        """What the run keeps after a tick of `dt` [s], from what it kept and what counts now."""
        ...

    def count(self, kept: np.ndarray) -> tuple[int, int]:
        """How many are met, out of how many needed."""
        ...

    def progress(self, kept: np.ndarray) -> float:
        """How far along it is, from 0 to 1: its bar."""
        ...

    def lost(self, kept: np.ndarray) -> bool:
        """Whether it has lost the run, whatever the rest."""
        ...


class Outcome(Enum):
    WON = "won"
    TIME_UP = "time up"
    LOST = "lost"  # an objective lost the run: a light touched (D-040)


def reaching(arena: Arena, pos: np.ndarray, radius: np.ndarray) -> np.ndarray:
    """(N, L): whether each swimmer reaches each light now: centres within REACH (R + r), 2.1 u
    for a base body, 1.05 diameters. pos (N, 2) [u], radius (N,) [u]."""
    dx = arena.light_xy[None, :, 0] - pos[:, None, 0]
    dy = arena.light_xy[None, :, 1] - pos[:, None, 1]
    reach = REACH * (LIGHT_RADIUS + np.asarray(radius, dtype=np.float64)[:, None])
    return dx * dx + dy * dy <= reach * reach


def begin(level: Level, pos: np.ndarray, radius: np.ndarray) -> Kept:
    """What the run keeps for each of the level's objectives at t = 0."""
    return tuple(o.start(o.marks(level.arena, pos, radius)) for o in level.objectives)


def follow(level: Level, kept: Kept, pos: np.ndarray, radius: np.ndarray, dt: float) -> Kept:
    """What the run keeps after a tick of `dt` [s], the swimmers now at `pos`."""
    pairs = zip(level.objectives, kept, strict=True)
    return tuple(o.keep(k, o.marks(level.arena, pos, radius), dt) for o, k in pairs)


def met(objective: Objective, kept: np.ndarray) -> bool:
    done, needed = objective.count(kept)
    return done >= needed


def outcome(level: Level, kept: Kept, tick: int, dt: float) -> Outcome | None:
    """How the run stands after `tick` ticks of `dt` [s]: lost as soon as an objective loses it,
    won when the level has objectives and every one is met, else over when its time is up, else
    still running (None)."""
    pairs = list(zip(level.objectives, kept, strict=True))
    if any(o.lost(k) for o, k in pairs):
        return Outcome.LOST
    if level.objectives and all(met(o, k) for o, k in pairs):
        return Outcome.WON
    if tick >= round(level.time_limit / dt):
        return Outcome.TIME_UP
    return None


class Latched:
    """What most objectives keep: their marks, latched; met as they count; never lost."""

    broken: ClassVar[str] = "Lost"

    def start(self, now: np.ndarray) -> np.ndarray:
        return now

    def keep(self, kept: np.ndarray, now: np.ndarray, dt: float) -> np.ndarray:
        return kept | now

    def count(self, kept: np.ndarray) -> tuple[int, int]:
        return int(kept.sum()), int(kept.size)

    def progress(self, kept: np.ndarray) -> float:
        done, needed = self.count(kept)
        return done / needed if needed else 1.0

    def lost(self, kept: np.ndarray) -> bool:
        return False


@dataclass(frozen=True)
class VisitLights(Latched):
    """Every swimmer reaches every light of the arena, in any order."""

    kind: ClassVar[str] = "visit lights"
    name: str = "Visit every light"

    def marks(self, arena: Arena, pos: np.ndarray, radius: np.ndarray) -> np.ndarray:
        return reaching(arena, pos, radius)  # (N, L)


@dataclass(frozen=True, kw_only=True)  # LeaveRing(radius=12.0), never by position
class LeaveRing(Latched):
    """Every swimmer gets out of the ring of `radius` round every light: fear (D-038)."""

    kind: ClassVar[str] = "leave ring"
    name: str = "Leave the ring"
    radius: float = 12.0  # [u], from the light's centre to the swimmer's

    def marks(self, arena: Arena, pos: np.ndarray, radius: np.ndarray) -> np.ndarray:
        dx = arena.light_xy[None, :, 0] - pos[:, None, 0]
        dy = arena.light_xy[None, :, 1] - pos[:, None, 1]
        return (dx * dx + dy * dy > self.radius * self.radius).all(axis=1)[:, None]  # (N, 1)


@dataclass(frozen=True, kw_only=True)
class StayNear:
    """Every swimmer stays within `radius` of a light for `seconds` in a row: love (D-040).
    The run keeps each swimmer's time in the ring, back to 0 when it leaves, kept once full."""

    kind: ClassVar[str] = "stay near"
    name: str = "Stay by the light"
    radius: float = 6.0  # [u], from the light's centre to the swimmer's
    seconds: float = 5.0  # [s]
    broken: ClassVar[str] = "Lost"

    def marks(self, arena: Arena, pos: np.ndarray, radius: np.ndarray) -> np.ndarray:
        dx = arena.light_xy[None, :, 0] - pos[:, None, 0]
        dy = arena.light_xy[None, :, 1] - pos[:, None, 1]
        return (dx * dx + dy * dy <= self.radius * self.radius).any(axis=1)[:, None]  # (N, 1)

    def start(self, now: np.ndarray) -> np.ndarray:
        return np.zeros(now.shape)

    def keep(self, kept: np.ndarray, now: np.ndarray, dt: float) -> np.ndarray:
        full = kept >= self.seconds - EPS
        return np.where(full, kept, np.where(now, kept + dt, 0.0))

    def count(self, kept: np.ndarray) -> tuple[int, int]:
        return int((kept >= self.seconds - EPS).sum()), int(kept.size)

    def progress(self, kept: np.ndarray) -> float:
        return float(min(1.0, kept.max() / self.seconds)) if kept.size else 0.0

    def lost(self, kept: np.ndarray) -> bool:
        return False


@dataclass(frozen=True)
class KeepOff(Latched):
    """No swimmer reaches a light: one that does loses the run at once (D-040)."""

    kind: ClassVar[str] = "keep off"
    name: str = "Don't touch the light"
    broken: ClassVar[str] = "It touched the light"

    def marks(self, arena: Arena, pos: np.ndarray, radius: np.ndarray) -> np.ndarray:
        return reaching(arena, pos, radius)  # (N, L): the lights touched

    def count(self, kept: np.ndarray) -> tuple[int, int]:
        return int((~kept.any(axis=1)).sum()), int(kept.shape[0])

    def lost(self, kept: np.ndarray) -> bool:
        return bool(kept.any())


@dataclass(frozen=True, kw_only=True)
class CircleLight:
    """Every swimmer goes round a light `turns` times, either way: an orbit (D-097). The run
    keeps, for each swimmer and light, the angle the light last saw it at and the angle swept
    since t = 0, each tick's change taken the short way round, so going back unwinds it; kept
    once the turns are full. Shape (N, L, 2) [rad]."""

    kind: ClassVar[str] = "circle light"
    name: str = "Circle the light"
    turns: int = 2
    broken: ClassVar[str] = "Lost"

    def marks(self, arena: Arena, pos: np.ndarray, radius: np.ndarray) -> np.ndarray:
        dx = pos[:, None, 0] - arena.light_xy[None, :, 0]
        dy = pos[:, None, 1] - arena.light_xy[None, :, 1]
        return np.arctan2(dy, dx)  # (N, L): where each light sees the swimmer [rad]

    def start(self, now: np.ndarray) -> np.ndarray:
        return np.stack((now, np.zeros(now.shape)), axis=-1)

    def keep(self, kept: np.ndarray, now: np.ndarray, dt: float) -> np.ndarray:
        turned = np.mod(now - kept[..., 0] + np.pi, 2.0 * np.pi) - np.pi  # in [-pi, pi)
        swept = np.stack((now, kept[..., 1] + turned), axis=-1)
        full = np.abs(kept[..., 1]) >= self._sweep - EPS
        return np.where(full[..., None], kept, swept)

    def count(self, kept: np.ndarray) -> tuple[int, int]:
        """Whole turns made round the light gone round most, at most `turns`, every swimmer's,
        out of `turns` each: "1 of 2"."""
        best = np.abs(kept[..., 1]).max(axis=1, initial=0.0)  # (N,)
        whole = np.minimum(self.turns, np.floor((best + EPS) / (2.0 * np.pi)))
        return int(whole.sum()), self.turns * int(kept.shape[0])

    def progress(self, kept: np.ndarray) -> float:
        best = float(np.abs(kept[..., 1]).max(initial=0.0))
        return min(1.0, best / self._sweep)

    def lost(self, kept: np.ndarray) -> bool:
        return False

    @property
    def _sweep(self) -> float:
        """The angle the turns take [rad]."""
        return 2.0 * np.pi * self.turns


OBJECTIVES: dict[str, type] = {
    o.kind: o for o in (VisitLights, LeaveRing, StayNear, KeepOff, CircleLight)
}


def objective_to_dict(objective: Objective) -> dict:
    """Its kind and its settings, as a level's data holds it; the name is the code's."""
    settings = {f.name: getattr(objective, f.name) for f in fields(objective) if f.name != "name"}
    return {"kind": objective.kind, **settings}


def objective_from_dict(data: Mapping) -> Objective:
    if data["kind"] not in OBJECTIVES:
        raise ValueError(f"no objective is called {data['kind']!r}")
    return OBJECTIVES[data["kind"]](**{k: v for k, v in data.items() if k != "kind"})
