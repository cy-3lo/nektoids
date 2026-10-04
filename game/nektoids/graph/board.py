"""The player's artifact: components placed on the hex board and the wires between them.

A component fills one cell. A wire is directed, from a component that emits to one that
receives, and runs through free cells, entering and leaving each through one of its six edges.
`orient` says which way a wire drawn between two components runs (D-026); `snapshot` and
`restore` are for undo (D-027); `adopt` puts on it a board built on another level's (D-092).
Wires may cross or turn in the same cell as long as no edge is used twice (D-010), so a cell
holds at most three. Wires are routed once, when drawn, and never move afterwards.

Every operation that the player can trigger returns `Refused(reason)` instead of raising, so
the editor can show the reason on screen. `to_dict` and `from_dict` turn a board into plain
data and back (D-024). Pure Python, no pygame.
"""

from __future__ import annotations

import heapq
import itertools
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace

from nektoids.graph.hexgrid import (
    Cell,
    direction_to,
    neighbour,
    opposite,
)
from nektoids.graph.kinds import Kind

FACING_NAMES = ("E", "NE", "NW", "W", "SW", "SE")  # hex directions 0..5, for `to_dict`


@dataclass(frozen=True)
class Node:
    id: int
    kind: Kind
    cell: Cell
    locked: bool = False  # pre-placed by the level: cannot be removed
    facing: int | None = None  # hex direction on the body (eyes, thrusters); None for the rest


@dataclass(frozen=True)
class Wire:
    source: int  # node id
    target: int  # node id
    path: tuple[Cell, ...]  # source cell, free cells crossed, target cell


@dataclass(frozen=True)
class BoardState:
    """What the player has built, frozen, for undo (D-027): equal states are equal boards."""

    nodes: tuple[Node, ...]  # by id
    wires: tuple[Wire, ...]  # in the order they were drawn
    stock: tuple[tuple[Kind, int | None], ...]  # what is left of each kind


@dataclass(frozen=True)
class Refused:
    reason: str  # short, shown to the player


def crossings(path: tuple[Cell, ...]) -> list[tuple[Cell, int, int]]:
    """For each free cell a wire crosses: (cell, edge it comes in by, edge it leaves by).

    An edge is named by the direction from the cell's centre through it, so a wire heading E
    comes in by the W edge.
    """
    return [
        (cell, direction_to(cell, before), direction_to(cell, after))
        for before, cell, after in zip(path, path[1:], path[2:], strict=False)
    ]


def can_pass(edges_used: set[int], into: int, out: int) -> bool:
    """Whether a new wire may cross a free cell, entering heading `into` and leaving heading `out`.

    edges_used: edges of the cell already taken by other wires. The new wire needs the edge it
    comes in by and the one it leaves by; a U-turn would need the same edge twice.
    """
    entry = opposite(into)
    return out != entry and entry not in edges_used and out not in edges_used


class Board:
    """Nodes and wires on the level's zone: the cells that can hold a component or a wire.

    stock: how many of each kind the player may still place; None means unlimited, and a kind
    left out means none. Without a stock, everything is unlimited. Locked nodes are placed by
    the level and do not use stock.
    """

    def __init__(self, cells: Iterable[Cell], stock: Mapping[Kind, int | None] | None = None):
        self.cells: list[Cell] = sorted(set(cells), key=lambda c: (c[1], c[0]))  # row by row
        self._on_board = set(self.cells)
        self._stock: dict[Kind, int | None] = (
            {kind: None for kind in Kind} if stock is None else dict(stock)
        )
        self._total = dict(self._stock)  # what the level handed out, for 'left/total'
        self.nodes: dict[int, Node] = {}  # by id; ids increase and are never reused
        self.wires: list[Wire] = []  # in the order they were drawn
        self._next_id = 0

    # Queries

    def remaining(self, kind: Kind) -> int | None:
        """How many more of `kind` the player may place; None means unlimited."""
        return self._stock.get(kind, 0)

    def total(self, kind: Kind) -> int | None:
        """How many of `kind` the level hands out in all; None means unlimited."""
        return self._total.get(kind, 0)

    def node_at(self, cell: Cell) -> Node | None:
        return next((node for node in self.nodes.values() if node.cell == cell), None)

    def wires_in(self, cell: Cell) -> list[Wire]:
        """Wires that cross `cell` (not the ones that start or end there)."""
        return [wire for wire in self.wires if cell in wire.path[1:-1]]

    # Components

    def place(
        self, kind: Kind, cell: Cell, locked: bool = False, facing: int | None = None
    ) -> Node | Refused:
        """Put a component on a cell no other holds. The wires crossing it are routed again round
        it, in the order they were drawn (D-086); if one finds no way round, nothing changes.

        Eyes and thrusters point along `facing`, or their kind's default if it is None;
        operators have no direction.
        """
        if cell not in self._on_board:
            return Refused("outside the zone")
        if self.node_at(cell) is not None:
            return Refused("cell taken")
        left = self.remaining(kind)
        if not locked and left == 0:
            return Refused("none left")
        if kind.default_facing is None:
            facing = None
        elif facing is None:
            facing = kind.default_facing
        node = Node(self._next_id, kind, cell, locked=locked, facing=facing)
        self.nodes[node.id] = node
        saved = list(self.wires)
        crossing = [i for i, wire in enumerate(saved) if cell in wire.path[1:-1]]
        if self._route_again(saved, crossing) is not None:
            del self.nodes[node.id]
            self.wires = saved
            return Refused("the wires here would find no way round")
        if not locked and left is not None:
            self._stock[kind] = left - 1
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

    def replace(self, node_id: int, kind: Kind) -> tuple[Node, int] | Refused:
        """A part of `kind` where node `node_id` is (D-068): on its cell, facing its way if both
        turn, with each of its wires the new part can take, routed again in the order they were
        drawn. Returns the new node and how many wires could not follow, which go."""
        old = self.nodes[node_id]
        if old.locked:
            return Refused("placed by the level")
        if self.remaining(kind) == 0:
            return Refused("none left")
        before = self.snapshot()
        ends = [(w.source, w.target) for w in self.wires if node_id in (w.source, w.target)]
        self.remove_node(node_id)
        facing = old.facing if kind.default_facing is not None else None
        node = self.place(kind, old.cell, facing=facing)
        if isinstance(node, Refused):
            self.restore(before)
            return node
        lost = 0
        for source, target in ends:
            ids = (
                node.id if source == node_id else source,
                node.id if target == node_id else target,
            )
            lost += isinstance(self.connect(*ids), Refused)
        return node, lost

    def move_node(self, node_id: int, cell: Cell) -> Node | Refused:
        """Move a component to another cell, routing again its wires (D-011) and those crossing
        that cell (D-086).

        They are routed in the order they were drawn; other wires stay put. If one of them finds
        no free path, nothing changes.
        """
        node = self.nodes[node_id]
        if node.locked:
            return Refused("placed by the level")
        if cell == node.cell:
            return node
        if cell not in self._on_board:
            return Refused("outside the zone")
        if self.node_at(cell) is not None:
            return Refused("cell taken")
        saved = list(self.wires)
        again = [
            i
            for i, wire in enumerate(saved)
            if node_id in (wire.source, wire.target) or cell in wire.path[1:-1]
        ]
        self.nodes[node_id] = replace(node, cell=cell)
        lost = self._route_again(saved, again)
        if lost is not None:
            self.nodes[node_id], self.wires = node, saved
            if node_id in (lost.source, lost.target):
                return Refused("its wires would find no free path")
            return Refused("the wires here would find no way round")
        return self.nodes[node_id]

    def rotate(self, node_id: int, steps: int) -> Node | Refused:
        """Turn an eye or a thruster by `steps` x 60°: counter-clockwise on screen if positive."""
        node = self.nodes[node_id]
        if node.facing is None:
            return Refused(f"{node.kind.value}s have no direction")
        if node.locked:
            return Refused("placed by the level")
        turned = replace(node, facing=(node.facing + steps) % 6)
        self.nodes[node_id] = turned
        return turned

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
        outputs = sum(wire.source == source_id for wire in self.wires)
        if source.kind.max_outputs is not None and outputs >= source.kind.max_outputs:
            return Refused(f"a {source.kind.value} has {_count(source.kind.max_outputs)} output")
        inputs = sum(wire.target == target_id for wire in self.wires)
        if target.kind.max_inputs is not None and inputs >= target.kind.max_inputs:
            return Refused(f"a {target.kind.value} takes {_count(target.kind.max_inputs)} inputs")
        path = self.route(source.cell, target.cell)
        return Refused("no free path") if path is None else path

    def orient(self, first_id: int, second_id: int) -> tuple[int, int]:
        """(source, target) of a wire drawn from `first_id` to `second_id` (D-026): turned round
        when only that way do their kinds allow it, from a thruster or into a sensor; as drawn
        otherwise, including between two operators, whatever the wires already there."""
        first, second = self.nodes[first_id].kind, self.nodes[second_id].kind
        forward = first.emits and second.receives
        backward = second.emits and first.receives
        return (second_id, first_id) if backward and not forward else (first_id, second_id)

    def connect(self, source_id: int, target_id: int) -> Wire | Refused:
        path = self.preview(source_id, target_id)
        if isinstance(path, Refused):
            return path
        wire = Wire(source_id, target_id, path)
        self.wires.append(wire)
        return wire

    def remove_wire(self, wire: Wire) -> None:
        self.wires.remove(wire)

    # Undo (D-027)

    def snapshot(self) -> BoardState:
        """The parts, the wires as drawn and the stock left, frozen."""
        nodes = tuple(self.nodes[i] for i in sorted(self.nodes))
        stock = tuple((kind, self._stock[kind]) for kind in Kind if kind in self._stock)
        return BoardState(nodes, tuple(self.wires), stock)  # in fixed orders, not dict order

    def restore(self, state: BoardState) -> None:
        """Put the board back as it was in `state`, in place, routes and all. Ids still never
        come back: the next part placed gets a new one."""
        self.nodes = {node.id: node for node in state.nodes}
        self.wires = list(state.wires)
        self._stock = dict(state.stock)

    def adopt(self, state: BoardState) -> Refused | None:
        """Put on this board a state built on another, a win of another level (D-092): its parts
        and wires as built, the stock left counted again from what this level hands out. Refused,
        and nothing changes, if a cell is off this zone, if the level's own locked parts differ,
        or if it holds more of a kind than this level hands out."""
        cells = {node.cell for node in state.nodes} | {c for w in state.wires for c in w.path}
        if not cells <= self._on_board:
            return Refused("the board goes outside this level's zone")
        locked = [n for n in self.nodes.values() if n.locked]
        if _placed(locked) != _placed(n for n in state.nodes if n.locked):
            return Refused("this level places other parts")
        free = [node.kind for node in state.nodes if not node.locked]
        stock = dict(self._total)
        for kind in Kind:
            used, total = free.count(kind), self.total(kind)
            if used and total == 0:
                return Refused(f"this level hands out no {kind.value}s")
            if total is not None and used > total:
                plural = "" if total == 1 else "s"
                return Refused(
                    f"this level hands out {_count(total)} {kind.value}{plural};"
                    f" the board has {_count(used)}"
                )
            if total is not None and kind in stock:
                stock[kind] = total - used
        self.restore(BoardState(state.nodes, state.wires, tuple(stock.items())))
        self._next_id = max([self._next_id, *(node.id + 1 for node in state.nodes)])
        return None

    # As plain data (D-024)

    def to_dict(self) -> dict:
        """The board as JSON-able data: the zone, what the level handed out, the components in
        id order and the wires in the order they were drawn, each naming its ends by their place
        in that list."""
        ids = sorted(self.nodes)
        index = {node_id: i for i, node_id in enumerate(ids)}
        return {
            "zone": [list(cell) for cell in self.cells],
            "stock": {kind.value: self._total[kind] for kind in Kind if kind in self._total},
            "parts": [
                {
                    "kind": node.kind.value,
                    "cell": list(node.cell),
                    "facing": None if node.facing is None else FACING_NAMES[node.facing],
                    "locked": node.locked,
                }
                for node in (self.nodes[i] for i in ids)
            ],
            "wires": [
                {
                    "from": index[wire.source],
                    "to": index[wire.target],
                    "path": [list(cell) for cell in wire.path],
                }
                for wire in self.wires
            ],
        }

    @classmethod
    def from_dict(cls, data: Mapping) -> Board:
        """A board from `to_dict`'s data: the parts placed in order, then the wires drawn in
        order, so the network is the one saved. A path comes back as saved unless the board had
        been edited with Move or Delete, or a part put on a wire; then it may take another route
        as short. Raises ValueError for data no board could hold."""
        stock = {Kind(name): left for name, left in data["stock"].items()}
        board = cls([tuple(cell) for cell in data["zone"]], stock)
        for part in data["parts"]:
            facing = part["facing"]
            placed = board.place(
                Kind(part["kind"]),
                tuple(part["cell"]),
                locked=part["locked"],
                facing=None if facing is None else FACING_NAMES.index(facing),
            )
            if isinstance(placed, Refused):
                raise ValueError(f"part {part}: {placed.reason}")
        for wire in data["wires"]:
            drawn = board.connect(wire["from"], wire["to"])
            if isinstance(drawn, Refused):
                raise ValueError(f"wire {wire['from']} -> {wire['to']}: {drawn.reason}")
        return board

    def route(self, start: Cell, goal: Cell) -> tuple[Cell, ...] | None:
        """Shortest free path between two component cells, both included; None if there is none.

        Dijkstra over (cell, heading) states with cost (steps, bends), compared in that order.
        Equal costs go to the path pushed first, with neighbours tried in direction order, so the
        result never depends on set or dict order.
        """
        edges_used = self._edges_used()
        blocked = {node.cell for node in self.nodes.values()}
        counter = itertools.count()
        # (steps, bends, tie-break, cell, heading into cell, path so far); heading -1 at the start
        heap = [(0, 0, next(counter), start, -1, (start,))]
        settled: set[tuple[Cell, int]] = set()
        while heap:
            steps, turns, _, cell, heading, path = heapq.heappop(heap)
            if cell == goal:
                return path if _uses_each_edge_once(path) else None
            if (cell, heading) in settled:
                continue
            settled.add((cell, heading))
            for out in range(6):
                nxt = neighbour(cell, out)
                if nxt not in self._on_board or (nxt in blocked and nxt != goal):
                    continue
                if heading >= 0 and not can_pass(edges_used.get(cell, set()), heading, out):
                    continue
                bend = int(heading >= 0 and out != heading)
                heapq.heappush(
                    heap, (steps + 1, turns + bend, next(counter), nxt, out, path + (nxt,))
                )
        return None

    # Internals

    def _route_again(self, saved: list[Wire], again: list[int]) -> Wire | None:
        """The wires at places `again` of `saved`, the wires as they were, routed again in the
        order they were drawn, each round the parts and the wires already there, which stay;
        each keeps its place. The first that finds no free path, if one does: the caller then
        puts the board back.
        """
        self.wires = [wire for i, wire in enumerate(saved) if i not in again]
        rerouted: dict[int, Wire] = {}
        for i in again:
            old = saved[i]
            path = self.route(self.nodes[old.source].cell, self.nodes[old.target].cell)
            if path is None:
                return old
            rerouted[i] = Wire(old.source, old.target, path)
            self.wires.append(rerouted[i])  # so the next ones route round it
        self.wires = [rerouted.get(i, wire) for i, wire in enumerate(saved)]
        return None

    def _edges_used(self) -> dict[Cell, set[int]]:
        """Edges of each free cell already taken by a wire."""
        used: dict[Cell, set[int]] = {}
        for wire in self.wires:
            for cell, entry, exit_ in crossings(wire.path):
                used.setdefault(cell, set()).update((entry, exit_))
        return used

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


def complexity(board: Board) -> int:
    """What a board costs in its level's score (D-028, D-045): its parts, the locked ones
    included; wires are free. It never changes the body, a sphere of radius 1 u."""
    return len(board.nodes)


def _uses_each_edge_once(path: tuple[Cell, ...]) -> bool:
    """A route found cell by cell could cross itself through an edge it already used."""
    seen: set[tuple[Cell, int]] = set()
    for cell, entry, exit_ in crossings(path):
        for edge in (entry, exit_):
            if (cell, edge) in seen:
                return False
            seen.add((cell, edge))
    return True


def _placed(nodes: Iterable[Node]) -> list[tuple[str, Cell, int | None]]:
    """Parts as placed, whatever their ids: to tell whether two boards' locked parts agree."""
    return sorted((n.kind.value, n.cell, n.facing) for n in nodes)


def _count(n: int) -> str:
    return {1: "one", 2: "two", 3: "three"}.get(n, str(n))
