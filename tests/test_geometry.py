"""Wire drawing geometry. geometry.py imports no pygame, so this runs headless."""

import math

import pytest

from nektoids.editor.geometry import (
    distance_to_polyline,
    edge_midpoint,
    nearest_wire,
    turn_centre,
    wire_points,
)
from nektoids.graph.board import Wire
from nektoids.graph.hexgrid import NE, NW, SQRT3, E, W, to_pixel

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
