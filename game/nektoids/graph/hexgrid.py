"""Hex grid geometry for the board.

Pointy-top hexes in axial coordinates (q, r). Screen y points down, so r grows downwards.
Directions are indexed 0..5 so that opposite = (d + 3) % 6 and the three axes are d % 3:

         NW(2)   NE(1)
    W(3)    [cell]    E(0)
         SW(4)   SE(5)

The board is a rectangle of cols x rows cells in "odd-r" offset layout: odd rows are shifted
half a cell to the right. Pure Python, no pygame: pixel conversion takes the hex size and the
pixel position of cell (0, 0) as arguments.
"""

from __future__ import annotations

import math

Cell = tuple[int, int]  # axial (q, r)

# Axial step for each direction, in the order E, NE, NW, W, SW, SE.
DIRECTIONS: tuple[Cell, ...] = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))
E, NE, NW, W, SW, SE = range(6)

SQRT3 = math.sqrt(3.0)


def neighbour(cell: Cell, direction: int) -> Cell:
    """The adjacent cell one step away in `direction` (0..5)."""
    dq, dr = DIRECTIONS[direction]
    return (cell[0] + dq, cell[1] + dr)


def direction_to(a: Cell, b: Cell) -> int:
    """Direction of the single step from `a` to the adjacent cell `b`; ValueError otherwise."""
    return DIRECTIONS.index((b[0] - a[0], b[1] - a[1]))


def opposite(direction: int) -> int:
    """The direction pointing the other way along the same axis."""
    return (direction + 3) % 6


def axis(direction: int) -> int:
    """Which of the three axes (0: E-W, 1: NE-SW, 2: NW-SE) a direction runs along."""
    return direction % 3


def offset_rect(cols: int, rows: int) -> list[Cell]:
    """All cells of a cols x rows odd-r board, row by row, left to right."""
    return [(col - (row - (row & 1)) // 2, row) for row in range(rows) for col in range(cols)]


def vertical_step(cell: Cell, rows: int) -> Cell:
    """The cell `rows` rows down (negative: up) in the same odd-r column: the neighbour that
    keeps a straight vertical line on screen, alternating NW / NE going up (SW / SE going down)."""
    q, r = cell
    col = q + (r - (r & 1)) // 2
    r2 = r + rows
    return (col - (r2 - (r2 & 1)) // 2, r2)


def hex_distance(a: Cell, b: Cell) -> int:
    """Number of single steps from `a` to `b`."""
    dq, dr = a[0] - b[0], a[1] - b[1]
    return max(abs(dq), abs(dr), abs(dq + dr))


def hex_disc(radius: int) -> list[Cell]:
    """Cells within `radius` steps of (0, 0), row by row: a hexagon of 3 r (r + 1) + 1 cells."""
    span = range(-radius, radius + 1)
    return [(q, r) for r in span for q in span if hex_distance((q, r), (0, 0)) <= radius]


def disc_size(radius: int) -> int:
    """How many cells a hexagon of `radius` rings round (0, 0) holds: 1, 7, 19, 37..."""
    return 3 * radius * (radius + 1) + 1


def disc_radius(size: int) -> int:
    """The rings of the hexagon round (0, 0) that holds `size` cells; ValueError if none does."""
    radius = 0
    while disc_size(radius) < size:
        radius += 1
    if disc_size(radius) != size:
        raise ValueError(f"no hexagon holds {size} cells: 1, 7, 19, 37...")
    return radius


def to_pixel(cell: Cell, size: float, origin: tuple[float, float]) -> tuple[float, float]:
    """Pixel centre of `cell`.

    size: centre-to-corner distance [px]. origin: pixel centre of cell (0, 0) [px].
    """
    q, r = cell
    x = origin[0] + size * SQRT3 * (q + 0.5 * r)
    y = origin[1] + size * 1.5 * r
    return (x, y)


def from_pixel(x: float, y: float, size: float, origin: tuple[float, float]) -> Cell:
    """The cell containing pixel (x, y); inverse of `to_pixel`, with cube rounding."""
    dx = (x - origin[0]) / size
    dy = (y - origin[1]) / size
    q = SQRT3 / 3.0 * dx - dy / 3.0
    r = 2.0 / 3.0 * dy
    s = -q - r
    # Round each cube coordinate, then recompute the one that moved most so q + r + s == 0.
    rq, rr, rs = round(q), round(r), round(s)
    error_q, error_r, error_s = abs(rq - q), abs(rr - r), abs(rs - s)
    if error_q > error_r and error_q > error_s:
        rq = -rr - rs
    elif error_r > error_s:
        rr = -rq - rs
    return (rq, rr)
