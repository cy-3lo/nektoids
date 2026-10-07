"""What is picked on the Board (D-402): empty cells, or parts, one after another, in the order
clicked, which the code keeps and the screen does not show (D-401). The first click says which:
a click of the other kind starts a pick of its own; a click on a picked one drops it; a click off
the zone drops them all. A drag from an empty cell picks the empty cells it crosses, the parts
it crosses left out (D-404). A part's pick follows its parts by their cells. Pure Python, no
pygame.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from nektoids.graph.board import Board, Node
from nektoids.graph.hexgrid import Cell


class Picked(Enum):
    CELLS = "cells"  # empty cells, for parts to go into
    PARTS = "parts"  # parts, for the buttons to act on


@dataclass(frozen=True)
class Pick:
    what: Picked | None = None
    cells: tuple[Cell, ...] = ()  # in the order clicked

    def __bool__(self) -> bool:
        return bool(self.cells)


NOTHING = Pick()


def clicked(pick: Pick, board: Board, cell: Cell | None) -> Pick:
    """The pick after a click with Select on `cell`, None or off the zone dropping it all."""
    if cell is None or cell not in board.cells:
        return NOTHING
    what = Picked.PARTS if board.node_at(cell) is not None else Picked.CELLS
    if what is not pick.what:
        return Pick(what, (cell,))
    if cell in pick.cells:
        rest = tuple(c for c in pick.cells if c != cell)
        return Pick(what, rest) if rest else NOTHING
    return Pick(what, (*pick.cells, cell))


def along(pick: Pick, board: Board, cell: Cell) -> Pick:
    """The pick of a drag that picks cells, as it enters `cell`: added if it is an empty cell of
    the zone not picked yet; a part, or a cell picked already, leaves it as it was (D-404)."""
    if cell not in board.cells or board.node_at(cell) is not None:
        return pick
    cells = pick.cells if pick.what is Picked.CELLS else ()
    return pick if cell in cells else Pick(Picked.CELLS, (*cells, cell))


def of_parts(cells: Iterable[Cell]) -> Pick:
    """The parts on `cells` picked, in that order: the parts a button just placed (D-402)."""
    cells = tuple(cells)
    return Pick(Picked.PARTS, cells) if cells else NOTHING


def kept(pick: Pick, board: Board) -> Pick:
    """The pick as the board now holds it: its cells still empty, or its parts still there."""
    if pick.what is Picked.CELLS:
        cells = tuple(c for c in pick.cells if c in board.cells and board.node_at(c) is None)
    else:
        cells = tuple(c for c in pick.cells if board.node_at(c) is not None)
    return Pick(pick.what, cells) if cells else NOTHING


def parts(pick: Pick, board: Board) -> list[Node]:
    """The parts picked, in the order picked; none for a pick of cells."""
    if pick.what is not Picked.PARTS:
        return []
    return [node for node in (board.node_at(c) for c in pick.cells) if node is not None]


def moved(pick: Pick, offset: Cell) -> Pick:
    """The pick after its parts moved together by `offset`."""
    dq, dr = offset
    return Pick(pick.what, tuple((q + dq, r + dr) for q, r in pick.cells))
