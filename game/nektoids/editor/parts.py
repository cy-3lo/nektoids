"""The parts as the player reads them: each kind's name in the menu, and what its info box says
(D-036): what it does, then what may come in and go out, from the board's own rules (D-014,
D-016). Rates run from 0 to 1, what one wire carries. Pure Python, no pygame.
"""

from __future__ import annotations

from nektoids.graph.board import Category, Kind

NAME = {
    Kind.EYE: "Eye",
    Kind.SOURCE: "Source",
    Kind.DOUBLE: "Double",
    Kind.HALVE: "Halve",
    Kind.SUM: "Sum",
    Kind.DIFFERENCE: "Diff",
    Kind.THRUSTER: "Thruster",
}

# What each part does, a paragraph the box wraps to its width (D-094).
WHAT = {
    Kind.EYE: "Reads the light that falls on its flat face: more from a light near it and in front"
    " of it, nothing in a shadow; it sends 1 at most.",
    Kind.SOURCE: "Senses nothing: it sends a steady 1, a drive of the swimmer's own.",
    Kind.DOUBLE: "Sends twice what comes in, 1 at most.",
    Kind.HALVE: "Sends half what comes in.",
    Kind.SUM: "Sends the sum of its two inputs, 1 at most.",
    Kind.DIFFERENCE: "Sends the gap between its two inputs, |a - b|: the same whichever way round"
    " they come.",
    Kind.THRUSTER: "Pushes the body the way it points, as hard as what comes in. Off the centre, it"
    " turns the body too: where it sits is its lever.",
}


def ports(kind: Kind) -> tuple[str, str]:
    """What may come into the part, and what may go out of it."""
    if kind.category is Category.SENSOR:
        inward = "nothing"
    elif kind.max_inputs is not None:
        inward = f"{_count(kind.max_inputs)} wires at most; with one, it passes it on"
    else:
        inward = "any number of wires, added"
    if not kind.emits:
        outward = "nothing"
    elif kind.max_outputs is not None:
        outward = f"{_count(kind.max_outputs)} wire"
    else:
        outward = "any number of wires, sharing what it sends"
    return f"In: {inward}.", f"Out: {outward}."


def info(kind: Kind) -> tuple[str, ...]:
    """The paragraphs of the part's info box, after its name: what it does, In, Out."""
    return (WHAT[kind], *ports(kind))


def _count(n: int) -> str:
    return {1: "one", 2: "two", 3: "three"}.get(n, str(n))
