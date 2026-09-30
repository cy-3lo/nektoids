"""Light: point sources, 1/r, hard shadows cast by discs, no reflection (D-019).

An eye is a flat detector at x looking along the unit vector n. It reads

    E = sum over lights l of  P_l max(0, n . s_l) / max(r_l, R_MIN) V_l

with s_l the unit vector from x to light l, r_l its distance, P_l its power, and V_l = 1 if the
segment from x to the light meets no disc, 0 otherwise. The 2 pi of 2D spreading is folded into
P, so P is the distance at which an eye looking straight at the light reads RATE_MAX. The rate
of an eye is min(RATE_MAX, E), the cap every node has (D-016).

The discs are the obstacles and the swimmers' bodies. A body shadows every eye but its own: the
body is transparent to its own parts (D-018). The light map a player sees is what an eye looking
straight at each light would read there, so what is drawn is what is sensed.

Arrays are combined component by component and the lights are added one by one in a fixed
order, never with `@` or einsum, so a row does not depend on the batch it is in (invariant 1).
Lengths in u, the base body radius; x right, y up, angles counter-clockwise. Pure numpy.
"""

from __future__ import annotations

import numpy as np

from nektoids.graph.dynamics import RATE_MAX
from nektoids.sim.arena import Arena

R_MIN = 0.5  # [u] a light closer than this counts as this far: its own size, no 1/0
TINY = 1e-12  # [u] below this a length is zero, and a direction along it is none
FACING_STEP = np.pi / 3  # hex direction d points at 60° * d on the body (D-009)


def exposure(
    points: np.ndarray, looks: np.ndarray | None, lights: np.ndarray, power: np.ndarray
) -> np.ndarray:
    """(P, L): what each light gives each point with nothing in the way, P_l cos+ / max(r, R_MIN).

    points (P, 2); looks (P, 2) unit vectors, or None for an eye that looks straight at each
    light in turn (the light map); lights (L, 2); power (L,). A point on a light sees no
    direction to it and gets nothing from it unless `looks` is None.
    """
    dx = lights[None, :, 0] - points[:, None, 0]
    dy = lights[None, :, 1] - points[:, None, 1]
    r = np.sqrt(dx * dx + dy * dy)
    if looks is None:
        cosine = np.ones_like(r)
    else:
        cosine = (looks[:, None, 0] * dx + looks[:, None, 1] * dy) / np.maximum(r, TINY)
    return power[None, :] * np.maximum(cosine, 0.0) / np.maximum(r, R_MIN)


def visible(
    points: np.ndarray,
    lights: np.ndarray,
    centres: np.ndarray,
    radii: np.ndarray,
    skip: np.ndarray | None = None,
) -> np.ndarray:
    """(P, L) bool: whether the segment from each point to each light misses every disc.

    points (P, 2), lights (L, 2), centres (M, 2), radii (M,). skip: (P,) the disc each point
    ignores (its own body), -1 for none. With d = light - point and w = centre - point, the point
    of the segment nearest the centre is at t = clip(w.d / d.d, 0, 1), and the disc blocks the
    ray if that point is closer than its radius. A ray that grazes a disc passes.
    """
    dx = lights[None, :, 0] - points[:, None, 0]  # (P, L)
    dy = lights[None, :, 1] - points[:, None, 1]
    wx = centres[None, :, 0] - points[:, None, 0]  # (P, M)
    wy = centres[None, :, 1] - points[:, None, 1]
    dx, dy = dx[:, :, None], dy[:, :, None]  # (P, L, 1)
    wx, wy = wx[:, None, :], wy[:, None, :]  # (P, 1, M)
    t = np.clip((wx * dx + wy * dy) / np.maximum(dx * dx + dy * dy, TINY * TINY), 0.0, 1.0)
    qx, qy = t * dx - wx, t * dy - wy  # nearest point of the segment, from the centre
    blocked = qx * qx + qy * qy < (radii * radii)[None, None, :]
    if skip is not None:
        blocked &= np.arange(len(radii))[None, None, :] != np.asarray(skip)[:, None, None]
    return ~blocked.any(axis=2)


def add_lights(given: np.ndarray, seen: np.ndarray) -> np.ndarray:
    """(P,): the sum over lights of what each gives where it is seen, lights taken in order."""
    total = np.zeros(given.shape[0])
    for light in range(given.shape[1]):
        total = total + np.where(seen[:, light], given[:, light], 0.0)
    return total


def eye_poses(
    pos: np.ndarray,
    heading: np.ndarray,
    radius: np.ndarray,
    mount: np.ndarray,
    facing: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Where each eye is and where it looks: two arrays (N, k, 2), points [u] and unit vectors.

    pos (N, 2), heading (N,) [rad], radius (N,) [u] for N bodies; mount (k, 2) in body radii and
    facing (k,) hex directions for their k eyes (`Network.mount`, `Network.facing`, D-018).
    """
    cos, sin = np.cos(heading)[:, None], np.sin(heading)[:, None]
    mx, my = mount[None, :, 0], mount[None, :, 1]
    x = pos[:, 0, None] + radius[:, None] * (cos * mx - sin * my)
    y = pos[:, 1, None] + radius[:, None] * (sin * mx + cos * my)
    angle = heading[:, None] + FACING_STEP * np.asarray(facing, dtype=np.float64)[None, :]
    return np.stack((x, y), axis=2), np.stack((np.cos(angle), np.sin(angle)), axis=2)


def discs(arena: Arena, pos: np.ndarray, radius: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Everything that casts a shadow: the obstacles, then the N bodies. (M + N, 2), (M + N,)."""
    centres = np.concatenate((arena.disc_xy, np.asarray(pos, dtype=np.float64).reshape(-1, 2)))
    return centres, np.concatenate((arena.disc_radius, np.asarray(radius, dtype=np.float64)))


def eye_rates(
    arena: Arena,
    pos: np.ndarray,
    heading: np.ndarray,
    radius: np.ndarray,
    mount: np.ndarray,
    facing: np.ndarray,
) -> np.ndarray:
    """(N, k): what the k eyes of each of N bodies send, in [0, RATE_MAX].

    Arguments as for `eye_poses`. Every body shadows the others' eyes, never its own.
    """
    points, looks = eye_poses(pos, heading, radius, mount, facing)
    n, k = points.shape[:2]
    points, looks = points.reshape(-1, 2), looks.reshape(-1, 2)
    centres, radii = discs(arena, pos, radius)
    own = len(arena.obstacles) + np.repeat(np.arange(n), k)
    given = exposure(points, looks, arena.light_xy, arena.light_power)
    seen = visible(points, arena.light_xy, centres, radii, skip=own)
    return np.minimum(RATE_MAX, add_lights(given, seen)).reshape(n, k)


def light_map(arena: Arena, points: np.ndarray, pos: np.ndarray, radius: np.ndarray) -> np.ndarray:
    """(P,): what an eye looking straight at each light would read at each point, in
    [0, RATE_MAX], with the obstacles and the bodies at `pos` (N, 2), `radius` (N,) in the way.
    """
    centres, radii = discs(arena, pos, radius)
    given = exposure(points, None, arena.light_xy, arena.light_power)
    seen = visible(points, arena.light_xy, centres, radii)
    return np.minimum(RATE_MAX, add_lights(given, seen))
