"""A wiring chain on the Board (D-402): the parts clicked or dragged over one after another, each
wired to the one before. Wiring over a wire already there takes it away instead: a drag that
follows its path, or a click the way it runs; a drag another way, or a click the other way,
draws a wire back, a loop (D-429). Going back to a
part of the chain, a click or a drag on it, undoes what the chain did after it, however far back:
the wires it made go, those it took away come back. A wire refused ends the chain. Pure Python,
no pygame.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from nektoids.graph.board import Board, Wire
from nektoids.graph.hexgrid import Cell, neighbour


class Did(Enum):
    MADE = "made"  # a wire drawn from the part before
    CUT = "cut"  # the wire already there taken away


@dataclass(frozen=True)
class Chain:
    path: tuple[int, ...]  # node ids, the first where the chain began
    steps: tuple[tuple[Did, Wire], ...] = ()  # what each step did, between path[i] and path[i + 1]

    @property
    def last(self) -> int:
        return self.path[-1]


def wired(board: Board, source: int, target: int) -> Wire | None:
    """The wire from `source` to `target`, if there is one."""
    return next((w for w in board.wires if (w.source, w.target) == (source, target)), None)


def retraces(wire: Wire, trail: tuple[Cell, ...]) -> bool:
    """Whether a drag's trail, the cells it entered between the wire's two parts, follows the
    wire (D-429): every cell between its ends entered, and none that does not border them, so a
    corner clipped still counts. Between neighbours, no cell: only a drag straight across."""
    inner = set(wire.path[1:-1])
    near = inner | {neighbour(cell, d) for cell in inner for d in range(6)}
    return inner <= set(trail) and set(trail) <= near


def chain_to(
    chain: Chain,
    board: Board,
    node_id: int,
    make: Callable[[int, int], Wire | None],
    cut: Callable[[Wire], bool],
    trail: tuple[Cell, ...] | None = None,
) -> Chain | None:
    """The chain after it reaches `node_id`: back to it if it is on the chain, its steps after it
    undone; else the wire between the last part and it taken away if the gesture retraces it, or
    one made (`make`, `cut`: the scene's, which may refuse and say why). `trail`: the cells a drag
    entered since the last part; None for a click, which takes away the wire the way it runs
    (D-429). None: refused, the chain ends."""
    if node_id == chain.last:
        return chain
    if node_id in chain.path:
        i = chain.path.index(node_id)
        for did, wire in reversed(chain.steps[i:]):
            if did is Did.MADE:
                made = wired(board, wire.source, wire.target)
                if made is not None:
                    board.remove_wire(made)
            else:
                board.connect(wire.source, wire.target, wire.path)
        return Chain(chain.path[: i + 1], chain.steps[:i])
    if trail is None:
        there = wired(board, *board.orient(chain.last, node_id))
    else:
        there = next(
            (
                w
                for w in board.wires
                if {w.source, w.target} == {chain.last, node_id} and retraces(w, trail)
            ),
            None,
        )
    if there is not None:
        if not cut(there):
            return None
        return Chain((*chain.path, node_id), (*chain.steps, (Did.CUT, there)))
    wire = make(chain.last, node_id)
    if wire is None:
        return None
    return Chain((*chain.path, node_id), (*chain.steps, (Did.MADE, wire)))
