"""A board as a short line of text, to copy, paste and keep (D-205).

A board is a diagram on a body, without a level: its zone, a hex disc; its parts in id order,
each a cell, a kind and a facing if it turns; its wires in the order they were drawn, each its
two ends and its path. Loading one into a level goes through `Board.adopt` (D-092), which says
what the level does not hand out.

The text holds only the decisions the rules leave open. Replaying the board decision by decision
on a bare body, each decision is a digit whose base is the number of choices the rules allow at
that point, and the board is one integer in that mixed radix. A forced choice costs nothing. A
wire's path costs one binary digit when it is the router's, drawn after the wires before it,
and a step at a time otherwise. A kind is one of CAPACITY codes, `Kind`'s order, so the kinds to
come fit the same text; a zone is one of RADII codes, the discs and room for other shapes.

The integer is written in base 59, the alphanumerics without I, l and O, in blocks of at most
BLOCK characters, each followed by CHECKS check characters of a Reed-Solomon code over the
integers mod 59, a field since 59 is prime. The version of the format is a hidden first symbol:
never written, it enters every check, so a text of another version fails them. Distance
CHECKS + 1 = 5: in each block one wrong character is put right, and two are refused, never read as
another board. Pure Python, no pygame.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from nektoids.graph.board import Board, Kind, Wire
from nektoids.graph.hexgrid import Cell, hex_disc

VERSION = 1  # of the format; raised when the rules of a part or the router change
RADII = 16  # zone codes: a hex disc of radius 0 to 7, then room for other shapes
DISCS = 8
CAPACITY = 32  # kind codes, the kinds to come included

ALPHABET = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"  # no I, l, O
P = len(ALPHABET)  # 59, a prime: the check characters are reckoned mod 59
READ = {c: i for i, c in enumerate(ALPHABET)} | {"I": 1, "l": 1, "O": 0}
IGNORED = " -\t\n"  # spaces and dashes a person may put in
CHECKS = 4
BLOCK = P - 2 - CHECKS  # data characters a block holds: P - 1 symbols, the version one of them
ROOT = 2  # a primitive root mod 59: its powers are every non-zero symbol
POWER = [pow(ROOT, i, P) for i in range(P - 1)]
LOG = {value: i for i, value in enumerate(POWER)}

Choose = Callable[[str, Sequence], object]


def to_text(board: Board) -> str:
    """The board as text. ValueError if its zone is not a disc."""
    digits: list[tuple[int, int]] = []
    _replay(_Encoder(board, digits))
    number = 0
    for choice, base in reversed(digits):
        number = number * base + choice
    return _spell(number)


def from_text(text: str) -> Board:
    """The board a text holds, on a bare body: its zone, every kind without limit. ValueError,
    with a reason a player can read, for a text that holds no board of this version."""
    return read(text)[0]


def read(text: str) -> tuple[Board, bool]:
    """`from_text`'s board, and whether a wrong character was put right on the way."""
    number, corrected = _read(text)

    def choose(tag: str, options: Sequence) -> object:
        nonlocal number
        number, choice = divmod(number, len(options))
        return options[choice]

    board = _replay(choose)
    if number:
        raise ValueError("this text holds more than a board")
    return board, corrected


# The replay, the same for both ways


def _replay(choose: Choose) -> Board:
    """Build a board decision by decision; `choose(tag, options)` picks one of `options`."""
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
        board.place(kind, cell, facing=facing)
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


class _Encoder:
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
        elif tag in ("kind", "facing"):
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


# Base 59 and the check characters


def _spell(number: int) -> str:
    data = []
    while number:
        number, digit = divmod(number, P)
        data.append(digit)
    data = data[::-1] or [0]
    blocks = [data[i : i + BLOCK] for i in range(0, len(data), BLOCK)]
    return "".join(ALPHABET[s] for block in blocks for s in (*block, *_checks(block)))


def _read(text: str) -> tuple[int, bool]:
    symbols = []
    for char in text:
        if char in IGNORED:
            continue
        if char not in READ:
            raise ValueError(f"no board has the character {char!r}")
        symbols.append(READ[char])
    size = BLOCK + CHECKS
    blocks = [symbols[i : i + size] for i in range(0, len(symbols), size)]
    if not blocks or len(blocks[-1]) <= CHECKS:
        raise ValueError("this text is too short to hold a board")
    number, corrected = 0, False
    for block in blocks:
        fixed = _corrected([VERSION, *block])
        if fixed is None:
            raise ValueError("this text holds no board: mistyped, or of another version")
        corrected |= fixed[1:] != block
        for digit in fixed[1:-CHECKS]:
            number = number * P + digit
    return number, corrected


def _generator() -> list[int]:
    """The product of (x - ROOT^j) for j = 1..CHECKS, lowest degree first."""
    g = [1]
    for j in range(1, CHECKS + 1):
        g = [(lower - POWER[j] * same) % P for same, lower in zip([*g, 0], [0, *g], strict=True)]
    return g


GENERATOR = _generator()[::-1]  # highest degree first


def _checks(block: Sequence[int]) -> list[int]:
    """The check symbols of the version and `block`: minus the remainder of their polynomial,
    times x^CHECKS, divided by the generator, so the whole word divides by it."""
    rest = [VERSION, *block, *[0] * CHECKS]
    for i in range(len(rest) - CHECKS):
        if rest[i]:
            factor = rest[i]
            for j in range(1, len(GENERATOR)):
                rest[i + j] = (rest[i + j] - GENERATOR[j] * factor) % P
    return [(-r) % P for r in rest[-CHECKS:]]


def _corrected(word: list[int]) -> list[int] | None:
    """The word with one wrong symbol put right, the hidden first one excepted; None if it has
    two or more. Its syndromes are the word's values at ROOT^j: all 0 for a word of the code,
    e X^j for one error of e at the place whose locator is X."""
    syndromes = []
    for j in range(1, CHECKS + 1):
        value = 0
        for symbol in word:
            value = (value * POWER[j] + symbol) % P
        syndromes.append(value)
    if not any(syndromes):
        return word
    if not all(syndromes) or any(
        (syndromes[j + 1] * syndromes[j + 1] - syndromes[j] * syndromes[j + 2]) % P
        for j in range(CHECKS - 2)
    ):
        return None
    locator = syndromes[1] * pow(syndromes[0], P - 2, P) % P  # ROOT^p, p from the last symbol
    where = len(word) - 1 - LOG[locator]
    if where < 1:  # the version, or before the word: not one error
        return None
    fixed = list(word)
    fixed[where] = (fixed[where] - syndromes[0] * pow(locator, P - 2, P)) % P
    return fixed
