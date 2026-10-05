"""A level made by hand, one change at a time (D-301): an item placed, moved, set or removed; the
swimmer's start moved or turned; its title or its spec written (D-305). Each change returns a
new `Level`, the old one untouched, so the Maker's undo keeps whole levels (D-027), and each
lands on the lattice (`lattice.py`). A change the level could not hold is refused with its
reason, for the status line: a light touching an obstacle, as the arena refuses it, the swimmer
starting inside one, a title or a spec with nothing in it. Pure Python, no pygame.
"""

from __future__ import annotations

import math
from dataclasses import replace

from nektoids.levels.lattice import HEADING, Range, snap, snapped
from nektoids.levels.level import Item, ItemKind, Level
from nektoids.sim.arena import BASE_RADIUS

SETTING = {  # what each item's setting may be (D-301)
    ItemKind.LIGHT: Range(1.0, 16.0, 1.0),  # its power
    ItemKind.OBSTACLE: Range(0.5, 5.0, 0.5, "u"),  # its radius
    ItemKind.MARK: Range(0.5, 30.0, 0.5, "u"),  # its radius: a zone as wide as Fear's ring
}
NEW = {ItemKind.LIGHT: 4.0, ItemKind.OBSTACLE: 1.0, ItemKind.MARK: 3.0}  # a new item's setting
TITLE_LONGEST = 40  # characters: the caption's line holds it with a short spec beside it
SPEC_LONGEST = 120  # a sentence or two, as the shipped levels' (D-305)


class Unmade(ValueError):
    """A change the level could not hold; its message says why, as the status line says it."""


def placed(level: Level, kind: ItemKind, at: tuple[float, float]) -> Level:
    """A new item of `kind` at the lattice point nearest `at`, set as NEW says, last in order."""
    return _checked(replace(level, items=(*level.items, Item(kind, snapped(at), NEW[kind]))))


def moved(level: Level, index: int, at: tuple[float, float]) -> Level:
    """Item `index` at the lattice point nearest `at`."""
    return _with(level, index, replace(level.items[index], at=snapped(at)))


def adjusted(level: Level, index: int, steps: int) -> Level:
    """Item `index`'s setting moved by `steps` steps of its range: a light brighter or dimmer, an
    obstacle bigger or smaller; it stays within its range."""
    item = level.items[index]
    return _with(level, index, replace(item, value=SETTING[item.kind].stepped(item.value, steps)))


def removed(level: Level, index: int) -> Level:
    """Item `index` gone; those after it move up in order."""
    return replace(level, items=level.items[:index] + level.items[index + 1 :])


def start_moved(level: Level, at: tuple[float, float]) -> Level:
    """The swimmer's start at the lattice point nearest `at`, its heading kept."""
    return _checked(replace(level, start=(*snapped(at), level.start[2])))


def turned(level: Level, steps: int) -> Level:
    """The swimmer's start turned by `steps` x 15°, counter-clockwise if positive, onto the
    lattice of headings, in [0, 360)."""
    x, y, heading = level.start
    return replace(level, start=(x, y, snap(heading + steps * HEADING, HEADING) % 360.0))


def titled(level: Level, title: str) -> Level:
    """The level called `title`, its spaces squeezed to one between words."""
    title = " ".join(title.split())
    if not title:
        raise Unmade("a level needs a title")
    return replace(level, title=title[:TITLE_LONGEST])


def specified(level: Level, spec: str) -> Level:
    """The level asking what `spec` says, its spaces squeezed to one between words."""
    spec = " ".join(spec.split())
    if not spec:
        raise Unmade("say what the level asks")
    return replace(level, spec=spec[:SPEC_LONGEST])


def _with(level: Level, index: int, item: Item) -> Level:
    items = list(level.items)
    items[index] = item
    return _checked(replace(level, items=tuple(items)))


def _checked(level: Level) -> Level:
    """`level`, if it could be played; Unmade, saying why, if not."""
    try:
        arena = level.arena
    except ValueError as refused:  # a light touching an obstacle
        raise Unmade(str(refused)) from None
    x, y, _ = level.start
    for disc in arena.obstacles:
        if math.hypot(disc.x - x, disc.y - y) < disc.radius + BASE_RADIUS:
            raise Unmade("the swimmer would start inside an obstacle")
    return level
