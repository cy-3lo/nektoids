"""A tick's senses and actions (D-203): each sensor reads by its kind's sense, each actuator acts
by its kind's action. world.py imports no pygame."""

import numpy as np

from nektoids.graph.board import Kind
from nektoids.graph.dynamics import SOURCE_RATE, given_rates, outputs
from nektoids.graph.hexgrid import NE, SW, E, hex_disc
from nektoids.graph.network import Network, body_mounts
from nektoids.sim.arena import Arena, Light
from nektoids.sim.motion import thrust
from nektoids.sim.optics import eye_rates
from nektoids.sim.world import parts, push, readings

EYE, SRC, SUM, THR = Kind.EYE, Kind.SOURCE, Kind.SUM, Kind.THRUSTER


def swimmers():
    """Two eyes and a source into a sum and two thrusters, on a body of 19 cells, two swimmers
    near a light."""
    kinds = [EYE, SRC, EYE, SUM, THR, THR]
    cells = [(1, -1), (0, 0), (1, 1), (-1, 0), (-2, 1), (-1, 2)]
    net = Network.from_edges(
        kinds,
        [(0, 3), (1, 3), (3, 4), (2, 5)],
        facing=[NE, None, SW, None, E, E],
        mount=body_mounts(hex_disc(2), cells),
    )
    pos, heading = np.array([[10.0, 8.0], [14.0, 11.0]]), np.array([0.3, 2.0])
    return Arena(lights=(Light(12.0, 10.0, 6.0),)), net, pos, heading, np.ones(2)


def test_the_eyes_read_the_light_and_a_source_its_steady_rate():
    arena, net, pos, heading, radius = swimmers()
    eyes = eye_rates(arena, pos, heading, radius, *parts(net, net.eyes))
    found = readings(arena, net, pos, heading, radius)
    assert np.array_equal(found, given_rates(net, eyes))  # bit for bit: what the run did
    assert found[:, net.sources].tolist() == [[SOURCE_RATE], [SOURCE_RATE]]
    assert not found[:, [3, 4, 5]].any()  # operators and actuators read nothing


def test_the_thrusters_push_by_their_outputs_and_alone_are_not_added_to_a_zero():
    arena, net, pos, heading, radius = swimmers()
    y = np.random.default_rng(0).uniform(0.0, 1.0, (2, net.n))
    rates = outputs(net, y)[:, net.thrusters]
    force, torque = push(net, y, radius)
    expected = thrust(rates, radius, *parts(net, net.thrusters))
    assert np.array_equal(force, expected[0]) and np.array_equal(torque, expected[1])
    bare = Network.from_edges([EYE, SUM], [(0, 1)])  # nothing acts: no force, no torque
    assert [a.tolist() for a in push(bare, np.ones((1, 2)), np.ones(1))] == [[[0.0, 0.0]], [0.0]]
