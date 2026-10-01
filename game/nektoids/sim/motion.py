"""How thrust moves a body: Stokes drag on a sphere, no inertia (D-022).

A thruster k at rate y_k pushes with y_k THRUST along its facing f_k, at R m_k from the centre of
a body of radius R (D-018). In the body's frame

    F = THRUST sum_k y_k f_k,     T = THRUST R sum_k y_k (m_k x f_k)

and the body moves at once with the velocity and spin at which the drag of a sphere balances them:

    V = F / (6 pi mu R),     Omega = T / (8 pi mu R^3).

A sphere, because a disc in 2D has no Stokes drag. One mu sets one scale and the sphere sets the
other: one thruster of lever l = m x f turns its body on a circle of radius (4/3) R / l.

Thrusters are added one by one in a fixed order, never with `@`, so a row does not depend on the
batch it is in (invariant 1). Lengths in u, the base body radius; forces in f, the push of one
thruster at RATE_MAX; x right, y up, angles counter-clockwise. Pure numpy.
"""

from __future__ import annotations

import numpy as np

from nektoids.sim.arena import BASE_RADIUS
from nektoids.sim.optics import FACING_STEP

THRUST = 1.0  # [f] what a thruster at RATE_MAX pushes with: the unit of force
SPEED = 3.0  # [u/s] how fast one thruster at RATE_MAX pushing through its centre moves a base body
VISCOSITY = THRUST / (6.0 * np.pi * BASE_RADIUS * SPEED)  # [f s/u^2] mu, chosen to give SPEED


def thrust(
    rates: np.ndarray, radius: np.ndarray, mount: np.ndarray, facing: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """The thrusters' total force (N, 2) in the body's frame [f] and torque (N,) [f u].

    rates (N, k) in [0, RATE_MAX]; radius (N,) [u]; mount (k, 2) in body radii and facing (k,)
    hex directions of the k thrusters (`Network.mount`, `Network.facing`, D-018).
    """
    rates = np.asarray(rates, dtype=np.float64)
    mount = np.asarray(mount, dtype=np.float64).reshape(-1, 2)
    angle = FACING_STEP * np.asarray(facing, dtype=np.float64)
    fx, fy = np.cos(angle), np.sin(angle)
    lever = mount[:, 0] * fy - mount[:, 1] * fx  # m x f [body radii]
    n = rates.shape[0]
    force_x, force_y, moment = np.zeros(n), np.zeros(n), np.zeros(n)
    for k in range(rates.shape[1]):
        push = THRUST * rates[:, k]
        force_x = force_x + push * fx[k]
        force_y = force_y + push * fy[k]
        moment = moment + push * lever[k]
    return np.stack((force_x, force_y), axis=1), np.asarray(radius, dtype=np.float64) * moment


def stokes(
    force: np.ndarray, torque: np.ndarray, radius: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Velocity (N, 2) [u/s] and spin (N,) [rad/s] at which the drag of a sphere of radius (N,)
    [u] balances force (N, 2) [f] and torque (N,) [f u]. The velocity is in the force's frame."""
    radius = np.asarray(radius, dtype=np.float64)
    vel = force / (6.0 * np.pi * VISCOSITY * radius)[:, None]
    spin = torque / (8.0 * np.pi * VISCOSITY * radius**3)
    return vel, spin


def advance(
    pos: np.ndarray, heading: np.ndarray, vel: np.ndarray, spin: np.ndarray, dt: float
) -> tuple[np.ndarray, np.ndarray]:
    """Position (N, 2) [u] and heading (N,) [rad] dt [s] later, as new arrays.

    vel (N, 2) [u/s] is in the body's frame, turned by the heading at the start of the step;
    spin (N,) [rad/s]. Explicit Euler: under a constant thrust the path is a closed regular
    polygon of side V dt and turn Omega dt, so it never spirals.
    """
    cos, sin = np.cos(heading), np.sin(heading)
    vx = cos * vel[:, 0] - sin * vel[:, 1]
    vy = sin * vel[:, 0] + cos * vel[:, 1]
    return pos + dt * np.stack((vx, vy), axis=1), heading + dt * spin
