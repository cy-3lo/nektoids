"""The equations of a network as plain ASCII text, for the developer view (D-017).

ASCII only: the default pygame font has no Greek letters. Pure Python, no pygame.
"""

from __future__ import annotations

from nektoids.graph.analysis import LoopReport, Status
from nektoids.graph.dynamics import RATE_MAX, TAU
from nektoids.graph.network import Network, label


def _terms(net: Network, i: int) -> list[str]:
    """The wires into node i, by their source: E0, or E0/2 when E0 sends two wires."""
    terms = []
    for j in (int(j) for j in net.slots[i] if j < net.n):
        terms.append(label(net, j) if net.outdeg[j] == 1 else f"{label(net, j)}/{net.outdeg[j]}")
    return terms


def node_equations(net: Network) -> tuple[str, ...]:
    """One line per node; the first gives R and tau. Sensors are given, the rest follow their
    kind's law, which writes its own equation (D-202)."""
    lines = [f"R = {RATE_MAX:g}, tau = {TAU * 1000:.1f} ms"]
    for i in range(net.n):
        name, law = label(net, i), net.kinds[i].spec.law
        if law is None:
            lines.append(f"{name} = {net.kinds[i].value}")
        else:
            lines.append(law.equation(name, _terms(net, i)))
    return tuple(lines)


def report_lines(net: Network, report: LoopReport) -> tuple[str, ...]:
    """The loop report in words, one line per point."""
    if report.status is Status.DAG:
        return ("no loop",)
    lines = []
    for part in report.components:
        members = " ".join(label(net, i) for i in part.members)
        lines.append(f"loop {members}: rho = {part.rho:.3g}")
    if report.status is Status.CONTRACTIVE:
        lines.append(f"rho < 1 (q = {report.factor:.3g}): it settles to one value")
    else:
        lines.append("rho >= 1: it may hold a value, latch, oscillate or saturate")
    return tuple(lines)
