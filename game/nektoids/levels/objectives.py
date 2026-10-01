"""What a level asks of its swimmers, each measured as how far along it is: 0, then 1 when met.

An objective reads the swimmers' positions and never changes them. Countable ones (so many
swimmers past the gap, brief section 1) come with the real levels; `ReachLight` is the first.
Pure numbers, no pygame.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from nektoids.sim.arena import LIGHT_RADIUS, Arena


class Objective(Protocol):
    name: str

    def progress(
        self, arena: Arena, start: np.ndarray, pos: np.ndarray, radius: np.ndarray
    ) -> float:
        """In [0, 1]. start, pos: (N, 2) where the swimmers began and are now [u]; radius (N,)."""
        ...


def _nearest_light(arena: Arena, pos: np.ndarray) -> np.ndarray:
    """(N,): how far each point is from the centre of its nearest light [u]."""
    dx = arena.light_xy[None, :, 0] - pos[:, None, 0]
    dy = arena.light_xy[None, :, 1] - pos[:, None, 1]
    return np.sqrt(dx * dx + dy * dy).min(axis=1)


@dataclass(frozen=True)
class ReachLight:
    """Touch a light: each swimmer's fraction of the way from where it began to touching the
    nearest light, averaged over the swimmers. Moving away from the lights counts as 0."""

    name: str = "Reach a light"

    def progress(
        self, arena: Arena, start: np.ndarray, pos: np.ndarray, radius: np.ndarray
    ) -> float:
        if len(arena.lights) == 0 or len(pos) == 0:
            return 0.0
        touch = LIGHT_RADIUS + np.asarray(radius, dtype=np.float64)
        begun, now = _nearest_light(arena, start) - touch, _nearest_light(arena, pos) - touch
        way = np.where(begun > 0, 1.0 - np.maximum(now, 0.0) / np.where(begun > 0, begun, 1.0), 1.0)
        return float(np.clip(way, 0.0, 1.0).mean())
