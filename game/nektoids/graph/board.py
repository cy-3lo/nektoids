"""The player's artifact: components placed on the hex board and the wires between them.

A component fills one cell. A wire is directed, from a component that emits to one that
receives, and runs centre to centre through free cells. Each free cell holds either nothing,
one wire that bends there, or up to three straight wires on distinct axes (D-007). Wires are
routed once, when drawn, and never move afterwards.

Every operation that the player can trigger returns `Refused(reason)` instead of raising, so
the editor can show the reason on screen. Pure Python, no pygame.
"""

from __future__ import annotations

import heapq
import itertools
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from nektoids.graph.hexgrid import (
    NE,
    SE,
    Cell,
    E,
    axis,
    direction_to,
    neighbour,
    offset_rect,
    opposite,
)


class Category(Enum):
    SENSOR = "sensor"
    CONVERTER = "converter"
    ACTUATOR = "actuator"


class Kind(Enum):
    SENSOR_L = "sensor_l"
    SENSOR_R = "sensor_r"
    DOUBLE = "double"
    HALVE = "halve"
    THRUSTER_L = "thruster_l"
    THRUSTER_R = "thruster_r"

    @property
    def category(self) -> Category:
        return _CATEGORY[self]

    @property
    def emits(self) -> bool:
        return self.category is not Category.ACTUATOR

    @property
    def receives(self) -> bool:
        return self.category is not Category.SENSOR

    @property
    def facing(self) -> int | None:
        """Hex direction it points to on the body, forward being E; None for converters.

        Where an eye looks, or which way a thruster pushes. Fixed per kind for the jam (D-008).
        """
        return _FACING.get(self)


_CATEGORY = {
    Kind.SENSOR_L: Category.SENSOR,
    Kind.SENSOR_R: Category.SENSOR,
    Kind.DOUBLE: Category.CONVERTER,
    Kind.HALVE: Category.CONVERTER,
    Kind.THRUSTER_L: Category.ACTUATOR,
    Kind.THRUSTER_R: Category.ACTUATOR,
}
_FACING = {Kind.SENSOR_L: NE, Kind.SENSOR_R: SE, Kind.THRUSTER_L: E, Kind.THRUSTER_R: E}


@dataclass(frozen=True)
class Node:
    id: int
    kind: Kind
    cell: Cell
    locked: bool = False  # pre-placed by the level: cannot be removed


@dataclass(frozen=True)
class Wire:
    source: int  # node id
    target: int  # node id
    path: tuple[Cell, ...]  # source cell, free cells crossed, target cell


@dataclass(frozen=True)
class Refused:
    reason: str  # short, shown to the player


def can_pass(axes_used: set[int], has_bend: bool, into: int, out: int) -> bool:
    """Whether a new wire may cross a free cell, entering heading `into` and leaving heading `out`.

    axes_used: axes of the straight wires already in the cell. has_bend: a wire bends there.
    """
    if has_bend:
        return False
    if out == into:
        return axis(into) not in axes_used
    return out != opposite(into) and not axes_used


class Board:
    """Nodes and wires on a cols x rows board.

    stock: how many of each kind the player may still place; None means unlimited, and a kind
    left out means none. Without a stock, everything is unlimited. Locked nodes are placed by
    the level and do not use stock.
    """

    def __init__(self, cols: int, rows: int, stock: Mapping[Kind, int | None] | None = None):
        self.cols, self.rows = cols, rows
        self.cells: list[Cell] = offset_rect(cols, rows)
        self._on_board = set(self.cells)
        self._stock: dict[Kind, int | None] = (
            {kind: None for kind in Kind} if stock is None else dict(stock)
        )
        self.nodes: dict[int, Node] = {}  # by id; ids increase and are never reused
        self.wires: list[Wire] = []  # in the order they were drawn
        self._next_id = 0

    # Queries

    def remaining(self, kind: Kind) -> int | None:
        """How many more of `kind` the player may place; None means unlimited."""
        return self._stock.get(kind, 0)

    def node_at(self, cell: Cell) -> Node | None:
        return next((node for node in self.nodes.values() if node.cell == cell), None)

    def wires_in(self, cell: Cell) -> list[Wire]:
        """Wires that cross `cell` (not the ones that start or end there)."""
        return [wire for wire in self.wires if cell in wire.path[1:-1]]

    # Components

    def place(self, kind: Kind, cell: Cell, locked: bool = False) -> Node | Refused:
        if cell not in self._on_board:
            return Refused("off the board")
        if self.node_at(cell) is not None:
            return Refused("cell taken")
        if self.wires_in(cell):
            return Refused("a wire runs here")
        left = self.remaining(kind)
        if not locked and left is not None:
            if left == 0:
                return Refused("none left")
            self._stock[kind] = left - 1
        node = Node(self._next_id, kind, cell, locked)
        self.nodes[node.id] = node
        self._next_id += 1
        return node

    def remove_node(self, node_id: int) -> Refused | None:
        """Remove a node and every wire attached to it; its stock comes back."""
        node = self.nodes[node_id]
        if node.locked:
            return Refused("placed by the level")
        self.wires = [wire for wire in self.wires if node_id not in (wire.source, wire.target)]
        del self.nodes[node_id]
        left = self.remaining(node.kind)
        if left is not None:
            self._stock[node.kind] = left + 1
        return None

    # Wires

    def preview(self, source_id: int, target_id: int) -> tuple[Cell, ...] | Refused:
        """The path a wire from source to target would take, without drawing it."""
        source, target = self.nodes[source_id], self.nodes[target_id]
        if source_id == target_id:
            return Refused("same component")
        if not source.kind.emits:
            return Refused("thrusters have no output")
        if not target.kind.receives:
            return Refused("sensors have no input")
        if any(wire.source == source_id and wire.target == target_id for wire in self.wires):
            return Refused("already wired")
        if self._reaches(target_id, source_id):
            return Refused("would close a loop")
        path = self.route(source.cell, target.cell)
        return Refused("no free path") if path is None else path

    def connect(self, source_id: int, target_id: int) -> Wire | Refused:
        path = self.preview(source_id, target_id)
        if isinstance(path, Refused):
            return path
        wire = Wire(source_id, target_id, path)
        self.wires.append(wire)
        return wire

    def remove_wire(self, wire: Wire) -> None:
        self.wires.remove(wire)

    def route(self, start: Cell, goal: Cell) -> tuple[Cell, ...] | None:
        """Shortest free path between two component cells, both included; None if there is none.

        Dijkstra over (cell, heading) states with cost (steps, bends), compared in that order.
        Equal costs go to the path pushed first, with neighbours tried in direction order, so the
        result never depends on set or dict order.
        """
        axes_used, bends = self._occupancy()
        blocked = {node.cell for node in self.nodes.values()}
        counter = itertools.count()
        # (steps, bends, tie-break, cell, heading into cell, path so far); heading -1 at the start
        heap = [(0, 0, next(counter), start, -1, (start,))]
        settled: set[tuple[Cell, int]] = set()
        while heap:
            steps, turns, _, cell, heading, path = heapq.heappop(heap)
            if cell == goal:
                crossed = path[1:-1]
                return path if len(set(crossed)) == len(crossed) else None
            if (cell, heading) in settled:
                continue
            settled.add((cell, heading))
            for out in range(6):
                nxt = neighbour(cell, out)
                if nxt not in self._on_board or (nxt in blocked and nxt != goal):
                    continue
                if heading >= 0 and not can_pass(
                    axes_used.get(cell, set()), cell in bends, heading, out
                ):
                    continue
                bend = int(heading >= 0 and out != heading)
                heapq.heappush(
                    heap, (steps + 1, turns + bend, next(counter), nxt, out, path + (nxt,))
                )
        return None

    # Internals

    def _occupancy(self) -> tuple[dict[Cell, set[int]], set[Cell]]:
        """Axes of the straight wires in each cell, and the cells where a wire bends."""
        axes_used: dict[Cell, set[int]] = {}
        bends: set[Cell] = set()
        for wire in self.wires:
            for before, cell, after in zip(wire.path, wire.path[1:], wire.path[2:], strict=False):
                into, out = direction_to(before, cell), direction_to(cell, after)
                if into == out:
                    axes_used.setdefault(cell, set()).add(axis(into))
                else:
                    bends.add(cell)
        return axes_used, bends

    def _reaches(self, start: int, goal: int) -> bool:
        """Whether signal from node `start` already flows to node `goal` along existing wires."""
        frontier, seen = [start], {start}
        while frontier:
            node_id = frontier.pop()
            if node_id == goal:
                return True
            for wire in self.wires:
                if wire.source == node_id and wire.target not in seen:
                    seen.add(wire.target)
                    frontier.append(wire.target)
        return False
