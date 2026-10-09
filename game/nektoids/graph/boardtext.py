"""A board as a short line of text, to copy, paste and keep (D-205).

A board is a diagram on a body, without a level: its zone, a hex disc; its parts in id order,
each a cell, a kind, a facing if it turns and a hue if it may be painted (D-501); its wires in
the order they were drawn, each its two ends and its path. Loading one into a level goes through
`Board.adopt` (D-092), which says what the level does not hand out.

The text holds only the decisions the rules leave open. Replaying the board decision by decision
on a bare body, each decision is a digit whose base is the number of choices the rules allow at
that point, and the board is one integer in that mixed radix. A forced choice costs nothing. A
wire's path costs one binary digit when it is the router's, drawn after the wires before it,
and a step at a time otherwise. A kind is one of CAPACITY codes, `Kind`'s order, so the kinds to
come fit the same text; a zone is one of RADII codes, the discs and room for other shapes.

The integer is written in base 59, with check characters, by `spelling.py`; the version of the
format is its hidden first symbol, so a level's word fails the checks. A text of an older
version is read as that version wrote it: version 1 had no hues, its parts amber. Pure Python,
no pygame.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from nektoids.graph.board import Board, Hue, Kind, Wire
from nektoids.graph.hexgrid import Cell, hex_disc
from nektoids.graph.spelling import spell, unspell

VERSION = 2  # of the format, its hidden symbol; raised when a part's rules or the router change
READABLE = (2, 1)  # the versions still read, newest first: 1 had no hues (D-501)
RADII = 16  # zone codes: a hex disc of radius 0 to 7, then room for other shapes
DISCS = 8
CAPACITY = 32  # kind codes, the kinds to come included

Choose = Callable[[str, Sequence], object]


def to_text(board: Board) -> str:
    """The board as text. ValueError if its zone is not a disc."""
    digits: list[tuple[int, int]] = []
    replay(Encoder(board, digits))
    number = 0
    for choice, base in reversed(digits):
        number = number * base + choice
    return spell(number, VERSION)


def from_text(text: str) -> Board:
    """The board a text holds, on a bare body: its zone, every kind without limit. ValueError,
    with a reason a player can read, for a text that holds no board of this version."""
    return read(text)[0]


def read(text: str) -> tuple[Board, bool]:
    """`from_text`'s board, and whether a wrong character was put right on the way."""
    number, corrected, version = unspell_any(text)

    def choose(tag: str, options: Sequence) -> object:
        nonlocal number
        number, choice = divmod(number, len(options))
        return options[choice]

    board = replay(choose, version)
    if number:
        raise ValueError("this text holds more than a board")
    return board, corrected


def unspell_any(text: str) -> tuple[int, bool, int]:
    """The number a board's text writes, whether a wrong character was put right, and the
    version it was written in, the newest that reads it (`READABLE`); ValueError as `unspell`
    says it for the newest version if none does."""
    for version in READABLE:
        try:
            return (*unspell(text, version, "board"), version)
        except ValueError as error:
            if version == VERSION:
                newest = error
    raise newest


# The replay, the same for both ways


def replay(choose: Choose, version: int = VERSION) -> Board:
    """Build a board decision by decision; `choose(tag, options)` picks one of `options`. A text
    of `version` 1 holds no hues: its parts are amber."""
    radius = choose("zone", [*range(DISCS), *[None] * (RADII - DISCS)])
    if radius is None:
        raise ValueError("a body this version of the game does not have")
    board = Board(hex_disc(radius))
    for _ in range(choose("parts", range(len(board.cells) + 1))):
        cell = choose("cell", _free(board))
        kind = choose("kind", [*Kind, *[None] * (CAPACITY - len(Kind))])
        if kind is None:
            raise ValueError("a part this version of the game does not have")
        facing = choose("facing", range(6)) if kind.default_facing is not None else None
        hue = choose("hue", list(Hue)) if version >= 2 and kind.paintable else Hue.AMBER
        board.place(kind, cell, facing=facing, hue=hue)
    while True:
        ids = sorted(board.nodes)
        pairs = [(a, b) for a in ids for b in ids if a != b and board.refusal(a, b) is None]
        pair = choose("wire", [None, *pairs])
        if pair is None:
            return board
        start, goal = (board.nodes[i].cell for i in pair)
        routed = board.route(start, goal)  # the router's path, after the wires before it
        if choose("how", [routed, None] if routed else [None]) is not None:
            board.wires.append(Wire(*pair, routed))
            continue
        path, heading = [start], -1
        while path[-1] != goal:
            exits = board.exits(path[-1], heading, goal)
            if not exits:
                raise ValueError("a wire that leads nowhere")
            cell, heading = choose("step", exits)
            path.append(cell)
        laid = board.connect(*pair, tuple(path))
        if not isinstance(laid, Wire):
            raise ValueError(f"a wire the rules refuse: {laid.reason}")


def _free(board: Board) -> list[Cell]:
    return [cell for cell in board.cells if board.node_at(cell) is None]


class Encoder:
    """Answers the replay's questions with `board`'s own choices, keeping each as a digit."""

    def __init__(self, board: Board, digits: list[tuple[int, int]]) -> None:
        zone = set(board.cells)
        radius = next((r for r in range(DISCS) if set(hex_disc(r)) == zone), None)
        if radius is None:
            raise ValueError("only a body whose zone is a disc can be written as text")
        self.radius, self.digits = radius, digits
        self.parts = [board.nodes[i] for i in sorted(board.nodes)]
        index = {node.id: k for k, node in enumerate(self.parts)}  # the replay numbers from 0
        self.wires = [(index[w.source], index[w.target], w.path) for w in board.wires]
        self.part, self.wire, self.step = -1, -1, 0

    def __call__(self, tag: str, options: Sequence) -> object:
        if tag == "zone":
            want = self.radius
        elif tag == "parts":
            want = len(self.parts)
        elif tag == "cell":
            self.part += 1
            want = self.parts[self.part].cell
        elif tag in ("kind", "facing", "hue"):
            want = getattr(self.parts[self.part], tag)
        elif tag == "wire":
            self.wire += 1
            want = self.wires[self.wire][:2] if self.wire < len(self.wires) else None
        elif tag == "how":  # the router's path costs one binary digit, another its steps
            path = self.wires[self.wire][2]
            want = path if options[0] == path else None
            self.step = 1
        else:
            path = self.wires[self.wire][2]
            want = next(option for option in options if option[0] == path[self.step])
            self.step += 1
        choice = list(options).index(want)
        self.digits.append((choice, len(options)))
        return options[choice]
