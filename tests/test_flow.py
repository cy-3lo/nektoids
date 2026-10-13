"""The swimmer moved by the Stokes flow (D-601, D-602): checked against the prototype it was
ported from, and against the speeds D-602 gives. flow.py imports no pygame."""

import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest

from nektoids.sim import flow
from nektoids.sim.arena import STIR_RADIUS, Arena, Disc, Light, Pump, Source
from nektoids.sim.motion import VISCOSITY

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


SIDES = ([[0.0, 1.0], [0.0, -1.0]], [[1.0, 0.0], [1.0, 0.0]])  # two side thrusters, full push


def test_a_light_holds_a_body_pushing_into_it_and_lets_one_slide_along_it():
    head_on = Arena(lights=(Light(2.0, 0.0, 4.0),))  # touching, ahead
    held = _alone(*SIDES, head_on)
    assert abs(held.velocity[0, 0]) < 1e-12 and held.contact[0, 0] < 0.0  # pushed back
    assert held.load[0, 0] == pytest.approx(2.0 + held.contact[0, 0])  # the fluid gets it too
    aside = Arena(lights=(Light(math.sqrt(2.0), math.sqrt(2.0), 4.0),))  # touching, at 45°
    slid = _alone(*SIDES, aside)
    normal = np.array([-1.0, -1.0]) / math.sqrt(2.0)  # from the light to the body
    assert slid.velocity[0] @ normal == pytest.approx(0.0, abs=1e-12)
    assert slid.velocity[0, 0] > 1.0  # along it, still
    apart = _alone(*SIDES, Arena(lights=(Light(2.5, 0.0, 4.0),)))  # 0.5 u off: free
    assert apart.contact.tolist() == [[0.0, 0.0]]


def test_a_body_pushing_an_obstacle_comes_to_rest_the_spring_holding_the_contact():
    from nektoids.graph.board import Kind
    from nektoids.graph.dynamics import initial_state
    from nektoids.graph.network import Network
    from nektoids.sim.contact import SPRING
    from nektoids.sim.world import step, swimming

    kinds = [Kind.SOURCE, Kind.DOUBLE, Kind.THRUSTER, Kind.THRUSTER]  # full rate on each
    mount = [[0.0, 0.0], [0.0, 0.0], [0.0, 1.0], [0.0, -1.0]]
    net = Network.from_edges(kinds, [(0, 1), (1, 2), (1, 3)], mount=mount)
    arena = Arena(obstacles=(Disc(6.0, 0.0, 2.0),))
    pos, heading, radius = np.array([[0.0, 0.0]]), np.zeros(1), np.ones(1)
    y = initial_state(net, 1)
    for _ in range(600):  # 5 s: there in well under one, then still
        pos, heading, y, arena = step(arena, net, pos, heading, radius, y, 1 / 120)
    swum = swimming(arena, net, pos, heading, radius, y)
    thrust = swum.load[0, 0] - swum.contact[0, 0]  # 1 f: a Source's rate on each
    assert abs(swum.velocity[0, 0]) < 1e-3  # at rest against it
    assert 0.5 * thrust < -swum.contact[0, 0] < thrust  # most of the thrust, by contact; the rest
    # through the fluid, which the obstacle's clamp takes (D-601)
    assert SPRING * arena.offsets[0, 0] == pytest.approx(-swum.contact[0, 0], rel=1e-3)  # k u = C


STILL = (np.zeros((0, 2)), np.zeros((0, 2)))  # no thrust: the body only drifts


def _drifting(arena: Arena, at) -> flow.Swim:
    """One thrustless body of radius 1 at `at` (2,) [u] in `arena`."""
    tips, forces = STILL
    return flow.swim(arena, np.array([at], float), np.ones(1), tips[None], forces[None])


def test_a_pump_carries_a_body_along_its_axis_twice_as_fast_as_beside_it_and_turns_it():
    arena = Arena(pumps=(Pump(0.0, 0.0, 0, 1.0),))  # pushes the fluid along +x
    ahead, beside, below = (_drifting(arena, at) for at in ((40.0, 0.0), (0.0, 40.0), (0.0, -40.0)))
    assert ahead.velocity[0, 1] == 0.0 and ahead.spin[0] == 0.0 and ahead.velocity[0, 0] > 0.0
    assert beside.velocity[0, 1] == pytest.approx(0.0, abs=1e-15)
    assert ahead.velocity[0, 0] / beside.velocity[0, 0] == pytest.approx(2.0, rel=1e-3)  # far field
    assert beside.spin[0] > 0.0 and below.spin[0] == pytest.approx(-beside.spin[0])  # omega / 2
    stokeslet = 1.0 / (8.0 * math.pi * VISCOSITY * 40.0)
    assert beside.velocity[0, 0] == pytest.approx(stokeslet, rel=1e-3)


def test_a_source_carries_a_body_radially_by_its_rate_and_does_not_turn_it():
    arena = Arena(sources=(Source(0.0, 0.0, 30.0),))
    out = _drifting(arena, (3.0, 4.0))
    radial = 30.0 / (4.0 * math.pi * 25.0) * np.array([0.6, 0.8])
    np.testing.assert_allclose(out.velocity[0], radial, rtol=1e-12)
    assert out.spin[0] == 0.0
    sink = _drifting(Arena(sources=(Source(0.0, 0.0, -30.0),)), (3.0, 4.0))
    np.testing.assert_allclose(sink.velocity[0], -radial, rtol=1e-12)


def test_a_sink_draws_a_body_in_and_holds_it_at_its_rim():
    from nektoids.sim.contact import collide

    arena = Arena(sources=(Source(0.0, 0.0, -50.0),))
    pos, radius, dt = np.array([[3.0, 0.0]]), np.ones(1), 1 / 120
    for _ in range(600):  # 5 s: drawn in in about 2
        swum = _drifting(arena, pos[0])
        pos, _ = collide(arena, arena.at_rest, pos + dt * swum.velocity, radius, dt, swum.pushes)
    assert np.hypot(*pos[0]) == pytest.approx(1.0 + STIR_RADIUS, abs=flow.TOUCH)
    assert abs(swum.velocity[0, 0]) < 1e-9 and swum.contact[0, 0] > 0.0  # held off, pushed out


def test_a_mirrored_plane_with_pumps_and_sources_moves_a_mirrored_swimmer_mirrored():
    light, obstacle = (Light(5.0, 0.0, 6.0),), (Disc(2.0, 4.0, 2.0),)
    arena = Arena(light, obstacle, pumps=(Pump(-3.0, 2.0, 1, 1.0),), sources=(Source(6, 5, 9),))
    mirror = Arena(
        light,
        (Disc(2.0, -4.0, 2.0),),
        pumps=(Pump(-3.0, -2.0, 5, 1.0),),
        sources=(Source(6, -5, 9),),
    )
    tips, forces = SIDES
    one = _alone(tips, forces, arena)
    other = _alone([[0.0, -1.0], [0.0, 1.0]], forces, mirror)
    assert other.velocity[0].tolist() == pytest.approx([one.velocity[0, 0], -one.velocity[0, 1]])
    assert other.spin[0] == pytest.approx(-one.spin[0]) and one.spin[0] != pytest.approx(0.0)
    on_axis = Arena(light, pumps=(Pump(-4.0, 0.0, 0, 1.0),), sources=(Source(-6.0, 0.0, 9),))
    straight = _alone(tips, forces, on_axis)
    assert straight.velocity[0, 1] == pytest.approx(0.0, abs=1e-15)
    assert straight.spin[0] == pytest.approx(0.0, abs=1e-15)


def test_the_lights_and_obstacles_hold_against_a_pump_solved_once():
    arena = Arena((Light(5.0, 0.0, 6.0),), (Disc(2.0, 4.0, 2.0),), pumps=(Pump(0, 0, 0, 1.0),))
    held = arena.stirred_reactions
    assert held.shape == (2, 3) and held[0, 0] < 0.0  # the light holds against the stream
    assert arena.moved(np.array([[0.1, 0.0]])).stirred_reactions is held  # handed on
    assert not Arena((Light(5.0, 0.0, 6.0),)).stirred_reactions.any()


def test_the_tracers_see_a_pump_and_are_kept_out_of_it():
    from nektoids.editor.flowfield import _outside

    arena = Arena(pumps=(Pump(0.0, 0.0, 0, 1.0),))
    far = np.array([100.0, 100.0])
    swum = _drifting(arena, far)
    x = np.array([[5.0, 0.0], [0.1, 0.0]])
    u = flow.flow_at(arena, x[:1], far, 1.0, swum)
    expected = flow.stirred(arena, x[:1], np.zeros(1))
    assert u[0, 0] == pytest.approx(expected[0][0], rel=1e-3) and u[0, 0] > 0.0
    assert np.hypot(*_outside(arena, far, 1.0, x)[1]) == pytest.approx(STIR_RADIUS)


def test_a_pump_or_a_source_may_not_touch_another_item():
    with pytest.raises(ValueError):
        Arena((Light(1.0, 0.0, 4.0),), pumps=(Pump(0.0, 0.0, 0, 1.0),))
    with pytest.raises(ValueError):
        Arena(pumps=(Pump(0.0, 0.0, 0, 1.0),), sources=(Source(0.9, 0.0, 1.0),))
    Arena(pumps=(Pump(0.0, 0.0, 0, 1.0),), sources=(Source(1.1, 0.0, 1.0),))


def test_rise_is_the_planes_divergence_negated_round_every_kind_of_singularity():
    arena = Arena(
        (Light(6.0, 0.0, 4.0),),
        (Disc(-5.0, 4.0, 2.0),),
        pumps=(Pump(0.0, -6.0, 1, 0.8),),
        sources=(Source(-6.0, -4.0, 30.0), Source(8.0, 6.0, -30.0)),
    )
    pos = np.array([0.5, 0.2])  # D-704
    tips, forces = np.array([[[0.0, 1.0], [0.0, -1.0]]]), np.array([[[1.0, 0.3], [1.0, 0.0]]])
    swum = flow.swim(arena, pos[None], np.ones(1), pos + tips, forces)
    x = np.random.default_rng(1).uniform(-10.0, 10.0, (400, 2))
    clear = [(pos, 1.6), ((6, 0), 1.5), ((-5, 4), 2.5), ((0, -6), 1.0), ((-6, -4), 1.0)]
    clear += [((8, 6), 1.0), ((0.5, 1.2), 0.6), ((0.5, -0.8), 0.6)]
    x = x[np.all([np.hypot(*(x - c).T) > r for c, r in clear], axis=0)]
    e = 1e-5

    def u(p):
        return flow.flow_at(arena, p, pos, 1.0, swum)

    div = u(x + [e, 0])[:, 0] - u(x - [e, 0])[:, 0] + u(x + [0, e])[:, 1] - u(x - [0, e])[:, 1]
    rise = flow.rise_at(arena, x, pos, 1.0, swum)
    np.testing.assert_allclose(rise, -div / (2 * e), atol=1e-7)
    assert np.abs(rise).max() > 0.1


AROUND = np.array([[1.0, 0.0], [-1.0, 0.0], [0.0, 1.0], [0.0, -1.0]])  # four Hairs on the rim
OUT = np.array([0, 3, 1, 4])  # each facing out: E, W, then 60° and 240°


def _hairs(arena: Arena, at, facing, swum=None) -> np.ndarray:
    """(k,): what Hairs at AROUND facing `facing` read on a body of radius 1 at `at`, heading E,
    in the amber channel."""
    pos = np.array([at], float)
    rates = flow.hair_rates(arena, pos, np.zeros(1), np.ones(1), AROUND, facing, swum)
    return rates[0, :, 0]


def test_a_hair_reads_the_flow_past_it_the_way_it_points_never_against_it():
    arena = Arena(pumps=(Pump(-6.0, 0.0, 0, 0.8),))  # D-705: water along +x, on the axis
    downstream = _hairs(arena, (0.0, 0.0), np.zeros(4, int))  # all facing E
    upstream = _hairs(arena, (0.0, 0.0), np.full(4, 3))  # all facing W
    assert np.all(downstream > 0.0) and np.all(upstream == 0.0)
    expected = flow.GAIN * flow.flow_at(
        arena, AROUND, np.array([50.0, 50.0]), 1.0, _drifting(arena, (50.0, 50.0))
    )
    np.testing.assert_allclose(downstream, expected[:, 0], rtol=1e-9)
    mirrored = _hairs(arena, (0.0, 0.0), np.array([0, 3, 1, 5]))  # the third and fourth mirrored
    assert mirrored[2] == pytest.approx(mirrored[3])


def test_still_water_reads_nothing_and_a_swimmer_hears_its_echo_off_a_light():
    tips, forces = np.array(SIDES[0])[None], np.array(SIDES[1])[None]
    alone = flow.swim(EMPTY, np.zeros((1, 2)), np.ones(1), tips, forces)
    assert not _hairs(EMPTY, (0.0, 0.0), OUT, alone).any()  # its own flow is not read
    lit = Arena(lights=(Light(4.0, 0.0, 4.0),))
    near = flow.swim(lit, np.zeros((1, 2)), np.ones(1), tips, forces)
    assert _hairs(lit, (0.0, 0.0), OUT, near).any()  # the light, held, pushes back on the fluid
    assert not _hairs(lit, (0.0, 0.0), OUT).any()  # no solve: no echo


def test_relative_a_swimmer_reads_its_head_wind_and_a_drifting_body_hardly_any(monkeypatch):
    monkeypatch.setattr(flow, "RELATIVE", True)  # D-700's other form, one switch away
    tips, forces = np.array(SIDES[0])[None], np.array(SIDES[1])[None]
    alone = flow.swim(EMPTY, np.zeros((1, 2)), np.ones(1), tips, forces)
    ahead, behind = _hairs(EMPTY, (0.0, 0.0), OUT, alone)[:2]
    assert ahead == 0.0 and behind == pytest.approx(flow.GAIN * alone.velocity[0, 0])
    arena = Arena(pumps=(Pump(-6.0, 0.0, 0, 0.8),))
    drifting = _drifting(arena, (0.0, 0.0))
    felt = _hairs(arena, (0.0, 0.0), np.zeros(4, int), drifting)
    monkeypatch.setattr(flow, "RELATIVE", False)
    carried = _hairs(arena, (0.0, 0.0), np.zeros(4, int), drifting)
    assert felt.max() < 0.25 * carried.min()  # it moves with the water it is in


def test_a_hair_on_a_board_reads_in_its_own_channel_where_the_body_has_moved():
    from nektoids.graph.board import Hue, Kind
    from nektoids.graph.dynamics import initial_state
    from nektoids.graph.network import Network
    from nektoids.sim.world import readings, swimming

    net = Network.from_edges(
        [Kind.HAIR, Kind.THRUSTER], [(0, 1)], [0, 0], mount=AROUND[:2], hues=[Hue.VIOLET, Hue.AMBER]
    )
    arena = Arena(pumps=(Pump(-6.0, 0.0, 0, 0.8),))
    pos, heading, radius = np.zeros((1, 2)), np.zeros(1), np.ones(1)
    swum = swimming(arena, net, pos, heading, radius, initial_state(net, 1))
    seen = readings(arena, net, pos, heading, radius, swum)
    assert seen[0, 0, 0] == 0.0 and seen[0, 0, 1] > 0.0  # violet: its channel alone
    assert not seen[0, 1].any()  # the thruster's row: not a sensor's
