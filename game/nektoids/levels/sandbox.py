"""Two starting boards for trying the editor, until real levels exist.

Eyes and thrusters are all alike; what makes one a "left" eye is where it looks. The agent's
left is up on screen (forward = E, D-008), so the tutorial's eyes look NE and SE.
"""

from __future__ import annotations

from nektoids.graph.board import Board, Kind
from nektoids.graph.hexgrid import NE, SE, E

COLS, ROWS = 9, 7
CONVERTERS = {Kind.DOUBLE: None, Kind.HALVE: None}  # unlimited
# Tuples, not dicts: placement order sets the node ids (invariant 1).
IO_PARTS = (
    (Kind.EYE, (0, 1), NE),  # left column, row 1
    (Kind.EYE, (-2, 5), SE),  # left column, row 5
    (Kind.THRUSTER, (8, 1), E),  # right column, row 1
    (Kind.THRUSTER, (6, 5), E),  # right column, row 5
)


def free_board() -> Board:
    """Typical level: two eyes and two thrusters in the palette, converters unlimited."""
    return Board(COLS, ROWS, {Kind.EYE: 2, Kind.THRUSTER: 2} | CONVERTERS)


def tutorial_board() -> Board:
    """Braitenberg tutorial: eyes and thrusters pre-placed and locked, converters unlimited."""
    board = Board(COLS, ROWS, CONVERTERS)
    for kind, cell, facing in IO_PARTS:
        board.place(kind, cell, locked=True, facing=facing)
    return board
