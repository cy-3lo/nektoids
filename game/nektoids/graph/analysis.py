"""What the loops of a network can do, and what looks wrong in a graph (D-017).

Developer tools: the game never calls this. Pure numpy, no pygame.

With the lag of every node a loop is always computable; the report says what to expect from it.
If rho(|W|) < 1 (see `network.contraction_factor`) the loop has one equilibrium for a constant
input and every start goes to it: it settles. If rho(|W|) >= 1 it may also hold a value, latch
on one of several states, oscillate, or saturate; watch it run. The bound is sufficient, not
necessary: a Difference can cancel what a loop feeds back.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np

from nektoids.graph.board import Kind
from nektoids.graph.network import (
    Network,
    abs_coupling,
    contraction_factor,
    cyclic_components,
    label,
)


class Status(Enum):
    DAG = "dag"  # no loop
    CONTRACTIVE = "contractive"  # rho(|W|) < 1: every loop settles to one value
    NONCONTRACTIVE = "noncontractive"  # rho(|W|) >= 1: a loop may latch, oscillate or integrate


@dataclass(frozen=True)
class LoopComponent:
    members: tuple[int, ...]  # node indices of one strongly connected component with a loop
    rho: float  # spectral radius of |W| restricted to the component


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
        parts.append(LoopComponent(members, rho))
    status = Status.CONTRACTIVE if factor is not None else Status.NONCONTRACTIVE
    return LoopReport(status, factor, tuple(parts))


def problems(net: Network) -> tuple[str, ...]:
    """What looks wrong or idle in the graph, for the developer panel."""
    fed = _fed_by_a_sensor(net)
    found = []
    for i in range(net.n):
        name, kind = label(net, i), net.kinds[i]
        inputs = int((net.slots[i] < net.n).sum())
        if net.gain[i] > 0 and i not in fed:
            found.append(f"{name} is fed by no sensor: its rate stays 0")
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
