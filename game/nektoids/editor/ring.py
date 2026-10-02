"""The ring of icons round the focused cell, what can be done there (D-068), as Tools draws it:
round a picture of the cell, large, where the icons have room.

An empty cell of the zone offers the parts the level still hands out; a part offers turn left,
move, wire, swap when another part of its group is left, turn right (eyes and thrusters only)
and delete; swapping, the ring offers those parts. Up to five icons sit beyond the cell's
corners, the lowest left free, the gap at the foot: an odd number centred on the top corner, an
even one as many each side of it. More turn on a wheel, as cards on a rotary
file: five on the ring, the others piled below its two ends, each further one lower, those before
the ring under its first end, those after it under its last. The keyboard going round turns the
wheel. Each icon has its key just outside it. Pure numbers, no pygame.
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
RING_HEX = 40  # the cell's size in Tools' picture [px]
IN_RING = 5  # the most icons on the ring itself; more pile up below its ends
CORNERS = (210.0, 150.0, 90.0, 30.0, -30.0)  # left to right over the top; the lowest is the gap
PILE = 1.4  # from one icon of a pile to the next, further, below it [icon radii]
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
    `turn`: the icons before it piled under the ring's first end, those after it under its last."""
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
        (ex, ey), _ = on_ring(ring[0] if before else ring[-1])
        at = (ex, ey + depth * PILE * ICON * size)
        side = -1 if before else 1  # its key outwards, beside the pile
        out.append(Slot(item, at, (at[0] + side * KEY_OUT * size, at[1]), key, depth))
    return out


def slot_at(ring: Sequence[Slot], point: tuple[float, float], size: float) -> Slot | None:
    """The icon a press at `point` falls on, if any: where they overlap, the nearer, drawn over
    the further."""
    near_first = sorted(ring, key=lambda s: s.depth)
    return next((s for s in near_first if math.dist(s.at, point) <= ICON * size), None)


def cycled(ring: Sequence[Slot], chosen: int | None, step: int, blank: bool) -> int | None:
    """The keyboard's choice after an arrow: the next icon round (step 1) or the one before;
    with `blank`, "nothing" is one of the stops, between the last icon and the first."""
    stops: list[int | None] = list(range(len(ring))) + ([None] if blank else [])
    if not stops:
        return None
    k = stops.index(chosen) if chosen in stops else (len(stops) - 1 if step > 0 else 0)
    return stops[(k + step) % len(stops)]
