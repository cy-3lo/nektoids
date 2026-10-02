"""The Run preview's engine (D-051, D-058): the board as it would run where a probe stands.

The probe is the swimmer put anywhere on the level and turned any way; nothing moves and
nothing is scored. Its eyes read the light there, as they would in a run, and the circuit
settles tick by tick, with its lags (D-017) and its beads. The player may hold an eye at a
level by its meter, to see what follows: a test input, kept nowhere and never seen by a run, so
the board still holds no continuous parameter (brief: "No sliders"; amends D-016's developer
sliders). Moving or turning the probe gives every eye back to the light. Pure Python and numpy,
no pygame.
"""

from __future__ import annotations

import math
from typing import NamedTuple

import numpy as np

from nektoids.editor.arena_view import ArenaView, frame
from nektoids.editor.circuit import METER_AT, METER_HEIGHT, Circuit
from nektoids.editor.devdrive import DT
from nektoids.editor.layout import Rect
from nektoids.graph.board import Board
from nektoids.graph.dynamics import RATE_MAX, initial_state, step
from nektoids.graph.network import Network
from nektoids.levels.level import Level
from nektoids.levels.objectives import LeaveRing, StayNear
from nektoids.sim import world
from nektoids.sim.arena import BASE_RADIUS, LIGHT_RADIUS
from nektoids.sim.contact import confine
from nektoids.sim.optics import eye_rates

PREVIEW_MARGIN = 1.6  # room round the body's circle on the main screen [hex sizes]
MAP_MARGIN = 2.0  # room round what Sense's map shows of the level [u]
HANDLE_GRAB = 10  # a press this close to an eye's meter takes it [px]


class Pose(NamedTuple):
    x: float  # [u]
    y: float  # [u]
    heading: float  # [rad], counter-clockwise from +x


class Track(NamedTuple):
    """An eye's meter as a handle: its x, its top and its foot on screen [px]."""

    x: float
    top: float
    bottom: float


class Probe:
    def __init__(self, board: Board, level: Level, area: Rect, pose: Pose | None = None):
        """area: where the circuit is drawn [px]; pose: where the probe stands, else the
        level's start."""
        self.board, self.level = board, level
        self.circuit = Circuit(board, area, PREVIEW_MARGIN, body=True)
        x, y, heading = level.start
        start = pose or Pose(x, y, math.radians(heading))
        self.pos = np.array([[start.x, start.y]], dtype=np.float64)  # (1, 2) [u]
        self.heading = np.array([start.heading])  # (1,) [rad]
        self.radius = np.full(1, BASE_RADIUS)  # every body alike (D-045)
        self.held: dict[int, float] = {}  # an eye's network index: the level it is held at
        self.state = initial_state(self.net)  # (1, n), from rest
        self.mount, self.facing = world.parts(self.net, self.net.eyes)
        self._look()

    @property
    def net(self) -> Network:
        return self.circuit.net

    @property
    def y(self) -> np.ndarray:
        """Every node's rate now, (n,)."""
        return self.state[0]

    @property
    def pose(self) -> Pose:
        return Pose(float(self.pos[0, 0]), float(self.pos[0, 1]), float(self.heading[0]))

    def _look(self) -> None:
        """What each eye reads where the probe stands: once, as nothing moves."""
        arena = self.level.arena
        self.light = eye_rates(arena, self.pos, self.heading, self.radius, self.mount, self.facing)[
            0
        ]

    def eyes(self) -> np.ndarray:
        """What each eye sends now, (n_eyes,): the light, or the level it is held at."""
        sent = self.light.copy()
        for k, i in enumerate(self.net.eyes):
            sent[k] = self.held.get(int(i), sent[k])
        return sent

    def tick(self, dt: float = DT) -> None:
        self.state = step(self.net, self.state, self.eyes()[None, :], dt)
        self.circuit.advance(self.y, dt)

    def place(self, x: float, y: float) -> None:
        """The probe to (x, y) [u], outside the obstacles; the eyes back to the light."""
        point = np.array([[x, y]], dtype=np.float64)
        self.pos = confine(self.level.arena, point, self.radius)
        self.held.clear()
        self._look()

    def turn(self, angle: float) -> None:
        """Turn the probe by `angle` [rad], counter-clockwise; the eyes back to the light."""
        self.heading = self.heading + angle
        self.held.clear()
        self._look()

    def hold(self, i: int, level: float) -> None:
        """Hold eye `i` (its network index) at `level`, clamped to [0, RATE_MAX]."""
        self.held[i] = min(RATE_MAX, max(0.0, level))

    def fit(self, area: Rect) -> None:
        """Draw the circuit in another area; the rates and the beads go on as they were."""
        beads = self.circuit.beads
        self.circuit = Circuit(self.board, area, PREVIEW_MARGIN, body=True)
        self.circuit.beads = beads
        self.circuit.show(self.y)

    # The eyes' meters as handles

    def track(self, i: int) -> Track:
        """Eye `i`'s meter, beside it, as `schematic_draw` draws every meter (D-052)."""
        cx, cy = self.circuit.centre(i)
        size = self.circuit.view.size
        half = 0.5 * METER_HEIGHT * size
        return Track(cx + METER_AT * size, cy - half, cy + half)

    def handle_at(self, point: tuple[float, float]) -> int | None:
        """The eye whose meter a press at `point` takes, if any."""
        for i in self.net.eyes:
            track = self.track(int(i))
            near = abs(point[0] - track.x) <= HANDLE_GRAB
            if near and track.top - HANDLE_GRAB <= point[1] <= track.bottom + HANDLE_GRAB:
                return int(i)
        return None

    def level_at(self, i: int, y: float) -> float:
        """The level eye `i`'s handle sets with its knob at screen height `y` [px]."""
        track = self.track(i)
        return RATE_MAX * min(1.0, max(0.0, (track.bottom - y) / (track.bottom - track.top)))


def level_view(level: Level, area: Rect) -> ArenaView:
    """The level seen whole in `area`, as the run frames it at its start: its lights and their
    rings, its obstacles, where the swimmer starts."""
    x, y, _ = level.start
    arena = level.arena
    rims = [
        arena.light_xy + d for r in ring_radii(level) for d in ((r, 0), (-r, 0), (0, r), (0, -r))
    ]
    points = np.concatenate(([[x, y]], arena.light_xy, arena.disc_xy, *rims))
    reach = float(np.concatenate(([LIGHT_RADIUS, BASE_RADIUS], arena.disc_radius)).max())
    return frame(area, points, MAP_MARGIN + reach)


def ring_radii(level: Level) -> list[float]:
    """The rings the level's objectives draw round its lights, to leave or to stay in [u]."""
    return [o.radius for o in level.objectives if isinstance(o, LeaveRing | StayNear)]
