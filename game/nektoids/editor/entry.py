"""A part's entry at work (D-082): under what its info box says, the part in a small circuit of
its own, running as Inside shows a board, beads and meters alike.

The inputs on the left, the part in the middle, a thruster on the right taking what it sends; a
sensor has no input, a thruster no thruster after it. The inputs are eyes set to a reading, not
lit by a light, so that less than 1 can go in: a Source sends 1, and ×2 of 1 is still 1. Only
the Eye's own reading moves, to show more light giving more beads; the rest are steady, so that
the beads can be counted. The circuit opens at its steady rates, and for ×2 and ÷2 the beads
going out keep time with those coming in: one in, two out; two in, one out. Never read by the
model. Pure Python, no pygame.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from nektoids.editor.beads import BEAD_RATE_AT_FULL
from nektoids.editor.circuit import Circuit
from nektoids.editor.devdrive import DT, TICKS_PER_FRAME
from nektoids.editor.layout import Rect
from nektoids.graph.board import Board, Kind
from nektoids.graph.dynamics import RATE_MAX, initial_state, step
from nektoids.graph.hexgrid import Cell

ENTRY_AREA: Rect = (0, 0, 360, 140)  # the circuit, in the box's own frame [px]
MARGIN = 1.3  # round the circuit, in its area, the meters beside it included [hex sizes]
SETTLE = 0.25  # [s] run before it shows, so that it opens at its steady rates
EYE_LOW, EYE_HIGH, EYE_PERIOD = 0.2, 0.9, 4.0  # the Eye's own reading, rising and falling [s]
ZONE = [(q, r) for q in range(-6, 6) for r in range(-2, 3)]  # room for every route

# Where the parts sit: one input, two inputs one over the other, the part, its thruster.
IN, UPPER, LOWER, PART, OUT = (-3, 0), (-2, -1), (-3, 1), (0, 0), (3, 0)
SENSOR, ITS_THRUSTER = (-3, 0), (3, 0)  # a sensor's own entry: it, then a thruster


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
        board = Board(ZONE)
        for part, cell in demo.parts:
            board.place(part, cell)
        for start, end in demo.wires:
            board.connect(board.node_at(start).id, board.node_at(end).id)
        self.kind, self.time = kind, 0.0
        self.circuit = Circuit(board, ENTRY_AREA, MARGIN)
        self.readings = np.array(demo.readings)
        self.state = initial_state(self.circuit.net)
        for _ in range(round(SETTLE / DT)):
            self.state = step(self.circuit.net, self.state, self.eyes()[None, :], DT)
        self.circuit.show(self.y)
        if kind in KEEP_TIME:
            self._keep_time(KEEP_TIME[kind])

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

    def _keep_time(self, ratio: float) -> None:
        """The beads out of the part leave as one comes in, and `ratio` times as often: wire 0
        comes in, wire 1 goes out. A bead reaches the end of wire 0 when its phase is
        `length × flux / speed`, modulo 1; wire 1's phase is set to wrap then."""
        beads = self.circuit.beads
        flux = BEAD_RATE_AT_FULL / RATE_MAX * float(self.circuit.flux[0])
        arrives = beads.lengths[0] * flux / beads.speed
        beads.phase[1] = (ratio * (beads.phase[0] - arrives)) % 1.0
