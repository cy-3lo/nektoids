"""The Maker's objects on the plane and its Wheel (D-301), as Parts and the Wheel are the board's
(D-068, D-069).

What a click focuses on the plane: an empty point of the lattice, an item by its place in the
level, or the swimmer's start. The Wheel round an empty point offers a light, an obstacle and a
mark, as an empty cell offers the parts; round an item, less, move, delete, more, the less and
the more either side of the gap, where a part's turns sit; round the swimmer, turn left, move,
turn right. What is under the mouse: the swimmer, a light or an obstacle under it, else a mark
by its rim or its centre, so that a click inside a zone still finds the point there (D-306).
What the line under the Wheel says. Pure numbers, no pygame.
"""

from __future__ import annotations

import math
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

PLACED = {Piece.LIGHT: ItemKind.LIGHT, Piece.OBSTACLE: ItemKind.OBSTACLE, Piece.MARK: ItemKind.MARK}
ONE = {Piece.LIGHT: "a light", Piece.OBSTACLE: "an obstacle", Piece.MARK: "a mark"}
POINT_PIECES = (Piece.LIGHT, Piece.OBSTACLE, Piece.MARK)  # what an empty point's Wheel offers
KEYS = {**TOOL_KEYS, **{p: str(k + 1) for k, p in enumerate(POINT_PIECES)}}  # 1 2 3; its tips'
MARK_GRAB = 6.0  # a mark is grabbed this near its rim, or its centre [px]
ITEM_ACTIONS = (Tool.LESS, Tool.MOVE, Tool.DELETE, Tool.MORE)  # less and more by the gap
START_ACTIONS = (Tool.TURN_LEFT, Tool.MOVE, Tool.TURN_RIGHT)
WORDS = {  # the less and the more, as each kind of item says them
    ItemKind.LIGHT: ("Dimmer", "Brighter", "A light, power {:g}"),
    ItemKind.OBSTACLE: ("Smaller", "Bigger", "An obstacle, radius {:g} u"),
    ItemKind.MARK: ("Smaller", "Bigger", "A mark, radius {:g} u"),
}
NAMES = {
    Piece.LIGHT: "Light",
    Piece.OBSTACLE: "Obstacle",
    Piece.MARK: "Mark",
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
        return POINT_PIECES
    return START_ACTIONS if focus is Piece.START else ITEM_ACTIONS


def object_at(level: Level, view: ArenaView, point: tuple[float, float]) -> int | Piece | None:
    """What is under the screen point `point`: the swimmer's start, else the nearest light or
    obstacle under it, else a mark whose rim or centre it is near, by index; None over the open
    plane, inside a mark too."""
    x, y, _ = level.start
    if body_at(view, np.array([[x, y]]), np.array([BASE_RADIUS]), point) is not None:
        return Piece.START
    solid = [k for k, item in enumerate(level.items) if item.kind is not ItemKind.MARK]
    if solid:
        pos = np.array([level.items[k].at for k in solid])
        hit = body_at(view, pos, np.array([reach(level, k) for k in solid]), point)
        if hit is not None:
            return solid[hit]
    wx, wy = view.to_world(*point)
    for k, item in enumerate(level.items):
        if item.kind is ItemKind.MARK:
            off = math.hypot(item.at[0] - wx, item.at[1] - wy) * view.scale  # [px]
            if off <= MARK_GRAB or abs(off - item.value * view.scale) <= MARK_GRAB:
                return k
    return None


def reach(level: Level, focus: int | Piece) -> float:
    """How far the object `focus` reaches from its centre [u]: the swimmer's or a light's
    radius, an obstacle's own."""
    if focus is Piece.START:
        return BASE_RADIUS
    item = level.items[focus]
    return LIGHT_RADIUS if item.kind is ItemKind.LIGHT else item.value  # an obstacle's, a mark's


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
