"""Where a wire is drawn, as a polyline in pixels.

A wire leaves its source centre, crosses each free cell from the midpoint of the edge it comes
in by to the midpoint of the edge it leaves by, and ends at its target centre. At an edge
midpoint it always runs perpendicular to the edge, so the drawing is smooth:

- straight through: a segment through the cell centre;
- turning: the circular arc tangent to both edge normals (D-010). For a sharp 120° turn the two
  edges are adjacent and the arc, of radius s/2, is centred on their shared corner; for a gentle
  60° turn one edge lies between them and the arc, of radius 1.5 s, is centred outside the cell
  (s: centre-to-corner size of a hex).

An arrow in each crossed cell shows which way the signal flows: a little past the centre on a
straight run (so two wires crossing there keep distinct arrows), at the middle of the arc on a
turn.

Pure numbers, no pygame, so the drawing and the delete tool's hit test share one geometry.
"""

from __future__ import annotations

import math
from bisect import bisect_right

from nektoids.graph.board import Wire, crossings
from nektoids.graph.hexgrid import SQRT3, Cell, opposite, to_pixel
from nektoids.graph.network import body_disc

Point = tuple[float, float]  # [px]

ARC_SAMPLES = 8  # segments per arc (even, so an arc has a middle sample)
ARROW_PAST_CENTRE = 0.3  # where a straight run's arrow sits, past the centre [hex sizes]


# The swimmer's symbol: a circle round a wedge, two sides of an equilateral triangle, tip
# forward [rad]: the tip, then its two other corners.
BODY_CORNERS = (0.0, 2.0 * math.pi / 3.0, -2.0 * math.pi / 3.0)


def body_circle(zone: list[Cell], size: float, origin: Point) -> tuple[Point, float]:
    """The swimmer's body on the board (D-018): its centre and radius [px]."""
    (cx, cy), reach = body_disc(zone)
    return (origin[0] + size * cx, origin[1] + size * cy), size * reach


def symbol_corners(centre: Point, radius: float, heading: float = 0.0) -> list[Point]:
    """The tip and the two other corners of the swimmer's wedge, on the circle of `radius` round
    `centre` [px], the tip at `heading` [rad, counter-clockwise on screen, 0 = E], 120° apart."""
    x, y = centre
    return [
        (x + radius * math.cos(heading + a), y - radius * math.sin(heading + a))
        for a in BODY_CORNERS
    ]


def edge_midpoint(cell: Cell, edge: int, size: float, origin: Point) -> Point:
    """Midpoint of the edge of `cell` that faces direction `edge` (at screen angle -60° * edge)."""
    x, y = to_pixel(cell, size, origin)
    inner = 0.5 * SQRT3 * size  # centre to edge midpoint
    angle = math.radians(-60.0 * edge)
    return (x + inner * math.cos(angle), y + inner * math.sin(angle))


def turn_centre(cell: Cell, entry: int, exit_: int, size: float, origin: Point) -> Point:
    """Centre of the arc of a wire turning in `cell`: where the lines of its two edges meet."""
    a, b = edge_midpoint(cell, entry, size, origin), edge_midpoint(cell, exit_, size, origin)
    # Each edge line runs perpendicular to its outward normal, at screen angle -60° * edge.
    ta = _unit(-60.0 * entry + 90.0)
    tb = _unit(-60.0 * exit_ + 90.0)
    # Solve a + t * ta = b + u * tb for t (2 x 2, by Cramer's rule).
    det = ta[0] * (-tb[1]) - ta[1] * (-tb[0])
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = (dx * (-tb[1]) - dy * (-tb[0])) / det
    return (a[0] + t * ta[0], a[1] + t * ta[1])


def wire_points(path: tuple[Cell, ...], size: float, origin: Point) -> list[Point]:
    """The drawn wire, from the source centre to the target centre."""
    points = [to_pixel(path[0], size, origin)]
    for cell, entry, exit_ in crossings(path):
        a = edge_midpoint(cell, entry, size, origin)
        b = edge_midpoint(cell, exit_, size, origin)
        if exit_ == opposite(entry):
            points += [a, b]
        else:
            points += _arc(turn_centre(cell, entry, exit_, size, origin), a, b)
    points.append(to_pixel(path[-1], size, origin))
    return points


def wire_arrows(path: tuple[Cell, ...], size: float, origin: Point) -> list[tuple[Point, float]]:
    """One arrow per free cell the wire crosses: where it sits, and its screen angle [rad]."""
    arrows = []
    for cell, entry, exit_ in crossings(path):
        a = edge_midpoint(cell, entry, size, origin)
        b = edge_midpoint(cell, exit_, size, origin)
        if exit_ == opposite(entry):
            angle = math.atan2(b[1] - a[1], b[0] - a[0])
            x, y = to_pixel(cell, size, origin)
            reach = ARROW_PAST_CENTRE * size
            arrows.append(((x + reach * math.cos(angle), y + reach * math.sin(angle)), angle))
        else:
            arc = _arc(turn_centre(cell, entry, exit_, size, origin), a, b)
            mid = ARC_SAMPLES // 2
            before, after = arc[mid - 1], arc[mid + 1]
            arrows.append((arc[mid], math.atan2(after[1] - before[1], after[0] - before[0])))
    return arrows


def _arc(centre: Point, a: Point, b: Point) -> list[Point]:
    """Points on the circle about `centre` from a to b, the short way round, both included."""
    radius = math.dist(centre, a)
    start = math.atan2(a[1] - centre[1], a[0] - centre[0])
    end = math.atan2(b[1] - centre[1], b[0] - centre[0])
    sweep = (end - start + math.pi) % (2.0 * math.pi) - math.pi
    return [
        (
            centre[0] + radius * math.cos(start + sweep * k / ARC_SAMPLES),
            centre[1] + radius * math.sin(start + sweep * k / ARC_SAMPLES),
        )
        for k in range(ARC_SAMPLES + 1)
    ]


def _unit(degrees: float) -> Point:
    return (math.cos(math.radians(degrees)), math.sin(math.radians(degrees)))


def cumulative_lengths(points: list[Point]) -> list[float]:
    """Distance along the polyline to each of its points; starts at 0, ends at its length."""
    lengths = [0.0]
    for a, b in zip(points, points[1:], strict=False):
        lengths.append(lengths[-1] + math.dist(a, b))
    return lengths


def point_at(points: list[Point], cumulative: list[float], distance: float) -> Point:
    """The point `distance` along the polyline (clamped to its ends); `cumulative` from above."""
    if distance <= 0.0:
        return points[0]
    if distance >= cumulative[-1]:
        return points[-1]
    k = bisect_right(cumulative, distance) - 1  # the segment points[k] -> points[k + 1]
    span = cumulative[k + 1] - cumulative[k]
    t = (distance - cumulative[k]) / span
    (x0, y0), (x1, y1) = points[k], points[k + 1]
    return (x0 + t * (x1 - x0), y0 + t * (y1 - y0))


def distance_to_polyline(point: Point, points: list[Point]) -> float:
    """Shortest distance from `point` to the polyline through `points` [px]."""
    return min(_distance_to_segment(point, a, b) for a, b in zip(points, points[1:], strict=False))


def nearest_wire(
    point: Point, wires: list[Wire], size: float, origin: Point, within: float
) -> Wire | None:
    """The wire drawn closest to `point`, if closer than `within` [px]; ties go to the first."""
    best, best_distance = None, within
    for wire in wires:
        distance = distance_to_polyline(point, wire_points(wire.path, size, origin))
        if distance < best_distance:
            best, best_distance = wire, distance
    return best


def _distance_to_segment(p: Point, a: Point, b: Point) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 == 0.0 else ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length2
    t = min(1.0, max(0.0, t))
    return math.dist(p, (a[0] + t * dx, a[1] + t * dy))
