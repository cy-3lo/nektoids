"""The streams on a circuit (D-082, D-415): light into each eye's face, flames out of each
thruster's back, as many as the rates. streams.py imports no pygame."""

import math

import numpy as np

from nektoids.editor import streams
from nektoids.editor.circuit import Circuit
from nektoids.graph.board import Board, Kind
from nektoids.graph.dynamics import RATE_MAX
from nektoids.graph.hexgrid import NW, E, hex_disc

REACH = 1.4


def _circuit(facing: int) -> Circuit:
    board = Board(hex_disc(2))
    board.place(Kind.EYE, (1, 0), facing=facing)
    board.place(Kind.THRUSTER, (-1, 0), facing=facing)
    return Circuit(board, (0, 0, 400, 300), 0.6)


def _rates(circuit: Circuit, rate: float) -> np.ndarray:
    return np.full(len(circuit.net.ids), rate * RATE_MAX)


def test_light_comes_into_an_eyes_face_and_flames_leave_a_thrusters_back():
    circuit = _circuit(E)
    eye, thruster = (
        circuit.centre(int(i)) for i in (circuit.net.eyes[0], circuit.net.thrusters[0])
    )
    for frame in range(0, 200, 7):
        light = streams.light(circuit, _rates(circuit, 1.0), frame, REACH, 0)
        flames = streams.flames(circuit, _rates(circuit, 1.0), frame, REACH, 0)
        assert all(x > eye[0] for x, _ in light)  # ahead of the eye, facing E: to the right
        assert all(x < thruster[0] for x, _ in flames)  # behind the thruster: to the left
        size = circuit.view.size
        farthest = (REACH + 1.0) * size  # the reach, from a face within a hex size of its centre
        assert all(math.dist(p, eye) <= farthest for p in light)
        assert all(math.dist(p, thruster) <= farthest for p in flames)


def test_the_streams_turn_with_the_part():
    circuit = _circuit(NW)
    eye = circuit.centre(int(circuit.net.eyes[0]))
    light = [
        p for f in range(0, 200, 7) for p in streams.light(circuit, _rates(circuit, 1), f, 1, 0)
    ]
    assert light and all(y < eye[1] for _, y in light)  # ahead of an eye facing NW: above it


def test_as_many_specks_as_the_rate_none_at_rest():
    circuit = _circuit(E)

    def count(rate: float) -> int:
        y = _rates(circuit, rate)
        frames = range(0, 251)
        return sum(len(streams.flames(circuit, y, f, REACH, 0)) for f in frames)

    assert count(0.0) == 0
    assert 1.6 < count(1.0) / count(0.5) < 2.4
