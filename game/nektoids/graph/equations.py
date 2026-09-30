"""The equations of a network as plain ASCII text, for the developer view (D-017).

ASCII only: the default pygame font has no Greek letters. Pure Python, no pygame.
"""

from __future__ import annotations

from nektoids.graph.analysis import LoopReport, Status
from nektoids.graph.board import Kind
from nektoids.graph.dynamics import RATE_MAX, TAU
from nektoids.graph.network import Network, label


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


def _target_text(net: Network, i: int) -> str:
    """What the inputs of operator i ask for: min(R, gain * |sum of its wires|)."""
    terms = []
    for j in (int(j) for j in net.slots[i] if j < net.n):
        terms.append(label(net, j) if net.outdeg[j] == 1 else f"{label(net, j)}/{net.outdeg[j]}")
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
    """One line per node; the first gives R and tau. Sensors are given, operators relax."""
    lines = [f"R = {RATE_MAX:g}, tau = {TAU * 1000:.1f} ms"]
    for i in range(net.n):
        name = label(net, i)
        if net.kinds[i] is Kind.EYE:
            lines.append(f"{name} = eye")
        elif net.kinds[i] is Kind.SOURCE:
            lines.append(f"{name} = source")
        else:
            lines.append(f"tau d{name}/dt = -{name} + {_target_text(net, i)}")
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
