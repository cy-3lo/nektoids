"""Two starting boards for trying the Board, until real levels exist.

The zone is the hexagon of 19 cells around (0, 0). Eyes and thrusters are all alike; what makes
one a "left" eye is where it looks. The agent's left is up on screen (forward = E, D-008), so
the tutorial's eyes look NE and SE, on the left edge of the zone, and its thrusters sit
opposite them on the right edge.
"""

from __future__ import annotations

from nektoids.graph.board import Board, Kind
from nektoids.graph.hexgrid import NE, SE, E, hex_disc

ZONE = hex_disc(2)
OPERATORS = {kind: None for kind in (Kind.DOUBLE, Kind.HALVE, Kind.SUM, Kind.DIFFERENCE)}
# Tuples, not dicts: placement order sets the node ids (invariant 1).
IO_PARTS = (
    (Kind.EYE, (-1, -1), NE),  # upper left
    (Kind.EYE, (-2, 1), SE),  # lower left
    (Kind.THRUSTER, (2, -1), E),  # upper right
    (Kind.THRUSTER, (1, 1), E),  # lower right
)


def free_board() -> Board:
    """Typical level: two eyes, a source and two thrusters in the menu, operators unlimited."""
    return Board(ZONE, {Kind.EYE: 2, Kind.SOURCE: 1, Kind.THRUSTER: 2} | OPERATORS)


def tutorial_board() -> Board:
    """Braitenberg tutorial: eyes and thrusters pre-placed and locked, operators unlimited."""
    board = Board(ZONE, OPERATORS)
    for kind, cell, facing in IO_PARTS:
        board.place(kind, cell, locked=True, facing=facing)
    return board
