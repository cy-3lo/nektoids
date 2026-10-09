"""What is picked on the Board (D-402): empty cells, or parts, in the order picked, which the
code keeps and the screen does not show (D-401). A click picks the one thing clicked, and a click
on the only thing picked drops it; with the add key (Shift or Cmd), it adds the thing to the pick,
or drops it from it, a click of the other kind starting a pick of its own. A click off the zone
drops the pick. A drag picks along its path, the empty cells or the parts it crosses; one that
meets a part picks parts from there; going back over its path cuts it back to the cell entered
(`Drag`). A part's pick follows its parts by their cells. Pure Python, no pygame.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from nektoids.graph.board import Board, Node, Wire
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


def clicked(pick: Pick, board: Board, cell: Cell | None, add: bool = False) -> Pick:
    """The pick after a click with Select on `cell`: that one thing, or none if it was the only
    one picked; with `add`, it is added to the pick, or dropped from it. A click off the zone
    drops the pick, or leaves it as it was with `add`."""
    if cell is None or cell not in board.cells:
        return pick if add else NOTHING
    what = Picked.PARTS if board.node_at(cell) is not None else Picked.CELLS
    if not add:
        return NOTHING if pick == Pick(what, (cell,)) else Pick(what, (cell,))
    if what is not pick.what:
        return Pick(what, (cell,))
    if cell in pick.cells:
        rest = tuple(c for c in pick.cells if c != cell)
        return Pick(what, rest) if rest else NOTHING
    return Pick(what, (*pick.cells, cell))


@dataclass(frozen=True)
class Drag:
    """A drag with Select: the cells it crossed, from the one it started on, of the kind that
    one is, empty cells or parts; with `base`, what was picked before, kept (the add key)."""

    what: Picked
    path: tuple[Cell, ...]
    base: tuple[Cell, ...] = ()

    @property
    def pick(self) -> Pick:
        return Pick(self.what, tuple(dict.fromkeys((*self.base, *self.path))))


def begin(pick: Pick, board: Board, cell: Cell, add: bool = False) -> Drag:
    """A drag begun on `cell`: a part's starts a pick of parts, an empty cell's of cells."""
    what = Picked.PARTS if board.node_at(cell) is not None else Picked.CELLS
    return Drag(what, (cell,), pick.cells if add and pick.what is what else ())


def extend(drag: Drag, board: Board, cell: Cell) -> Drag:
    """The drag after it enters `cell`: a cell of its path cuts the path back to it, however far
    back; a cell of its kind not on it is added. A drag of empty cells that meets a part picks
    parts from there, the cells dropped; a drag of parts passes over empty cells."""
    if cell in drag.path:
        return Drag(drag.what, drag.path[: drag.path.index(cell) + 1], drag.base)
    if cell not in board.cells:
        return drag
    part = board.node_at(cell) is not None
    if part and drag.what is Picked.CELLS:  # a part met: the drag picks parts from here
        return Drag(Picked.PARTS, (cell,))
    if not part and drag.what is Picked.PARTS:
        return drag
    return Drag(drag.what, (*drag.path, cell), drag.base)


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


def crossing(pick: Pick, board: Board) -> list[Wire]:
    """The wires that cross the empty cells picked, each once, in the order drawn (D-431); none
    for a pick of parts."""
    if pick.what is not Picked.CELLS:
        return []
    cells = set(pick.cells)
    return [wire for wire in board.wires if cells.intersection(wire.path[1:-1])]


def moved(pick: Pick, offset: Cell) -> Pick:
    """The pick after its parts moved together by `offset`."""
    dq, dr = offset
    return Pick(pick.what, tuple((q + dq, r + dr) for q, r in pick.cells))
