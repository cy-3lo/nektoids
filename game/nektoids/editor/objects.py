"""The Maker's objects on the plane and its Wheel (D-301), as Parts and the Wheel are the board's
(D-068, D-069).

What a click focuses on the plane: an empty point of the lattice, an item by its place in the
level, or the swimmer's start. The Wheel round an empty point offers a light and an obstacle, as
an empty cell offers the parts; round a light or an obstacle, less, move, delete, more, the less
and the more either side of the gap, where a part's turns sit; round the swimmer, turn left,
move, turn right. What is under the mouse, and what the line under the Wheel says. Pure numbers,
no pygame.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from nektoids.editor.arena_view import ArenaView, body_at
from nektoids.editor.layout import TOOL_KEYS, Piece, Tool
from nektoids.levels.level import ItemKind, Level
from nektoids.sim.arena import BASE_RADIUS, LIGHT_RADIUS


@dataclass(frozen=True)
class Point:
    """An empty point of the plane, on the lattice."""

    at: tuple[float, float]  # [u]


Focus = Point | int | Piece  # an empty point; an item, by its index in the level; Piece.START

PLACED = {Piece.LIGHT: ItemKind.LIGHT, Piece.OBSTACLE: ItemKind.OBSTACLE}  # what a row places
ONE = {Piece.LIGHT: "a light", Piece.OBSTACLE: "an obstacle"}
KEYS = {**TOOL_KEYS, Piece.LIGHT: "1", Piece.OBSTACLE: "2"}  # the Wheel's keys, as its tooltips
ITEM_ACTIONS = (Tool.LESS, Tool.MOVE, Tool.DELETE, Tool.MORE)  # less and more by the gap
START_ACTIONS = (Tool.TURN_LEFT, Tool.MOVE, Tool.TURN_RIGHT)
WORDS = {  # the less and the more, as each kind of item says them
    ItemKind.LIGHT: ("Dimmer", "Brighter", "A light, power {:g}"),
    ItemKind.OBSTACLE: ("Smaller", "Bigger", "An obstacle, radius {:g} u"),
}
NAMES = {
    Piece.LIGHT: "Light",
    Piece.OBSTACLE: "Obstacle",
    Piece.START: "Swimmer",  # its start; "Swimmer's start" runs into the row's info disc
    Tool.LESS: "Less",
    Tool.MORE: "More",
    Tool.MOVE: "Move",
    Tool.DELETE: "Delete",
    Tool.TURN_LEFT: "Turn left",
    Tool.TURN_RIGHT: "Turn right",
}


def offer(focus: Focus | None) -> tuple[Piece | Tool, ...]:
    """What the Wheel round `focus` offers: on an empty point, what may be placed there; on an
    item, its actions; on the swimmer's start, its turns and Move; nothing with no focus."""
    if focus is None:
        return ()
    if isinstance(focus, Point):
        return (Piece.LIGHT, Piece.OBSTACLE)
    return START_ACTIONS if focus is Piece.START else ITEM_ACTIONS


def object_at(level: Level, view: ArenaView, point: tuple[float, float]) -> int | Piece | None:
    """What is under the screen point `point`: the swimmer's start, else the nearest item, by its
    index; None over the open plane."""
    x, y, _ = level.start
    if body_at(view, np.array([[x, y]]), np.array([BASE_RADIUS]), point) is not None:
        return Piece.START
    if not level.items:
        return None
    pos = np.array([item.at for item in level.items])
    radius = np.array([reach(level, k) for k in range(len(level.items))])
    return body_at(view, pos, radius, point)


def reach(level: Level, focus: int | Piece) -> float:
    """How far the object `focus` reaches from its centre [u]: the swimmer's or a light's
    radius, an obstacle's own."""
    if focus is Piece.START:
        return BASE_RADIUS
    item = level.items[focus]
    return LIGHT_RADIUS if item.kind is ItemKind.LIGHT else item.value


def where(level: Level, focus: Focus) -> tuple[float, float]:
    """Where `focus` sits on the plane [u]."""
    if isinstance(focus, Point):
        return focus.at
    if focus is Piece.START:
        return level.start[:2]
    return level.items[focus].at


def says(level: Level, focus: Focus | None) -> str:
    """The line under the Wheel: what is focused, and its setting."""
    if focus is None:
        return "Click the plane"
    if isinstance(focus, Point):
        return f"({focus.at[0]:g}, {focus.at[1]:g}): empty"
    if focus is Piece.START:
        return f"Swimmer, heading {level.start[2]:g}°"
    item = level.items[focus]
    return WORDS[item.kind][2].format(item.value)


def name(level: Level, focus: Focus | None, what: Piece | Tool) -> str:
    """An icon of the Wheel, or a row of Objects, named: the less and the more as the focused
    item's kind says them."""
    if what in (Tool.LESS, Tool.MORE) and isinstance(focus, int):
        dimmer, brighter, _ = WORDS[level.items[focus].kind]
        return dimmer if what is Tool.LESS else brighter
    return NAMES[what]
