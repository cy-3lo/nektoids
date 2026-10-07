"""A wiring chain on the Board (D-402): the parts clicked or dragged over one after another, each
wired to the one before. Wiring over a wire already there takes it away instead. Going back to a
part of the chain, a click or a drag on it, undoes what the chain did after it, however far back:
the wires it made go, those it took away come back. A wire refused ends the chain. Pure Python,
no pygame.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from nektoids.graph.board import Board, Wire


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


def between(board: Board, a: int, b: int) -> Wire | None:
    """The wire between two parts, either way round, if there is one."""
    return next((w for w in board.wires if {w.source, w.target} == {a, b}), None)


def chain_to(
    chain: Chain,
    board: Board,
    node_id: int,
    make: Callable[[int, int], Wire | None],
    cut: Callable[[Wire], bool],
) -> Chain | None:
    """The chain after it reaches `node_id`: back to it if it is on the chain, its steps after it
    undone; else the wire to it from the last part taken away if there is one, or made (`make`,
    `cut`: the scene's, which may refuse and say why). None: refused, the chain ends."""
    if node_id == chain.last:
        return chain
    if node_id in chain.path:
        i = chain.path.index(node_id)
        for did, wire in reversed(chain.steps[i:]):
            if did is Did.MADE:
                made = between(board, wire.source, wire.target)
                if made is not None:
                    board.remove_wire(made)
            else:
                board.connect(wire.source, wire.target, wire.path)
        return Chain(chain.path[: i + 1], chain.steps[:i])
    there = between(board, chain.last, node_id)
    if there is not None:
        if not cut(there):
            return None
        return Chain((*chain.path, node_id), (*chain.steps, (Did.CUT, there)))
    wire = make(chain.last, node_id)
    if wire is None:
        return None
    return Chain((*chain.path, node_id), (*chain.steps, (Did.MADE, wire)))
