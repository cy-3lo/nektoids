"""A level as plain data (D-028): what the player is asked, where the swimmer starts, the items
placed in the open plane, the board the player builds on, the objectives and the time allowed.

Items are to the plane what parts are to the board: each has a kind (`ItemKind`, as a part has
its `Kind`), the point where it sits, and the one setting its kind takes, a light's power, an
obstacle's radius or a mark's. A mark is a zone, a circle that only the objectives read: the
arena, and so the simulation, never has it (D-306). An objective is a sentence (D-307,
`objectives.py`). The Editor places items as the Board
places parts (D-302). `to_dict` and `from_dict` turn a level into JSON-able data and back, as
`Board.to_dict` does (D-024); the shipped levels are JSON files in `data/`. Each file says the
version of its format; `to_dict` writes `FORMAT`, and `from_dict` upgrades an older version
(`upgraded`), refuses a newer one, and refuses any key it does not know, so that a file from
another game or a mistyped key fails as it is loaded (D-201). A whole number is written as an
integer, and a board's zone as its size when it is a hexagon round the centre (D-313). Pure
Python, no pygame.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from functools import cached_property
from pathlib import Path

from nektoids.graph.board import Board
from nektoids.graph.hexgrid import disc_radius, hex_disc
from nektoids.levels import objectives as goals
from nektoids.levels.objectives import Goal, objective_from_dict, objective_to_dict
from nektoids.sim.arena import OBSTACLE_RADIUS, Arena, Disc, Light

LINE = 96  # a level file's lines stay this short where they can [characters]
START_NUDGE = (1e-3, -1e-3)  # [u] a run's swimmer starts so far off its whole start (D-425)
FORMAT = 5  # a level file's format: 2 has marks (D-306), 3 objectives as sentences (D-307),
# 4 a zone written as its size (D-313), 5 an author (D-331)
KEYS = (  # what a level file may hold, in the order `to_dict` writes it
    "version",
    "title",
    "spec",
    "author",
    "start",
    "items",
    "board",
    "time_limit",
    "objectives",
    "passkey",
    "tutorial",
    "proof",
)


class ItemKind(Enum):
    LIGHT = "light"
    OBSTACLE = "obstacle"
    MARK = "mark"  # a zone the objectives read, nothing else (D-306)

    @property
    def setting(self) -> str:
        """The name of what an item of this kind is set by, as it reads in a level's data."""
        return _SETTING[self]

    @property
    def default(self) -> float | None:
        """Its setting when a level does not give one; None if a level must."""
        return _DEFAULT.get(self)


_SETTING = {ItemKind.LIGHT: "power", ItemKind.OBSTACLE: "radius", ItemKind.MARK: "radius"}
_DEFAULT = {ItemKind.OBSTACLE: OBSTACLE_RADIUS}


@dataclass(frozen=True)
class Item:
    kind: ItemKind
    at: tuple[float, float]  # where its centre sits [u]
    value: float  # its kind's setting: a light's power, an obstacle's radius [u]

    def to_dict(self) -> dict:
        at = [whole(v) for v in self.at]
        return {"kind": self.kind.value, "at": at, self.kind.setting: whole(self.value)}

    @classmethod
    def from_dict(cls, data: Mapping) -> Item:
        kind = ItemKind(data["kind"])
        known(data, ("kind", "at", kind.setting), f"a {kind.value}")
        value = data.get(kind.setting, kind.default)
        if value is None:
            raise ValueError(f"a {kind.value} needs its {kind.setting}")
        x, y = data["at"]
        return cls(kind, (float(x), float(y)), float(value))


@dataclass(frozen=True)
class Level:
    title: str
    spec: str  # what the player is asked, in a sentence or two
    start: tuple[float, float, float]  # x, y [u] and heading [degrees, counter-clockwise from +x]
    items: tuple[Item, ...]  # in the plane, in the order the arena's arrays take them
    board: Mapping = field(repr=False)  # `Board.to_dict`'s data: zone, stock, the parts it places
    time_limit: float  # the run is over after this long [s]
    objectives: tuple[Goal, ...] = ()  # each a sentence (D-307)
    tutorial: Mapping | None = field(default=None, repr=False)  # its ghosts and steps (D-039)
    passkey: str | None = None  # the word its win gives: it opens the next level (D-075)
    proof: Mapping | None = field(default=None, repr=False)  # a level shared: its win (D-320)
    author: str | None = None  # who made it, as they sign: "@Cy-3LO" (D-331)

    @property
    def start_at(self) -> tuple[float, float]:
        """Where a run puts the swimmer [u]: its start, nudged by START_NUDGE, so that no push is
        ever exactly on an obstacle's centre, which a real one never is (D-425)."""
        return self.start[0] + START_NUDGE[0], self.start[1] + START_NUDGE[1]

    @cached_property
    def marks(self) -> tuple[Item, ...]:
        """The level's marks, in item order: zones the arena never has (D-306)."""
        return tuple(item for item in self.items if item.kind is ItemKind.MARK)

    @cached_property
    def arena(self) -> Arena:
        """What the simulation reads: the lights and the obstacles, each in item order."""
        lights = tuple(
            Light(*item.at, item.value) for item in self.items if item.kind is ItemKind.LIGHT
        )
        obstacles = tuple(
            Disc(*item.at, item.value) for item in self.items if item.kind is ItemKind.OBSTACLE
        )
        return Arena(lights, obstacles)

    def new_board(self) -> Board:
        """The board the player starts the level from, built afresh each time."""
        return Board.from_dict(self.board)

    def blank_board(self) -> Board:
        """The level's zone, stock and locked parts, none of its free parts or wires: what a
        hint's shadow is built on (D-103), over what the level places (D-328)."""
        parts = [part for part in self.board["parts"] if part["locked"]]
        return Board.from_dict({**self.board, "parts": parts, "wires": []})

    def to_dict(self) -> dict:
        x, y, heading = self.start
        return (
            {"version": FORMAT, "title": self.title, "spec": self.spec}
            | ({"author": self.author} if self.author else {})
            | {
                "start": {"at": [whole(x), whole(y)], "heading": whole(heading)},
                "items": [item.to_dict() for item in self.items],
                "board": self.board,
                "time_limit": whole(self.time_limit),
                "objectives": [objective_to_dict(o) for o in self.objectives],
            }
            | ({"passkey": self.passkey} if self.passkey else {})
            | ({"tutorial": self.tutorial} if self.tutorial is not None else {})
            | ({"proof": self.proof} if self.proof is not None else {})
        )

    @classmethod
    def from_dict(cls, data: Mapping) -> Level:
        """ValueError for data no level could hold: no version or a newer one than FORMAT, a
        key it does not know, an unknown kind, an item without its setting, items that overlap
        as the arena refuses, a board that cannot be built. The keys of `board` and `tutorial`
        are theirs to check. An older version is upgraded first."""
        data = upgraded(data)
        known(data, KEYS, "a level")
        known(data["start"], ("at", "heading"), "the start")
        x, y = data["start"]["at"]
        level = cls(
            title=data["title"],
            spec=data["spec"],
            start=(float(x), float(y), float(data["start"]["heading"])),
            items=tuple(Item.from_dict(item) for item in data["items"]),
            board=data["board"],
            time_limit=float(data["time_limit"]),
            objectives=tuple(objective_from_dict(o) for o in data["objectives"]),
            tutorial=data.get("tutorial"),
            passkey=data.get("passkey"),
            proof=data.get("proof"),
            author=data.get("author"),
        )
        if level.proof is not None:  # its board's text, its score (`proof.Proof`, D-320)
            known(level.proof, ("board", "ticks", "parts"), "a proof")
        for goal in level.objectives:  # each aims at something the level has
            if not len(goals.targets(level, goal.target)[0]):
                raise ValueError(
                    f"{goal.name(level)!r}: the level has no {goals.THING[goal.target][1]}"
                )
        if level.passkey is not None and not is_passkey(level.passkey):
            raise ValueError(f"a passkey is A to Z, at most {PASSKEY_LENGTH}: {level.passkey!r}")
        level.arena  # noqa: B018 - built now, so that bad items fail here, not mid-run
        level.new_board()
        return level


def upgraded(data: Mapping) -> Mapping:
    """`data` in FORMAT, from the version it says (D-201): version 1 had no marks, and is
    version 2 as it is (D-306); version 2's objectives become sentences, its rings marks on its
    lights (D-307, `objectives.upgraded`); version 3's zone, a hexagon's cells, becomes its size
    (D-313); version 4 has no author, and is version 5 as it is (D-331). ValueError for no
    version, one this game does not know, or rings that would mix with the marks a level has."""
    if "version" not in data:
        raise ValueError(f"a level without its version: this game reads version {FORMAT}")
    version = data["version"]
    if version not in range(1, FORMAT + 1):
        raise ValueError(
            f"a level of version {version}: this game reads version {FORMAT} and those before"
        )
    if version < 3:
        items = list(data["items"])
        lights = [item["at"] for item in items if item.get("kind") == "light"]
        sentences, marks = goals.upgraded(list(data["objectives"]), lights)
        if marks and any(item.get("kind") == "mark" for item in items):
            raise ValueError("its rings would count its marks: make it again in the Editor")
        data = {**data, "items": items + marks, "objectives": sentences}
    if version < 4:
        data = {**data, "board": {**data["board"], "zone": _sized(data["board"]["zone"])}}
    return {**data, "version": FORMAT}


def _sized(zone: int | list) -> int | list:
    """A zone's cells as version 4 writes them: its size if it is a hexagon round (0, 0), as
    every shipped level's is, else the cells as they were; a size stays one."""
    if isinstance(zone, int):
        return zone
    cells = {tuple(cell) for cell in zone}
    try:
        return len(zone) if cells == set(hex_disc(disc_radius(len(zone)))) else zone
    except ValueError:  # no hexagon holds so many
        return zone


def whole(value: float) -> float | int:
    """`value`, an integer if it is a whole number: a level's file writes 25, not 25.0 (D-313)."""
    return int(value) if float(value).is_integer() else value


PASSKEY_LENGTH = 10  # the most letters a passkey has (D-075)


def is_passkey(word: str) -> bool:
    """Whether `word` may be a passkey: A to Z, upper case, at most PASSKEY_LENGTH letters."""
    return 0 < len(word) <= PASSKEY_LENGTH and all("A" <= c <= "Z" for c in word)


def known(data: Mapping, keys: Iterable[str], what: str) -> None:
    """ValueError if `data` holds a key not among `keys`: refused, not ignored (D-201)."""
    unknown = [key for key in data if key not in keys]
    if unknown:
        raise ValueError(f"{what} takes no {', '.join(map(repr, unknown))}")


def load(path: Path) -> Level:
    """A level from its JSON file (opened by path: pygbag cannot open files from memory)."""
    with path.open(encoding="utf-8") as file:
        return Level.from_dict(json.load(file))


def to_json(level: Level) -> str:
    """The level as its file holds it: JSON, each list or object on one line if it fits."""
    return _dumps(level.to_dict(), 0) + "\n"


def _dumps(value: object, indent: int) -> str:
    flat = json.dumps(value)
    if not isinstance(value, (list, dict)) or not value or indent + len(flat) <= LINE:
        return flat
    pad = " " * (indent + 2)
    if isinstance(value, dict):
        lines = [f"{pad}{json.dumps(key)}: {_dumps(v, indent + 2)}" for key, v in value.items()]
        return "{\n" + ",\n".join(lines) + "\n" + " " * indent + "}"
    parts = [_dumps(v, indent + 2) for v in value]
    if any(isinstance(v, dict) or "\n" in part for v, part in zip(value, parts, strict=True)):
        lines = [pad + part for part in parts]  # objects, or what needs lines of its own
    else:  # short values, as many to a line as fit
        lines = [pad + parts[0]]
        for part in parts[1:]:
            if len(lines[-1]) + 2 + len(part) <= LINE:
                lines[-1] += ", " + part
            else:
                lines[-1] += ","
                lines.append(pad + part)
        return "[\n" + "\n".join(lines) + "\n" + " " * indent + "]"
    return "[\n" + ",\n".join(lines) + "\n" + " " * indent + "]"


if __name__ == "__main__":  # PYTHONPATH=game python -m nektoids.levels.level FILE...
    import sys

    for name in sys.argv[1:]:  # each file, edited by hand, written again as the game writes it
        path = Path(name)
        path.write_text(to_json(load(path)), encoding="utf-8")
