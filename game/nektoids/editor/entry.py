"""A part's entry at work (D-082): under what its info box says, the part in a small circuit of
its own, running as Inside shows a board, beads and meters alike.

The inputs on the left, the part in the middle, a thruster on the right taking what it sends; a
sensor has no input, a thruster no thruster after it. The inputs are eyes set to a reading, not
lit by a light, so that less than 1 can go in: a Source sends 1, and ×2 of 1 is still 1. Eyes
and thrusters turn their faces outwards: the light comes into each eye's face from the left, and
the thrust streams out of each thruster's back to the right, drawn as the run draws them, specks
of light drawn in and flames (D-076), as many as the rate. Only the Eye's own reading moves, to
show more light giving more beads; the rest are steady, so that the beads can be counted. Beads
keep their speed once out (`beads.Travelling`), so none goes backwards as the reading changes.
The circuit opens at its steady rates, and for ×2 and ÷2 the beads going out keep time with
those coming in: one in, two out; two in, one out. Never read by the model. Pure Python, no
pygame.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import cache

import numpy as np

from nektoids.editor.beads import BEAD_RATE_AT_FULL
from nektoids.editor.circuit import Circuit
from nektoids.editor.devdrive import DT, TICKS_PER_FRAME
from nektoids.editor.geometry import EYE_DISC, SQUARE_POINT
from nektoids.editor.layout import Rect, View, fitted_view
from nektoids.editor.marks import (
    FLAME_LIFE,
    FLAME_SPECKS,
    FLAME_SPREAD,
    INTAKE_LIFE,
    INTAKE_SPECKS,
    INTAKE_SPREAD,
    SPECKS,
    face,
)
from nektoids.graph.board import Board, Kind
from nektoids.graph.dynamics import RATE_MAX, initial_state, step
from nektoids.graph.hexgrid import Cell, W, to_pixel
from nektoids.sim.optics import FACING_STEP

ENTRY_AREA: Rect = (0, 0, 420, 140)  # the circuit, in the box's own frame [px]
MARGIN = 0.6  # round the circuit and its specks, in its area [hex sizes]
SETTLE = 0.25  # [s] run before it shows, so that it opens at its steady rates
EYE_LOW, EYE_HIGH, EYE_PERIOD = 0.2, 0.9, 10.0  # the Eye's own reading, rising and falling [s]
REACH = 1.8  # [hex sizes] how far out the light comes from, and the flames go
STREAMS = 400  # the entry's streams in the specks' table, after the swimmer's and the sparks'
OUTWARDS = W  # every eye and thruster faces left: the eye's face, the thruster's back, outwards
ZONE = [(q, r) for q in range(-6, 6) for r in range(-2, 3)]  # room for every route

# Where the parts sit: one input, two inputs one over the other, the part, its thruster.
IN, UPPER, LOWER, PART, OUT = (-3, 0), (-2, -1), (-3, 1), (0, 0), (3, 0)
SENSOR, ITS_THRUSTER = (-2, 0), (1, 0)  # a sensor's own entry: it, then a thruster
# Each face's middle along the part's axis, and half its width [hex sizes]: the eye's in front,
# the thruster's back behind (`marks.face`).
EYE_FACE, THRUSTER_BACK = face(np.array(EYE_DISC)), face(np.array(SQUARE_POINT))
AHEAD = (math.cos(FACING_STEP * OUTWARDS), -math.sin(FACING_STEP * OUTWARDS))  # on screen

Point = tuple[float, float]


@dataclass(frozen=True)
class Demo:
    parts: tuple[tuple[Kind, Cell], ...]  # in the order they are placed
    wires: tuple[tuple[Cell, Cell], ...]  # in the order they are made
    readings: tuple[float, ...]  # each eye's, in the parts' order; the Eye's own moves


def _through(kind: Kind, readings: tuple[float, ...]) -> Demo:
    """`kind` between its inputs, eyes at `readings`, and a thruster."""
    ins = (IN,) if len(readings) == 1 else (UPPER, LOWER)
    parts = (*((Kind.EYE, cell) for cell in ins), (kind, PART), (Kind.THRUSTER, OUT))
    wires = (*((cell, PART) for cell in ins), (PART, OUT))
    return Demo(parts, wires, readings)


DEMOS: dict[Kind, Demo] = {
    Kind.EYE: Demo(
        ((Kind.EYE, SENSOR), (Kind.THRUSTER, ITS_THRUSTER)), ((SENSOR, ITS_THRUSTER),), (EYE_LOW,)
    ),
    Kind.SOURCE: Demo(
        ((Kind.SOURCE, SENSOR), (Kind.THRUSTER, ITS_THRUSTER)), ((SENSOR, ITS_THRUSTER),), ()
    ),
    Kind.DOUBLE: _through(Kind.DOUBLE, (0.3,)),
    Kind.HALVE: _through(Kind.HALVE, (0.8,)),
    Kind.SUM: _through(Kind.SUM, (0.3, 0.4)),
    Kind.DIFFERENCE: _through(Kind.DIFFERENCE, (0.7, 0.3)),
    Kind.THRUSTER: Demo(  # two eyes into it: what comes in is added
        ((Kind.EYE, UPPER), (Kind.EYE, LOWER), (Kind.THRUSTER, PART)),
        ((UPPER, PART), (LOWER, PART)),
        (0.3, 0.4),
    ),
}
KEEP_TIME = {Kind.DOUBLE: 2.0, Kind.HALVE: 0.5}  # beads out for each bead in


class Entry:
    def __init__(self, kind: Kind):
        """`kind`'s circuit, built, at its steady rates."""
        demo = DEMOS[kind]
        board = _built(demo)
        self.kind, self.time, self.frame = kind, 0.0, 0
        self.circuit = Circuit(board, ENTRY_AREA, MARGIN, view=_seen(board), travelling=True)
        self.readings = np.array(demo.readings)
        self.state = initial_state(self.circuit.net)
        for _ in range(round(SETTLE / DT)):
            self.state = step(self.circuit.net, self.state, self.eyes()[None, :], DT)
        self.circuit.show(self.y)
        if kind in KEEP_TIME:
            self._keep_time(KEEP_TIME[kind])
        self.circuit.beads.fill((BEAD_RATE_AT_FULL / RATE_MAX * self.circuit.flux).tolist())

    @property
    def y(self) -> np.ndarray:
        """Every node's rate now, (n,)."""
        return self.state[0]

    def eyes(self) -> np.ndarray:
        """What each eye reads now: its reading; the Eye's own rises and falls."""
        if self.kind is not Kind.EYE:
            return self.readings
        swing = 0.5 - 0.5 * math.cos(2.0 * math.pi * self.time / EYE_PERIOD)
        return np.array([EYE_LOW + (EYE_HIGH - EYE_LOW) * swing])

    def tick(self) -> None:
        """A frame: its ticks run, the beads move."""
        for _ in range(TICKS_PER_FRAME):
            self.state = step(self.circuit.net, self.state, self.eyes()[None, :], DT)
            self.circuit.advance(self.y, DT)
            self.time += DT
        self.frame += 1

    def light(self) -> list[Point]:
        """The specks of light drawn into each eye's face, from REACH ahead of it, as many as it
        reads (`marks.intake`, D-076) [px, in ENTRY_AREA]."""
        (middle, _), half = EYE_FACE
        found = []
        for k, i in enumerate(self.circuit.net.eyes):
            share = float(self.y[i]) / RATE_MAX
            u, across = SPECKS.stream(INTAKE_SPECKS * share, self.frame, INTAKE_LIFE, STREAMS + k)
            found += self._off_face(int(i), middle, half, 1.0 - u, across, INTAKE_SPREAD, 1.0)
        return found

    def flames(self) -> list[Point]:
        """The specks of each thruster's flame, out of its back, REACH long, as many as its rate
        (`marks.flames`, D-076) [px, in ENTRY_AREA]."""
        (middle, _), half = THRUSTER_BACK
        found = []
        for k, i in enumerate(self.circuit.net.thrusters):
            rate = float(self.y[i]) / RATE_MAX
            stream = STREAMS + 8 + k
            u, across = SPECKS.stream(FLAME_SPECKS * rate, self.frame, FLAME_LIFE, stream)
            found += self._off_face(int(i), middle, half, u, across, FLAME_SPREAD, -1.0)
        return found

    def _off_face(self, i, middle, half, along, across, spread, way) -> list[Point]:
        """Specks off node i's face, `middle` hex sizes along its axis and `half` wide: `along`
        in [0, 1] of REACH out of it, ahead of the part if `way` is +1, behind it if -1; `across`
        in [-1, 1], widening by `spread` [rad] either side."""
        size = self.circuit.view.size
        cx, cy = self.circuit.centre(i)
        ax, ay = AHEAD
        out = along * REACH * size
        wide = across * (half * size + out * math.tan(spread))
        x = cx + ax * middle * size + way * ax * out - ay * wide
        y = cy + ay * middle * size + way * ay * out + ax * wide
        return list(zip(x.tolist(), y.tolist(), strict=True))

    def _keep_time(self, ratio: float) -> None:
        """The beads out of the part leave as one comes in, and `ratio` times as often: wire 0
        comes in, wire 1 goes out. A bead reaches the end of wire 0 when its phase is
        `length × flux / speed`, modulo 1; wire 1's phase is set to wrap then."""
        beads = self.circuit.beads
        flux = BEAD_RATE_AT_FULL / RATE_MAX * float(self.circuit.flux[0])
        arrives = beads.lengths[0] * flux / beads.speed
        beads.phase[1] = (ratio * (beads.phase[0] - arrives)) % 1.0


def _seen(board: Board) -> View:
    """The view of `board` in ENTRY_AREA, centred, at the size every entry shares: the size at
    which the entry that needs the most room fits, its specks included."""
    points = _shown(board)
    xs, ys = [x for x, _ in points], [y for _, y in points]
    x, y, w, h = ENTRY_AREA
    size, cx, cy = _shared_size(), (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    return View(size, (x + w / 2 - size * cx, y + h / 2 - size * cy))


@cache
def _shared_size() -> float:
    """The largest hex size at which every entry fits its area [px]."""
    boards = [_built(demo) for demo in DEMOS.values()]
    return min(fitted_view(ENTRY_AREA, _shown(board), MARGIN).size for board in boards)


def _built(demo: Demo) -> Board:
    """The demo's board: its parts placed, facing outwards, then its wires made, in order."""
    board = Board(ZONE)
    for part, cell in demo.parts:
        board.place(part, cell, facing=OUTWARDS)
    for start, end in demo.wires:
        board.connect(board.node_at(start).id, board.node_at(end).id)
    return board


def _shown(board: Board) -> list[Point]:
    """What an entry shows of `board`, at hex size 1 about cell (0, 0): its parts, its wires and
    the specks off the faces, REACH out."""
    ax, ay = AHEAD
    points = []
    for node in board.nodes.values():
        x, y = to_pixel(node.cell, 1.0, (0.0, 0.0))
        points.append((x, y))
        if node.kind is Kind.EYE:  # the light comes from REACH ahead of its face
            reach = float(EYE_FACE[0][0]) + REACH
            points.append((x + ax * reach, y + ay * reach))
        elif node.kind is Kind.THRUSTER:  # the flames go REACH behind its back
            reach = float(THRUSTER_BACK[0][0]) - REACH
            points.append((x + ax * reach, y + ay * reach))
    for wire in board.wires:
        points += [to_pixel(cell, 1.0, (0.0, 0.0)) for cell in wire.path]
    return points
