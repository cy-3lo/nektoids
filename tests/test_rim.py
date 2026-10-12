"""Thrusters act from the body's rim, the zone's outer ring (D-605): one inside may stand there,
idle, drawn dimmed, and pushes nothing. Imports no pygame."""

import numpy as np

from nektoids.graph.board import Board, Kind
from nektoids.graph.dynamics import CHANNELS
from nektoids.graph.hexgrid import E, hex_disc, on_rim
from nektoids.graph.network import Network
from nektoids.sim.world import push


def test_the_rim_is_the_zones_outer_ring_and_a_single_cell_is_all_rim():
    for radius in (1, 2, 3):
        zone = set(hex_disc(radius))
        rim = {cell for cell in zone if on_rim(zone, cell)}
        assert rim == {cell for cell in zone if cell not in set(hex_disc(radius - 1))}
    assert on_rim({(0, 0)}, (0, 0))


def test_a_thruster_may_stand_inside_the_rim_idle_and_only_an_actuator_is_idle():
    board = Board(hex_disc(2))
    inside = board.place(Kind.THRUSTER, (-1, 0), facing=E)
    rim = board.place(Kind.THRUSTER, (-2, 0), facing=E)
    source = board.place(Kind.SOURCE, (0, 0))
    assert board.idle(inside) and not board.idle(rim) and not board.idle(source)
    assert board.idle_count() == 1 and board.idle_note().startswith("A thruster inside the rim")
    board.place(Kind.THRUSTER, (0, 1), facing=E)
    assert board.idle_note().startswith("Two thrusters inside the rim push nothing")
    board.remove_node(board.node_at((0, 1)).id)
    assert board.move_node(inside.id, (-2, 1)).cell == (-2, 1) and board.idle_note() == ""


def test_an_idle_thruster_pushes_nothing_yet_keeps_its_rate():
    board = Board(hex_disc(2))
    source = board.place(Kind.SOURCE, (0, 0))
    inside = board.place(Kind.THRUSTER, (-1, 0), facing=E)
    board.connect(source.id, inside.id)
    net = Network.from_board(board)
    assert net.rim.tolist() == [False, False] and net.actions == ()
    assert len(net.thrusters) == 1  # still a thruster: its meter and beads show its rate
    force, torque = push(net, np.ones((1, net.n, CHANNELS)), np.ones(1))
    assert force.tolist() == [[0.0, 0.0]] and torque.tolist() == [0.0]
    board.move_node(inside.id, (-2, 0))
    force, _ = push(Network.from_board(board), np.ones((1, net.n, CHANNELS)), np.ones(1))
    assert force[0, 0] > 0.0
