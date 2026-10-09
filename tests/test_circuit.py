import numpy as np

from nektoids.editor.circuit import Circuit
from nektoids.graph.board import Board
from nektoids.graph.hexgrid import hex_disc
from nektoids.levels.sandbox import tutorial_board

AREA = (640, 36, 320, 290)


def wired_tutorial() -> Board:
    board = tutorial_board()
    eye_up, eye_down, thruster_up, thruster_down = sorted(board.nodes)
    board.connect(eye_up, thruster_up)
    board.connect(eye_down, thruster_down)
    return board


def test_the_circuit_is_drawn_inside_its_area():
    circuit = Circuit(wired_tutorial(), AREA, 2.2)
    x, y, w, h = AREA
    for i in range(circuit.net.n):
        cx, cy = circuit.centre(i)
        assert x < cx < x + w and y < cy < y + h


def test_the_flux_follows_the_rates_and_only_advancing_moves_the_beads():
    circuit = Circuit(wired_tutorial(), AREA, 2.2)
    y = np.array([[0.5, 0.0], [0.25, 0.0], [0.5, 0.0], [0.25, 0.0]])  # eyes, then thrusters
    circuit.show(y)  # amber, in each channel (D-502)
    assert circuit.flux.tolist() == [[0.5, 0.0], [0.25, 0.0]]
    assert circuit.beads.phase == [0.0, 0.0, 0.5, 0.5]  # a stream a channel, violet half behind
    circuit.advance(y, 0.1)
    assert all(phase > 0.0 for phase in circuit.beads.phase[:2])
    assert circuit.beads.phase[2:] == [0.5, 0.5]  # no violet: its streams stand still
    assert circuit.stream(1, 1) == 3 and len(circuit.rates()) == 4


def test_an_empty_board_makes_an_empty_circuit():
    circuit = Circuit(Board(hex_disc(2)), AREA, 2.2)
    assert circuit.cells == [] and circuit.paths == [] and len(circuit.flux) == 0
    assert circuit.rates() == []
