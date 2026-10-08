"""The streams on a circuit (D-082, D-415): the specks of light each eye draws into its face and
the flames out of each thruster's back, as the run draws them (D-076), as many as the rates, at
most `reach` hex sizes from the face, which way the part faces. A part's entry and Diagnostic
draw them under the circuit. Never read by the model. Pure Python, no pygame.
"""

from __future__ import annotations

import math

import numpy as np

from nektoids.editor.circuit import Circuit
from nektoids.editor.geometry import EYE_DISC, SQUARE_POINT
from nektoids.editor.marks import (
    FADE,
    FLAME_LIFE,
    FLAME_SPECKS,
    FLAME_SPREAD,
    INTAKE_LIFE,
    INTAKE_SPECKS,
    INTAKE_SPREAD,
    SPECKS,
    face,
)
from nektoids.graph.dynamics import RATE_MAX
from nektoids.sim.optics import FACING_STEP

# Each face's middle along the part's axis, and half its width [hex sizes]: the eye's in front,
# the thruster's back behind (`marks.face`).
EYE_FACE, THRUSTER_BACK = face(np.array(EYE_DISC)), face(np.array(SQUARE_POINT))
FLAMES_AFTER = 8  # a circuit's flames' streams come after its eyes' in the specks' table
DIAGNOSTIC_REACH = 1.4  # [hex sizes] Diagnostic's streams, shorter than an entry's (D-415)

Point = tuple[float, float]


def light(circuit: Circuit, y: np.ndarray, frame: int, reach: float, first: int) -> list[Point]:
    """The specks of light drawn into each eye's face from `reach` ahead of it, as many as it
    reads (`marks.intake`) [px]; `first`: its streams in the specks' table."""
    (middle, _), half = EYE_FACE
    found = []
    for k, i in enumerate(circuit.net.eyes):
        share = float(y[i]) / RATE_MAX
        _, left, across = SPECKS.stream(INTAKE_SPECKS * share, frame, INTAKE_LIFE, first + k, FADE)
        found += _off_face(circuit, int(i), middle, half, left, across, INTAKE_SPREAD, 1.0, reach)
    return found


def flames(circuit: Circuit, y: np.ndarray, frame: int, reach: float, first: int) -> list[Point]:
    """The specks of each thruster's flame, out of its back, `reach` long at most, as many as
    its rate (`marks.flames`) [px]; `first`: its streams in the specks' table."""
    (middle, _), half = THRUSTER_BACK
    found = []
    for k, i in enumerate(circuit.net.thrusters):
        rate = float(y[i]) / RATE_MAX
        stream = first + FLAMES_AFTER + k
        gone, _, across = SPECKS.stream(FLAME_SPECKS * rate, frame, FLAME_LIFE, stream, FADE)
        found += _off_face(circuit, int(i), middle, half, gone, across, FLAME_SPREAD, -1.0, reach)
    return found


def _off_face(circuit, i, middle, half, along, across, spread, way, reach) -> list[Point]:
    """Specks off node i's face, `middle` hex sizes along its axis and `half` wide: `along` out
    of it in units of the stream's length, reach / (1 + FADE), so that the farthest speck is
    `reach` out; ahead of the part if `way` is +1, behind it if -1; `across` in [-1, 1],
    widening by `spread` [rad] either side."""
    size = circuit.view.size
    cx, cy = circuit.centre(i)
    facing = circuit.board.nodes[circuit.net.ids[i]].facing
    ax, ay = math.cos(FACING_STEP * facing), -math.sin(FACING_STEP * facing)  # on screen
    out = along * reach / (1.0 + FADE) * size
    wide = across * (half * size + out * math.tan(spread))
    x = cx + ax * middle * size + way * ax * out - ay * wide
    y = cy + ay * middle * size + way * ay * out + ax * wide
    return list(zip(x.tolist(), y.tolist(), strict=True))
