"""Boards for the developer view: one idea each, built by hand (D-017).

Not levels. They show what the dynamics do: Braitenberg wiring, a fork, saturation, a
threshold-like |x - c|, and loops that settle, hold a value or latch. `Board.connect` refuses
loops, so the loops are drawn with public calls only: `route` finds the path and the wire is
appended by hand, which is how a test hand-draws one too. The editor never does this.
"""

from __future__ import annotations

from dataclasses import dataclass

from nektoids.graph.board import Board, Kind, Node, Refused, Wire
from nektoids.graph.dynamics import SOURCE_RATE
from nektoids.graph.hexgrid import offset_rect

ZONE = offset_rect(9, 7)
EYE, SRC, DBL, HLV, SUM, DIF, THR = (
    Kind.EYE,
    Kind.SOURCE,
    Kind.DOUBLE,
    Kind.HALVE,
    Kind.SUM,
    Kind.DIFFERENCE,
    Kind.THRUSTER,
)


@dataclass(frozen=True)
class Scenario:
    title: str
    board: Board
    source_level: float = SOURCE_RATE  # where the developer view starts the source sliders


def _build(parts, wires, loops=(), title="", source_level=SOURCE_RATE) -> Scenario:
    """parts: (name, kind, cell) in placement order; wires and loops: (name, name) pairs."""
    board = Board(ZONE)
    nodes: dict[str, Node] = {}
    for name, kind, cell in parts:
        placed = board.place(kind, cell)
        if isinstance(placed, Refused):
            raise ValueError(f"{title}: {name} at {cell}: {placed.reason}")
        nodes[name] = placed
    for a, b in wires:
        result = board.connect(nodes[a].id, nodes[b].id)
        if isinstance(result, Refused):
            raise ValueError(f"{title}: {a} -> {b}: {result.reason}")
    for a, b in loops:
        path = board.route(nodes[a].cell, nodes[b].cell)
        if path is None:
            raise ValueError(f"{title}: no path {a} -> {b}")
        board.wires.append(Wire(nodes[a].id, nodes[b].id, path))
    return Scenario(title, board, source_level)


def scenarios() -> list[Scenario]:
    two_eyes_two_thrusters = [
        ("up eye", EYE, (1, 1)),
        ("down eye", EYE, (-1, 5)),
        ("up thruster", THR, (7, 1)),
        ("down thruster", THR, (5, 5)),
    ]
    return [
        _build(
            two_eyes_two_thrusters,
            [("up eye", "up thruster"), ("down eye", "down thruster")],
            title="Braitenberg, uncrossed",
        ),
        _build(
            two_eyes_two_thrusters,
            [("up eye", "down thruster"), ("down eye", "up thruster")],
            title="Braitenberg, crossed",
        ),
        _build(
            [
                ("up eye", EYE, (1, 1)),
                ("half", HLV, (4, 1)),
                ("down eye", EYE, (-1, 5)),
                ("up thruster", THR, (7, 1)),
                ("down thruster", THR, (5, 5)),
            ],
            [
                ("up eye", "half"),
                ("half", "up thruster"),
                ("down eye", "down thruster"),
            ],
            title="Halve on one side: asymmetry",
        ),
        _build(
            [
                ("eye", EYE, (0, 3)),
                ("upper", THR, (7, 1)),
                ("middle", THR, (6, 3)),
                ("lower", THR, (5, 5)),
            ],
            [("eye", "upper"), ("eye", "middle"), ("eye", "lower")],
            title="A fork splits the rate",
        ),
        _build(
            [
                ("up eye", EYE, (1, 1)),
                ("down eye", EYE, (-1, 5)),
                ("gap", DIF, (3, 3)),
                ("thruster", THR, (6, 3)),
            ],
            [("up eye", "gap"), ("down eye", "gap"), ("gap", "thruster")],
            title="Difference of two eyes",
        ),
        _build(
            [
                ("eye", EYE, (-1, 3)),
                ("first", DBL, (1, 3)),
                ("second", DBL, (3, 3)),
                ("third", DBL, (5, 3)),
                ("thruster", THR, (7, 3)),
            ],
            [
                ("eye", "first"),
                ("first", "second"),
                ("second", "third"),
                ("third", "thruster"),
            ],
            title="Doublers saturate at R",
        ),
        _build(
            [
                ("eye", EYE, (-1, 3)),
                ("source", SRC, (1, 1)),
                ("gap", DIF, (3, 3)),
                ("thruster", THR, (6, 3)),
            ],
            [("eye", "gap"), ("source", "gap"), ("gap", "thruster")],
            title="Source and Difference: |x - c|",
            source_level=0.5,
        ),
        _build(
            [
                ("eye", EYE, (-1, 3)),
                ("sum", SUM, (2, 3)),
                ("half", HLV, (5, 3)),
                ("thruster", THR, (7, 1)),
            ],
            [("eye", "sum"), ("sum", "half"), ("half", "thruster")],
            [("half", "sum")],
            title="Loop that settles (gain 1/4)",
        ),
        # A fork halves what leaves a node: the second Double makes the loop gain exactly 1.
        _build(
            [
                ("eye", EYE, (-1, 3)),
                ("sum", SUM, (1, 3)),
                ("first", DBL, (3, 3)),
                ("second", DBL, (5, 3)),
                ("half", HLV, (3, 1)),
                ("thruster", THR, (7, 3)),
            ],
            [
                ("eye", "sum"),
                ("sum", "first"),
                ("first", "second"),
                ("second", "thruster"),
                ("second", "half"),
            ],
            [("half", "sum")],
            title="Loop of gain 1: holds a value",
        ),
        # The same, with the loop gain 2 and a Difference: y = |eye - 2y| settles on eye/3.
        _build(
            [
                ("eye", EYE, (-1, 3)),
                ("gap", DIF, (1, 3)),
                ("first", DBL, (3, 3)),
                ("second", DBL, (5, 3)),
                ("thruster", THR, (7, 3)),
            ],
            [
                ("eye", "gap"),
                ("gap", "first"),
                ("first", "second"),
                ("second", "thruster"),
            ],
            [("second", "gap")],
            title="Loop through a Difference (gain 2)",
        ),
        # Two stages that inhibit each other: each is y = min(1, 4 |source - other / 2|), the
        # fork halving what the other sees, so the loop gain is 2 per stage and one stage wins
        # and stays. With both sources at 0.5, nudge one slider down and put it back: the
        # winner stays.
        _build(
            [
                ("source a", SRC, (0, 1)),
                ("gap a", DIF, (2, 1)),
                ("first a", DBL, (4, 1)),
                ("second a", DBL, (6, 1)),
                ("thruster a", THR, (8, 1)),
                ("source b", SRC, (-2, 5)),
                ("gap b", DIF, (0, 5)),
                ("first b", DBL, (2, 5)),
                ("second b", DBL, (4, 5)),
                ("thruster b", THR, (6, 5)),
            ],
            [
                ("source a", "gap a"),
                ("gap a", "first a"),
                ("first a", "second a"),
                ("second a", "thruster a"),
                ("source b", "gap b"),
                ("gap b", "first b"),
                ("first b", "second b"),
                ("second b", "thruster b"),
                ("second a", "gap b"),
            ],
            [("second b", "gap a")],
            title="Toggle: two stages inhibiting each other",
            source_level=0.5,
        ),
    ]
