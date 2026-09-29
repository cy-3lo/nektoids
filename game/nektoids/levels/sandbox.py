"""Two starting boards for trying the editor, until real levels exist.

The agent's left is up on screen (forward = E, D-008), so left-side parts sit on the top row.
"""

from __future__ import annotations

from nektoids.graph.board import Board, Kind

COLS, ROWS = 9, 7
CONVERTERS = {Kind.DOUBLE: None, Kind.HALVE: None}  # unlimited
EYES = {Kind.SENSOR_L: (0, 1), Kind.SENSOR_R: (-2, 5)}  # left column, rows 1 and 5
THRUSTERS = {Kind.THRUSTER_L: (8, 1), Kind.THRUSTER_R: (6, 5)}  # right column, rows 1 and 5


def free_board() -> Board:
    """Typical level: one of each sensor and thruster in the palette, converters unlimited."""
    stock = {kind: 1 for kind in (*EYES, *THRUSTERS)} | CONVERTERS
    return Board(COLS, ROWS, stock)


def tutorial_board() -> Board:
    """Braitenberg tutorial: eyes and thrusters pre-placed and locked, converters unlimited."""
    board = Board(COLS, ROWS, CONVERTERS)
    for kind, cell in (EYES | THRUSTERS).items():
        board.place(kind, cell, locked=True)
    return board
