"""What the loops of a network do to its evaluation, and what is wrong with a graph (D-016).

Developer tools: the game never calls this. Pure numpy, no pygame.

`evaluate` relies on one guarantee only, rho(|W|) < 1 (see `network.contraction_factor`). The
report adds a sharper look at each loop. On a branch of F with no cap active, the unknown rates
follow y = W_s y + b_s, where W_s carries the sign chosen at every Difference. If det(I - W_s) > 0
on every sign pattern, F is coherently oriented and the solution is unique even where rho(|W|) >= 1;
a non-positive determinant flags a branch that is singular or reversed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import product

import numpy as np

from nektoids.graph.board import Kind
from nektoids.graph.evaluate import RATE_MAX
from nektoids.graph.network import (
    MARGIN,
    Network,
    abs_coupling,
    contraction_factor,
    cyclic_components,
    label,
)

MAX_SIGNED = 10  # Differences in one loop up to which every sign pattern is tried (2**10)


class Status(Enum):
    DAG = "dag"  # no loop: one pass
    CONTRACTIVE = "contractive"  # rho(|W|) < 1: unique solution, found by iteration
    NONCONTRACTIVE = "noncontractive"  # rho(|W|) >= 1: evaluate refuses


@dataclass(frozen=True)
class LoopComponent:
    members: tuple[int, ...]  # node indices of one strongly connected component with a loop
    rho: float  # spectral radius of |W| restricted to the component
    determinants: tuple[float, ...] | None  # det(I - W_s) per sign pattern; None if too many

    @property
    def coherent(self) -> bool | None:
        """Whether every uncapped branch is regular and alike in orientation; None if unchecked."""
        if self.determinants is None:
            return None
        return all(d > MARGIN for d in self.determinants)


@dataclass(frozen=True)
class LoopReport:
    status: Status
    factor: float | None  # contraction factor q, None unless contractive (0 for a DAG)
    components: tuple[LoopComponent, ...]


def loop_report(net: Network) -> LoopReport:
    factor = contraction_factor(net)
    cyclic = cyclic_components(net)
    if not cyclic:
        return LoopReport(Status.DAG, 0.0, ())
    w = abs_coupling(net)
    parts = []
    for members in cyclic:
        inside = list(members)
        rho = float(np.max(np.abs(np.linalg.eigvals(w[np.ix_(inside, inside)]))))
        parts.append(LoopComponent(members, rho, _determinants(net, members)))
    status = Status.CONTRACTIVE if factor is not None else Status.NONCONTRACTIVE
    return LoopReport(status, factor, tuple(parts))


def _determinants(net: Network, members: tuple[int, ...]) -> tuple[float, ...] | None:
    position = {node: k for k, node in enumerate(members)}
    signed = [
        i
        for i in members
        if net.kinds[i] is Kind.DIFFERENCE and int((net.slots[i] < net.n).sum()) == 2
    ]
    if len(signed) > MAX_SIGNED:
        return None
    found = []
    for pattern in product((1.0, -1.0), repeat=len(signed)):
        sign_of = dict(zip(signed, pattern, strict=True))
        branch = np.zeros((len(members), len(members)))
        for i in members:
            for k in range(net.slots.shape[1]):
                j = int(net.slots[i, k])
                if j in position:
                    weight = net.gain[i] * sign_of.get(i, 1.0) * net.signs[i, k] / net.outdeg[j]
                    branch[position[i], position[j]] += weight
        found.append(float(np.linalg.det(np.eye(len(members)) - branch)))
    return tuple(found)


@dataclass(frozen=True)
class Branch:
    """The affine system F follows at some rates: y_i = sum_j coef[i, j] y_j + const[i].

    Rows of sensors are empty: their rates are given. `const` is RATE_MAX where a cap is active.
    """

    coef: np.ndarray  # (n, n)
    const: np.ndarray  # (n,)

    def solution(self, net: Network, y: np.ndarray) -> np.ndarray:
        """The rates this branch gives for the sensor rates in `y`, by one linear solve."""
        unknown = np.flatnonzero(net.gain > 0)
        known = np.flatnonzero(net.gain == 0)
        rhs = self.coef[np.ix_(unknown, known)] @ y[known] + self.const[unknown]
        out = y.astype(np.float64)
        out[unknown] = np.linalg.solve(
            np.eye(len(unknown)) - self.coef[np.ix_(unknown, unknown)], rhs
        )
        return out


def active_branch(net: Network, y: np.ndarray) -> Branch:
    """The branch of F (sign of each Difference, cap state of each node) that holds at rates `y`."""
    n = net.n
    flux = np.append(y / np.maximum(net.outdeg, 1), 0.0)
    coef = np.zeros((n, n))
    const = np.zeros(n)
    for i in range(n):
        if net.gain[i] == 0:
            continue
        total = sum(net.signs[i, k] * flux[net.slots[i, k]] for k in range(net.slots.shape[1]))
        if net.gain[i] * abs(total) >= RATE_MAX:
            const[i] = RATE_MAX
            continue
        sign = -1.0 if total < 0 else 1.0
        for k in range(net.slots.shape[1]):
            j = int(net.slots[i, k])
            if j < n:
                coef[i, j] += net.gain[i] * sign * net.signs[i, k] / net.outdeg[j]
    return Branch(coef, const)


def problems(net: Network) -> tuple[str, ...]:
    """What looks wrong or idle in the graph, for the developer panel."""
    fed = _fed_by_a_sensor(net)
    found = []
    for i in range(net.n):
        name, kind = label(net, i), net.kinds[i]
        inputs = int((net.slots[i] < net.n).sum())
        if net.gain[i] > 0 and i not in fed:
            found.append(f"{name} is fed by no sensor: its rate is always 0")
        elif kind in (Kind.SUM, Kind.DIFFERENCE) and inputs == 1:
            found.append(f"{name} has one input and passes it through")
        if kind is not Kind.THRUSTER and net.outdeg[i] == 0:
            found.append(f"{name} sends its rate nowhere")
    return tuple(found)


def _fed_by_a_sensor(net: Network) -> set[int]:
    """Nodes with a sensor somewhere upstream, sensors included."""
    reached = set(net.sensors.tolist())
    edges = net.edges.tolist()
    changed = True
    while changed:
        changed = False
        for a, b in edges:
            if a in reached and b not in reached:
                reached.add(b)
                changed = True
    return reached
