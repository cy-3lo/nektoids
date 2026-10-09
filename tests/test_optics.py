import math

import numpy as np
import pytest

from nektoids.graph.network import Network
from nektoids.levels.sandbox import tutorial_board
from nektoids.sim import optics
from nektoids.sim.arena import Arena, Colour, Disc, Light
from nektoids.sim.optics import (
    R_MIN,
    add_lights,
    angular_irradiance,
    exposure,
    eye_poses,
    light_map,
    still_light,
    visible,
)


def eye_rates(*args):
    """`optics.eye_rates` under white lights, as every test here has: the same in both channels
    (D-506), the amber one returned."""
    rates = optics.eye_rates(*args)
    assert np.array_equal(rates[..., 0], rates[..., 1])
    return rates[..., 0]


LIGHT = Light(50.0, 30.0, power=10.0)
CENTRE = np.zeros((1, 2))  # one eye at the centre of its body
AHEAD = np.array([0])  # ... looking forward (E)


def one_eye(arena, x, y, heading=0.0, radius=1.0, mount=CENTRE, facing=AHEAD):
    """The rate of the eyes of one body at (x, y); a float if it has one eye."""
    rates = eye_rates(
        arena, np.array([[x, y]]), np.array([heading]), np.array([radius]), mount, facing
    )[0]
    return float(rates[0]) if len(rates) == 1 else rates


def lit(*obstacles, lights=(LIGHT,)):
    return Arena(lights, obstacles)


# 1/r, cosine, cap


def test_an_eye_looking_at_the_light_reads_half_as_much_twice_as_far():
    assert one_eye(lit(), 30.0, 30.0) == pytest.approx(10.0 / 20.0)
    assert one_eye(lit(), 10.0, 30.0) == pytest.approx(10.0 / 40.0)


def test_an_eye_turned_60_degrees_away_reads_half_and_one_looking_away_reads_nothing():
    straight = one_eye(lit(), 30.0, 30.0)
    assert one_eye(lit(), 30.0, 30.0, heading=math.pi / 3) == pytest.approx(straight / 2)
    assert one_eye(lit(), 30.0, 30.0, heading=-math.pi / 3) == pytest.approx(straight / 2)
    assert one_eye(lit(), 30.0, 30.0, heading=math.pi / 2) == pytest.approx(0.0, abs=1e-15)
    assert one_eye(lit(), 30.0, 30.0, heading=math.pi) == 0.0


def test_close_to_the_light_an_eye_saturates():
    assert one_eye(lit(), 45.0, 30.0) == 1.0  # 10 / 5 = 2, capped
    assert one_eye(lit(), 50.0 - R_MIN / 2, 30.0) == 1.0  # nearer than R_MIN: no 1/0


# Shadows


def test_an_obstacle_on_the_ray_shadows_the_eye_and_one_just_off_it_does_not():
    assert one_eye(lit(Disc(40.0, 30.0)), 30.0, 30.0) == 0.0
    assert one_eye(lit(Disc(40.0, 30.9)), 30.0, 30.0) == 0.0  # 0.9 < 1 from the ray
    assert one_eye(lit(Disc(40.0, 31.5)), 30.0, 30.0) == one_eye(lit(), 30.0, 30.0)


def test_an_obstacle_behind_the_eye_or_behind_the_light_casts_no_shadow_on_it():
    assert one_eye(lit(Disc(25.0, 30.0)), 30.0, 30.0) == one_eye(lit(), 30.0, 30.0)
    assert one_eye(lit(Disc(55.0, 30.0)), 30.0, 30.0) == one_eye(lit(), 30.0, 30.0)


def test_a_body_never_shadows_its_own_eyes():
    """Eyes all round the rim, each looking at the light through the body (D-018)."""
    rim = np.array([[math.cos(a), math.sin(a)] for a in np.arange(6) * math.pi / 3])
    heading = 0.0  # the light is due E; facing E
    rates = one_eye(lit(), 30.0, 30.0, heading, 1.0, rim, np.zeros(6, dtype=int))
    points, looks = eye_poses(
        np.array([[30.0, 30.0]]), np.array([heading]), np.ones(1), rim, np.zeros(6, dtype=int)
    )
    alone = exposure(points[0], looks[0], lit().light_xy, lit().light_power)[:, 0]
    assert np.all(rates > 0) and rates.tolist() == pytest.approx(alone.tolist())


def test_one_body_shadows_the_eye_of_another():
    """A at (30, 30), B at (40, 30), light at (50, 30): B stands in A's light, not A in B's."""
    pos = np.array([[30.0, 30.0], [40.0, 30.0]])
    rates = eye_rates(lit(), pos, np.zeros(2), np.ones(2), CENTRE, AHEAD)
    assert rates[0, 0] == 0.0
    assert rates[1, 0] == pytest.approx(10.0 / 10.0)


# Several lights


def test_two_lights_add_and_shadowing_one_leaves_the_other():
    """An eye at (30, 30) looking N, lights at (20, 40) and (40, 40): 45° off, 10 sqrt 2 away."""
    lights = (Light(20.0, 40.0, 5.0), Light(40.0, 40.0, 5.0))
    each = 5.0 * math.cos(math.pi / 4) / (10.0 * math.sqrt(2.0))  # = 1/4
    assert one_eye(lit(lights=lights), 30.0, 30.0, math.pi / 2) == pytest.approx(2 * each)
    shaded = lit(Disc(35.0, 35.0), lights=lights)  # on the way to the right light
    assert one_eye(shaded, 30.0, 30.0, math.pi / 2) == pytest.approx(each)


def test_without_lights_every_eye_reads_nothing():
    assert one_eye(Arena(), 30.0, 30.0) == 0.0


# Batches and consistency


def test_a_body_reads_the_same_bits_alone_or_among_others():
    """Three tutorial swimmers round the light, far enough apart to cast no shadow on each other."""
    net = Network.from_board(tutorial_board())
    mount, facing = net.mount[net.eyes], np.array([net.facing[i] for i in net.eyes])
    arena = lit(Disc(20.0, 10.0), Disc(80.0, 50.0))
    angles = np.array([0.3, 2.4, 4.5])
    pos = np.column_stack((50.0 + 18.0 * np.cos(angles), 30.0 + 18.0 * np.sin(angles)))
    heading = np.random.default_rng(0).uniform(0.0, 2.0 * math.pi, size=3)
    together = eye_rates(arena, pos, heading, np.ones(3), mount, facing)
    for i in range(3):
        alone = eye_rates(arena, pos[i : i + 1], heading[i : i + 1], np.ones(1), mount, facing)
        assert np.array_equal(together[i], alone[0])
    assert np.all(together.max(axis=1) > 0)  # each of them sees the light with some eye


def test_the_light_map_reads_what_an_eye_looking_at_the_light_reads():
    arena = lit(Disc(40.0, 30.0), Disc(60.0, 20.0), Disc(30.0, 45.0))
    points = np.random.default_rng(1).uniform((0.0, 0.0), (100.0, 60.0), size=(40, 2))
    points = np.vstack((points, [[35.0, 30.0]]))  # in the shadow of the disc at (40, 30)
    shown = light_map(arena, points, np.zeros((0, 2)), np.zeros(0))
    for (x, y), value in zip(points, shown, strict=True):
        towards = math.atan2(LIGHT.y - y, LIGHT.x - x)
        assert one_eye(arena, x, y, towards) == pytest.approx(value, abs=1e-12)
    assert shown[-1] == 0.0


def test_a_body_casts_a_shadow_on_the_light_map():
    behind = np.array([[36.0, 30.0], [36.0, 36.0]])  # behind the body at (40, 30), and off it
    shown = light_map(lit(), behind, np.array([[40.0, 30.0]]), np.ones(1))
    assert shown[0] == 0.0 and shown[1] > 0.0


# Pieces


def test_eye_poses_turn_the_mount_and_the_look_with_the_heading():
    points, looks = eye_poses(
        np.array([[10.0, 20.0]]),
        np.array([math.pi / 2]),
        np.array([2.0]),
        np.array([[1.0, 0.0]]),
        np.array([1]),
    )
    assert points[0, 0].tolist() == pytest.approx([10.0, 22.0])  # forward is now +y
    assert looks[0, 0].tolist() == pytest.approx([math.cos(math.radians(150)), 0.5])


def test_a_grazing_ray_passes_and_an_empty_arena_blocks_nothing():
    point, light = np.array([[0.0, 0.0]]), np.array([[10.0, 0.0]])
    assert visible(point, light, np.array([[5.0, 1.0]]), np.ones(1))[0, 0]
    assert visible(point, light, np.zeros((0, 2)), np.zeros(0)).tolist() == [[True]]


def test_lights_add_only_where_they_are_seen():
    given = np.array([[0.25, 0.5], [0.25, 0.5]])
    seen = np.array([[True, False], [True, True]])
    assert add_lights(given, seen).tolist() == [0.25, 0.75]


# What no level should hold


@pytest.mark.parametrize(
    ("lights", "obstacles", "message"),
    [
        ((Light(50.0, 30.0, 0.0),), (), "power"),
        ((), (Disc(50.0, 30.0, 0.0),), "radius"),
        ((Light(50.0, 30.0, 1.0),), (Disc(50.5, 30.0),), "touches an obstacle"),
        ((Light(50.0, 30.0, 1.0),), (Disc(51.9, 30.0),), "touches an obstacle"),  # 1.9 < 1 + 1
    ],
)
def test_impossible_arenas_are_refused(lights, obstacles, message):
    with pytest.raises(ValueError, match=message):
        Arena(lights, obstacles)


# The light at a point, facing each way


def test_facing_each_way_one_light_gives_a_cosine_lobe_pointing_at_it():
    angles = np.radians(np.arange(0.0, 360.0, 30.0))
    curve = angular_irradiance(lit(), np.array([30.0, 30.0]), angles, np.zeros((0, 2)), np.zeros(0))
    expected = 10.0 / 20.0 * np.maximum(np.cos(angles), 0.0)  # the light is due E, 20 away
    assert curve.tolist() == pytest.approx(expected.tolist(), abs=1e-15)


def test_a_shadowed_light_gives_nothing_facing_any_way():
    angles = np.radians(np.arange(0.0, 360.0, 30.0))
    point = np.array([30.0, 30.0])
    curve = angular_irradiance(lit(Disc(40.0, 30.0)), point, angles, np.zeros((0, 2)), np.zeros(0))
    assert np.all(curve == 0.0)


def test_each_eye_reads_its_own_polar_plot_at_the_angle_it_looks():
    net = Network.from_board(tutorial_board())
    mount, facing = net.mount[net.eyes], np.array([net.facing[i] for i in net.eyes])
    arena = lit(Disc(40.0, 30.0), Disc(45.0, 36.0), lights=(LIGHT, Light(20.0, 50.0, 6.0)))
    pos, radius = np.array([[30.0, 33.0], [37.0, 31.0]]), np.ones(2)
    heading = np.array([0.4, 2.0])
    rates = eye_rates(arena, pos, heading, radius, mount, facing)
    points, looks = eye_poses(pos, heading, radius, mount, facing)
    for k in range(2):
        for e in range(len(facing)):
            angle = np.array([np.arctan2(looks[k, e, 1], looks[k, e, 0])])
            curve = angular_irradiance(arena, points[k, e], angle, pos, radius, own=k)
            assert min(1.0, float(curve[0])) == pytest.approx(rates[k, e], abs=1e-12)


def test_the_light_map_from_what_never_moves_is_the_same_bit_for_bit():
    arena = lit(Disc(40.0, 30.0), Disc(60.0, 20.0), lights=(LIGHT, Light(10.0, 10.0, 5.0)))
    points = np.random.default_rng(2).uniform((0.0, 0.0), (100.0, 60.0), size=(200, 2))
    pos, radius = np.array([[30.0, 30.0], [70.0, 40.0]]), np.ones(2)
    kept = still_light(arena, points)
    assert np.array_equal(
        light_map(arena, points, pos, radius, kept), light_map(arena, points, pos, radius)
    )


def test_an_eye_reads_in_each_channel_the_lights_that_shine_in_it():
    lights = (  # D-506: white shines in both, amber and violet in one each
        Light(10.0, 0.0, 4.0, Colour.AMBER),
        Light(10.0, 2.0, 4.0, Colour.VIOLET),
        Light(10.0, -2.0, 4.0, Colour.WHITE),
    )
    rates = optics.eye_rates(
        Arena(lights), np.zeros((1, 2)), np.zeros(1), np.ones(1), CENTRE, AHEAD
    )
    alone = [
        optics.eye_rates(Arena((light,)), np.zeros((1, 2)), np.zeros(1), np.ones(1), CENTRE, AHEAD)
        for light in lights
    ]
    amber, violet, white = (float(r[0, 0, c]) for r, c in zip(alone, (0, 1, 0), strict=True))
    assert rates[0, 0, 0] == pytest.approx(amber + white)
    assert rates[0, 0, 1] == pytest.approx(violet + white)
    assert alone[0][0, 0, 1] == 0.0 and alone[1][0, 0, 0] == 0.0  # each in its own channel
    assert Colour.WHITE.channels == (True, True) and Colour.VIOLET.channels == (False, True)
