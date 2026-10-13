"""The flow drawn: tracers carried by it over the plane in view (D-603, D-608).

A fixed field: one tracer in every CELL-sided cell of the plane in view, at random in it, none in
a light, an obstacle or the swimmer, kept for good; one that leaves the view comes back on the
other side. Each frame it moves as the flow round the first swimmer goes (`flow.flow_at`). It is
seen, never run: nothing here touches the run's state, so a run is the same with it shown or not
(invariant 1); a restart, a seek or another view seeds it again. Lengths in u. Pure numpy, no
pygame.
"""

from __future__ import annotations

import numpy as np

from nektoids.sim import flow
from nektoids.sim.arena import Arena

CELL = 0.9  # [u] one tracer per cell of this side (D-603, D-610)
SLOW = 0.015  # [u/s] the dimmest speed shown...
FAST = 1.0  # [u/s] ... and the brightest, on a log scale between
LEVELS = 8  # how many brightnesses
SEED = 7  # where in its cell each tracer starts: the same every time it is seeded

Rect = tuple[float, float, float, float]  # left, bottom, right, top [u]


class Tracers:
    """The tracers of the plane in view; empty until `follow` first sees it."""

    def __init__(self) -> None:
        self.rect: Rect | None = None
        self.x = np.zeros((0, 2))  # (P, 2) [u]
        self.speed = np.zeros(0)  # (P,) [u/s], as they last moved
        self.seeded = 0  # how many times seeded: a drawing of them starts again when it changes

    def clear(self) -> None:
        """Seeded again at the next `follow`: after a restart or a seek."""
        self.rect = None

    def follow(
        self,
        arena: Arena,
        pos: np.ndarray,
        radius: float,
        swum: flow.Swim,
        rect: Rect,
        seconds: float,
    ) -> None:
        """The tracers `seconds` [s] on, carried by the flow round a swimmer at pos (2,) [u] of
        `radius` [u] that `swum` solved; seeded first over `rect` if it is not their plane."""
        if rect != self.rect:
            self._seed(arena, pos, radius, rect)
        if not len(self.x):
            return
        u = flow.flow_at(arena, self.x, pos, radius, swum)
        self.speed = np.hypot(u[:, 0], u[:, 1])
        if seconds > 0.0:
            left, bottom, right, top = rect
            x = _outside(arena, pos, radius, self.x + seconds * u)
            x[:, 0] = (x[:, 0] - left) % (right - left) + left
            x[:, 1] = (x[:, 1] - bottom) % (top - bottom) + bottom
            self.x = x

    def levels(self) -> np.ndarray:
        """(P,) int: each tracer's brightness, 0 to LEVELS - 1, by its speed on a log scale."""
        rise = np.log(np.maximum(self.speed, SLOW) / SLOW) / np.log(FAST / SLOW)
        return np.clip((rise * LEVELS).astype(np.int64), 0, LEVELS - 1)

    def _seed(self, arena: Arena, pos: np.ndarray, radius: float, rect: Rect) -> None:
        left, bottom, right, top = rect
        ix, iy = np.meshgrid(
            np.arange(int(np.ceil((right - left) / CELL))),
            np.arange(int(np.ceil((top - bottom) / CELL))),
        )
        corner = np.stack((left + CELL * ix.ravel(), bottom + CELL * iy.ravel()), axis=1)
        x = corner + CELL * np.random.default_rng(SEED).random(corner.shape)
        x = x[(x[:, 0] < right) & (x[:, 1] < top)]
        self.x = x[np.all(_outside(arena, pos, radius, x) == x, axis=1)]
        self.speed = np.zeros(len(self.x))
        self.rect = rect
        self.seeded += 1


def _outside(arena: Arena, pos: np.ndarray, radius: float, x: np.ndarray) -> np.ndarray:
    """Points x (P, 2) [u] put back outside the lights, the obstacles and the swimmer, radially."""
    xy, size = flow.clamped(arena)
    centres = np.concatenate((pos[None], xy))
    reach = np.concatenate(([radius], size))
    dx = x[:, None, 0] - centres[None, :, 0]
    dy = x[:, None, 1] - centres[None, :, 1]
    d = np.maximum(np.sqrt(dx * dx + dy * dy), 1e-9)
    depth = np.maximum(0.0, reach - d)
    return x + np.stack(((depth * dx / d).sum(axis=1), (depth * dy / d).sum(axis=1)), axis=1)
