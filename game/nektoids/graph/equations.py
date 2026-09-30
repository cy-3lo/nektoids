"""The equations of a network as plain ASCII text, for the developer view (D-016).

ASCII only: the default pygame font has no Greek letters. Pure Python, no pygame.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from nektoids.graph.analysis import LoopReport, Status, active_branch
from nektoids.graph.board import Kind
from nektoids.graph.evaluate import RATE_MAX, SOURCE_RATE
from nektoids.graph.network import Network, cyclic_components, label, topological_order

LIMIT = 100  # characters of a substituted sub-expression before it is shown by its name


def _wrap(text: str) -> str:
    """Parentheses around a sum or difference, unless it is already inside a call or bars."""
    depth, inside_bars = 0, False
    for k, char in enumerate(text):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "|":
            inside_bars = not inside_bars
        elif depth == 0 and not inside_bars and text[k : k + 3] in (" + ", " - "):
            return f"({text})"
    return text


def _rate_text(net: Network, i: int, name_of: Callable[[int], str]) -> str:
    """Rate of operator i from the texts of the nodes that feed it, split by their fan-out."""
    terms = []
    for j in (int(j) for j in net.slots[i] if j < net.n):
        terms.append(name_of(j) if net.outdeg[j] == 1 else f"{name_of(j)}/{net.outdeg[j]}")
    if not terms:
        return "0"
    if net.kinds[i] is Kind.DIFFERENCE and len(terms) == 2:
        inner = f"|{terms[0]} - {terms[1]}|"
    else:
        inner = " + ".join(terms)
    gain = net.gain[i]
    if gain == 2.0:
        body = f"2*{_wrap(inner)}"
    elif gain == 0.5:
        body = f"{_wrap(inner)}/2"
    else:
        body = inner
    return f"min(R, {body})"


def node_equations(net: Network) -> tuple[str, ...]:
    """One line per node, each in terms of the nodes that feed it; the first line gives R."""
    lines = [f"R = {RATE_MAX:g}"]
    for i in range(net.n):
        name = label(net, i)
        if net.kinds[i] is Kind.EYE:
            lines.append(f"{name} = eye")
        elif net.kinds[i] is Kind.SOURCE:
            lines.append(f"{name} = {SOURCE_RATE:g}")
        else:
            lines.append(f"{name} = {_rate_text(net, i, lambda j: label(net, j))}")
    return tuple(lines)


def composed(net: Network) -> dict[int, str] | None:
    """For each thruster, its rate from the sensors by substitution; None if there is a loop.

    A sub-expression longer than LIMIT is left as the node's name, since a fork duplicates it.
    """
    order = topological_order(net)
    if order is None:
        return None
    text: dict[int, str] = {}

    def name_of(j: int) -> str:
        return text[j] if len(text[j]) <= LIMIT else label(net, j)

    for i in order:
        text[i] = label(net, i) if net.gain[i] == 0 else _rate_text(net, i, name_of)
    return {int(i): f"{label(net, i)} = {text[int(i)]}" for i in net.thrusters}


def _linear(terms: list[tuple[float, str]]) -> str:
    out = ""
    for coefficient, name in terms:
        size = abs(coefficient)
        body = name if size == 1.0 else f"{size:g}*{name}"
        if not out:
            out = f"-{body}" if coefficient < 0 else body
        else:
            out += f" - {body}" if coefficient < 0 else f" + {body}"
    return out or "0"


def branch_equations(net: Network, y: np.ndarray) -> tuple[str, ...]:
    """The affine equations of each node in a loop on the branch that holds at rates `y` (1-D)."""
    branch = active_branch(net, y)
    lines = []
    for members in cyclic_components(net):
        for i in members:
            if branch.const[i]:
                lines.append(f"{label(net, i)} = R")
                continue
            terms = [
                (float(branch.coef[i, j]), label(net, j)) for j in np.flatnonzero(branch.coef[i])
            ]
            lines.append(f"{label(net, i)} = {_linear(terms)}")
    return tuple(lines)


def report_lines(net: Network, report: LoopReport) -> tuple[str, ...]:
    """The loop report in words, one line per point."""
    if report.status is Status.DAG:
        return ("no loop: one pass in topological order",)
    lines = []
    for part in report.components:
        members = " ".join(label(net, i) for i in part.members)
        lines.append(f"loop {members}: rho = {part.rho:.3g}")
        if part.determinants is not None:
            lines.append(
                "  det(I - W_s) per sign pattern: "
                + ", ".join(f"{d:.3g}" for d in part.determinants)
            )
    if report.status is Status.CONTRACTIVE:
        lines.append(f"contractive (q = {report.factor:.3g}): the solution is unique")
    else:
        lines.append("rho >= 1: evaluation refuses this loop")
        if all(part.coherent for part in report.components):
            lines.append("  every uncapped branch is regular: the solution is unique without caps")
        elif any(part.coherent is False for part in report.components):
            lines.append("  a branch is singular or reversed: the solution may not be unique")
    return tuple(lines)
