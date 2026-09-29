import math

import pytest

from nektoids.graph.hexgrid import (
    DIRECTIONS,
    SQRT3,
    axis,
    from_pixel,
    neighbour,
    offset_rect,
    opposite,
    to_pixel,
)

SIZE = 30.0  # [px]
ORIGIN = (100.0, 80.0)  # [px]
BOARD = offset_rect(9, 7)


def test_opposite_steps_cancel_and_share_an_axis():
    for d in range(6):
        assert neighbour(neighbour((2, 3), d), opposite(d)) == (2, 3)
        assert axis(d) == axis(opposite(d))
    assert sorted(axis(d) for d in range(6)) == [0, 0, 1, 1, 2, 2]


def test_offset_rect_has_distinct_cells_row_by_row():
    assert len(BOARD) == 9 * 7
    assert len(set(BOARD)) == len(BOARD)
    assert BOARD[0] == (0, 0)
    assert [r for _, r in BOARD] == sorted(r for _, r in BOARD)


def test_offset_rect_rows_are_aligned_on_screen():
    # Even rows start at the left edge, odd rows half a cell to the right.
    for row in range(7):
        first = BOARD[row * 9]
        x, _ = to_pixel(first, SIZE, ORIGIN)
        expected = ORIGIN[0] + (0.5 * SQRT3 * SIZE if row % 2 else 0.0)
        assert x == pytest.approx(expected)


def test_each_direction_points_the_way_its_name_says():
    # Direction d sits at screen angle -60° * d (y down): E is right, NE up-right, ...
    for d in range(6):
        x0, y0 = to_pixel((4, 3), SIZE, ORIGIN)
        x1, y1 = to_pixel(neighbour((4, 3), d), SIZE, ORIGIN)
        angle = math.radians(-60.0 * d)
        assert x1 - x0 == pytest.approx(SQRT3 * SIZE * math.cos(angle))
        assert y1 - y0 == pytest.approx(SQRT3 * SIZE * math.sin(angle))


def test_pixel_round_trip_on_every_cell():
    for cell in BOARD:
        assert from_pixel(*to_pixel(cell, SIZE, ORIGIN), SIZE, ORIGIN) == cell


@pytest.mark.parametrize("cell", [(0, 0), (3, 2), (-2, 5)])
def test_points_near_the_boundary_pick_the_right_hex(cell):
    x0, y0 = to_pixel(cell, SIZE, ORIGIN)
    inner = 0.5 * SQRT3 * SIZE  # centre to edge midpoint [px]
    for d in range(len(DIRECTIONS)):
        edge = math.radians(-60.0 * d)
        corner = edge + math.radians(30.0)
        just_inside_corner = (
            x0 + 0.95 * SIZE * math.cos(corner),
            y0 + 0.95 * SIZE * math.sin(corner),
        )
        just_inside_edge = (x0 + 0.95 * inner * math.cos(edge), y0 + 0.95 * inner * math.sin(edge))
        just_outside_edge = (x0 + 1.05 * inner * math.cos(edge), y0 + 1.05 * inner * math.sin(edge))
        assert from_pixel(*just_inside_corner, SIZE, ORIGIN) == cell
        assert from_pixel(*just_inside_edge, SIZE, ORIGIN) == cell
        assert from_pixel(*just_outside_edge, SIZE, ORIGIN) == neighbour(cell, d)
