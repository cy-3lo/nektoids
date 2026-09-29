"""Simulation state and integrator.

PLACEHOLDER physics: point masses with linear drag, so the pipeline and the determinism test
have something real to run. Heading, the two thrusters, body size and the opacity sensors are
Day-1 work (docs/brief.md, section 3). Keep the shape: numpy arrays, fixed dt, no Python loop
over agents.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np

DRAG_RATE = 0.5  # linear drag coefficient per unit mass [1/s]
INITIAL_SPEED = 120.0  # [px/s]


@dataclass
class World:
    pos: np.ndarray  # (N, 2) positions [px]
    vel: np.ndarray  # (N, 2) velocities [px/s]
    width: float  # [px]
    height: float  # [px]
    tick: int = 0  # integer step counter: no accumulated float time


def make_world(seed: int, n_agents: int, width: float, height: float) -> World:
    """Deterministic initial state: agents near the centre, random headings."""
    rng = np.random.default_rng(seed)
    low = (0.4 * width, 0.4 * height)
    high = (0.6 * width, 0.6 * height)
    pos = rng.uniform(low, high, size=(n_agents, 2))
    angle = rng.uniform(0.0, 2.0 * np.pi, size=n_agents)
    vel = INITIAL_SPEED * np.column_stack((np.cos(angle), np.sin(angle)))
    return World(pos=pos, vel=vel, width=width, height=height)


def step(world: World, force: np.ndarray, dt: float) -> None:
    """Advance one fixed step, in place.

    force: (N, 2) applied force per unit mass [px/s^2].
    Semi-implicit Euler: update velocity first, then position with the new velocity.
    """
    world.vel += dt * (force - DRAG_RATE * world.vel)
    world.pos += dt * world.vel
    world.tick += 1


def state_hash(world: World) -> str:
    """Fingerprint of the full state, for determinism tests."""
    digest = hashlib.sha256()
    digest.update(world.pos.tobytes())
    digest.update(world.vel.tobytes())
    digest.update(world.tick.to_bytes(8, "little"))
    return digest.hexdigest()
