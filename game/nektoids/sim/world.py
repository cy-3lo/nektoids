"""One tick of the swimmers: move, touch, see, think (D-022).

The state of N swimmers is four arrays that the caller keeps (the arena view, a test): pos (N, 2)
[u], heading (N,) [rad], radius (N,) [u], and y (N, n), the rates of their nodes (D-017). A tick
of dt [s]:

1. move: with the thrust the nodes have now, against the Stokes drag of a sphere (`motion`);
2. touch: back outside the obstacles (`contact`); the plane is open (D-028);
3. see: the eyes read the light where the bodies now are (`optics`);
4. think: the nodes follow, one lagged step (`graph.dynamics`).

So after a tick, as after a restart or a drag, y's eye columns are what the eyes read where the
bodies are. Nothing is changed in place. Pure numpy, no pygame.
"""

from __future__ import annotations

import hashlib

import numpy as np

from nektoids.graph import dynamics
from nektoids.graph.network import Network
from nektoids.sim.arena import Arena
from nektoids.sim.contact import confine
from nektoids.sim.motion import advance, stokes, thrust
from nektoids.sim.optics import eye_rates


def parts(net: Network, indices: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Mounts (k, 2) in body radii and facings (k,) hex directions of the nodes `indices`, such
    as `net.eyes` or `net.thrusters` (D-018)."""
    facing = np.array([net.facing[i] for i in indices], dtype=np.int64)
    return net.mount[indices], facing


def step(
    arena: Arena,
    net: Network,
    pos: np.ndarray,
    heading: np.ndarray,
    radius: np.ndarray,
    y: np.ndarray,
    dt: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(pos, heading, y) one tick later, as new arrays; the arguments are not changed.

    pos (N, 2) [u], heading (N,) [rad], radius (N,) [u], y (N, n) the nodes' rates; dt [s], with
    0 < dt <= TAU (`graph.dynamics.step` raises ValueError otherwise).
    """
    force, torque = thrust(dynamics.thrust_rates(net, y), radius, *parts(net, net.thrusters))
    vel, spin = stokes(force, torque, radius)
    pos, heading = advance(pos, heading, vel, spin, dt)
    pos = confine(arena, pos, radius)
    eyes = eye_rates(arena, pos, heading, radius, *parts(net, net.eyes))
    return pos, heading, dynamics.step(net, y, eyes, dt)


def state_hash(
    pos: np.ndarray, heading: np.ndarray, radius: np.ndarray, y: np.ndarray, tick: int
) -> str:
    """Fingerprint of the whole state of a run, for determinism tests."""
    digest = hashlib.sha256()
    for array in (pos, heading, radius, y):
        digest.update(np.ascontiguousarray(array, dtype=np.float64).tobytes())
    digest.update(tick.to_bytes(8, "little"))
    return digest.hexdigest()
