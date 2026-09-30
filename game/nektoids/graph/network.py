"""The board compiled for evaluation: nodes and wires as numpy arrays (D-016).

A `Network` holds no positions and no wire paths, only what the maths needs. Node `i` of the
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
        )

    @classmethod
    def from_edges(
        cls,
        kinds: Sequence[Kind],
        edges: Iterable[tuple[int, int]],
        facing: Sequence[int | None] | None = None,
        ids: Sequence[int] | None = None,
    ) -> Network:
        """Network of nodes 0..n-1 of the given kinds and directed wires (source, target).

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
        if len(ids) != n or len(facing) != n:
            raise ValueError("ids and facing need one entry per node")

        def indices(kind: Kind) -> np.ndarray:
            return _frozen(np.array([i for i, k in enumerate(kinds) if k is kind], dtype=np.int64))

        return cls(
            ids=ids,
            kinds=kinds,
            facing=tuple(facing),
            edges=_frozen(np.array(pairs, dtype=np.int64).reshape(-1, 2)),
            slots=_frozen(slots),
            signs=_frozen(signs),
            gain=_frozen(np.array([GAIN.get(kind, 0.0) for kind in kinds])),
            outdeg=_frozen(outdeg),
            eyes=indices(Kind.EYE),
            sources=indices(Kind.SOURCE),
            thrusters=indices(Kind.THRUSTER),
        )


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

    With sensors known, the unknown rates solve y = F(y; sensors), F piecewise affine.
    |W|[i, j] = gain_i / outdeg_j if a wire runs j -> i. On every branch of F (a sign for each abs,
    a saturated or free state for each cap) the matrix of the affine system has spectral radius at
    most rho(|W|), because abs and cap only drop or flip entries. For a DAG, |W| is nilpotent.
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
    q = max_i (|W| v)_i / v_i = 1 - 1 / max(v). Such a v >= 1 exists exactly when rho(|W|) < 1, and
    then the solution is unique and Jacobi iteration converges to it.
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
