"""The swimmer at work (D-076): its motion is what the next tick does; its flames are as long at
any rate and as dense as the rate, and thin out at their end; the light it draws in comes from
the light, in its share of the reading; the specks stand still within a frame; no stream is
drawn shorter on screen than LEAST_STREAM."""

import math

import numpy as np
import pytest

from nektoids.editor.arena_view import OPENING_SCALE
from nektoids.editor.geometry import EYE_DISC, SQUARE_POINT
from nektoids.editor.marks import (
    FADE,
    FLAME_LENGTH,
    FLAME_SPECKS,
    INTAKE_LENGTH,
    INTAKE_SPECKS,
    LEAST_STREAM,
    SPECKS,
    SPIN_MOST,
    SPIN_RADIUS,
    TABLE_FRAMES,
    Specks,
    face,
    flames,
    intake,
    light_shares,
    motion,
    outlines,
    part_scale,
    spin_arc,
    stretch_at,
    velocity_segment,
)
from nektoids.graph.board import Refused
from nektoids.graph.network import Network
from nektoids.levels.sandbox import tutorial_board
from nektoids.sim.arena import BASE_RADIUS, LIGHT_RADIUS, Arena, Disc, Light
from nektoids.sim.optics import eye_rates
from nektoids.sim.world import parts, step

DT = 1.0 / 120.0
STILL = (0.0, 0.0, 0.0)  # a pose: at the origin, heading +x
FRAMES = 600


def crossed():
    """The tutorial board (eyes 0 upper looking NE, 1 lower looking SE; thrusters 2 upper, 3
    lower, facing E), each eye wired to the thruster across: Aggression's model."""
    board = tutorial_board()
    for a, b in ((0, 3), (1, 2)):
        assert not isinstance(board.connect(a, b), Refused)
    return board, Network.from_board(board)


def test_the_motion_drawn_is_what_the_next_tick_does():
    _, net = crossed()
    arena = Arena(lights=(Light(20.0, 4.0, 8.0),))
    pos, heading, radius = np.array([[3.0, 2.0]]), np.array([0.4]), np.ones(1)
    y = np.array([[[0.6, 0.1], [0.2, 0.4], [0.3, 0.0], [0.9, 0.5]]])  # (1, n, C), white and red
    vel, spin = motion(net, y[0], 1.0)
    after, turned, _, _ = step(arena, net, pos, heading, radius, y, DT)
    c, s = math.cos(0.4), math.sin(0.4)
    drawn = [c * vel[0] - s * vel[1], s * vel[0] + c * vel[1]]
    assert np.allclose(drawn, (after[0] - pos[0]) / DT)
    assert spin == pytest.approx((turned[0] - heading[0]) / DT)


def test_the_segment_leaves_the_rim_and_the_arc_the_heading():
    heading_north = math.pi / 2  # the body's forward, +x in its frame, is the plane's +y
    segment = velocity_segment((1.0, 2.0), heading_north, 1.0, np.array([3.0, 0.0]))
    assert np.allclose(segment, [[1.0, 3.0], [1.0, 6.0]])  # 3 u/s for 1 s, from the rim
    assert velocity_segment((0.0, 0.0), 0.0, 1.0, np.zeros(2)) is None
    arc = spin_arc((0.0, 0.0), 0.0, 1.0, 1.0)  # 1 rad/s for 2 s: 2 rad, counter-clockwise
    assert np.allclose(arc[0], [SPIN_RADIUS, 0.0])
    assert math.atan2(arc[-1][1], arc[-1][0]) == pytest.approx(2.0)
    fast = spin_arc((0.0, 0.0), 0.0, 1.0, -10.0)  # clockwise, past the longest arc
    assert np.allclose(
        fast[-1], SPIN_RADIUS * np.array([math.cos(-SPIN_MOST), math.sin(-SPIN_MOST)])
    )
    assert spin_arc((0.0, 0.0), 0.0, 1.0, 0.0) is None


def test_a_part_shows_its_face_where_the_board_has_it():
    board, net = crossed()
    scale = part_scale(board.cells)
    mount, facing = parts(net, net.eyes)
    middle, half = face(outlines(mount, facing, EYE_DISC, scale)[0])
    k = max(math.hypot(u, v) for u, v in EYE_DISC)  # the eye's disc, cut by a chord at k / 2
    look = np.array([math.cos(math.pi / 3), math.sin(math.pi / 3)])  # NE
    assert np.allclose(middle, mount[0] + scale * 0.5 * k * look)
    assert half == pytest.approx(scale * k * math.sin(math.pi / 3))


def test_a_flame_is_as_long_at_any_rate_and_as_dense_as_its_rate():
    board, net = crossed()
    mount, facing = parts(net, net.thrusters)
    outline = outlines(mount, facing, SQUARE_POINT, part_scale(board.cells))
    start, _ = face(outline[0])
    for rate, stretch in ((1.0, 1.0), (0.25, 1.0), (1.0, 2.0)):
        length = stretch * FLAME_LENGTH
        counts, farthest = [], 0.0
        for frame in range(FRAMES):
            rates = np.array([rate, 0.0])
            specks = flames(rates, facing, outline, STILL, 1.0, frame, stretch=stretch)
            along = start[0] - specks[:, 0]  # facing E, the flame goes out along -x
            assert np.all(along >= 0.0) and np.all(along <= length * (1.0 + FADE))
            counts.append(len(specks))
            farthest = max(farthest, float(along.max(initial=0.0)))
        assert farthest > 0.9 * length
        assert np.mean(counts) == pytest.approx(FLAME_SPECKS * rate, rel=0.2)
    assert len(flames(np.zeros(2), facing, outline, STILL, 1.0, 7)) == 0


def test_a_stream_thins_out_over_its_fade_as_dense_as_before_it():
    density, life, fade = 6.0, 16, 1.0 / 3.0
    gone, counts = [], []
    for seed in range(8):  # a table holds a hundred specks or so: eight, for the statistics
        table = Specks(seed)
        for frame in range(TABLE_FRAMES):
            went, left, _ = table.stream(density, frame, life, 0, fade)
            assert np.all(went + left <= 1.0 + fade) and np.all(went + left >= 1.0 - fade)
            gone.append(went)
            counts.append(len(went))
    assert np.mean(counts) == pytest.approx(density, rel=0.1)  # as many as with no fade
    edges = np.array([0.0, 1.0 - fade, 1.0, 1.0 + fade])
    within, _ = np.histogram(np.concatenate(gone), bins=edges)
    dense = within / np.diff(edges)
    _, middle, tail = dense / dense[0]  # linearly down: 1, then 3/4, then 1/4 on average
    assert middle == pytest.approx(0.75, abs=0.1) and tail == pytest.approx(0.25, abs=0.1)
    went, left, _ = SPECKS.stream(density, 5, life, 0)  # no fade: every speck ends at 1
    assert np.allclose(went + left, 1.0)


def test_the_specks_stand_still_within_a_frame():
    board, net = crossed()
    mount, facing = parts(net, net.thrusters)
    outline = outlines(mount, facing, SQUARE_POINT, part_scale(board.cells))
    rates = np.array([1.0, 1.0])
    now = flames(rates, facing, outline, STILL, 1.0, 41)
    assert np.array_equal(now, flames(rates, facing, outline, STILL, 1.0, 41))
    later = flames(rates, facing, outline, STILL, 1.0, 42)
    assert now.shape != later.shape or not np.allclose(now, later)


def test_the_light_is_drawn_in_from_the_light_in_its_share_of_the_reading():
    board, net = crossed()
    mount, facing = parts(net, net.eyes)
    outline = outlines(mount, facing, EYE_DISC, part_scale(board.cells))
    arena = Arena(lights=(Light(2.0, 6.0, 8.0),))  # ahead and to the left: the upper eye sees it
    shares, _ = light_shares(arena, mount, facing, STILL, 1.0)
    read = eye_rates(arena, np.zeros((1, 2)), np.zeros(1), np.ones(1), mount, facing)[0]
    assert shares[:, 0] == pytest.approx(read)
    assert shares[0, 0] > 0.0 and shares[1, 0] == 0.0  # the lower eye looks away
    end, _ = face(outline[0])
    way = (arena.light_xy[0] - end) / np.hypot(*(arena.light_xy[0] - end))
    counts = []
    for frame in range(FRAMES):
        specks = intake(arena, mount, facing, outline, STILL, 1.0, frame)
        out = (specks - end) @ way  # how far out toward the light
        assert np.all(out >= 0.0) and np.all(out <= INTAKE_LENGTH * (1.0 + FADE))
        counts.append(len(specks))
    assert np.mean(counts) == pytest.approx(INTAKE_SPECKS * shares[0, 0], rel=0.25)


def test_the_light_drawn_in_from_a_light_nearer_than_its_length_comes_from_the_light():
    board, net = crossed()
    mount, facing = parts(net, net.eyes)
    outline = outlines(mount, facing, EYE_DISC, part_scale(board.cells))
    end, _ = face(outline[0])
    arena = Arena(lights=(Light(1.4, 2.0, 8.0),))  # just ahead of the upper eye
    far = float(np.hypot(*(arena.light_xy[0] - end)))
    assert far - LIGHT_RADIUS < INTAKE_LENGTH
    way = (arena.light_xy[0] - end) / far
    for frame in range(0, FRAMES, 3):
        out = (intake(arena, mount, facing, outline, STILL, 1.0, frame) - end) @ way
        assert np.all(out >= 0.0) and np.all(out <= far - LIGHT_RADIUS + 1e-9)


def test_no_light_is_drawn_in_from_a_light_in_shadow():
    board, net = crossed()
    mount, facing = parts(net, net.eyes)
    outline = outlines(mount, facing, EYE_DISC, part_scale(board.cells))
    screen = Disc(0.6, 3.2, 1.0)  # across the way from the upper eye to the light
    arena = Arena(lights=(Light(2.0, 6.0, 8.0),), obstacles=(screen,))
    for frame in range(0, FRAMES, 7):
        assert len(intake(arena, mount, facing, outline, STILL, 1.0, frame)) == 0


def test_no_stream_is_drawn_shorter_on_screen_than_its_least():
    for scale in (2.0, 5.0, 9.4, 16.0, 48.0):  # [px/u]
        on_screen = FLAME_LENGTH * stretch_at(scale, 1.0) * scale
        assert on_screen == pytest.approx(max(LEAST_STREAM, FLAME_LENGTH * scale))
    assert stretch_at(OPENING_SCALE, BASE_RADIUS) == 1.0  # the run as it opens: as they are
