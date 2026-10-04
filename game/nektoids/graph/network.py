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
from nektoids.graph.kinds import Category
from nektoids.graph.laws import Law

SENSOR, ACTUATOR = Category.SENSOR, Category.ACTUATOR

MARGIN = 1e-9  # a loop gain this close to 1 counts as 1


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
    gain: np.ndarray  # (n,): its law's slope, how far it follows one input (D-202); 0 for sensors
    given: np.ndarray  # (n,) bool: its rate is given, not computed: the sensors
    laws: tuple[tuple[Law, np.ndarray, np.ndarray], ...]  # each law, its nodes, their slots
    senses: tuple[tuple[Kind, np.ndarray], ...]  # each sensor kind, its nodes; table order
    actions: tuple[tuple[Kind, np.ndarray], ...]  # each actuator kind, its nodes; table order
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
        for b, feeders in enumerate(incoming):
            for k, a in enumerate(feeders):
                slots[b, k] = a
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
            gain=_frozen(np.array([k.spec.law.slope if k.spec.law else 0.0 for k in kinds])),
            given=_frozen(np.array([kind.spec.law is None for kind in kinds], dtype=bool)),
            laws=_by_law(kinds, slots),
            senses=tuple((k, indices(k)) for k in Kind if k.category is SENSOR and k in kinds),
            actions=tuple((k, indices(k)) for k in Kind if k.category is ACTUATOR and k in kinds),
            outdeg=_frozen(outdeg),
            eyes=indices(Kind.EYE),
            sources=indices(Kind.SOURCE),
            thrusters=indices(Kind.THRUSTER),
        )


def _by_law(
    kinds: Sequence[Kind], slots: np.ndarray
) -> tuple[tuple[Law, np.ndarray, np.ndarray], ...]:
    """Each law of the nodes, with the nodes that follow it, ascending, and their rows of
    `slots`; laws in the order of the table of kinds, kinds with equal laws together (a Sum and
    a Thruster). Nodes step independently, each from the same state, so this order cannot change
    a result; it is fixed all the same (invariant 1)."""
    laws: list[Law] = []
    members: list[list[int]] = []
    for kind in Kind:
        nodes = [i for i, k in enumerate(kinds) if k is kind]
        if kind.spec.law is None or not nodes:
            continue
        if kind.spec.law not in laws:
            laws.append(kind.spec.law)
            members.append([])
        members[laws.index(kind.spec.law)].extend(nodes)
    found = []
    for law, nodes in zip(laws, members, strict=True):
        index = np.array(sorted(nodes), dtype=np.int64)
        found.append((law, _frozen(index), _frozen(slots[index])))
    return tuple(found)


def body_disc(zone: Sequence[Cell]) -> tuple[tuple[float, float], float]:
    """Where the body lies on the board (D-018), at hex size 1 with cell (0, 0) at the origin and
    screen y down: the centre of the zone's cell centres, and the distance from it to the
    farthest of them, the body's radius. zone: every cell of the board, row by row
    (`Board.cells`), so the sums run in a fixed order."""
    if not zone:
        return (0.0, 0.0), 0.0
    points = np.array([to_pixel(cell, 1.0, (0.0, 0.0)) for cell in zone])
    centre = points.mean(axis=0)
    offset = points - centre
    reach = float(np.sqrt(offset[:, 0] ** 2 + offset[:, 1] ** 2).max())
    return (float(centre[0]), float(centre[1])), reach


def body_mounts(zone: Sequence[Cell], cells: Sequence[Cell]) -> np.ndarray:
    """(len(cells), 2): where parts on these cells sit on the body, in body radii (D-018).

    The board is the body seen from above, forward = E = +x, and the board's up is the body's
    left, +y: the zone's outermost cells lie on the rim of `body_disc`.
    """
    (cx, cy), reach = body_disc(zone)
    points = np.array([to_pixel(cell, 1.0, (0.0, 0.0)) for cell in cells]).reshape(-1, 2)
    offset = (points - np.array([cx, cy])) * np.array([1.0, -1.0])  # the body's left is up
    return offset / (reach if reach > 0.0 else 1.0)


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


def label(net: Network, i: int) -> str:
    """Short name of node i for panels: E0 eye, S1 source, D2, H3, P4 sum, M5 difference, T6."""
    return f"{net.kinds[i].spec.letter}{i}"


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
            if j < n and not net.given[j]:  # a sensor is given, so it is not a variable
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
