"""The Editor's objects on the plane (D-301): what the keys round the plane and Objects' rows name
them (D-410), and what is under the mouse: the swimmer, a light or an obstacle under it, else a
mark by its rim or its centre, so that a press inside a zone still finds the open plane there
(D-306). Pure numbers, no pygame.
"""

from __future__ import annotations

import math

import numpy as np

from nektoids.editor.arena_view import ArenaView, body_at
from nektoids.editor.layout import Piece
from nektoids.levels.level import ItemKind, Level
from nektoids.sim.arena import BASE_RADIUS, LIGHT_RADIUS, Colour

PLACED = {
    Piece.LIGHT: ItemKind.LIGHT,
    Piece.AMBER_LIGHT: ItemKind.LIGHT,
    Piece.VIOLET_LIGHT: ItemKind.LIGHT,
    Piece.OBSTACLE: ItemKind.OBSTACLE,
    Piece.MARK: ItemKind.MARK,
}
COLOUR = {  # a light's, by its key (D-506)
    Piece.LIGHT: Colour.WHITE,
    Piece.AMBER_LIGHT: Colour.AMBER,
    Piece.VIOLET_LIGHT: Colour.VIOLET,
}
ONE = {
    Piece.LIGHT: "a white light",
    Piece.AMBER_LIGHT: "an amber light",
    Piece.VIOLET_LIGHT: "a violet light",
    Piece.OBSTACLE: "an obstacle",
    Piece.MARK: "a mark",
}
MARK_GRAB = 6.0  # a mark is grabbed this near its rim, or its centre [px]
NAMES = {
    Piece.LIGHT: "White light",
    Piece.AMBER_LIGHT: "Amber light",
    Piece.VIOLET_LIGHT: "Violet light",
    Piece.OBSTACLE: "Obstacle",
    Piece.MARK: "Mark",
    Piece.START: "Swimmer",  # its start; "Swimmer's start" runs into the row's info disc
}


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


def where(level: Level, obj: int | Piece) -> tuple[float, float]:
    """Where the object `obj` sits on the plane [u]."""
    if obj is Piece.START:
        return level.start[:2]
    return level.items[obj].at
