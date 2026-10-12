"""The swimmer moved by the Stokes flow (D-601, D-602): checked against the prototype it was
ported from, and against the speeds D-602 gives. flow.py imports no pygame."""

import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest

from nektoids.sim import flow
from nektoids.sim.arena import Arena, Disc, Light

PROTOTYPE = Path(__file__).parents[1] / "prototypes" / "stokes" / "viewer" / "flow.py"
EMPTY = Arena()


def _alone(tips, forces, arena: Arena = EMPTY) -> flow.Swim:
    """One body of radius 1 at the origin, pushed by forces (k, 2) [f] at tips (k, 2) [u]."""
    tips, forces = np.array(tips, float)[None], np.array(forces, float)[None]
    return flow.swim(arena, np.zeros((1, 2)), np.ones(1), tips, forces)


def test_the_speeds_of_d602_two_at_the_sides_one_behind_one_turning():
    sides = _alone([[0, 1], [0, -1]], [[1, 0], [1, 0]])
    assert sides.velocity[0].tolist() == pytest.approx([7.125, 0.0]) and sides.spin[0] == 0.0
    assert _alone([[-1, 0]], [[1, 0]]).velocity[0].tolist() == pytest.approx([1.875, 0.0])
    turning = _alone([[1, 0]], [[0, 1]])
    assert turning.spin[0] == pytest.approx(37 / 12)  # 3.08 rad/s, against 2.25 before
    assert turning.velocity[0].tolist() == pytest.approx([0.0, 3.5625])


def test_a_force_inside_the_hydrodynamic_sphere_moves_nothing():
    inside = _alone([[0.2, 0.1], [0.0, 0.0]], [[1, 0], [0, 1]])
    assert inside.velocity.tolist() == [[0.0, 0.0]] and inside.spin.tolist() == [0.0]


@pytest.mark.skipif(not PROTOTYPE.exists(), reason="the prototype is not in this checkout")
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_it_solves_as_the_prototype_among_obstacles_of_any_radius(seed):
    spec = importlib.util.spec_from_file_location("prototype_flow", PROTOTYPE)
    prototype = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prototype)
    rng = np.random.default_rng(seed)
    xy = np.array([[4.0, 1.0], [-3.0, 5.0], [6.0, -4.0], [-5.0, -5.0]])
    radius = np.array([1.0, 2.0, 1.5, 1.0])
    arena = Arena(obstacles=tuple(Disc(x, y, r) for (x, y), r in zip(xy, radius, strict=True)))
    pos, heading = rng.uniform(-1.0, 1.0, 2), rng.uniform(0.0, 2.0 * math.pi)
    angle, facing = rng.uniform(0.0, 2.0 * math.pi, 3), rng.integers(0, 6, 3)
    rates = rng.uniform(0.0, 1.0, 3)
    expected = prototype.Flow(xy, radius).solve(pos, heading, rates, angle, facing).velocity
    ring, look = heading + angle, heading + math.pi / 3 * facing
    tips = pos + np.stack((np.cos(ring), np.sin(ring)), 1)
    forces = rates[:, None] * np.stack((np.cos(look), np.sin(look)), 1)
    swum = flow.swim(arena, pos[None], np.ones(1), tips[None], forces[None])
    found = [*swum.velocity[0], swum.spin[0]]
    np.testing.assert_allclose(found, expected, rtol=1e-12, atol=1e-14)


def test_a_mirrored_swimmer_moves_mirrored_and_a_row_does_not_depend_on_its_batch():
    arena = Arena(lights=(Light(5.0, 0.0, 6.0),), obstacles=(Disc(2.0, 4.0, 2.0),))
    tips = np.array([[[0.0, 1.0], [-1.0, 0.0]], [[0.0, -1.0], [-1.0, 0.0]]])
    forces = np.array([[[1.0, 0.0], [0.5, 0.5]], [[1.0, 0.0], [0.5, -0.5]]])
    pos = np.array([[0.0, 0.0], [0.0, 0.0]])
    mirror = Arena(lights=arena.lights, obstacles=(Disc(2.0, -4.0, 2.0),))
    one = flow.swim(arena, pos[:1], np.ones(1), tips[:1], forces[:1])
    other = flow.swim(mirror, pos[1:], np.ones(1), tips[1:], forces[1:])
    assert other.velocity[0].tolist() == pytest.approx([one.velocity[0, 0], -one.velocity[0, 1]])
    assert other.spin[0] == pytest.approx(-one.spin[0])
    both = flow.swim(arena, pos, np.ones(2), tips, forces)
    assert np.array_equal(both.velocity[:1], one.velocity)  # bit for bit (invariant 1)
    assert np.array_equal(both.spin[:1], one.spin)


def test_an_obstacle_changes_a_swimmers_motion_and_its_inverse_is_built_once():
    arena = Arena(obstacles=(Disc(2.0, 3.0, 2.0),))  # on the axis, by reversibility, no drift
    near = _alone([[0, 1], [0, -1]], [[1, 0], [1, 0]], arena)
    assert near.velocity[0, 0] != pytest.approx(7.125) and abs(near.velocity[0, 1]) > 1e-3
    moved = arena.moved(np.array([[0.1, 0.0]]))
    assert moved.clamped_inverse is arena.clamped_inverse  # handed on, not built again
