"""How the arena is seen: from the sim's u (y up) to screen pixels (y down), and back.

Also the rays drawn from the lights, the grid of the light map (the other way to show the light)
and the grey level of a reading, and which swimmer is under the mouse. The plane is open
(D-028): a view frames what a level holds, and shows as much of the plane as its area allows;
rays and the light map go as far as it shows. Pure numbers, no pygame.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from nektoids.editor.layout import Rect
from nektoids.editor.palette import LIGHT, SHADOW

DARKEST = np.array(SHADOW)  # a reading of 0: shadow
BRIGHTEST = np.array(LIGHT)  # a reading of RATE_MAX
GRAB = 6.0  # a press this far outside a body still grabs it [px]
EDGE_INSET = 14.0  # a marker for a swimmer out of view sits this far inside the edge [px]
SMOOTHING = 2  # passes of the 1-2-1 filter over the light map
POLAR_STEPS = 8  # the polar plot zooms in by halves down to 1/256 of RATE_MAX
MIN_SCALE, MAX_SCALE = 4.0, 48.0  # how far the view zooms [px/u]
MAP_COLUMNS = 160  # at most this many light-map cells across, however far the view zooms out
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
    origin: tuple[float, float]  # screen pixel of the plane's point (0, 0)

    def to_screen(self, x: float, y: float) -> tuple[float, float]:
        return (self.origin[0] + self.scale * x, self.origin[1] - self.scale * y)

    def to_world(self, px: float, py: float) -> tuple[float, float]:
        return ((px - self.origin[0]) / self.scale, (self.origin[1] - py) / self.scale)


def shown(view: ArenaView, area: Rect) -> tuple[float, float, float, float]:
    """The part of the plane that `area` shows: (left, bottom, right, top) [u]."""
    x, y, w, h = area
    left, top = view.to_world(x, y)
    right, bottom = view.to_world(x + w, y + h)
    return (left, bottom, right, top)


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


def map_grid(
    region: tuple[float, float, float, float], finest: float, columns: int = MAP_COLUMNS
) -> tuple[tuple[float, float], float, tuple[int, int]]:
    """The light map's grid over `region` (left, bottom, right, top) [u]: its top-left corner
    [u], on a multiple of the cell so that panning does not shift it; the cell [u], `finest` or
    coarser, so that at most `columns` fit across; and (rows, cols), covering the region."""
    left, bottom, right, top = region
    cell = max(finest, (right - left) / columns)
    x0, y0 = math.floor(left / cell) * cell, math.ceil(top / cell) * cell
    cols, rows = math.ceil((right - x0) / cell), math.ceil((y0 - bottom) / cell)
    return (x0, y0), cell, (rows, cols)


def map_points(corner: tuple[float, float], cell: float, shape: tuple[int, int]) -> np.ndarray:
    """(rows * cols, 2): centres of the grid's squares [u], row by row from its top-left
    `corner`, left to right."""
    (x0, y0), (rows, cols) = corner, shape
    gx, gy = np.meshgrid(x0 + (np.arange(cols) + 0.5) * cell, y0 - (np.arange(rows) + 0.5) * cell)
    return np.column_stack((gx.ravel(), gy.ravel()))


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


def edge_marker(
    view: ArenaView, area: Rect, point: tuple[float, float], inset: float = EDGE_INSET
) -> tuple[tuple[float, float], float] | None:
    """Where to point at `point` [u] while it is out of `area`, so that nothing leaves the screen
    unseen (invariant 6): the spot `inset` [px] inside the edge on the line from the area's
    centre to it, and that line's angle on screen [rad, y down]. None while it shows."""
    x, y, w, h = area
    px, py = view.to_screen(*point)
    if x <= px <= x + w and y <= py <= y + h:
        return None
    cx, cy = x + w / 2, y + h / 2
    dx, dy = px - cx, py - cy
    t = min(
        (w / 2 - inset) / abs(dx) if dx else math.inf,
        (h / 2 - inset) / abs(dy) if dy else math.inf,
    )
    return (cx + t * dx, cy + t * dy), math.atan2(dy, dx)


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
    length: float,
) -> np.ndarray:
    """(K, 2): where rays from `origin` at `angles` (K,) stop [u]: the first disc they meet, or
    `length` [u] away. A ray that starts inside a disc stops at once.

    centres (M, 2), radii (M,). Along a ray x = s + t u, a disc c, R is met at the smaller root
    of t^2 - 2 (u.w) t + |w|^2 - R^2 = 0, w = c - s, if that root is positive.
    """
    sx, sy = origin
    ux, uy = np.cos(angles), np.sin(angles)
    reach = np.full(len(ux), float(length))
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
