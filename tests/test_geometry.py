"""Wire drawing geometry. geometry.py imports no pygame, so this runs headless."""

import math

import pytest

from nektoids.editor.geometry import (
    body_circle,
    cumulative_lengths,
    distance_to_polyline,
    edge_midpoint,
    filled_to,
    nearest_wire,
    point_at,
    symbol_corners,
    turn_centre,
    wire_arrows,
    wire_points,
)
from nektoids.graph.board import Wire
from nektoids.graph.hexgrid import NE, NW, SQRT3, E, W, hex_disc, to_pixel
from nektoids.graph.network import body_disc

SIZE = 40.0  # [px]
ORIGIN = (100.0, 100.0)  # [px]
CELL = (3, 3)


def test_edge_midpoints_sit_half_way_to_each_neighbour():
    x, y = to_pixel(CELL, SIZE, ORIGIN)
    for edge in range(6):
        mx, my = edge_midpoint(CELL, edge, SIZE, ORIGIN)
        assert math.hypot(mx - x, my - y) == pytest.approx(0.5 * SQRT3 * SIZE)


@pytest.mark.parametrize(
    ("entry", "exit_", "radius"),
    [
        (W, NW, 0.5),  # sharp 120° turn: adjacent edges, arc about their shared corner
        (W, NE, 1.5),  # gentle 60° turn: one edge between, arc centred outside the cell
    ],
)
def test_turns_are_arcs_tangent_to_both_edges(entry, exit_, radius):
    centre = turn_centre(CELL, entry, exit_, SIZE, ORIGIN)
    a = edge_midpoint(CELL, entry, SIZE, ORIGIN)
    b = edge_midpoint(CELL, exit_, SIZE, ORIGIN)
    assert math.dist(centre, a) == pytest.approx(radius * SIZE)
    assert math.dist(centre, b) == pytest.approx(radius * SIZE)
    # Tangent to the wire: the radius at a midpoint runs along the edge, i.e. perpendicular to
    # the edge's normal (the line from the cell centre to the midpoint).
    cx, cy = to_pixel(CELL, SIZE, ORIGIN)
    for m in (a, b):
        normal = (m[0] - cx, m[1] - cy)
        radial = (m[0] - centre[0], m[1] - centre[1])
        assert normal[0] * radial[0] + normal[1] * radial[1] == pytest.approx(0.0, abs=1e-9)


def test_wire_points_run_centre_to_centre_and_arc_inside_the_turning_cell():
    path = ((1, 3), (2, 3), (3, 3), (3, 2))  # straight through (2, 3), then turns in (3, 3)
    points = wire_points(path, SIZE, ORIGIN)
    assert points[0] == pytest.approx(to_pixel((1, 3), SIZE, ORIGIN))
    assert points[-1] == pytest.approx(to_pixel((3, 2), SIZE, ORIGIN))
    cx, cy = to_pixel(CELL, SIZE, ORIGIN)
    arc = points[3:-1]  # after source centre and the two midpoints of (2, 3)
    assert all(math.hypot(x - cx, y - cy) <= SIZE for x, y in arc)
    assert arc[0] == pytest.approx(edge_midpoint(CELL, W, SIZE, ORIGIN))
    assert arc[-1] == pytest.approx(edge_midpoint(CELL, NW, SIZE, ORIGIN))


def test_adjacent_components_are_joined_by_one_segment():
    points = wire_points(((0, 0), (1, 0)), SIZE, ORIGIN)
    assert points == [to_pixel((0, 0), SIZE, ORIGIN), to_pixel((1, 0), SIZE, ORIGIN)]


def test_distance_to_polyline():
    square = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)]
    assert distance_to_polyline((5.0, 3.0), square) == pytest.approx(3.0)
    assert distance_to_polyline((12.0, 5.0), square) == pytest.approx(2.0)
    assert distance_to_polyline((-3.0, -4.0), square) == pytest.approx(5.0)


def test_a_wire_between_neighbours_is_found_between_their_shapes():
    # Two components side by side: the wire crosses no free cell, only their shared edge.
    wire = Wire(0, 1, ((1, 3), (2, 3)))
    x, y = edge_midpoint((1, 3), E, SIZE, ORIGIN)
    assert nearest_wire((x - 3.0, y + 2.0), [wire], SIZE, ORIGIN, within=8.0) == wire
    assert nearest_wire((x, y + 20.0), [wire], SIZE, ORIGIN, within=8.0) is None


def test_nearest_wire_picks_the_closer_of_two_crossing_wires():
    across = Wire(0, 1, ((1, 3), (2, 3), (3, 3), (4, 3)))  # straight E-W through (3, 3)
    diagonal = Wire(2, 3, ((2, 4), (3, 3), (4, 2)))  # straight SW-NE through (3, 3)
    cx, cy = to_pixel((3, 3), SIZE, ORIGIN)
    assert nearest_wire((cx + 12.0, cy + 1.0), [across, diagonal], SIZE, ORIGIN, 8.0) == across
    ne = edge_midpoint((3, 3), NE, SIZE, ORIGIN)
    near_ne = (0.5 * (cx + ne[0]), 0.5 * (cy + ne[1]))
    assert nearest_wire(near_ne, [across, diagonal], SIZE, ORIGIN, 8.0) == diagonal


def test_one_arrow_per_crossed_cell_pointing_downstream():
    path = ((1, 3), (2, 3), (3, 3), (3, 2))  # straight E through (2, 3), then turns in (3, 3)
    arrows = wire_arrows(path, SIZE, ORIGIN)
    assert len(arrows) == 2  # the two free cells; none on the components
    (at, angle), (arc_at, arc_angle) = arrows
    cx, cy = to_pixel((2, 3), SIZE, ORIGIN)
    assert angle == pytest.approx(0.0)  # heading E
    assert at[0] > cx and at[1] == pytest.approx(cy)  # past the centre, on the wire
    # On the turn: on the arc, tangent to it, heading on towards NW (up the screen).
    centre = turn_centre(CELL, W, NW, SIZE, ORIGIN)
    assert math.dist(centre, arc_at) == pytest.approx(0.5 * SIZE)
    radial = (arc_at[0] - centre[0], arc_at[1] - centre[1])
    tangent = (math.cos(arc_angle), math.sin(arc_angle))
    assert radial[0] * tangent[0] + radial[1] * tangent[1] == pytest.approx(0.0, abs=1e-6)
    assert math.sin(arc_angle) < 0  # y down: moving up


def test_crossing_wires_keep_distinct_arrows():
    across = ((1, 3), (2, 3), (3, 3), (4, 3))
    diagonal = ((2, 4), (3, 3), (4, 2))
    a = dict(zip([(2, 3), (3, 3)], [p for p, _ in wire_arrows(across, SIZE, ORIGIN)], strict=True))
    ((b, _),) = wire_arrows(diagonal, SIZE, ORIGIN)
    assert math.dist(a[(3, 3)], b) > 0.2 * SIZE


# Walking along a wire


def test_cumulative_lengths_start_at_zero_and_end_at_the_length():
    assert cumulative_lengths([(0.0, 0.0), (3.0, 4.0), (3.0, 10.0)]) == [0.0, 5.0, 11.0]


def test_a_point_at_a_distance_lies_on_the_polyline_and_clamps_at_its_ends():
    points = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]
    cumulative = cumulative_lengths(points)
    assert point_at(points, cumulative, 0.5) == (0.5, 0.0)
    assert point_at(points, cumulative, 1.0) == (1.0, 0.0)  # exactly at the corner
    assert point_at(points, cumulative, 1.5) == (1.0, 0.5)
    assert point_at(points, cumulative, -3.0) == (0.0, 0.0)
    assert point_at(points, cumulative, 99.0) == (1.0, 1.0)


def test_walking_a_drawn_wire_moves_one_step_at_a_time_along_it():
    path = ((1, 3), (2, 3), (3, 3), (3, 2), (4, 1))  # straight, then a turn
    points = wire_points(path, SIZE, ORIGIN)
    cumulative = cumulative_lengths(points)
    walked = [point_at(points, cumulative, k * 0.5) for k in range(int(cumulative[-1] / 0.5))]
    steps = [math.dist(a, b) for a, b in zip(walked, walked[1:], strict=False)]
    assert max(steps) <= 0.5 + 1e-9  # never jumps, even round the arc
    assert walked[0] == points[0]


# The swimmer's triangle behind the board (D-018)


def test_the_body_is_the_disc_round_the_zone_centred_on_it():
    zone = hex_disc(2)
    (cx, cy), reach = body_disc(zone)
    assert (cx, cy) == pytest.approx((0.0, 0.0), abs=1e-12) and reach == pytest.approx(2 * SQRT3)
    centre, radius = body_circle(zone, 10.0, (100.0, 50.0))
    assert centre == pytest.approx((100.0, 50.0)) and radius == pytest.approx(20 * SQRT3)
    assert body_circle(zone, 10.0, (100.0, 50.0))[0][0] + radius == pytest.approx(
        to_pixel((2, 0), 10.0, (100.0, 50.0))[0]
    )  # the E-most cell is on the rim


def test_the_symbol_is_an_equilateral_triangle_on_its_circle_with_a_corner_where_it_heads():
    for heading in (0.0, 1.0, -2.5):
        corners = symbol_corners((100.0, 50.0), 20.0, heading)
        for x, y in corners:
            assert math.hypot(x - 100.0, y - 50.0) == pytest.approx(20.0)
        sides = [math.dist(a, b) for a, b in zip(corners, corners[1:] + corners[:1], strict=True)]
        assert sides == pytest.approx([20.0 * SQRT3] * 3)
        forward = corners[0]
        assert forward == pytest.approx(
            (100.0 + 20.0 * math.cos(heading), 50.0 - 20.0 * math.sin(heading))
        )


def _area(polygon):
    closed = zip(polygon, polygon[1:] + polygon[:1], strict=True)
    return 0.5 * abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in closed))


def test_a_tank_fills_its_outline_from_the_bottom_by_height():
    diamond = [(0.0, -1.0), (1.0, 0.0), (0.0, 1.0), (-1.0, 0.0)]  # on screen, y down
    assert filled_to(diamond, 0.0) == []
    assert _area(filled_to(diamond, 1.0)) == pytest.approx(_area(diamond))
    half = filled_to(diamond, 0.5)
    assert _area(half) == pytest.approx(_area(diamond) / 2)
    assert min(y for _, y in half) == pytest.approx(0.0)  # up to the middle, no higher
    assert filled_to(diamond, 2.0) == filled_to(diamond, 1.0)  # a level above full is full
