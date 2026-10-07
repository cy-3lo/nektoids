"""The Wheel of the Editor (D-314): the icons round the focused cell, what can be done there, at
the foot of Objects, round a picture of the cell, large, where the icons have room. The Board's
left with Tools (D-401): its buttons round the board do its work.

Up to five icons sit on its rim, beyond the cell's corners, the lowest left free, the gap at the
foot: an odd number centred on the top corner, an even one as many each side of it. More turn as
cards on a rotary file: five on the rim, the others piled under its two ends, drawn empty, each
set back a third of an icon's radius along the circle. An icon's key shows in its tooltip, not
round the rim, which leaves the Wheel room to be larger (D-069). Pure numbers, no pygame.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

from nektoids.editor.buttons import part_key
from nektoids.editor.layout import TOOL_KEYS, Tool
from nektoids.graph.board import Kind

RADIUS = 1.8  # from the cell's centre to an icon's, beyond a corner [hex sizes]
ICON = 0.62  # an icon's disc, its radius: the part on it just smaller than the cell's [hex sizes]
WHEEL_HEX = 46  # the cell's size in the drawer's picture [px]
HEADROOM = 6  # over the Wheel's top icon, in that picture [px]
LINE_BELOW = 12  # from its lowest icon to the line under it, saying what the cell holds [px]
ON_RIM = 5  # the most icons on the rim, beyond the cell's corners; more pile up below its ends
CORNERS = (210.0, 150.0, 90.0, 30.0, -30.0)  # left to right over the top; the lowest is the gap
PILE = 0.35  # from one icon of a pile to the next, further, along the circle [icon radii]


@dataclass(frozen=True)
class Slot:
    what: Enum  # a part to place, or an action on the part; in the Editor, its own (D-301)
    at: tuple[float, float]  # the icon's centre [px]
    key: str
    depth: float = 0  # 0 on the rim; 1, 2... down a pile, the further the lower; between, sliding


def angles(n: int) -> list[float]:
    """Where n <= ON_RIM icons sit round the cell, from the left clockwise, each beyond a
    corner, side by side with no corner left empty between them, as near the middle as they can
    be: an odd number centred on the top one, an even one a corner to its left (D-316)
    [degrees, counter-clockwise from the right]."""
    first = (ON_RIM - n) // 2
    return list(CORNERS[first : first + n])


def slots(
    items: Sequence[Enum],
    centre: tuple[float, float],
    size: float,
    kinds: frozenset[Kind],
    turn: float = 0,
    keys: Mapping[Enum, str] | None = None,
) -> list[Slot]:
    """The icons round a cell drawn at `centre` with hexes of `size` [px], the Wheel turned by
    `turn`, a fraction while it slides from one turn to the next: the icons before it piled under
    the rim's first end, those after it under its last, each further one set back along the
    circle, towards the gap. Each icon's key is the tool's or the part's number, or `keys`'s."""
    turn = min(max(turn, 0), max(0, len(items) - ON_RIM))  # never past the last
    rim = angles(min(len(items), ON_RIM))
    back = math.degrees(PILE * ICON / RADIUS)  # from one icon of a pile to the next [degrees]
    cx, cy = centre
    out = []
    for k, item in enumerate(items):
        if keys is not None:
            key = keys[item]
        else:
            key = TOOL_KEYS[item] if isinstance(item, Tool) else part_key(item, kinds)
        s = k - turn  # its place on the rim from the first end
        depth = max(0, -s, s - len(rim) + 1)  # past an end: down its pile
        if s < 0:
            angle = rim[0] + depth * back
        elif depth:
            angle = rim[-1] - depth * back
        else:  # on the rim; while it slides, between two corners
            lo, hi = math.floor(s), math.ceil(s)
            angle = rim[lo] + (s - lo) * (rim[hi] - rim[lo])
        a = math.radians(angle)
        at = (cx + RADIUS * size * math.cos(a), cy - RADIUS * size * math.sin(a))
        out.append(Slot(item, at, key, depth))  # drawn empty while piled
    return out


def centre_in(view: tuple[int, int, int, int]) -> tuple[float, float]:
    """Where a drawer draws the focused cell in its picture `view` (x, y, width, height [px]):
    across the middle, the Wheel's top icon just under its top."""
    x, y, w, _ = view
    return (x + w / 2, y + HEADROOM + (RADIUS + ICON) * WHEEL_HEX)


def slot_at(wheel: Sequence[Slot], point: tuple[float, float], size: float) -> Slot | None:
    """The icon on the rim a press at `point` falls on, if any; a pile's lie under its end."""
    return next((s for s in wheel if not s.depth and math.dist(s.at, point) <= ICON * size), None)
