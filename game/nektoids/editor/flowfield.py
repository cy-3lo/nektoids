"""The flow drawn: tracers carried by it over the plane in view (D-603, D-608).

A field: one tracer in every CELL-sided cell of the plane in view, coarser on Diagnostic's map
(D-706), at random in it, none in a light, an obstacle, a pump, a source or the swimmer; one that
leaves the view comes back on the other side. Each frame it moves as the flow round the first
swimmer goes (`flow.flow_at`).

The tracers are a thin slab of the fluid round the plane, which the flow leaves, up and down,
where dw/dz > 0 and comes into where it is negative (`flow.rise_at`, integrated along each step,
`_carried`):
ahead of a pump, round a
source, the plane's flow converges, and the tracers would bunch, behind it diverges, and gaps would
open. So each leaves the slab at the rate dw/dz, or splits in two at the rate -dw/dz, which keeps
their density, n, as the fluid's: dn/dt + div(n u) = -n dw/dz, uniform as seeded. A sink swallows
those that reach it; a source in view puts out new ones on its rim, n Q / 2R a second, as many as
cross it in the plane. Past MOST times the count seeded, the most crowded cells lose their oldest
first (D-704).

It is seen, never run: nothing here touches the run's state, so a run is the same with it shown or
not (invariant 1); a restart, a seek or another view seeds it again, its own draws too. Lengths in
u. Pure numpy, no pygame.
"""

from __future__ import annotations

import numpy as np

from nektoids.sim import flow
from nektoids.sim.arena import STIR_RADIUS, Arena

CELL = 0.9  # [u] one tracer per cell of this side (D-603, D-610)
SLOW = 0.015  # [u/s] the dimmest speed shown...
FAST = 1.0  # [u/s] ... and the brightest, on a log scale between
LEVELS = 8  # how many brightnesses
SEED = 7  # where in its cell each tracer starts: the same every time it is seeded
EMIT_SEED = 11  # which leave or split, and where new ones land: the same every time
STEP = 0.2  # [u] a tracer moves at most this far a substep...
SUBSTEPS = 8  # ... in at most this many: 1.6 u a frame, as a source's rim at 8 (D-704)
MOST = 2.0  # times the count seeded, at most: a guard, the slab keeping it near 1 (D-704)

Rect = tuple[float, float, float, float]  # left, bottom, right, top [u]


class Tracers:
    """The tracers of the plane in view; empty until `follow` first sees it."""

    def __init__(self, cell: float = CELL) -> None:
        """cell: one tracer seeded in each cell of this side [u]; coarser on a small map (D-706)."""
        self.cell = cell
        self.rect: Rect | None = None
        self.x = np.zeros((0, 2))  # (P, 2) [u]
        self.speed = np.zeros(0)  # (P,) [u/s], as they last moved
        self.seeded = 0  # how many times seeded: a drawing of them starts again when it changes
        self.most = 0  # MOST times the count seeded: no more are kept
        self.owed = np.zeros(0)  # (S,) the part of a tracer each source owes, to put out next
        self.rng = np.random.default_rng(EMIT_SEED)

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
        u = flow.flow_at(arena, self.x, pos, radius, swum)
        self.speed = np.hypot(u[:, 0], u[:, 1])
        if seconds > 0.0:
            left, bottom, right, top = rect
            x, rise = _carried(arena, self.x, u, pos, radius, swum, seconds)
            speed = self.speed
            draw = self.rng.random(len(x))
            leaves = draw < -np.expm1(-np.maximum(rise, 0.0))  # out of the slab...
            splits = draw < np.expm1(np.maximum(-rise, 0.0))  # ... or a second one into it
            twins = x[splits] + _scattered(self.rng, int(splits.sum()), self.cell)
            x = np.concatenate((x[~leaves], twins))
            speed = np.concatenate((speed[~leaves], speed[splits]))
            kept = ~_in_sinks(arena, x)
            x, self.speed = _outside(arena, pos, radius, x[kept]), speed[kept]
            x[:, 0] = (x[:, 0] - left) % (right - left) + left
            x[:, 1] = (x[:, 1] - bottom) % (top - bottom) + bottom
            new, fast = self._put_out(arena, rect, seconds)
            x, self.speed = np.concatenate((x, new)), np.concatenate((self.speed, fast))
            keep = _thinned(x, rect, max(0, len(x) - self.most), self.cell)
            self.x, self.speed = x[keep], self.speed[keep]

    def _put_out(self, arena: Arena, rect: Rect, seconds: float) -> tuple[np.ndarray, np.ndarray]:
        """The tracers the sources in view put out in `seconds` [s], on their rims (P, 2) [u],
        and their speed there (P,) [u/s]."""
        left, bottom, right, top = rect
        rate = arena.source_rate
        x, y = arena.source_xy[:, 0], arena.source_xy[:, 1]
        shown = (rate > 0.0) & (x >= left) & (x < right) & (y >= bottom) & (y < top)
        owed = seconds * rate / (2 * STIR_RADIUS * self.cell**2)
        self.owed = self.owed + np.where(shown, owed, 0.0)
        count = self.owed.astype(np.int64)
        self.owed = self.owed - count
        centre = np.repeat(arena.source_xy, count, axis=0)
        angle = 2.0 * np.pi * self.rng.random(len(centre))
        rim = centre + STIR_RADIUS * np.stack((np.cos(angle), np.sin(angle)), axis=1)
        return rim, np.repeat(rate / (4.0 * np.pi * STIR_RADIUS**2), count)

    def levels(self) -> np.ndarray:
        """(P,) int: each tracer's brightness, 0 to LEVELS - 1, by its speed on a log scale."""
        rise = np.log(np.maximum(self.speed, SLOW) / SLOW) / np.log(FAST / SLOW)
        return np.clip((rise * LEVELS).astype(np.int64), 0, LEVELS - 1)

    def _seed(self, arena: Arena, pos: np.ndarray, radius: float, rect: Rect) -> None:
        left, bottom, right, top = rect
        cell = self.cell
        ix, iy = np.meshgrid(
            np.arange(int(np.ceil((right - left) / cell))),
            np.arange(int(np.ceil((top - bottom) / cell))),
        )
        corner = np.stack((left + cell * ix.ravel(), bottom + cell * iy.ravel()), axis=1)
        x = corner + cell * np.random.default_rng(SEED).random(corner.shape)
        x = x[(x[:, 0] < right) & (x[:, 1] < top)]
        self.x = x[np.all(_outside(arena, pos, radius, x) == x, axis=1)]
        self.speed = np.zeros(len(self.x))
        self.rect = rect
        self.seeded += 1
        self.most = int(MOST * len(self.x))
        self.owed = np.zeros(len(arena.sources))
        self.rng = np.random.default_rng(EMIT_SEED)


def _carried(
    arena: Arena, x, u, pos, radius, swum, seconds: float
) -> tuple[np.ndarray, np.ndarray]:
    """Points x (P, 2) [u] at u (P, 2) [u/s] carried `seconds` [s] on (P, 2), and dw/dz
    integrated along the way (P,): by the midpoint rule, in substeps of at most STEP, at most
    SUBSTEPS, the rise by the trapezoid rule on each. Near a source, the flow is fast and dw/dz
    changes much in a frame: one Euler step would carry a new tracer twice as far as it goes,
    and the start's dw/dz alone would take every one out of the slab at once (D-704)."""
    count = np.clip(np.ceil(np.hypot(u[:, 0], u[:, 1]) * seconds / STEP), 1, SUBSTEPS)
    h = (seconds / count)[:, None]
    x, rise = x.copy(), flow.rise_at(arena, x, pos, radius, swum)
    total = np.zeros(len(x))
    for k in range(int(count.max(initial=1))):
        on = count > k
        at, step = x[on], h[on]
        start = u[on] if k == 0 else flow.flow_at(arena, at, pos, radius, swum)
        at = at + step * flow.flow_at(arena, at + 0.5 * step * start, pos, radius, swum)
        risen = flow.rise_at(arena, at, pos, radius, swum)
        total[on] += step[:, 0] * 0.5 * (rise[on] + risen)
        x[on], rise[on] = at, risen
    return x, total


def _scattered(rng: np.random.Generator, count: int, cell: float = CELL) -> np.ndarray:
    """(count, 2) [u]: offsets at random in a disc of diameter `cell`, where a twin lands from
    the tracer it split from."""
    angle, reach = 2.0 * np.pi * rng.random(count), 0.5 * cell * np.sqrt(rng.random(count))
    return reach[:, None] * np.stack((np.cos(angle), np.sin(angle)), axis=1)


def _thinned(x: np.ndarray, rect: Rect, gone: int, side: float = CELL) -> np.ndarray:
    """(P,) bool: which of the points x (P, 2) [u] stay when `gone` go, taken from the most
    crowded `side`-sided cells of `rect` first, the oldest of each first: each cell's k-th newest
    goes, k the highest first, the oldest first among them, so that a cell keeps one while
    another has two, and a source's newest stay (D-704)."""
    if gone == 0:
        return np.ones(len(x), dtype=bool)
    left, bottom, right, _ = rect
    columns = int(np.ceil((right - left) / side))
    cell = np.floor((x[:, 1] - bottom) / side) * columns + np.floor((x[:, 0] - left) / side)
    order = np.lexsort((-np.arange(len(x)), cell))  # by cell, then newest first
    ranked = cell[order]
    first = np.r_[True, ranked[1:] != ranked[:-1]]
    start = np.maximum.accumulate(np.where(first, np.arange(len(x)), 0))
    rank = np.empty(len(x), dtype=np.int64)
    rank[order] = np.arange(len(x)) - start  # each one's place in its cell, 0 the newest
    stays = np.ones(len(x), dtype=bool)
    stays[np.lexsort((np.arange(len(x)), -rank))[:gone]] = False
    return stays


def _in_sinks(arena: Arena, x: np.ndarray) -> np.ndarray:
    """(P,) bool: whether each point x (P, 2) [u] is in a sink, which swallows it (D-704)."""
    sinks = arena.source_xy[arena.source_rate < 0.0]
    dx = x[:, None, 0] - sinks[None, :, 0]
    dy = x[:, None, 1] - sinks[None, :, 1]
    return (dx * dx + dy * dy <= STIR_RADIUS**2).any(axis=1)


def _outside(arena: Arena, pos: np.ndarray, radius: float, x: np.ndarray) -> np.ndarray:
    """Points x (P, 2) [u] put back outside the lights, the obstacles, the pumps, the sources and
    the swimmer, radially."""
    centres = np.concatenate((pos[None], arena.solid_xy, arena.disc_xy))
    reach = np.concatenate(([radius], arena.solid_radius, arena.disc_radius))
    dx = x[:, None, 0] - centres[None, :, 0]
    dy = x[:, None, 1] - centres[None, :, 1]
    d = np.maximum(np.sqrt(dx * dx + dy * dy), 1e-9)
    depth = np.maximum(0.0, reach - d)
    return x + np.stack(((depth * dx / d).sum(axis=1), (depth * dy / d).sum(axis=1)), axis=1)
