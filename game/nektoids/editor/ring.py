"""The ring of icons round the focused cell, what can be done there (D-068), as Tools and Parts
draw it: round a picture of the cell, large, where the icons have room (D-069).

An empty cell of the zone offers the parts the level still hands out; a part offers turn left,
move, wire, swap when another part of its group is left, turn right (eyes and thrusters only)
and delete; swapping, the ring offers those parts. Up to five icons sit beyond the cell's
corners, the lowest left free, the gap at the foot: an odd number centred on the top corner, an
even one as many each side of it. More turn on a wheel, as cards on a rotary
file: five on the ring, the others piled under its two ends, drawn empty, each set back a third
of an icon's radius along the circle, those before the ring under its first end, those after it
under its last. The keyboard going round turns the wheel; so does the mouse wheel, or the mouse
resting on a pile, past its end icon. Each icon on the
ring has its key just outside it. Pure numbers, no pygame.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from nektoids.editor.layout import MENU_GROUPS, TOOL_KEYS, Tool
from nektoids.graph.board import Board, Kind

RADIUS = 1.8  # from the cell's centre to an icon's, beyond a corner [hex sizes]
ICON = 0.62  # an icon's disc, its radius: the part on it just smaller than the cell's [hex sizes]
KEY_OUT = 0.95  # its key, this far past the icon's centre, outwards [hex sizes]
RING_HEX = 40  # the cell's size in the drawer's picture [px]
HEADROOM = 14  # over the ring's top key, in that picture [px]
LINE_BELOW = 12  # from the ring's lowest icon to the line under it, saying what the cell holds [px]
IN_RING = 5  # the most icons on the ring itself; more pile up below its ends
CORNERS = (210.0, 150.0, 90.0, 30.0, -30.0)  # left to right over the top; the lowest is the gap
PILE = 0.35  # from one icon of a pile to the next, further, along the circle [icon radii]
ACTIONS = (  # the wire at the top, the turns either side of the gap, delete last
    Tool.TURN_LEFT,
    Tool.MOVE,
    Tool.WIRE,
    Tool.SWAP,
    Tool.TURN_RIGHT,
    Tool.DELETE,
)
TURNING = (Kind.EYE, Kind.THRUSTER)  # the parts whose facing matters (D-009)


@dataclass(frozen=True)
class Slot:
    what: Kind | Tool  # a part to place, or an action on the part
    at: tuple[float, float]  # the icon's centre [px]
    key_at: tuple[float, float]  # where its key is written [px]
    key: str
    depth: int = 0  # 0 on the ring; 1, 2... down a pile, the further the lower


def offer(board: Board, cell, kinds: frozenset[Kind]) -> tuple[Kind | Tool, ...]:
    """What the ring round `cell` offers: on an empty cell of the zone, the parts the level still
    hands out, in Parts' order; on a part, its actions; elsewhere, nothing."""
    if cell not in board.cells:
        return ()
    node = board.node_at(cell)
    if node is None:
        ordered = [k for _, group in MENU_GROUPS for k in group if k in kinds]
        return tuple(k for k in ordered if board.remaining(k) != 0)
    if node.locked:  # placed by the level: it stays, it may still be wired
        return (Tool.WIRE,)
    turns = node.kind in TURNING
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
    """Where n <= IN_RING icons sit round the cell, from the left clockwise, each beyond a
    corner: an odd number centred on the top one, an even one as many each side of it
    [degrees, counter-clockwise from the right]."""
    if n % 2:
        first = (IN_RING - n) // 2
        return list(CORNERS[first : first + n])
    side = n // 2
    return list(CORNERS[2 - side : 2] + CORNERS[3 : 3 + side])


def turned(turn: int, chosen: int | None, n: int) -> int:
    """The wheel's turn, the first of `n` icons on the ring, moved just enough for icon `chosen`
    to be on it."""
    if chosen is not None:
        turn = min(max(turn, chosen - IN_RING + 1), chosen)
    return min(max(turn, 0), max(0, n - IN_RING))


def slots(
    items: Sequence[Kind | Tool],
    centre: tuple[float, float],
    size: float,
    kinds: frozenset[Kind],
    turn: int = 0,
) -> list[Slot]:
    """The icons round a cell drawn at `centre` with hexes of `size` [px], the wheel turned by
    `turn`: the icons before it piled under the ring's first end, those after it under its last,
    each further one set back along the circle, towards the gap."""
    turn = turned(turn, None, len(items))
    ring = angles(min(len(items), IN_RING))
    cx, cy = centre

    def on_ring(angle: float) -> tuple[tuple[float, float], tuple[float, float]]:
        c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        return (cx + RADIUS * size * c, cy - RADIUS * size * s), (c, s)

    out = []
    for k, item in enumerate(items):
        key = TOOL_KEYS[item] if isinstance(item, Tool) else part_key(item, kinds)
        if turn <= k < turn + IN_RING:
            at, (c, s) = on_ring(ring[k - turn])
            out.append(
                Slot(item, at, (at[0] + KEY_OUT * size * c, at[1] - KEY_OUT * size * s), key)
            )
            continue
        before = k < turn  # piled under the first end, or under the last
        depth = turn - k if before else k - turn - IN_RING + 1
        back = math.degrees(depth * PILE * ICON / RADIUS)  # set back along the circle
        at, _ = on_ring(ring[0] + back if before else ring[-1] - back)
        out.append(Slot(item, at, at, key, depth))  # drawn empty, its key unwritten
    return out


def pile_at(
    n: int, turn: int, centre: tuple[float, float], size: float, point: tuple[float, float]
) -> int:
    """Which way the mouse resting at `point` turns the wheel of `n` icons: -1 on the pile under
    the ring's first end, 1 on the one under its last, 0 elsewhere. A pile's area runs one icon
    radius on past its end icon, along the circle; the end icon itself is not in it."""
    turn = turned(turn, None, n)
    ring = angles(min(n, IN_RING))
    r = ICON * size

    def on_circle(angle: float) -> tuple[float, float]:
        a = math.radians(angle)
        return centre[0] + RADIUS * size * math.cos(a), centre[1] - RADIUS * size * math.sin(a)

    halfway = math.degrees(1.5 * ICON / RADIUS)  # past the end icon, half a radius on
    piles = (
        (-1, turn > 0, ring[0] if ring else 0.0),
        (1, n > turn + IN_RING, ring[-1] if ring else 0.0),
    )
    for way, piled, end in piles:
        if not piled or math.dist(point, on_circle(end)) <= r:
            continue  # no pile there, or on the end icon: a click takes it
        if math.dist(point, on_circle(end - way * halfway)) <= r:
            return way
    return 0


def centre_in(view: tuple[int, int, int, int]) -> tuple[float, float]:
    """Where a drawer draws the focused cell in its picture `view` (x, y, width, height [px]):
    across the middle, the ring's top key just under its top."""
    x, y, w, _ = view
    return (x + w / 2, y + HEADROOM + (RADIUS + KEY_OUT) * RING_HEX)


def slot_at(ring: Sequence[Slot], point: tuple[float, float], size: float) -> Slot | None:
    """The icon on the ring a press at `point` falls on, if any; a pile's lie under its end."""
    return next((s for s in ring if not s.depth and math.dist(s.at, point) <= ICON * size), None)


def cycled(ring: Sequence[Slot], chosen: int | None, step: int, blank: bool) -> int | None:
    """The keyboard's choice after an arrow: the next icon round (step 1) or the one before;
    with `blank`, "nothing" is one of the stops, between the last icon and the first."""
    stops: list[int | None] = list(range(len(ring))) + ([None] if blank else [])
    if not stops:
        return None
    k = stops.index(chosen) if chosen in stops else (len(stops) - 1 if step > 0 else 0)
    return stops[(k + step) % len(stops)]
