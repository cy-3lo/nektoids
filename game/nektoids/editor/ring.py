"""The ring of icons round a focused cell: what can be done there, at hand (D-068).

An empty cell of the zone offers the parts the level still hands out; a part offers turn left,
turn right (eyes and thrusters only), wire, move and delete. Up to six icons sit beyond the
cell's six faces, where its neighbours are; more are spread along a 300° arc, its gap at the
foot, at two radii in turn when they would touch, as the stations of an indexing table. Each
icon has its key just outside it. Where the ring would leave the main screen it is slid in,
whole. Pure numbers, no pygame.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from nektoids.editor.layout import MENU_GROUPS, TOOL_KEYS, Rect, Tool
from nektoids.graph.board import Board, Kind

RADIUS = 1.75  # from the cell's centre to an icon's, about a neighbour's [hex sizes]
ICON = 0.42  # an icon's disc, its radius [hex sizes]
KEY_OUT = 0.78  # its key, this far past the icon's centre, outwards [hex sizes]
FACES = (120.0, 60.0, 0.0, 300.0, 240.0, 180.0)  # the neighbours, from the top left, clockwise
ARC = 300.0  # more than six icons spread over this much, the gap at the foot [degrees]
STAGGER = 0.22  # in turn nearer and farther, when they would touch [hex sizes]
ACTIONS = (Tool.TURN_LEFT, Tool.TURN_RIGHT, Tool.WIRE, Tool.MOVE, Tool.DELETE)
ACTION_FACE = {  # each action beyond its own face: the turns on top, as they turn
    Tool.TURN_LEFT: 120.0,
    Tool.TURN_RIGHT: 60.0,
    Tool.WIRE: 0.0,
    Tool.MOVE: 300.0,
    Tool.DELETE: 240.0,
}
TURNING = (Kind.EYE, Kind.THRUSTER)  # the parts whose facing matters (D-009)


@dataclass(frozen=True)
class Slot:
    what: Kind | Tool  # a part to place, or an action on the part
    at: tuple[float, float]  # the icon's centre [px]
    key_at: tuple[float, float]  # where its key is written [px]
    key: str


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
    return tuple(
        a for a in ACTIONS if node.kind in TURNING or a not in (Tool.TURN_LEFT, Tool.TURN_RIGHT)
    )


def part_key(kind: Kind, kinds: frozenset[Kind]) -> str:
    """A part's number key: its place among the parts the level hands out, as in Parts."""
    ordered = [k for _, group in MENU_GROUPS for k in group if k in kinds]
    return str(ordered.index(kind) + 1)


def angles(items: Sequence[Kind | Tool]) -> list[float]:
    """Where each icon sits round the cell [degrees, counter-clockwise from the right]."""
    if items and all(isinstance(i, Tool) for i in items):
        return [ACTION_FACE[i] for i in items]
    if len(items) <= len(FACES):
        return list(FACES[: len(items)])
    start, step = 270.0 - (360.0 - ARC) / 2, ARC / (len(items) - 1)  # from the gap's left edge
    return [(start - k * step) % 360.0 for k in range(len(items))]


def slots(
    items: Sequence[Kind | Tool],
    centre: tuple[float, float],
    size: float,
    kinds: frozenset[Kind],
    area: Rect,
) -> list[Slot]:
    """The ring's icons round a cell drawn at `centre` with hexes of `size` [px], slid whole
    into `area` if it would leave it."""
    turns = angles(items)
    gaps = [abs((b - a + 180.0) % 360.0 - 180.0) for a, b in zip(turns, turns[1:], strict=False)]
    chord = 2 * RADIUS * math.sin(math.radians(min(gaps, default=360.0)) / 2)
    crowded = chord < 2.2 * ICON  # neighbouring icons would touch
    radii = [
        RADIUS + (STAGGER if crowded and k % 2 else -STAGGER if crowded else 0.0)
        for k in range(len(items))
    ]
    cx, cy = centre
    points = []
    for a, r in zip(turns, radii, strict=True):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        points.append(((cx + r * size * c, cy - r * size * s), (c, s), r))
    reach = (KEY_OUT + ICON) * size  # an icon and its key
    xs = [p[0][0] for p in points] or [cx]
    ys = [p[0][1] for p in points] or [cy]
    x, y, w, h = area
    dx = max(0.0, x + reach - min(xs)) - max(0.0, max(xs) + reach - (x + w))
    dy = max(0.0, y + reach - min(ys)) - max(0.0, max(ys) + reach - (y + h))
    out = []
    for item, ((px, py), (c, s), _) in zip(items, points, strict=True):
        at = (px + dx, py + dy)
        key = TOOL_KEYS[item] if isinstance(item, Tool) else part_key(item, kinds)
        out.append(Slot(item, at, (at[0] + KEY_OUT * size * c, at[1] - KEY_OUT * size * s), key))
    return out


def slot_at(ring: Sequence[Slot], point: tuple[float, float], size: float) -> Slot | None:
    """The icon a press at `point` falls on, if any."""
    return next((s for s in ring if math.dist(s.at, point) <= ICON * size), None)


def cycled(ring: Sequence[Slot], chosen: int | None, step: int, blank: bool) -> int | None:
    """The keyboard's choice after an arrow: the next icon round (step 1) or the one before;
    with `blank`, "nothing" is one of the stops, between the last icon and the first."""
    stops: list[int | None] = list(range(len(ring))) + ([None] if blank else [])
    if not stops:
        return None
    k = stops.index(chosen) if chosen in stops else (len(stops) - 1 if step > 0 else 0)
    return stops[(k + step) % len(stops)]
