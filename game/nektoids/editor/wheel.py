"""The Wheel: the icons round the focused cell, what can be done there (D-068), as Tools and
Parts draw it at their foot, round a picture of the cell, large, where the icons have room (D-069).

An empty cell of the zone offers the parts the level still hands out; a part offers turn left,
move, wire, swap when another part of its group is left, turn right (eyes and thrusters only)
and delete; swapping, the Wheel offers those parts. Up to five icons sit on its rim, beyond the
cell's corners, the lowest left free, the gap at the foot: an odd number centred on the top
corner, an even one as many each side of it. More turn as cards on a rotary file: five on the
rim, the others piled under its two ends, drawn empty, each set back a third of an icon's radius
along the circle, those before the rim under its first end, those after it under its last. The
keyboard going round turns the Wheel; so does the mouse wheel, or the mouse resting on a pile,
past its end icon. Each step slides the icons along the rim and the piles in 0.1 s; a step taken
during a slide goes straight on, from where the Wheel shows (D-083). An icon's key shows in its
tooltip, not round the rim, which leaves the Wheel room to be larger (D-069). Pure numbers, no
pygame.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

from nektoids.editor.layout import MENU_GROUPS, TOOL_KEYS, Tool
from nektoids.graph.board import Board, Kind

RADIUS = 1.8  # from the cell's centre to an icon's, beyond a corner [hex sizes]
ICON = 0.62  # an icon's disc, its radius: the part on it just smaller than the cell's [hex sizes]
WHEEL_HEX = 46  # the cell's size in the drawer's picture [px]
HEADROOM = 6  # over the Wheel's top icon, in that picture [px]
LINE_BELOW = 12  # from its lowest icon to the line under it, saying what the cell holds [px]
ON_RIM = 5  # the most icons on the rim, beyond the cell's corners; more pile up below its ends
CORNERS = (210.0, 150.0, 90.0, 30.0, -30.0)  # left to right over the top; the lowest is the gap
PILE = 0.35  # from one icon of a pile to the next, further, along the circle [icon radii]
SLIDE = 6  # a step of the Wheel slides its icons this long: 0.1 s (D-083) [frames]
ACTIONS = (  # the wire at the top, the turns either side of the gap, delete last
    Tool.TURN_LEFT,
    Tool.MOVE,
    Tool.WIRE,
    Tool.SWAP,
    Tool.TURN_RIGHT,
    Tool.DELETE,
)


@dataclass(frozen=True)
class Slot:
    what: Enum  # a part to place, or an action on the part; in the Editor, its own (D-301)
    at: tuple[float, float]  # the icon's centre [px]
    key: str
    depth: float = 0  # 0 on the rim; 1, 2... down a pile, the further the lower; between, sliding


def offer(board: Board, cell, kinds: frozenset[Kind]) -> tuple[Kind | Tool, ...]:
    """What the Wheel round `cell` offers: on an empty cell of the zone, the parts the level still
    hands out, in Parts' order; on a part, its actions; elsewhere, nothing."""
    if cell not in board.cells:
        return ()
    node = board.node_at(cell)
    if node is None:
        ordered = [k for _, group in MENU_GROUPS for k in group if k in kinds]
        return tuple(k for k in ordered if board.remaining(k) != 0)
    if node.locked:  # placed by the level: it stays, it may still be wired
        return (Tool.WIRE,)
    turns = node.kind.default_facing is not None  # its facing matters (D-009)
    swap = bool(swaps(board, cell, kinds))
    return tuple(
        a
        for a in ACTIONS
        if (turns or a not in (Tool.TURN_LEFT, Tool.TURN_RIGHT)) and (swap or a is not Tool.SWAP)
    )


def swaps(board: Board, cell, kinds: frozenset[Kind]) -> tuple[Kind, ...]:
    """What the part on `cell` may be swapped for: the other parts of its group in Parts that
    the level still hands out, in Parts' order."""
    node = board.node_at(cell)
    if node is None or node.locked:
        return ()
    ordered = [k for _, group in MENU_GROUPS for k in group if k in kinds]
    return tuple(
        k
        for k in ordered
        if k.category is node.kind.category and k is not node.kind and board.remaining(k) != 0
    )


def part_key(kind: Kind, kinds: frozenset[Kind]) -> str:
    """A part's number key: its place among the parts the level hands out, as in Parts."""
    ordered = [k for _, group in MENU_GROUPS for k in group if k in kinds]
    return str(ordered.index(kind) + 1)


def angles(n: int) -> list[float]:
    """Where n <= ON_RIM icons sit round the cell, from the left clockwise, each beyond a
    corner, side by side with no corner left empty between them, as near the middle as they can
    be: an odd number centred on the top one, an even one a corner to its left (D-316)
    [degrees, counter-clockwise from the right]."""
    first = (ON_RIM - n) // 2
    return list(CORNERS[first : first + n])


def turned(turn: int, chosen: int | None, n: int) -> int:
    """The Wheel's turn, the first of its `n` icons on the rim, moved just enough for icon
    `chosen` to be on it."""
    if chosen is not None:
        turn = min(max(turn, chosen - ON_RIM + 1), chosen)
    return min(max(turn, 0), max(0, n - ON_RIM))


def slid(start: float, aim: int, left: int) -> float:
    """The turn the Wheel shows `left` frames before its slide from `start` reaches `aim`: eased
    out, quick at first and slowing as it arrives, as a card file clicks into place (D-083)."""
    u = left / SLIDE
    return aim + (start - aim) * u * u


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


def pile_at(
    n: int, turn: int, centre: tuple[float, float], size: float, point: tuple[float, float]
) -> int:
    """Which way the mouse resting at `point` turns the Wheel of `n` icons: -1 on the pile under
    the rim's first end, 1 on the one under its last, 0 elsewhere. A pile's area runs one icon
    radius on past its end icon, along the circle; the end icon itself is not in it."""
    turn = turned(turn, None, n)
    rim = angles(min(n, ON_RIM))
    r = ICON * size

    def on_circle(angle: float) -> tuple[float, float]:
        a = math.radians(angle)
        return centre[0] + RADIUS * size * math.cos(a), centre[1] - RADIUS * size * math.sin(a)

    halfway = math.degrees(1.5 * ICON / RADIUS)  # past the end icon, half a radius on
    piles = (
        (-1, turn > 0, rim[0] if rim else 0.0),
        (1, n > turn + ON_RIM, rim[-1] if rim else 0.0),
    )
    for way, piled, end in piles:
        if not piled or math.dist(point, on_circle(end)) <= r:
            continue  # no pile there, or on the end icon: a click takes it
        if math.dist(point, on_circle(end - way * halfway)) <= r:
            return way
    return 0


def centre_in(view: tuple[int, int, int, int]) -> tuple[float, float]:
    """Where a drawer draws the focused cell in its picture `view` (x, y, width, height [px]):
    across the middle, the Wheel's top icon just under its top."""
    x, y, w, _ = view
    return (x + w / 2, y + HEADROOM + (RADIUS + ICON) * WHEEL_HEX)


def slot_at(wheel: Sequence[Slot], point: tuple[float, float], size: float) -> Slot | None:
    """The icon on the rim a press at `point` falls on, if any; a pile's lie under its end."""
    return next((s for s in wheel if not s.depth and math.dist(s.at, point) <= ICON * size), None)


def cycled(wheel: Sequence[Slot], chosen: int | None, step: int) -> int | None:
    """The keyboard's choice after an arrow: the next icon along the arc (step 1) or the one
    before, stopping at its first and its last; from "nothing", where the Wheel opens round a
    part, the first or the last (D-084)."""
    if not wheel:
        return None
    if chosen is None or not 0 <= chosen < len(wheel):
        return 0 if step > 0 else len(wheel) - 1
    return min(max(chosen + step, 0), len(wheel) - 1)
