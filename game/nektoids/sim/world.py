"""One tick of the swimmers: move, touch, see, think (D-022).

The state of N swimmers is four arrays that the caller keeps (the arena view, a test): pos (N, 2)
[u], heading (N,) [rad], radius (N,) [u], and y (N, n, C), the rates of their nodes in each
channel, white and red (D-017, D-502); and
the plane they swim in, each obstacle where its spring has it (`Arena.moved`, D-424). A tick of
dt [s]:

1. move: with what the actuators do now, the thrusters' push, against the Stokes drag of a
   sphere (`push`, `motion`);
2. touch: back outside the lights and obstacles, an obstacle giving a little (`contact`); the
   plane is open (D-028);
3. sense: each sensor reads where the bodies now are, the eyes the light (`readings`, `optics`);
4. think: the nodes follow, one step of their laws (`graph.dynamics`).

A sensor's rate comes from its kind's sense, an actuator's effect from its kind's action, each
named in the table of kinds and mapped here to its function, `SENSES` and `ACTIONS` (D-203). So
after a tick, as after a restart or a drag, y's sensor rows are what the sensors read where
the bodies are. Each part has its own channel, by its paint (D-502): an eye reads the light of its
channel, every light being white so far, a Source sends in its channel, an actuator acts on its
channel alone. Nothing is changed in place. Pure numpy, no pygame.
"""

from __future__ import annotations

import hashlib

import numpy as np

from nektoids.graph import dynamics
from nektoids.graph.dynamics import CHANNELS, RATE_MAX, WHITE_LIGHT, masks
from nektoids.graph.network import Network
from nektoids.sim.arena import Arena
from nektoids.sim.contact import collide
from nektoids.sim.motion import advance, stokes, thrust
from nektoids.sim.optics import eye_rates


def parts(net: Network, indices: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Mounts (k, 2) in body radii and facings (k,) hex directions of the nodes `indices`, such
    as `net.eyes` or `net.thrusters` (D-018); a part with no direction, a Source, faces E."""
    facing = np.array([net.facing[i] or 0 for i in indices], dtype=np.int64)
    return net.mount[indices], facing


def steady(
    arena: Arena,
    pos: np.ndarray,
    heading: np.ndarray,
    radius: np.ndarray,
    mount: np.ndarray,
    facing: np.ndarray,
) -> np.ndarray:
    """A Source's rate (N, k): SOURCE_RATE, whatever the world. It senses nothing."""
    return np.full((pos.shape[0], len(mount)), dynamics.SOURCE_RATE)


# A sense reads the world: (arena, pos, heading, radius, mount, facing) -> rates (N, k) of the k
# sensors at `mount` (k, 2) facing `facing` (k,). An action acts on the body: (rates (N, k),
# radius, mount, facing) -> force (N, 2) in the body's frame [f] and torque (N,) [f u].
SENSES = {"light": eye_rates, "steady": steady}
ACTIONS = {"push": thrust}


def readings(
    arena: Arena, net: Network, pos: np.ndarray, heading: np.ndarray, radius: np.ndarray
) -> np.ndarray:
    """(N, n, C): each sensor's rate where the bodies are, by its kind's sense, in
    [0, RATE_MAX], in its own channel by its paint (D-502): an eye's the light's, white so far,
    so that a red eye reads nothing; 0 in the other rows."""
    given = np.zeros((pos.shape[0], net.n, CHANNELS))
    for kind, nodes in net.senses:
        rates = SENSES[kind.spec.sense](arena, pos, heading, radius, *parts(net, nodes))
        own = masks(net.hues[i] for i in nodes)
        seen = own * WHITE_LIGHT if kind.spec.sense == "light" else own
        given[:, nodes] = np.clip(rates, 0.0, RATE_MAX)[:, :, None] * seen
    return given


def push(net: Network, y: np.ndarray, radius: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The force (N, 2) in the body's frame [f] and the torque (N,) [f u] that the actuators of
    rates y (N, n, C) exert, each kind's by its action, from its nodes' outputs in their own
    channels, `dynamics.painted` (D-502)."""
    out = dynamics.outputs(net, y)
    pushes = [
        ACTIONS[kind.spec.action](dynamics.painted(net, out, nodes), radius, *parts(net, nodes))
        for kind, nodes in net.actions
    ]
    if not pushes:
        return np.zeros((y.shape[0], 2)), np.zeros(y.shape[0])
    force, torque = pushes[0]
    for more, turn in pushes[1:]:  # one action alone is taken as it is, never added to a zero
        force, torque = force + more, torque + turn
    return force, torque


def step(
    arena: Arena,
    net: Network,
    pos: np.ndarray,
    heading: np.ndarray,
    radius: np.ndarray,
    y: np.ndarray,
    dt: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, Arena]:
    """(pos, heading, y, arena) one tick later, as new arrays and a new plane, its obstacles
    where their springs have them; the arguments are not changed.

    pos (N, 2) [u], heading (N,) [rad], radius (N,) [u], y (N, n, C) the nodes' rates; dt [s], with
    0 < dt <= the laws' limit (`graph.dynamics.step_given` raises ValueError otherwise).
    """
    vel, spin = stokes(*push(net, y, radius), radius)
    pos, heading = advance(pos, heading, vel, spin, dt)
    rest = arena.offsets if arena.offsets is not None else arena.at_rest
    pos, offsets = collide(arena, rest, pos, radius, dt)
    arena = arena.moved(offsets)
    seen = readings(arena, net, pos, heading, radius)
    return pos, heading, dynamics.step_given(net, y, seen, dt), arena


def state_hash(
    pos: np.ndarray,
    heading: np.ndarray,
    radius: np.ndarray,
    y: np.ndarray,
    tick: int,
    offsets: np.ndarray | None = None,
) -> str:
    """Fingerprint of the whole state of a run, for determinism tests: the obstacles' places
    too, when they have moved (D-424)."""
    digest = hashlib.sha256()
    moved = () if offsets is None else (offsets,)
    for array in (pos, heading, radius, y, *moved):
        digest.update(np.ascontiguousarray(array, dtype=np.float64).tobytes())
    digest.update(tick.to_bytes(8, "little"))
    return digest.hexdigest()
