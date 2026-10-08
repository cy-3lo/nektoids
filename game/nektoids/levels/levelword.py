"""A level shared as a few lines of text (D-413): its title, author and description as they
read, then the level as one word, then, once it is won, the winning board's text (D-205):

    Title: Dragster
    Author: @Cy-3LO
    Description: Reach the mark 15 u ahead in 4 s.
    Level: 2dK8...
    Board: rcAmD6PrhXQv

The word holds the level as it is played: the swimmer's start, the items, what the board hands
out, the parts it places, locked, the time allowed and the goals. As a board's text, it holds
only the decisions the format leaves open, each a digit whose base is the number of choices, the
level one integer in that mixed radix, written by `spelling.py` with its own hidden version
symbol, so that a board's text is never read as a level, nor a level's word as a board. The
parts a level places are the board's own digits (`boardtext.replay`), on a board of its zone. A
position costs one digit within NEAR of the origin, more beyond; a heading is a whole degree.
The kinds of part are `Kind`'s, in order: a new kind raises VERSION. Pure Python, no pygame.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from nektoids.graph import boardtext
from nektoids.graph.board import Kind
from nektoids.graph.spelling import spell, unspell
from nektoids.levels.level import FORMAT, Item, ItemKind, Level
from nektoids.levels.objectives import Count, Goal, Target, Verb, objective_to_dict

VERSION = 31  # of the word, its hidden symbol: boards' count from 1 (D-205), levels' from 31
NEAR = 32  # positions from -NEAR to NEAR - 1 cost one digit [u]
BITS = range(62)  # ... farther ones, their size in bits, then their bits
ITEMS = range(64)  # how many items
HEADINGS = range(360)  # whole degrees
SETTINGS = range(1, 9)  # an item's setting (making.SETTING, D-311)
STOCK = (*range(10), None)  # a part handed out: none to 9, or unlimited (making.STOCK, D-315)
TIMES = range(1, 121)  # the time allowed [s] (making.TIME, D-347)
GOALS = range(3)  # how many goals: at most two (making.GOALS_MOST, D-308)
STAYS = range(1, 61)  # a stay's seconds (objectives.SECONDS, D-307)

LABELS = ("Title", "Author", "Description", "Level", "Board")
WORDS = ("Level", "Board")  # a word, its first run of characters: what follows is left out
LABEL = re.compile(r"(?:^|(?<=\s))(" + "|".join(LABELS) + r"):")
BOARD_TAGS = ("zone", "parts", "cell", "kind", "facing", "wire", "how", "step")  # its questions
UNTITLED = ("New level", "Say what the level asks.")  # a text without them (making.blank)

Choose = Callable[[str, Sequence], object]


@dataclass(frozen=True)
class Play:
    """What the word holds: the level as it is played, without its words."""

    start: tuple[float, float, float]
    items: tuple[Item, ...]
    board: dict  # zone, stock and the parts it places, locked; no wire
    time_limit: float
    objectives: tuple[Goal, ...]


def to_word(level: Level) -> str:
    """The level as one word. ValueError for a level the word cannot hold: a value off its
    lattice, as no level made in the Editor has."""
    digits: list[tuple[int, int]] = []
    _replay(_Encoder(level, digits))
    number = 0
    for choice, base in reversed(digits):
        number = number * base + choice
    return spell(number, VERSION)


def from_word(text: str) -> tuple[Play, bool]:
    """What a level's word holds, and whether a wrong character was put right; ValueError, with
    a reason a player can read, for a text that holds no level."""
    try:
        number, corrected = unspell(text, VERSION, "level")
    except ValueError:
        if _is_board(text):
            raise ValueError("that is a board's text: paste it on the Board") from None
        raise

    def choose(tag: str, options: Sequence) -> object:
        nonlocal number
        number, choice = divmod(number, len(options))
        return options[choice]

    play = _replay(choose)
    if number:
        raise ValueError("this text holds more than a level")
    return play, corrected


def to_shared(level: Level, board: str | None = None) -> str:
    """The level as lines of text to share, its winning board's text last, if it has one."""
    lines = [f"Title: {level.title}"]
    lines += [f"Author: {level.author}"] if level.author else []
    lines += [f"Description: {level.spec}", f"Level: {to_word(level)}"]
    lines += [f"Board: {board}"] if board is not None else []
    return "\n".join(lines)


def read_shared(text: str) -> Level:
    """The level that `to_shared`'s lines hold, its proof the board's text, if it has one, to be
    run again (D-320); ValueError, saying why, for a text that holds none. The lines are found by
    their labels, in any order, on lines of their own or run together, as a field of one line
    takes them; what is before the first is left out, as an email's greeting, and what follows a
    word, as its signature. A word alone is a level untitled."""
    found = list(LABEL.finditer(text))
    ends = [match.start() for match in found[1:]] + [len(text)]  # one too many if none
    said = {m.group(1): text[m.end() : end].strip() for m, end in zip(found, ends, strict=False)}
    said = {**said, **{label: _word(said[label]) for label in WORDS if label in said}}
    if not found:
        said = {"Level": _word(text)}
    if not said.get("Level"):
        raise ValueError('that text has no line "Level:", the level\'s word')
    play, _ = from_word(said["Level"])
    title, spec = said.get("Title") or UNTITLED[0], said.get("Description") or UNTITLED[1]
    data = {
        "version": FORMAT,
        "title": title,
        "spec": spec,
        **({"author": said["Author"]} if said.get("Author") else {}),
        "start": {"at": list(play.start[:2]), "heading": play.start[2]},
        "items": [item.to_dict() for item in play.items],
        "board": play.board,
        "time_limit": play.time_limit,
        "objectives": [objective_to_dict(goal) for goal in play.objectives],
    }
    if said.get("Board"):  # its tick and its parts are its run's, counted again (D-320)
        data["proof"] = {"board": said["Board"], "ticks": 0, "parts": 0}
    return Level.from_dict(data)


# The replay, the same for both ways


def _replay(choose: Choose) -> Play:
    """Build what a level's word holds decision by decision; `choose(tag, options)` picks one
    of `options`. Its tags are not the board's, whose questions `boardtext.replay` asks."""
    x, y = _integer(choose), _integer(choose)
    start = (float(x), float(y), float(choose("heading", HEADINGS)))
    items = []
    for _ in range(choose("items", ITEMS)):
        kind = choose("item", list(ItemKind))
        at = (float(_integer(choose)), float(_integer(choose)))
        items.append(Item(kind, at, float(choose("setting", SETTINGS))))
    stock = {kind.value: choose("stock", STOCK) for kind in Kind}
    placed = boardtext.replay(choose)
    parts = [{**part, "locked": True} for part in placed.to_dict()["parts"]]
    zone = len(placed.cells)
    board = {"zone": zone, "stock": {k: n for k, n in stock.items() if n != 0}, "parts": parts}
    time_limit = float(choose("time", TIMES))
    goals = []
    for _ in range(choose("goals", GOALS)):
        verb, many = choose("verb", list(Verb)), choose("count", list(Count))
        target = choose("target", list(Target))
        seconds = float(choose("seconds", STAYS)) if verb is Verb.STAY else None
        goals.append(Goal(verb, many, target, seconds))
    return Play(start, tuple(items), {**board, "wires": []}, time_limit, tuple(goals))


def _integer(choose: Choose) -> int:
    """A whole number: one digit within NEAR of 0, else its size in bits and its bits, zigzag."""
    near = choose("near", [*range(-NEAR, NEAR), None])
    if near is not None:
        return near
    zigzag = choose("far", range(1 << choose("bits", BITS)))
    return -(zigzag + 1) // 2 if zigzag & 1 else zigzag // 2


def _word(text: str) -> str:
    return next(iter(text.split()), "")


def _is_board(text: str) -> bool:
    try:
        unspell(text, boardtext.VERSION, "board")
    except ValueError:
        return False
    return True


class _Encoder:
    """Answers the replay's questions with `level`'s own choices, keeping each as a digit; the
    board's questions answered by the board's encoder, on the parts the level places."""

    def __init__(self, level: Level, digits: list[tuple[int, int]]) -> None:
        self.digits = digits
        self.board = boardtext.Encoder(level.blank_board(), digits)
        stock = level.board["stock"]
        x, y, heading = level.start
        wants: list[object] = [*_far(x), *_far(y), _whole(heading)]
        wants.append(len(level.items))
        for item in level.items:
            wants += [item.kind, *_far(item.at[0]), *_far(item.at[1]), _whole(item.value)]
        wants += [stock.get(kind.value, 0) for kind in Kind]
        self.before = wants  # the level's choices before the board's
        self.after: list[object] = [_whole(level.time_limit), len(level.objectives)]
        for goal in level.objectives:
            self.after += [goal.verb, goal.many, goal.target]
            self.after += [_whole(goal.seconds)] if goal.verb is Verb.STAY else []

    def __call__(self, tag: str, options: Sequence) -> object:
        if tag in BOARD_TAGS:
            return self.board(tag, options)
        want = (self.before or self.after).pop(0)
        if want not in options:
            raise ValueError(f"a level's word cannot hold {tag} {want!r}")
        choice = options.index(want)
        self.digits.append((choice, len(options)))
        return options[choice]


def _whole(value: float | None) -> int | float | None:
    """`value` as an integer if it is one, for `options.index`; else as it is, which no option
    holds."""
    return int(value) if value is not None and value == int(value) else value


def _far(value: float) -> list[object]:
    """What `_integer` chooses for `value`."""
    whole = _whole(value)
    if not isinstance(whole, int) or -NEAR <= whole < NEAR:
        return [whole]  # one digit; or refused by the encoder, off the lattice
    zigzag = 2 * whole if whole >= 0 else -2 * whole - 1
    return [None, zigzag.bit_length(), zigzag]


if __name__ == "__main__":  # PYTHONPATH=game python -m nektoids.levels.levelword TEXT FILE
    # A level shared, its lines in the file TEXT, written to FILE as a shipped level's (D-328):
    # its proof run again, its tick and parts its run's; passkey and tutorial added by hand.
    import sys
    from dataclasses import replace
    from pathlib import Path

    from nektoids.editor.boardfield import load
    from nektoids.editor.devdrive import DT
    from nektoids.graph.board import complexity
    from nektoids.levels.level import to_json
    from nektoids.levels.objectives import Outcome
    from nektoids.levels.proof import Proof, Replay

    level = read_shared(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if level.proof is None:
        sys.exit('no line "Board:": a shipped level carries its proof (D-328)')
    board = level.new_board()
    fits, why = load(board, level.proof["board"])
    if not fits:
        sys.exit(f"its proof does not fit the level: {why}")
    replay = Replay(level, board, DT)
    if replay.advance(replay.last) is not Outcome.WON:
        sys.exit("its proof does not win it")
    proof = Proof(level.proof["board"], replay.tick, complexity(board))
    Path(sys.argv[2]).write_text(to_json(replace(level, proof=proof.to_dict())), encoding="utf-8")
