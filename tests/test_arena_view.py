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
    edge_marker,
    frame,
    map_grid,
    map_points,
    pan_view,
    polar_scale,
    ray_ends,
    shown,
    smooth,
    tone,
    zoom_view,
)

AREA = (0, 0, 640, 608)
VIEW = ArenaView(16.0, (0.0, 608.0))  # (0, 0) at the area's bottom left, 16 px/u


# Seeing the arena


def test_the_view_shows_a_part_of_the_open_plane_with_y_up():
    assert VIEW.to_screen(0.0, 0.0) == pytest.approx((0.0, 608.0))  # bottom left
    assert VIEW.to_screen(40.0, 38.0) == pytest.approx((640.0, 0.0))  # top right
    assert shown(VIEW, AREA) == pytest.approx((0.0, 0.0, 40.0, 38.0))  # left, bottom, right, top
    assert shown(pan_view(VIEW, 160.0, 0.0), AREA) == pytest.approx((-10.0, 0.0, 30.0, 38.0))


def test_screen_and_world_are_inverse():
    view = ArenaView(12.5, (30.0, 500.0))
    for x, y in [(0.0, 0.0), (3.2, 17.9), (40.0, 38.0), (-7.0, -3.5)]:
        assert view.to_world(*view.to_screen(x, y)) == pytest.approx((x, y))


def test_the_map_grid_covers_what_is_shown_row_by_row_from_the_top_left():
    corner, cell, (rows, cols) = map_grid((0.0, 0.0, 40.0, 38.0), 0.25)  # 4 px at 16 px/u
    assert (corner, cell, (rows, cols)) == ((0.0, 38.0), 0.25, (152, 160))
    points = map_points(corner, cell, (rows, cols))
    assert points.shape == (rows * cols, 2)
    assert points[0].tolist() == pytest.approx([0.125, 37.875])  # half a cell from the corner
    assert points[-1].tolist() == pytest.approx([39.875, 0.125])


def test_the_map_grid_sits_on_whole_cells_and_coarsens_when_zoomed_out():
    corner, cell, (rows, cols) = map_grid((0.1, 0.1, 40.1, 38.1), 0.25)  # panned a little
    assert corner == pytest.approx((0.0, 38.25)) and cell == 0.25  # the same cells as before
    assert corner[0] + cols * cell >= 40.1 and corner[1] - rows * cell <= 0.1  # covering it
    _, cell, (_, cols) = map_grid((0.0, 0.0, 160.0, 152.0), 0.25, columns=160)  # at 4 px/u
    assert cell == 1.0 and cols == 160  # never more than 160 cells across


def test_zooming_keeps_the_pixel_it_is_about_still_and_stays_within_the_limits():
    view = VIEW
    about = (320.0, 304.0)
    under = view.to_world(*about)
    closer = zoom_view(view, 1.25, about)
    assert closer.scale == pytest.approx(20.0)
    assert closer.to_world(*about) == pytest.approx(under)
    assert zoom_view(view, 100.0, about).scale == MAX_SCALE
    assert zoom_view(view, 0.01, about).scale == MIN_SCALE


def test_the_hand_slides_the_view_without_zooming():
    view = pan_view(VIEW, 30.0, -12.0)
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


def test_a_swimmer_out_of_view_gets_a_marker_at_the_edge_pointing_to_it():
    assert edge_marker(VIEW, AREA, (20.0, 19.0)) is None  # in view: nothing
    (x, y), angle = edge_marker(VIEW, AREA, (60.0, 19.0), inset=10.0)  # off the right edge
    assert (x, y) == pytest.approx((630.0, 304.0)) and angle == pytest.approx(0.0)
    (x, y), angle = edge_marker(VIEW, AREA, (20.0, -100.0), inset=10.0)  # far below
    assert (x, y) == pytest.approx((320.0, 598.0)) and angle == pytest.approx(np.pi / 2)
    (x, y), _ = edge_marker(VIEW, AREA, (-200.0, 300.0), inset=10.0)  # off a corner
    assert 10.0 <= x <= 630.0 and 10.0 <= y <= 598.0  # still inside the area
    assert x == pytest.approx(10.0) or y == pytest.approx(10.0)  # on the inset edge


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
    view = VIEW
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
    (end,) = ray_ends((10.0, 10.0), np.array([0.0]), centres, radii, 50.0)
    assert end.tolist() == pytest.approx([19.0, 10.0])


def test_a_ray_that_meets_no_disc_goes_as_far_as_it_is_drawn():
    centres, radii = np.array([[20.0, 12.5]]), np.ones(1)  # 2.5 off the ray: missed
    angles = np.array([0.0, np.pi, np.pi / 2, -np.pi / 2])
    ends = ray_ends((10.0, 10.0), angles, centres, radii, 30.0)
    expected = [[40.0, 10.0], [-20.0, 10.0], [10.0, 40.0], [10.0, -20.0]]  # no walls (D-028)
    np.testing.assert_allclose(ends, expected, atol=1e-12)


def test_a_light_inside_a_body_shows_no_rays():
    ends = ray_ends((10.0, 10.0), np.array([0.0, 2.0]), np.array([[10.5, 10.0]]), np.ones(1), 30.0)
    np.testing.assert_allclose(ends, [[10.0, 10.0], [10.0, 10.0]])


def test_the_runs_extent_is_room_times_what_matters_and_the_view_stays_in_it():
    import numpy as np

    from nektoids.editor.arena_view import ROOM, extent, kept_in, shown, view_of

    points = np.array([[0.0, 0.0], [20.0, 10.0]])
    left, bottom, right, top = extent(points, 1.0, 2.0)
    assert right - left >= ROOM * 22.0 and top - bottom >= ROOM * 12.0  # D-066, D-101
    assert (right - left) / (top - bottom) == pytest.approx(2.0)
    area = (0, 0, 400, 200)
    whole = view_of(area, (left, bottom, right, top))
    assert shown(whole, area) == pytest.approx((left, bottom, right, top))
    far = ArenaView(whole.scale / 3, whole.origin)
    assert kept_in(far, area, (left, bottom, right, top)).scale == pytest.approx(whole.scale)
    near = ArenaView(whole.scale * 4, (whole.origin[0] + 9000, whole.origin[1]))
    sl, sb, sr, st = shown(kept_in(near, area, (left, bottom, right, top)), area)
    assert sl >= left - 1e-9 and sr <= right + 1e-9 and sb >= bottom - 1e-9 and st <= top + 1e-9


@pytest.mark.parametrize("points", [[[0.0, 0.0], [20.0, 4.0]], [[0.0, 0.0], [3.0, 18.0]]])
def test_the_run_opens_a_click_in_from_its_farthest_on_the_middle_of_what_matters(points):
    from nektoids.editor.arena_view import OPENING, ROOM, ZOOM_STEP, extent, kept_in, view_of

    points, area = np.array(points), (0, 0, 664, 506)
    aspect = area[2] / area[3]
    farthest = view_of(area, extent(points, 1.0, aspect))
    opening = view_of(area, extent(points, 1.0, aspect, OPENING))
    assert kept_in(opening, area, extent(points, 1.0, aspect)) == opening  # inside the overview
    assert opening.scale / farthest.scale == pytest.approx(ROOM / OPENING) == ZOOM_STEP
    middle = (points.min(axis=0) + points.max(axis=0)) / 2  # D-101
    assert opening.to_world(332, 253) == pytest.approx(tuple(middle))


def test_the_runs_extent_grows_by_union_and_a_frame_at_its_border_touches_it():
    # D-073: the overview's extent kept frame to frame, never less than it may be
    from nektoids.editor.arena_view import touches, union, widened

    a, b = (0.0, 0.0, 10.0, 5.0), (5.0, -2.0, 12.0, 4.0)
    assert union(a, b) == (0.0, -2.0, 12.0, 5.0) == union(b, a)
    wide = widened((0.0, 0.0, 10.0, 10.0), 2.0)  # twice as wide as high: widened about its middle
    assert wide == (-5.0, 0.0, 15.0, 10.0)
    tall = widened((0.0, 0.0, 10.0, 1.0), 2.0)
    assert tall == (0.0, -2.0, 10.0, 3.0)
    assert touches((0.0, 1.0, 5.0, 4.0), a) and touches((1.0, 1.0, 10.0, 4.0), a)
    assert not touches((1.0, 1.0, 9.0, 4.0), a)  # inside, clear of every side
