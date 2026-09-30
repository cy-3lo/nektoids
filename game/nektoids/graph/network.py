"""The board compiled for the dynamics: nodes and wires as numpy arrays (D-017).

A `Network` holds no screen positions and no wire paths, only what the maths and the physics
need, including where each node sits on the body: the board is the body (D-018). Node `i` of the
network is the `i`-th node by id. Inputs are gathered slot by slot, sorted by source index, so the
order in which wires were drawn can never change a result (invariant 1).

`from_edges` accepts loops, which `Board` refuses, so that tests and developer scenarios can build
them. Pure numpy, no pygame.
"""

from __future__ import annotations

import heapq
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import numpy as np

from nektoids.graph.board import Board, Kind
from nektoids.graph.hexgrid import Cell, to_pixel

MARGIN = 1e-9  # a loop gain this close to 1 counts as 1

# Factor from the sum of incoming rates to the node's rate. Sensors are not here: they are given.
GAIN: dict[Kind, float] = {
    Kind.DOUBLE: 2.0,
    Kind.HALVE: 0.5,
    Kind.SUM: 1.0,
    Kind.DIFFERENCE: 1.0,
    Kind.THRUSTER: 1.0,
}


def _frozen(array: np.ndarray) -> np.ndarray:
    array.setflags(write=False)
    return array


@dataclass(frozen=True, eq=False)
class Network:
    ids: tuple[int, ...]  # board node id of each network node, ascending
    kinds: tuple[Kind, ...]
    facing: tuple[int | None, ...]  # hex direction of eyes and thrusters (D-009)
    mount: np.ndarray  # (n, 2): where each node sits on the body, in body radii (D-018)
    edges: np.ndarray  # (E, 2) int: source index, target index, in the order wires were drawn
    slots: np.ndarray  # (n, K) int: source index feeding each input slot, sorted; n = unused
    signs: np.ndarray  # (n, K): +1, except the second input of a Difference (-1); 0 = unused
    gain: np.ndarray  # (n,): see GAIN; 0 for sensors
    outdeg: np.ndarray  # (n,) int: number of wires leaving each node
    eyes: np.ndarray  # indices of the eyes, ascending
    sources: np.ndarray  # indices of the sources, ascending
    thrusters: np.ndarray  # indices of the thrusters, ascending

    @property
    def n(self) -> int:
        return len(self.kinds)

    @property
    def sensors(self) -> np.ndarray:
        """Indices of the nodes whose rate is given, not computed: eyes and sources."""
        return np.sort(np.concatenate((self.eyes, self.sources)))

    @classmethod
    def from_board(cls, board: Board) -> Network:
        ids = sorted(board.nodes)
        index = {node_id: i for i, node_id in enumerate(ids)}
        return cls.from_edges(
            [board.nodes[i].kind for i in ids],
            [(index[wire.source], index[wire.target]) for wire in board.wires],
            [board.nodes[i].facing for i in ids],
            ids=ids,
            mount=body_mounts(board.cells, [board.nodes[i].cell for i in ids]),
        )

    @classmethod
    def from_edges(
        cls,
        kinds: Sequence[Kind],
        edges: Iterable[tuple[int, int]],
        facing: Sequence[int | None] | None = None,
        ids: Sequence[int] | None = None,
        mount: np.ndarray | None = None,
    ) -> Network:
        """Network of nodes 0..n-1 of the given kinds and directed wires (source, target).

        mount: (n, 2) positions on the body in body radii; all at the centre if None.

        Raises ValueError for what no board could hold: a wire out of range, out of a thruster or
        into a sensor, a duplicate wire, or more inputs than the kind takes. Loops and a wire from
        a node to itself are allowed.
        """
        kinds = tuple(kinds)
        n = len(kinds)
        pairs = tuple((int(a), int(b)) for a, b in edges)
        if len(set(pairs)) != len(pairs):
            raise ValueError("duplicate wire")
        incoming: list[list[int]] = [[] for _ in range(n)]
        outdeg = np.zeros(n, dtype=np.int64)
        for a, b in pairs:
            if not (0 <= a < n and 0 <= b < n):
                raise ValueError(f"wire {a} -> {b} leaves the graph")
            if not kinds[a].emits:
                raise ValueError(f"{kinds[a].value} {a} has no output")
            if not kinds[b].receives:
                raise ValueError(f"{kinds[b].value} {b} has no input")
            incoming[b].append(a)
            outdeg[a] += 1
        for b, feeders in enumerate(incoming):
            limit = kinds[b].max_inputs
            if limit is not None and len(feeders) > limit:
                raise ValueError(f"{kinds[b].value} {b} takes at most {limit} inputs")
            feeders.sort()
        width = max(1, max((len(feeders) for feeders in incoming), default=0))
        slots = np.full((n, width), n, dtype=np.int64)
        signs = np.zeros((n, width))
        for b, feeders in enumerate(incoming):
            for k, a in enumerate(feeders):
                slots[b, k] = a
                signs[b, k] = -1.0 if kinds[b] is Kind.DIFFERENCE and k == 1 else 1.0
        if facing is None:
            facing = [kind.default_facing for kind in kinds]
        ids = tuple(range(n)) if ids is None else tuple(ids)
        mount = np.zeros((n, 2)) if mount is None else np.array(mount, dtype=np.float64)
        if len(ids) != n or len(facing) != n or mount.shape != (n, 2):
            raise ValueError("ids, facing and mount need one entry per node")

        def indices(kind: Kind) -> np.ndarray:
            return _frozen(np.array([i for i, k in enumerate(kinds) if k is kind], dtype=np.int64))

        return cls(
            ids=ids,
            kinds=kinds,
            facing=tuple(facing),
            mount=_frozen(mount),
            edges=_frozen(np.array(pairs, dtype=np.int64).reshape(-1, 2)),
            slots=_frozen(slots),
            signs=_frozen(signs),
            gain=_frozen(np.array([GAIN.get(kind, 0.0) for kind in kinds])),
            outdeg=_frozen(outdeg),
            eyes=indices(Kind.EYE),
            sources=indices(Kind.SOURCE),
            thrusters=indices(Kind.THRUSTER),
        )


def body_mounts(zone: Sequence[Cell], cells: Sequence[Cell]) -> np.ndarray:
    """(len(cells), 2): where parts on these cells sit on the body, in body radii (D-018).

    The board is the body seen from above, forward = E = +x, and the board's up is the body's
    left, +y. The centre of the zone's cell centres is the body's centre, and the zone's
    outermost cells lie on the rim. zone: every cell of the board, row by row (`Board.cells`),
    so the sums run in a fixed order.
    """
    if not zone:
        return np.zeros((len(cells), 2))

    def body_frame(some: Sequence[Cell]) -> np.ndarray:
        points = np.array([to_pixel(cell, 1.0, (0.0, 0.0)) for cell in some]).reshape(-1, 2)
        return points * np.array([1.0, -1.0])  # screen y points down, the body's left is up

    zone_points = body_frame(zone)
    centre = zone_points.mean(axis=0)
    offset = zone_points - centre
    reach = float(np.sqrt(offset[:, 0] ** 2 + offset[:, 1] ** 2).max())
    return (body_frame(cells) - centre) / (reach if reach > 0.0 else 1.0)


def topological_order(net: Network) -> tuple[int, ...] | None:
    """Node indices with every source before its targets, ties by index; None if there is a loop."""
    indegree = [0] * net.n
    successors: list[list[int]] = [[] for _ in range(net.n)]
    for a, b in net.edges.tolist():
        indegree[b] += 1
        successors[a].append(b)
    ready = [i for i in range(net.n) if indegree[i] == 0]
    heapq.heapify(ready)
    order: list[int] = []
    while ready:
        i = heapq.heappop(ready)
        order.append(i)
        for j in successors[i]:
            indegree[j] -= 1
            if indegree[j] == 0:
                heapq.heappush(ready, j)
    return tuple(order) if len(order) == net.n else None


def _reachability(net: Network) -> np.ndarray:
    """(n, n) bool: whether a path (possibly empty) leads from node i to node j."""
    reach = np.eye(net.n, dtype=bool)
    reach[net.edges[:, 0], net.edges[:, 1]] = True
    for _ in range(max(1, net.n.bit_length())):  # path length doubles each round
        reach = reach | (reach @ reach)
    return reach


def components(net: Network) -> tuple[tuple[int, ...], ...]:
    """Strongly connected components, each sorted, ordered by smallest member."""
    reach = _reachability(net)
    seen = np.zeros(net.n, dtype=bool)
    found: list[tuple[int, ...]] = []
    for i in range(net.n):
        if not seen[i]:
            members = np.flatnonzero(reach[i] & reach[:, i])
            seen[members] = True
            found.append(tuple(members.tolist()))
    return tuple(found)


def cyclic_components(net: Network) -> tuple[tuple[int, ...], ...]:
    """The components that contain a loop: several nodes, or one with a wire to itself."""
    selfloops = {a for a, b in net.edges.tolist() if a == b}
    return tuple(c for c in components(net) if len(c) > 1 or c[0] in selfloops)


_LETTER = {
    Kind.EYE: "E",
    Kind.SOURCE: "S",
    Kind.DOUBLE: "D",
    Kind.HALVE: "H",
    Kind.SUM: "P",
    Kind.DIFFERENCE: "M",
    Kind.THRUSTER: "T",
}


def label(net: Network, i: int) -> str:
    """Short name of node i for panels: E0 eye, S1 source, D2, H3, P4 sum, M5 difference, T6."""
    return f"{_LETTER[net.kinds[i]]}{i}"


def abs_coupling(net: Network) -> np.ndarray:
    """|W|, shape (n, n): how far node j's rate can move node i's; sensors have no row or column.

    |W|[i, j] = gain_i / outdeg_j if a wire runs j -> i: F(y) is piecewise affine in the rates
    of the operators, sensors being given, and abs and cap only drop or flip entries of the
    matrix of each piece, so |W| bounds how far one node can move another. For a DAG, |W| is
    nilpotent.
    """
    n = net.n
    w = np.zeros((n, n))
    for i in range(n):
        for k in range(net.slots.shape[1]):
            j = int(net.slots[i, k])
            if j < n and net.gain[j] > 0:  # a sensor is given, so it is not a variable
                w[i, j] = net.gain[i] / net.outdeg[j]
    return w


def contraction_factor(net: Network) -> float | None:
    """q < 1 such that F shrinks distances by q in a weighted max-norm; None if rho(|W|) >= 1.

    With v = (I - |W|)^-1 1 we have |W| v = v - 1, so the norm weighted by v is shrunk by
    q = max_i (|W| v)_i / v_i = 1 - 1 / max(v). Such a v >= 1 exists exactly when rho(|W|) < 1.
    Then, for a constant input, the lagged system has one equilibrium and every start goes to it
    (an Euler step of size h shrinks distances by 1 - h (1 - q)). Otherwise a loop may latch,
    oscillate or integrate.
    """
    if topological_order(net) is not None:
        return 0.0
    w = abs_coupling(net)
    try:
        v = np.linalg.solve(np.eye(net.n) - w, np.ones(net.n))
    except np.linalg.LinAlgError:
        return None
    if not (np.all(v >= 1 - MARGIN) and np.allclose(w @ v, v - 1, rtol=1e-6, atol=1e-9)):
        return None
    q = 1.0 - 1.0 / float(v.max())
    return q if q < 1.0 - MARGIN else None
