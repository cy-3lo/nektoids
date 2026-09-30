"""The graph as a system of ODEs from the sensors to the actuators (D-017).

Every node has a rate y in [0, RATE_MAX] and relaxes towards what its inputs ask for:

    TAU dy_i/dt = F_i(y) - y_i,     F_i = min(RATE_MAX, gain_i * |sum of the wires into i|)

A wire from j carries y_j / outdeg_j; a Difference subtracts its second input. Eyes and sources
are given, not computed. The system is one set of equations, so a loop is no special case: it
is just a feedback that the state remembers, and it can settle, hold a value, latch or oscillate.

The state is `y` of shape (N, n) for N agents: the caller keeps it from tick to tick, and it
belongs in the hash of the run. One explicit Euler step of length dt is
y + (dt / TAU) (F(y) - y), a weighted mean of y and F(y) when dt <= TAU, so every rate stays in
[0, RATE_MAX] for any graph. With dt = TAU the step is y <- F(y): loops that settle in
continuous time then flicker every tick, so keep dt well under TAU (dt <= TAU / 2).

Inputs are gathered slot by slot, never with `@`, so a row does not depend on the batch it is
in (invariant 1). Pure numpy, no pygame.
"""

from __future__ import annotations

import numpy as np

from nektoids.graph.network import Network

RATE_MAX = 1.0  # what one wire can carry: the unit of every rate
SOURCE_RATE = 1.0  # what a Source emits
TAU = 1.0 / 60.0  # the lag of every node [s]


def _flux(net: Network, y: np.ndarray) -> np.ndarray:
    """(N, n + 1): rate on a wire leaving each node; the extra column is 0, for unused slots."""
    flux = np.zeros((y.shape[0], net.n + 1))
    flux[:, : net.n] = y / np.maximum(net.outdeg, 1)
    return flux


def targets(net: Network, y: np.ndarray) -> np.ndarray:
    """F(y), shape (N, n): what each node's inputs ask for now (zero for sensors)."""
    flux = _flux(net, y)
    total = 0.0
    for k in range(net.slots.shape[1]):
        total = total + net.signs[:, k] * flux[:, net.slots[:, k]]
    return np.minimum(RATE_MAX, net.gain * np.abs(total))


def given_rates(net: Network, eyes: np.ndarray, sources: np.ndarray | None = None) -> np.ndarray:
    """(N, n): the rates of the sensors, zero elsewhere.

    eyes: (N, n_eyes), clipped to [0, RATE_MAX]. sources: override of SOURCE_RATE, (n_sources,)
    or (N, n_sources); only the developer view passes it.
    """
    eyes = np.asarray(eyes, dtype=np.float64)
    if eyes.ndim != 2 or eyes.shape[1] != len(net.eyes):
        raise ValueError(f"eyes must have shape (N, {len(net.eyes)}), got {eyes.shape}")
    agents = eyes.shape[0]
    given = np.zeros((agents, net.n))
    given[:, net.eyes] = np.clip(eyes, 0.0, RATE_MAX)
    if sources is None:
        sources = np.full(len(net.sources), SOURCE_RATE)
    sources = np.broadcast_to(np.asarray(sources, dtype=np.float64), (agents, len(net.sources)))
    given[:, net.sources] = np.clip(sources, 0.0, RATE_MAX)
    return given


def initial_state(net: Network, agents: int = 1) -> np.ndarray:
    """Everything at rest: every rate 0, shape (agents, n)."""
    return np.zeros((agents, net.n))


def step(
    net: Network,
    y: np.ndarray,
    eyes: np.ndarray,
    dt: float,
    sources: np.ndarray | None = None,
) -> np.ndarray:
    """The rates one tick later: a new array, `y` is not changed.

    y: (N, n) rates now. eyes: (N, n_eyes) sensor rates during this tick. dt: the tick [s],
    with 0 < dt <= TAU (ValueError otherwise).
    """
    h = dt / TAU
    if not 0.0 < h <= 1.0:
        raise ValueError(f"dt / TAU must be in (0, 1], got {h:g}")
    given = given_rates(net, eyes, sources)
    if y.shape != given.shape:
        raise ValueError(f"y must have shape {given.shape}, got {y.shape}")
    seen = np.where(net.gain > 0, y, given)  # the sensors' rates of this tick drive this tick
    moved = np.clip(y + h * (targets(net, seen) - y), 0.0, RATE_MAX)
    return np.where(net.gain > 0, moved, given)


def wire_flux(net: Network, y: np.ndarray) -> np.ndarray:
    """(N, E): rate on each wire, in `net.edges` order."""
    sources = net.edges[:, 0]
    return y[:, sources] / net.outdeg[sources]


def thrust_rates(net: Network, y: np.ndarray) -> np.ndarray:
    """(N, n_thrusters): the rate each thruster has; `net.facing` says where it pushes."""
    return y[:, net.thrusters]
