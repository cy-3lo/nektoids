"""Contacts: lights and obstacles are solid and frictionless (D-022, D-424); the plane is open, no
walls (D-028).

After each step, a body that overlaps a light or an obstacle is moved radially out until it
touches it. For an overdamped body this cancels the velocity into the contact and keeps the
rest: it slides. Contacts exert no torque. A few fixed passes settle a body in a crevice.

Lights are fixed. Each obstacle is a sphere in the same fluid as the swimmers, held at its rest
by a spring (D-424): a body pushing on it moves it, and it comes back. Neither has inertia, so
an overlap is shared as their drags say, ζ = 6πμR each: the body takes ζ_o / (ζ_b + ζ_o) of it,
the obstacle the rest. The spring pulls the obstacle back, ζ_o du/dt = -k u, by an Euler step as
the swimmers move (D-022): under a steady push F the obstacle then settles exactly where the
spring holds it, k u = F, whatever its size, a head-on push of two thrusters at full rate moving
it SPRING_GIVE; and let go it comes back by a factor 1 - k dt / ζ_o a step, never past its rest,
k dt / ζ_o being at most 1/3 for the smallest obstacle, 1 u.

Vectorised over the bodies; the Python loops run over the passes and the items only, in a fixed
order (invariant 1). Lengths in u, the base body radius. Pure numpy.
"""

from __future__ import annotations

import numpy as np

from nektoids.sim.arena import LIGHT_RADIUS, Arena
from nektoids.sim.motion import THRUST, VISCOSITY
from nektoids.sim.optics import TINY

CONTACT_PASSES = 3  # every light and obstacle in turn, this many times a step
SPRING_GIVE = 0.15  # [u] how far a head-on push of two thrusters at full rate moves an obstacle
SPRING = 2.0 * THRUST / SPRING_GIVE  # [f/u] k, each obstacle's spring, from SPRING_GIVE


def drag(radius: np.ndarray) -> np.ndarray:
    """A sphere's Stokes drag, ζ = 6πμR [f s/u], for radius (…) [u]."""
    return 6.0 * np.pi * VISCOSITY * np.asarray(radius, dtype=np.float64)


def _outwards(pos: np.ndarray, centre, touch) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """For bodies at `pos` (N, 2) and a disc at `centre` they touch at `touch` (N,): how deep each
    is in (N,), 0 if out, and the unit vector out of the disc's centre (N,) twice. A centre on
    the disc's centre leaves along +x."""
    dx, dy = pos[:, 0] - centre[0], pos[:, 1] - centre[1]
    dist = np.sqrt(dx * dx + dy * dy)
    centred = dist < TINY
    ux = np.where(centred, 1.0, dx / np.maximum(dist, TINY))
    uy = np.where(centred, 0.0, dy / np.maximum(dist, TINY))
    return np.maximum(0.0, touch - dist), ux, uy


def confine(arena: Arena, pos: np.ndarray, radius: np.ndarray) -> np.ndarray:
    """(N, 2): the centres `pos` (N, 2) [u] of bodies of `radius` (N,) [u], put back outside every
    light and obstacle, which do not move, as a new array: where a body is put by hand."""
    pos = np.array(pos, dtype=np.float64).reshape(-1, 2)
    radius = np.asarray(radius, dtype=np.float64)
    discs = [(c, LIGHT_RADIUS) for c in arena.light_xy]
    discs += list(zip(arena.disc_xy, arena.disc_radius, strict=True))
    for _ in range(CONTACT_PASSES):
        for centre, r in discs:
            depth, ux, uy = _outwards(pos, centre, radius + r)
            pos[:, 0] += depth * ux
            pos[:, 1] += depth * uy
    return pos


def collide(
    arena: Arena, offsets: np.ndarray, pos: np.ndarray, radius: np.ndarray, dt: float
) -> tuple[np.ndarray, np.ndarray]:
    """The bodies at `pos` (N, 2) [u] of `radius` (N,) [u] and the obstacles `offsets` (M, 2) [u]
    from their rest, a step of `dt` [s] on: each obstacle drawn back by its spring, then every
    overlap shared between body and obstacle, a light keeping its place. New arrays."""
    pos = np.array(pos, dtype=np.float64).reshape(-1, 2)
    radius = np.asarray(radius, dtype=np.float64)
    size = arena.disc_radius
    offsets = np.array(offsets, dtype=np.float64).reshape(-1, 2)
    offsets *= np.maximum(0.0, 1.0 - dt * SPRING / drag(size))[:, None]  # ζ du/dt = -k u
    body = drag(radius)
    for _ in range(CONTACT_PASSES):
        for centre in arena.light_xy:
            depth, ux, uy = _outwards(pos, centre, radius + LIGHT_RADIUS)
            pos[:, 0] += depth * ux
            pos[:, 1] += depth * uy
        for m, r in enumerate(size):
            centre = arena.rest_xy[m] + offsets[m]
            depth, ux, uy = _outwards(pos, centre, radius + r)
            share = drag(r) / (body + drag(r))  # the body's part of the overlap
            pos[:, 0] += share * depth * ux
            pos[:, 1] += share * depth * uy
            offsets[m, 0] -= np.sum((1.0 - share) * depth * ux)
            offsets[m, 1] -= np.sum((1.0 - share) * depth * uy)
    return pos, offsets
