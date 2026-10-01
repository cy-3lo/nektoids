"""How the arena is seen: from the sim's u (y up) to screen pixels (y down), and back.

Also the rays drawn from the lights, the grid of the light map (the other way to show the light)
and the grey level of a reading, and which swimmer is under the mouse. The view fits the arena
in its screen area, whatever its size in u (16 px/u for the arenas of `levels/arenas.py`). Pure
numbers, no pygame.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from nektoids.editor.layout import Rect
from nektoids.sim.arena import Arena

DARKEST = np.array([16, 17, 22])  # a reading of 0: shadow
BRIGHTEST = np.array([236, 238, 244])  # a reading of RATE_MAX
GRAB = 6.0  # a press this far outside a body still grabs it [px]
SMOOTHING = 2  # passes of the 1-2-1 filter over the light map
POLAR_STEPS = 8  # the polar plot zooms in by halves down to 1/256 of RATE_MAX
MIN_SCALE, MAX_SCALE = 4.0, 48.0  # how far the view zooms [px/u]
ZOOM_STEP = 1.25  # scale factor per click
RAYS_PER_POWER = 4.5  # rays drawn per u of a light's power: 36 for a power of 8, 18 for 4
MIN_RAYS = 6
FAN_DRIFT = (0.25, 1.0)  # a light's fan of rays turns at this speed, one way or the other [°/s]
FAN_SWING = (0.5, 2.0)  # ... give or take this much, back and forth [°/s]
SWING_PERIOD = (20.0, 60.0)  # ... over this long [s]
RAY_SWAY = 0.25  # each ray sways about its place by up to this fraction of the spacing
SWAY_PERIOD = (12.0, 30.0)  # ... over this long [s]


@dataclass(frozen=True)
class ArenaView:
    scale: float  # [px / u]
    origin: tuple[float, float]  # screen pixel of the arena's corner (0, 0), its bottom left

    def to_screen(self, x: float, y: float) -> tuple[float, float]:
        return (self.origin[0] + self.scale * x, self.origin[1] - self.scale * y)

    def to_world(self, px: float, py: float) -> tuple[float, float]:
        return ((px - self.origin[0]) / self.scale, (self.origin[1] - py) / self.scale)

    def rect(self, arena: Arena) -> Rect:
        """The arena on screen, (left, top, width, height) [px]."""
        w, h = self.scale * arena.width, self.scale * arena.height
        return (round(self.origin[0]), round(self.origin[1] - h), round(w), round(h))


def fit(area: Rect, arena: Arena) -> ArenaView:
    """The biggest view that shows the whole arena in `area`, centred, same scale on both axes."""
    x, y, w, h = area
    scale = min(w / arena.width, h / arena.height)
    left = x + (w - scale * arena.width) / 2
    bottom = y + (h + scale * arena.height) / 2
    return ArenaView(scale, (left, bottom))


def zoom_view(view: ArenaView, factor: float, about: tuple[float, float]) -> ArenaView:
    """Scale the view by `factor`, within MIN_SCALE and MAX_SCALE; the pixel `about` stays put."""
    scale = min(MAX_SCALE, max(MIN_SCALE, view.scale * factor))
    k = scale / view.scale
    ox, oy = view.origin
    return ArenaView(scale, (about[0] + k * (ox - about[0]), about[1] + k * (oy - about[1])))


def pan_view(view: ArenaView, dx: float, dy: float) -> ArenaView:
    """Slide the view by (dx, dy) [px]."""
    return ArenaView(view.scale, (view.origin[0] + dx, view.origin[1] + dy))


def frame(area: Rect, points: np.ndarray, margin: float) -> ArenaView:
    """The view centred on the mean of `points` (K, 2) [u], as close as it can while showing them
    all with `margin` [u] to spare, within MIN_SCALE and MAX_SCALE."""
    x, y, w, h = area
    centre = points.mean(axis=0)
    reach = np.abs(points - centre).max(axis=0) + margin  # half the room needed, each axis
    scale = max(MIN_SCALE, min(MAX_SCALE, w / (2 * reach[0]), h / (2 * reach[1])))
    cx, cy = x + w / 2, y + h / 2
    return ArenaView(scale, (cx - scale * centre[0], cy + scale * centre[1]))


def map_points(arena: Arena, cell: float) -> tuple[np.ndarray, tuple[int, int]]:
    """Centres of squares of side `cell` [u] covering the arena, row by row from its top edge,
    left to right. Returns the points [u], shape (rows * cols, 2), and (rows, cols)."""
    cols = math.ceil(arena.width / cell)
    rows = math.ceil(arena.height / cell)
    x = np.minimum((np.arange(cols) + 0.5) * cell, arena.width)
    y = np.maximum(arena.height - (np.arange(rows) + 0.5) * cell, 0.0)
    gx, gy = np.meshgrid(x, y)
    return np.column_stack((gx.ravel(), gy.ravel())), (rows, cols)


def smooth(readings: np.ndarray, passes: int = SMOOTHING) -> np.ndarray:
    """The readings (rows, cols) blurred by a 1-2-1 filter along both axes, `passes` times,
    the edges repeated: a hard shadow's edge spreads over about `passes` cells either side."""
    out = np.asarray(readings, dtype=np.float64)
    for _ in range(passes):
        rows = np.pad(out, ((1, 1), (0, 0)), mode="edge")
        out = 0.25 * rows[:-2] + 0.5 * rows[1:-1] + 0.25 * rows[2:]
        cols = np.pad(out, ((0, 0), (1, 1)), mode="edge")
        out = 0.25 * cols[:, :-2] + 0.5 * cols[:, 1:-1] + 0.25 * cols[:, 2:]
    return out


def tone(readings: np.ndarray) -> np.ndarray:
    """(rows, cols, 3) uint8 greys for readings (rows, cols) in [0, 1].

    The square root spreads the dim end, where 1/r changes slowly, so shadows far from a light
    still show; 0 is DARKEST and 1 BRIGHTEST.
    """
    level = np.sqrt(np.clip(readings, 0.0, 1.0))[:, :, None]
    return np.ascontiguousarray(np.round(DARKEST + level * (BRIGHTEST - DARKEST)), dtype=np.uint8)


def polar_scale(peak: float, top: float = 1.0, steps: int = POLAR_STEPS) -> float:
    """The reading the polar plot's circle stands for: `top` halved until the next halving would
    leave `peak` outside, at most `steps` times. Faint light still fills the plot, and the cosine
    lobes stay circles."""
    scale = top
    for _ in range(steps):
        if peak > scale / 2:
            break
        scale /= 2
    return scale


def body_at(
    view: ArenaView, pos: np.ndarray, radius: np.ndarray, point: tuple[float, float]
) -> int | None:
    """The body under the screen point `point`, the nearest if several; None if there is none."""
    if len(pos) == 0:
        return None
    x, y = view.to_world(*point)
    distance = np.hypot(pos[:, 0] - x, pos[:, 1] - y) * view.scale  # [px]
    nearest = int(np.argmin(distance))
    return nearest if distance[nearest] <= radius[nearest] * view.scale + GRAB else None


class Rays:
    """The rays drawn from each light: a picture of the light, never read by the model.

    Light l shows round(RAYS_PER_POWER P_l) rays, evenly spread, so that at a distance r their
    density, N / (2 pi r), is proportional to P / r: what an eye looking at the light reads
    (D-019). Each fan turns slowly, its speed wandering, and each ray sways a little about its
    place. The angles are a pure function of time, drawn from a seeded generator (invariant 1):
    the same at every run, and frozen while the clock is paused.
    """

    def __init__(self, power: np.ndarray, seed: int = 0):
        rng = np.random.default_rng(seed)
        self.counts = [max(MIN_RAYS, round(RAYS_PER_POWER * float(p))) for p in power]
        lights = len(self.counts)
        self.start = rng.uniform(0.0, 2.0 * np.pi, lights)
        self.drift = rng.choice((-1.0, 1.0), lights) * np.radians(rng.uniform(*FAN_DRIFT, lights))
        self.swing = np.radians(rng.uniform(*FAN_SWING, lights))  # [rad/s]
        self.swing_rate = 2.0 * np.pi / rng.uniform(*SWING_PERIOD, lights)  # [rad/s]
        self.swing_phase = rng.uniform(0.0, 2.0 * np.pi, lights)
        self.sway_rate = [2.0 * np.pi / rng.uniform(*SWAY_PERIOD, n) for n in self.counts]
        self.sway_phase = [rng.uniform(0.0, 2.0 * np.pi, n) for n in self.counts]

    def angles(self, light: int, t: float) -> np.ndarray:
        """Where the rays of `light` point at time t [s]: (N_l,) angles [rad], counter-clockwise."""
        n = self.counts[light]
        spacing = 2.0 * np.pi / n
        rate = self.swing_rate[light]
        fan = (
            self.start[light]
            + self.drift[light] * t
            + self.swing[light] / rate * np.sin(rate * t + self.swing_phase[light])
        )
        sway = RAY_SWAY * spacing * np.sin(self.sway_rate[light] * t + self.sway_phase[light])
        return fan + spacing * np.arange(n) + sway


def ray_ends(
    origin: tuple[float, float],
    angles: np.ndarray,
    centres: np.ndarray,
    radii: np.ndarray,
    width: float,
    height: float,
) -> np.ndarray:
    """(K, 2): where rays from `origin` at `angles` (K,) stop [u]: the first disc they meet, or
    the arena's wall. A ray that starts inside a disc stops at once.

    centres (M, 2), radii (M,). Along a ray x = s + t u, a disc c, R is met at the smaller root
    of t^2 - 2 (u.w) t + |w|^2 - R^2 = 0, w = c - s, if that root is positive.
    """
    sx, sy = origin
    ux, uy = np.cos(angles), np.sin(angles)
    with np.errstate(divide="ignore"):
        tx = np.where(ux > 0, (width - sx) / ux, np.where(ux < 0, -sx / ux, np.inf))
        ty = np.where(uy > 0, (height - sy) / uy, np.where(uy < 0, -sy / uy, np.inf))
    reach = np.minimum(tx, ty)
    if len(radii):
        wx, wy = centres[:, 0] - sx, centres[:, 1] - sy  # (M,)
        b = ux[:, None] * wx[None, :] + uy[:, None] * wy[None, :]  # (K, M)
        q = wx * wx + wy * wy - radii * radii  # (M,): negative when the ray starts inside
        room = b * b - q[None, :]
        met = (b > 0) & (room >= 0)
        t = np.where(met, b - np.sqrt(np.maximum(room, 0.0)), np.inf)
        t = np.where(q[None, :] <= 0, 0.0, t)
        reach = np.minimum(reach, t.min(axis=1))
    return np.column_stack((sx + reach * ux, sy + reach * uy))
