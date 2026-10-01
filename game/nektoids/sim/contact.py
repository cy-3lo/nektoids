"""Contacts: obstacles are hard and frictionless (D-022); the plane is open, no walls (D-028).

After each step, a body that overlaps an obstacle is moved radially out until it touches it,
obstacles in arena order. For an overdamped body this cancels the velocity into the contact and
keeps the rest: it slides. Contacts exert no torque. A few fixed passes settle a body in a
crevice between two obstacles. Lights are not solid, and bodies do not touch each other yet.

Vectorised over the bodies; the Python loops run over the passes and the obstacles only, in a
fixed order (invariant 1). Lengths in u, the base body radius. Pure numpy.
"""

from __future__ import annotations

import numpy as np

from nektoids.sim.arena import Arena
from nektoids.sim.optics import TINY

CONTACT_PASSES = 3  # every obstacle in turn, this many times a step


def confine(arena: Arena, pos: np.ndarray, radius: np.ndarray) -> np.ndarray:
    """(N, 2): the centres `pos` (N, 2) [u] of bodies of `radius` (N,) [u], put back outside
    every obstacle, as a new array. A centre on an obstacle's centre has no way out of its own
    and leaves along +x."""
    pos = np.array(pos, dtype=np.float64).reshape(-1, 2)
    radius = np.asarray(radius, dtype=np.float64)
    for _ in range(CONTACT_PASSES):
        for (cx, cy), r in zip(arena.disc_xy, arena.disc_radius, strict=True):
            dx, dy = pos[:, 0] - cx, pos[:, 1] - cy
            dist = np.sqrt(dx * dx + dy * dy)
            touch = radius + r
            centred = dist < TINY
            ux = np.where(centred, 1.0, dx / np.maximum(dist, TINY))
            uy = np.where(centred, 0.0, dy / np.maximum(dist, TINY))
            inside = dist < touch
            pos[:, 0] = np.where(inside, cx + touch * ux, pos[:, 0])
            pos[:, 1] = np.where(inside, cy + touch * uy, pos[:, 1])
    return pos
