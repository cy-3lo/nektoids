"""The Board's buttons (D-401): hexes as the cells are, in the cells round the board, at the same
places on every level, so that the hand learns them.

The board's centre is cell (0, 0), r down. At N, Select, Move and Lock, Lock on the board reached
from the Editor only (D-319); at S, Undo, Redo and Delete; at W, Turn left and Turn right side by
side, Wire under them; at E, the parts: Eye, Source and Thruster, then Double and Halve side by
side over Sum and Difference. A kind the level does not hand out leaves its place empty. The
board shows at one size, centred, so that the largest zone and every button fit beside a drawer.
"""

from __future__ import annotations

from enum import Enum

from nektoids.graph.board import Kind
from nektoids.graph.hexgrid import Cell, hex_disc


class Button(Enum):
    SELECT = "select"
    MOVE = "move"
    LOCK = "lock"
    UNDO = "undo"
    REDO = "redo"
    DELETE = "delete"
    TURN_LEFT = "turn left"
    TURN_RIGHT = "turn right"
    WIRE = "wire"


PLACES: dict[Button | Kind, Cell] = {
    Button.SELECT: (1, -4),
    Button.MOVE: (2, -4),
    Button.LOCK: (3, -4),
    Button.UNDO: (-3, 4),
    Button.REDO: (-2, 4),
    Button.DELETE: (-1, 4),
    Button.TURN_LEFT: (-3, -2),
    Button.TURN_RIGHT: (-2, -2),
    Button.WIRE: (-3, -1),
    Kind.EYE: (4, -3),
    Kind.SOURCE: (4, -2),
    Kind.THRUSTER: (4, -1),
    Kind.DOUBLE: (2, 2),
    Kind.HALVE: (3, 2),
    Kind.SUM: (1, 3),
    Kind.DIFFERENCE: (2, 3),
}
LARGEST_ZONE = 3  # the sandbox's, 37 cells (D-102, D-313)
FRAME: tuple[Cell, ...] = (*hex_disc(LARGEST_ZONE), *PLACES.values())  # what the view shows whole
