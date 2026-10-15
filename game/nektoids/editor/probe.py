"""Diagnostic's engine on the Board (D-051, D-058, D-407): the board as it would run where a probe
stands, drawn at work in the drawer over the map.

The probe is the swimmer put anywhere on the level and turned any way; nothing moves and
nothing is scored. Its sensors read the world there, as they would in a run: the eyes the light,
the Hairs the flow round the body held where it stands (D-706); and the circuit settles tick by
tick, with its lags (D-017) and its beads. Nothing sets an eye by hand: the eyes' meters, once
handles, are meters again (D-339). Pure Python and numpy, no pygame.
"""

from __future__ import annotations

import math
from typing import NamedTuple

import numpy as np

from nektoids.editor import arena_view
from nektoids.editor.arena_view import ArenaView, frame, rims
from nektoids.editor.circuit import Circuit
from nektoids.editor.devdrive import DT
from nektoids.editor.flowfield import Tracers
from nektoids.editor.layout import Rect
from nektoids.graph.board import Board
from nektoids.graph.dynamics import initial_state, shown, step_given
from nektoids.graph.network import Network
from nektoids.levels.level import Level
from nektoids.sim import flow, world
from nektoids.sim.arena import BASE_RADIUS, LIGHT_RADIUS, STIR_RADIUS
from nektoids.sim.contact import confine
from nektoids.sim.optics import eye_rates

CIRCUIT_MARGIN = 1.0  # room round the body's circle in Diagnostic, as in Run's [hex sizes]
MAP_MARGIN = 2.0  # room round what Diagnostic's map shows of the level [u]
MAP_TRACER_GAP = 9.0  # a tracer seeded every so many px on Diagnostic's map, 3 specks (D-706)


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
        """area: where the board at work is drawn, fitted with its body, as Run's Diagnostic
        draws it (D-089, D-407); pose: where the probe stands, else the level's start."""
        self.board, self.level = board, level
        self.circuit = Circuit(board, area, CIRCUIT_MARGIN, body=True)
        (x, y), heading = level.start_at, level.start[2]  # nudged as the run's (D-425)
        start = pose or Pose(x, y, math.radians(heading))
        self.pos = np.array([[start.x, start.y]], dtype=np.float64)  # (1, 2) [u]
        self.heading = np.array([start.heading])  # (1,) [rad]
        self.radius = np.full(1, BASE_RADIUS)  # every body alike (D-045)
        self.state = initial_state(self.net)  # (1, n, C), from rest
        self.ticks = 0  # ticks run: the clock of the specks on Diagnostic's map (D-076)
        self.swum: flow.Swim | None = None  # the last tick's solve, the body held (D-706)
        self.tracers = Tracers()  # the flow on Diagnostic's map; seen, never run (D-706)
        self.mount, self.facing = world.parts(self.net, self.net.eyes)
        self._look()

    @property
    def net(self) -> Network:
        return self.circuit.net

    @property
    def y(self) -> np.ndarray:
        """Every node's rate now, (n,), as the Board shows it (`dynamics.shown`, D-501)."""
        return shown(self.net, self.state)[0]

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
        """What each eye reads now, (n_eyes, C): the light in each channel; it sends its own."""
        return self.light.copy()

    def tick(self, dt: float = DT) -> None:
        """One tick where the probe stands: the flow solved as a run solves it, but the body
        held, and every sensor reading it, as `world.step` reads them (D-706)."""
        arena, pose = self.level.arena, (self.pos, self.heading, self.radius)
        self.swum = world.swimming(arena, self.net, *pose, self.state)
        given = world.readings(arena, self.net, *pose, self.swum)
        self.state = step_given(self.net, self.state, given, dt)
        self.circuit.advance(self.state[0], dt)
        self.ticks += 1

    def follow_flow(self, area: Rect, seconds: float) -> None:
        """The tracers of the level seen whole in `area`, Diagnostic's map, `seconds` [s] on, in
        the flow of the last tick round the probe, held: only if the level has pumps or sources
        (D-706)."""
        arena = self.level.arena
        if self.swum is not None and (arena.pumps or arena.sources):
            view = level_view(self.level, area)
            cell = MAP_TRACER_GAP / view.scale
            if self.tracers.cell != cell:  # as sparse on the map as in the run, on screen
                self.tracers = Tracers(cell)
            rect = arena_view.shown(view, area)
            radius = float(self.radius[0])
            self.tracers.follow(arena, self.pos[0], radius, self.swum, rect, seconds)

    def place(self, x: float, y: float) -> None:
        """The probe to (x, y) [u], outside the obstacles."""
        point = np.array([[x, y]], dtype=np.float64)
        self.pos = confine(self.level.arena, point, self.radius)
        self.tracers.clear()  # seeded again round it, as a run's after a drag
        self._look()

    def turn(self, angle: float) -> None:
        """Turn the probe by `angle` [rad], counter-clockwise."""
        self.heading = self.heading + angle
        self.tracers.clear()
        self._look()


def level_view(level: Level, area: Rect) -> ArenaView:
    """The level seen whole in `area`, as the run frames it at its start: its lights, its
    marks whole (D-306), its obstacles, its pumps, sources and sinks (D-706), where the swimmer
    starts."""
    x, y, _ = level.start
    arena, marks = level.arena, level.marks
    at, radii = np.array([m.at for m in marks]).reshape(-1, 2), np.array([m.value for m in marks])
    stirs = (arena.pump_xy, arena.source_xy)
    points = np.concatenate(([[x, y]], arena.light_xy, arena.disc_xy, *stirs, rims(at, radii)))
    sizes = [LIGHT_RADIUS, BASE_RADIUS, STIR_RADIUS]
    reach = float(np.concatenate((sizes, arena.disc_radius)).max())
    return frame(area, points, MAP_MARGIN + reach)
