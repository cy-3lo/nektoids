"""A level as plain data (D-028): what the player is asked, where the swimmer starts, the items
placed in the open plane, the board the player builds on, the objectives and the time allowed.

Items are to the plane what parts are to the board: each has a kind (`ItemKind`, as a part has
its `Kind`), the point where it sits, and the one setting its kind takes, a light's power or an
obstacle's radius. A level editor will place them as the board editor places parts. `to_dict`
and `from_dict` turn a level into JSON-able data and back, as `Board.to_dict` does (D-024);
the shipped levels are JSON files in `data/`. Pure Python, no pygame.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from functools import cached_property
from pathlib import Path

from nektoids.graph.board import Board
from nektoids.levels.objectives import Objective, objective_from_dict, objective_to_dict
from nektoids.sim.arena import OBSTACLE_RADIUS, Arena, Disc, Light

LINE = 96  # a level file's lines stay this short where they can [characters]


class ItemKind(Enum):
    LIGHT = "light"
    OBSTACLE = "obstacle"

    @property
    def setting(self) -> str:
        """The name of what an item of this kind is set by, as it reads in a level's data."""
        return _SETTING[self]

    @property
    def default(self) -> float | None:
        """Its setting when a level does not give one; None if a level must."""
        return _DEFAULT.get(self)


_SETTING = {ItemKind.LIGHT: "power", ItemKind.OBSTACLE: "radius"}  # both in u
_DEFAULT = {ItemKind.OBSTACLE: OBSTACLE_RADIUS}


@dataclass(frozen=True)
class Item:
    kind: ItemKind
    at: tuple[float, float]  # where its centre sits [u]
    value: float  # its kind's setting: a light's power, an obstacle's radius [u]

    def to_dict(self) -> dict:
        return {"kind": self.kind.value, "at": list(self.at), self.kind.setting: self.value}

    @classmethod
    def from_dict(cls, data: Mapping) -> Item:
        kind = ItemKind(data["kind"])
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
    objectives: tuple[Objective, ...] = ()
    tutorial: Mapping | None = field(default=None, repr=False)  # its ghosts and steps (D-039)
    passkey: str | None = None  # the word its win gives: it opens the next level (D-075)

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

    def to_dict(self) -> dict:
        x, y, heading = self.start
        return (
            {
                "title": self.title,
                "spec": self.spec,
                "start": {"at": [x, y], "heading": heading},
                "items": [item.to_dict() for item in self.items],
                "board": self.board,
                "time_limit": self.time_limit,
                "objectives": [objective_to_dict(o) for o in self.objectives],
            }
            | ({"passkey": self.passkey} if self.passkey else {})
            | ({"tutorial": self.tutorial} if self.tutorial is not None else {})
        )

    @classmethod
    def from_dict(cls, data: Mapping) -> Level:
        """ValueError for data no level could hold: an unknown kind, an item without its
        setting, items that overlap as the arena refuses, a board that cannot be built."""
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
        )
        if level.passkey is not None and not is_passkey(level.passkey):
            raise ValueError(f"a passkey is A to Z, at most {PASSKEY_LENGTH}: {level.passkey!r}")
        level.arena  # noqa: B018 - built now, so that bad items fail here, not mid-run
        level.new_board()
        return level


PASSKEY_LENGTH = 10  # the most letters a passkey has (D-075)


def is_passkey(word: str) -> bool:
    """Whether `word` may be a passkey: A to Z, upper case, at most PASSKEY_LENGTH letters."""
    return 0 < len(word) <= PASSKEY_LENGTH and all("A" <= c <= "Z" for c in word)


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
