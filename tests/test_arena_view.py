import numpy as np
import pytest

from nektoids.editor.arena_view import (
    BRIGHTEST,
    DARKEST,
    FAN_DRIFT,
    FAN_SWING,
    GRAB,
    MAX_SCALE,
    MIN_SCALE,
    RAY_SWAY,
    SWAY_PERIOD,
    ArenaView,
    Rays,
    body_at,
    fit,
    frame,
    map_points,
    pan_view,
    polar_scale,
    ray_ends,
    smooth,
    tone,
    zoom_view,
)
from nektoids.sim.arena import Arena

ARENA = Arena(40.0, 38.0)
AREA = (0, 0, 640, 608)


# Seeing the arena


def test_the_arena_fills_its_area_at_16_px_per_u_with_y_up():
    view = fit(AREA, ARENA)
    assert view.scale == pytest.approx(16.0)
    assert view.to_screen(0.0, 0.0) == pytest.approx((0.0, 608.0))  # bottom left
    assert view.to_screen(40.0, 38.0) == pytest.approx((640.0, 0.0))  # top right
    assert view.rect(ARENA) == (0, 0, 640, 608)


def test_screen_and_world_are_inverse():
    view = ArenaView(12.5, (30.0, 500.0))
    for x, y in [(0.0, 0.0), (3.2, 17.9), (40.0, 38.0)]:
        assert view.to_world(*view.to_screen(x, y)) == pytest.approx((x, y))


def test_a_wide_arena_is_centred_vertically_at_the_same_scale_on_both_axes():
    view = fit(AREA, Arena(80.0, 20.0))
    left, top, width, height = view.rect(Arena(80.0, 20.0))
    assert view.scale == pytest.approx(8.0) and (left, width) == (0, 640)
    assert top + height / 2 == pytest.approx(304.0)


def test_the_map_grid_runs_row_by_row_from_the_top_left_and_stays_in_the_arena():
    points, (rows, cols) = map_points(ARENA, 0.25)  # 4 px at 16 px/u
    assert (rows, cols) == (152, 160) and points.shape == (rows * cols, 2)
    assert points[0].tolist() == pytest.approx([0.125, 37.875])  # half a cell from the corner
    assert points[-1].tolist() == pytest.approx([39.875, 0.125])
    assert points[:, 0].min() >= 0 and points[:, 0].max() <= 40.0
    assert points[:, 1].min() >= 0 and points[:, 1].max() <= 38.0


def test_zooming_keeps_the_pixel_it_is_about_still_and_stays_within_the_limits():
    view = fit(AREA, ARENA)
    about = (320.0, 304.0)
    under = view.to_world(*about)
    closer = zoom_view(view, 1.25, about)
    assert closer.scale == pytest.approx(20.0)
    assert closer.to_world(*about) == pytest.approx(under)
    assert zoom_view(view, 100.0, about).scale == MAX_SCALE
    assert zoom_view(view, 0.01, about).scale == MIN_SCALE


def test_the_hand_slides_the_view_without_zooming():
    view = pan_view(fit(AREA, ARENA), 30.0, -12.0)
    assert view.scale == pytest.approx(16.0)
    assert view.to_screen(0.0, 0.0) == pytest.approx((30.0, 596.0))


def test_centring_puts_the_mean_of_the_points_in_the_middle_and_shows_them_all():
    points = np.array([[5.0, 5.0], [35.0, 30.0], [20.0, 10.0]])
    view = frame(AREA, points, 3.0)
    assert view.to_screen(*points.mean(axis=0)) == pytest.approx((320.0, 304.0))
    for x, y in points:
        px, py = view.to_screen(x, y)
        assert 0 <= px <= 640 and 0 <= py <= 608
    close = frame(AREA, np.array([[20.0, 19.0], [20.5, 19.0]]), 0.1)
    assert close.scale == MAX_SCALE  # a tight group: as close as the view goes


# Grey levels


def test_smoothing_keeps_a_uniform_field_and_turns_a_step_into_a_ramp():
    assert np.array_equal(smooth(np.full((5, 7), 0.3)), np.full((5, 7), 0.3))
    step = np.zeros((3, 12))
    step[:, 6:] = 1.0
    row = smooth(step, passes=2)[1]
    assert np.all(np.diff(row) >= 0) and 0.0 < row[5] < row[6] < 1.0
    assert row[0] == 0.0 and row[-1] == 1.0  # far from the edge nothing changes


def test_tone_runs_from_darkest_to_brightest_and_rises_with_the_reading():
    greys = tone(np.array([[0.0, 0.01, 0.25, 1.0, 2.0]]))
    assert greys.dtype == np.uint8 and greys.flags.c_contiguous and greys.shape == (1, 5, 3)
    assert greys[0, 0].tolist() == DARKEST.tolist() and greys[0, 3].tolist() == BRIGHTEST.tolist()
    assert np.all(np.diff(greys[0, :4, 0].astype(int)) > 0)
    assert greys[0, 4].tolist() == BRIGHTEST.tolist()  # above RATE_MAX: as bright as it gets


@pytest.mark.parametrize(
    ("peak", "scale"),
    [(3.0, 1.0), (0.9, 1.0), (0.5, 0.5), (0.3, 0.5), (0.2, 0.25), (0.0, 1.0 / 256)],
)
def test_the_polar_plot_halves_its_circle_while_the_peak_still_fits(peak, scale):
    assert polar_scale(peak) == scale


# The mouse


def test_a_press_on_a_body_or_just_beside_it_finds_it_and_further_away_does_not():
    view = fit(AREA, ARENA)
    pos, radius = np.array([[10.0, 10.0], [12.5, 10.0]]), np.ones(2)
    on_first = view.to_screen(9.5, 10.0)
    assert body_at(view, pos, radius, on_first) == 0
    beside = view.to_screen(10.0, 10.0 + 1.0 + 0.5 * GRAB / view.scale)
    assert body_at(view, pos, radius, beside) == 0
    assert body_at(view, pos, radius, view.to_screen(11.3, 10.0)) == 1  # the nearest of two
    assert body_at(view, pos, radius, view.to_screen(10.0, 14.0)) is None
    assert body_at(view, np.zeros((0, 2)), np.zeros(0), on_first) is None


# Rays


def test_a_light_has_rays_in_proportion_to_its_power():
    assert Rays(np.array([8.0, 4.0, 0.1])).counts == [36, 18, 6]  # never fewer than 6


def test_rays_are_the_same_at_every_run_and_spread_evenly_round_the_light():
    one, two = Rays(np.array([8.0, 4.0])), Rays(np.array([8.0, 4.0]))
    for t in (0.0, 3.7, 120.0):
        angles = one.angles(0, t)
        assert np.array_equal(angles, two.angles(0, t))
        gaps = np.diff(np.concatenate((angles, [angles[0] + 2 * np.pi])))
        spacing = 2 * np.pi / 36
        assert np.all(gaps > (1 - 2 * RAY_SWAY) * spacing - 1e-12)
        assert np.all(gaps < (1 + 2 * RAY_SWAY) * spacing + 1e-12)


def test_rays_turn_slowly_however_they_wander():
    rays, dt = Rays(np.array([8.0])), 0.01
    fastest = np.radians(FAN_DRIFT[1] + FAN_SWING[1]) + RAY_SWAY * 2 * np.pi / 36 * (
        2 * np.pi / SWAY_PERIOD[0]
    )
    for t in np.arange(0.0, 60.0, 1.3):
        speed = np.abs(rays.angles(0, t + dt) - rays.angles(0, t)) / dt
        assert np.all(speed <= fastest * 1.01)
    assert fastest < np.radians(5.0)  # under 5°/s


def test_a_ray_stops_on_the_near_side_of_the_first_disc_it_meets():
    centres, radii = np.array([[20.0, 10.0], [30.0, 10.0]]), np.array([1.0, 2.0])
    (end,) = ray_ends((10.0, 10.0), np.array([0.0]), centres, radii, 40.0, 38.0)
    assert end.tolist() == pytest.approx([19.0, 10.0])


def test_a_ray_that_meets_no_disc_stops_at_the_wall():
    centres, radii = np.array([[20.0, 12.5]]), np.ones(1)  # 2.5 off the ray: missed
    ends = ray_ends(
        (10.0, 10.0), np.array([0.0, np.pi, np.pi / 2, -np.pi / 2]), centres, radii, 40.0, 38.0
    )
    expected = [[40.0, 10.0], [0.0, 10.0], [10.0, 38.0], [10.0, 0.0]]
    np.testing.assert_allclose(ends, expected, atol=1e-12)
    (corner,) = ray_ends(
        (0.0, 0.0), np.array([np.pi / 4]), np.zeros((0, 2)), np.zeros(0), 40.0, 38.0
    )
    assert corner.tolist() == pytest.approx([38.0, 38.0])  # the top wall comes first


def test_a_light_inside_a_body_shows_no_rays():
    ends = ray_ends(
        (10.0, 10.0), np.array([0.0, 2.0]), np.array([[10.5, 10.0]]), np.ones(1), 40.0, 38.0
    )
    np.testing.assert_allclose(ends, [[10.0, 10.0], [10.0, 10.0]])
