"""A level made by hand, one change at a time (D-301): an item placed, moved, set or removed; the
swimmer's start moved or turned; its title or its spec written (D-305); the time allowed set; a
goal added, a word of it chosen, its setting set, or taken out (D-308). Each change returns a
new `Level`, the old one untouched, so the Maker's undo keeps whole levels (D-027), and each
lands on the lattice (`lattice.py`). A change the level could not hold is refused with its
reason, for the status line: a light touching an obstacle, as the arena refuses it, the swimmer
starting inside one, a title or a spec with nothing in it, a goal aiming at something the level
has none of, a sentence asked twice, a third goal. Pure Python, no pygame.
"""

from __future__ import annotations

import math
from dataclasses import replace
from itertools import product

from nektoids.levels.lattice import HEADING, Range, snap, snapped
from nektoids.levels.level import Item, ItemKind, Level
from nektoids.levels.objectives import (
    THING,
    Count,
    Goal,
    Target,
    Verb,
    reworded,
    sensible,
    settings,
    targets,
)
from nektoids.sim.arena import BASE_RADIUS

SETTING = {  # what each item's setting may be (D-301)
    ItemKind.LIGHT: Range(1.0, 16.0, 1.0),  # its power
    ItemKind.OBSTACLE: Range(0.5, 5.0, 0.5, "u"),  # its radius
    ItemKind.MARK: Range(0.5, 30.0, 0.5, "u"),  # its radius: a zone as wide as Fear's ring
}
NEW = {ItemKind.LIGHT: 4.0, ItemKind.OBSTACLE: 1.0, ItemKind.MARK: 3.0}  # a new item's setting
TIME = Range(5.0, 300.0, 5.0, "s")  # the time allowed, which every level has (D-301)
GOALS_MOST = 2  # goals a made level asks, besides its time (D-308)
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
    """Item `index` gone; those after it move up in order. The last of a kind a goal aims at
    stays (D-307)."""
    return _checked(replace(level, items=level.items[:index] + level.items[index + 1 :]))


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


def timed(level: Level, seconds: float) -> Level:
    """The level allowing `seconds`, on TIME's steps and within it."""
    return replace(level, time_limit=TIME.clamp(seconds))


def goal_added(level: Level) -> Level:
    """The level asking one more goal, after the rest: the first sentence, in the order of the
    words, that aims at something the level has and that it does not ask yet; reach every light,
    on most levels. GOALS_MOST at most."""
    if len(level.objectives) >= GOALS_MOST:
        raise Unmade(f"{GOALS_MOST} goals at most: take one out first")
    asked = [_words(goal) for goal in level.objectives]
    for words in product(Verb, Count, Target):
        if sensible(*words) is None and _has(level, words[2]) and words not in asked:
            return replace(level, objectives=(*level.objectives, Goal(*words)))
    raise Unmade("place a light, an obstacle or a mark first")


def goal_removed(level: Level, index: int) -> Level:
    """Goal `index` no longer asked; those after it move up."""
    return replace(level, objectives=level.objectives[:index] + level.objectives[index + 1 :])


def lacks(level: Level, index: int, word: Verb | Count | Target) -> str | None:
    """Why goal `index` cannot take `word`: the sentence it makes (`reworded`) aims at something
    the level has none of; None if it can. The Maker dims such a word (D-308)."""
    target = reworded(level.objectives[index], word).target
    if _has(level, target):
        return None
    return f"the level has no {target.value}: place one in Objects"


def goal_worded(level: Level, index: int, word: Verb | Count | Target) -> Level:
    """Goal `index` with `word` in its place, the other words moved as little as makes sense
    (`reworded`); refused if it would aim at nothing, or ask what another goal asks."""
    why = lacks(level, index, word)
    if why is not None:
        raise Unmade(why)
    goal = reworded(level.objectives[index], word)
    if any(_words(other) == _words(goal) for k, other in enumerate(level.objectives) if k != index):
        raise Unmade("the level asks that already")
    return _goal_with(level, index, goal)


def number(text: str) -> float:
    """What a slider's box holds once typed (D-308): a number, or Unmade."""
    try:
        value = float(text)
    except ValueError:
        raise Unmade("type a number") from None
    if not math.isfinite(value):
        raise Unmade("type a number")
    return value


def goal_set(level: Level, index: int, value: float) -> Level:
    """Goal `index`'s setting, a stay's seconds or a circle's turns, at `value`, on its range's
    steps and within it; ValueError for a goal whose verb takes none."""
    goal = level.objectives[index]
    taken = settings(goal)
    if not taken:
        raise ValueError(f"{goal.name(level)!r} has no setting")
    name, scale = taken[0]
    value = scale.clamp(value)
    whole = isinstance(getattr(goal, name), int)  # turns
    return _goal_with(level, index, replace(goal, **{name: round(value) if whole else value}))


def _words(goal: Goal) -> tuple[Verb, Count, Target]:
    return goal.verb, goal.many, goal.target


def _has(level: Level, target: Target) -> bool:
    return len(targets(level, target)[1]) > 0


def _goal_with(level: Level, index: int, goal: Goal) -> Level:
    goals = list(level.objectives)
    goals[index] = goal
    return replace(level, objectives=tuple(goals))


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
    for goal in level.objectives:  # each aims at something the level has (D-307)
        if not _has(level, goal.target):
            raise Unmade(
                f"{goal.name(level)} needs {THING[goal.target][2]}: take the goal out first"
            )
    return level
