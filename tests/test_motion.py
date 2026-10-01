import math

import numpy as np
import pytest

from nektoids.graph.network import Network
from nektoids.levels.sandbox import tutorial_board
from nektoids.sim.motion import SPEED, advance, stokes, thrust

DT = 1.0 / 120.0
CENTRE = np.zeros((1, 2))  # one thruster at the centre of its body
TUTORIAL = Network.from_board(tutorial_board())
TUTORIAL_MOUNT = TUTORIAL.mount[TUTORIAL.thrusters]  # upper right, then lower right
TUTORIAL_FACING = np.array([TUTORIAL.facing[i] for i in TUTORIAL.thrusters])  # both E


def drive(rates, radius=1.0, mount=CENTRE, facing=(0,)):
    """Velocity (2,) in the body's frame and spin of one body under its thrusters."""
    radii = np.array([radius])
    force, torque = thrust(np.array([rates], dtype=np.float64), radii, mount, np.array(facing))
    vel, spin = stokes(force, torque, radii)
    return vel[0], float(spin[0])


def run(rates, ticks, mount=TUTORIAL_MOUNT, facing=TUTORIAL_FACING):
    """Positions (ticks + 1, 2) of one body from the origin, heading 0, under constant thrust."""
    vel, spin = drive(rates, mount=mount, facing=facing)
    vel, spin = vel[None, :], np.array([spin])
    pos, heading = np.zeros((1, 2)), np.zeros(1)
    path = [pos[0]]
    for _ in range(ticks):
        pos, heading = advance(pos, heading, vel, spin, DT)
        path.append(pos[0])
    return np.array(path), heading


# Stokes drag on a sphere


@pytest.mark.parametrize("facing", range(6))
def test_one_thruster_through_the_centre_moves_a_base_body_at_speed_along_its_facing(facing):
    vel, spin = drive([1.0], facing=(facing,))
    angle = math.pi / 3 * facing
    assert vel == pytest.approx([SPEED * math.cos(angle), SPEED * math.sin(angle)], abs=1e-12)
    assert spin == 0.0


def test_twice_the_radius_gives_half_the_speed_and_a_quarter_of_the_spin():
    mount = np.array([[0.0, 0.5]])  # off-centre: it pushes and turns
    vel, spin = drive([1.0], radius=1.0, mount=mount)
    vel_big, spin_big = drive([1.0], radius=2.0, mount=mount)
    assert vel_big == pytest.approx(vel / 2)
    assert spin_big == pytest.approx(spin / 4)


@pytest.mark.parametrize("radius", [1.0, 2.0])
def test_a_thruster_tangent_to_the_rim_turns_its_body_on_a_circle_of_four_thirds_its_radius(
    radius,
):
    vel, spin = drive([1.0], radius=radius, mount=np.array([[0.0, -1.0]]))  # right side, E
    assert spin > 0  # pushing forward on its right side turns the body left
    assert np.hypot(*vel) / spin == pytest.approx(4.0 / 3.0 * radius)


def test_a_thruster_pushing_at_the_centre_from_the_rim_does_not_turn_the_body():
    vel, spin = drive([1.0], mount=np.array([[1.0, 0.0]]), facing=(3,))  # front, pushing W
    assert vel == pytest.approx([-SPEED, 0.0], abs=1e-12)
    assert spin == pytest.approx(0.0, abs=1e-15)


def test_without_thrust_a_body_stops_at_once():
    vel, spin = drive([0.0, 0.0], mount=TUTORIAL_MOUNT, facing=TUTORIAL_FACING)
    assert np.all(vel == 0.0) and spin == 0.0


# The tutorial board (D-018)


def test_the_upper_thruster_turns_the_body_right_like_braitenbergs_left_wheel():
    _, upper = drive([1.0, 0.0], mount=TUTORIAL_MOUNT, facing=TUTORIAL_FACING)
    _, lower = drive([0.0, 1.0], mount=TUTORIAL_MOUNT, facing=TUTORIAL_FACING)
    assert upper < 0 < lower
    assert upper == -lower


def test_equal_thrust_on_both_sides_gives_a_straight_line():
    path, heading = run([0.6, 0.6], ticks=1000)
    assert heading[0] == 0.0
    assert np.all(path[:, 1] == 0.0)
    assert path[-1, 0] == pytest.approx(1000 * DT * 2 * 0.6 * SPEED)


# The integrator


def test_advance_turns_the_body_frame_velocity_by_the_heading():
    pos, heading = advance(
        np.zeros((1, 2)), np.array([math.pi / 2]), np.array([[1.0, 0.0]]), np.zeros(1), 0.5
    )
    assert pos[0] == pytest.approx([0.0, 0.5], abs=1e-15)
    assert heading[0] == math.pi / 2


def test_a_constant_thrust_keeps_the_body_on_a_circle_and_never_spirals_out():
    vel, spin = drive([1.0, 0.5], mount=TUTORIAL_MOUNT, facing=TUTORIAL_FACING)
    speed = float(np.hypot(*vel))
    turns = 10
    path, heading = run([1.0, 0.5], ticks=int(turns * 2 * math.pi / abs(spin) / DT))
    # centre of the circle the body would draw in continuous time, from the origin at heading 0
    centre = np.array([-vel[1], vel[0]]) / spin
    distance = np.hypot(*(path - centre).T)
    assert abs(heading[0]) > turns * 2 * math.pi - abs(spin) * DT
    assert np.all(np.abs(distance - speed / abs(spin)) < speed * DT)
