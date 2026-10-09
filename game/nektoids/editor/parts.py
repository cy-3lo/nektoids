"""The parts as the player reads them: each kind's name in the menu, and what its info box says
(D-036): what it does, what its paint does if it may be painted (D-503), then what may come in
and go out, from the board's own rules (D-014,
D-016), the names and paragraphs from the table of kinds (`graph/kinds.py`, D-202). Rates run
from 0 to 1, what one wire carries. Pure Python, no pygame.
"""

from __future__ import annotations

from nektoids.graph.board import Kind
from nektoids.graph.kinds import Category

NAME = {kind: kind.spec.name for kind in Kind}  # from the table of kinds (D-202)
WHAT = {kind: kind.spec.what for kind in Kind}  # a paragraph the box wraps (D-094)
PAINTED = {  # what Paint does to it (D-502)
    Kind.EYE: "Amber, it senses amber light only; painted violet, violet light only.",
    Kind.SOURCE: "Amber, it sends an amber signal; painted violet, a violet one.",
    Kind.THRUSTER: "Amber, it pushes with the amber signal only; painted violet, the violet.",
    Kind.TINT: "Its colour is the one it sends: amber, or violet once painted.",
    Kind.FILTER: "Its colour is the one it lets through: amber, or violet once painted.",
}


def ports(kind: Kind) -> tuple[str, str]:
    """What may come into the part, and what may go out of it."""
    if kind.category is Category.SENSOR:
        inward = "nothing"
    elif kind.max_inputs is not None:
        inward = f"{_count(kind.max_inputs)} wires at most"
    else:
        inward = "any number of wires"
    if not kind.emits:
        outward = "nothing"
    elif kind.max_outputs is not None:
        outward = f"{_count(kind.max_outputs)} wire"
    else:
        outward = "any number of wires"
    return f"In: {inward}.", f"Out: {outward}."


def info(kind: Kind, colours: bool = True) -> tuple[str, ...]:
    """The paragraphs of the part's info box, after its name: what it does, its paint if it may
    be painted on a level that shows colour (D-509), In, Out."""
    painted = (PAINTED[kind],) if kind.paintable and colours else ()
    return (WHAT[kind], *painted, *ports(kind))


def _count(n: int) -> str:
    return {1: "one", 2: "two", 3: "three"}.get(n, str(n))
