"""The graph as a system of ODEs from the sensors to the actuators (D-017, D-202).

Every node has a rate y in [0, RATE_MAX], its state, and its kind's law (`laws.py`): an equation
for the state, dy/dt = f(x, y), from x, the rates on its wires in, and what it sends out,
o = g(y). A wire from j carries o_j / outdeg_j. Every part of the jam relaxes:

    TAU dy_i/dt = F_i(x) - y_i,   o_i = y_i,   F_i = min(RATE_MAX, gain_i * |sum of x|)

or |x_1 - x_2| for a Difference. Eyes and sources are given, not computed. The system is one set
of equations, so a loop is no special case: it is just a feedback that the state remembers, and
it can settle, hold a value, latch or oscillate.

The state is `y` of shape (N, n) for N agents: the caller keeps it from tick to tick, and it
belongs in the hash of the run. A tick reads every output, then steps every state by its law,
each from the same y, so the order in which kinds are stepped cannot change a result. The tick
is at most the shortest `max_dt` of the network's laws: TAU for the jam's parts, whose step is
then y <- F(y); keep it well under (dt <= TAU / 2, see `laws.Relax`).

Inputs are gathered slot by slot, never with `@`, so a row does not depend on the batch it is
in (invariant 1). Pure numpy, no pygame.
"""

from __future__ import annotations

import math

import numpy as np

from nektoids.graph.laws import RATE_MAX
from nektoids.graph.laws import TAU as TAU  # re-exported: the lag of every part of the jam
from nektoids.graph.network import Network

SOURCE_RATE = 1.0  # what a Source emits


def outputs(net: Network, y: np.ndarray) -> np.ndarray:
    """(N, n): what each node sends out, by its law from its state; a sensor its rate. `y`
    itself when every law sends its state, as every part of the jam does."""
    out = y
    for law, nodes, _ in net.laws:
        if not law.sends_state:
            out = out.copy() if out is y else out
            out[:, nodes] = law.output(y[:, nodes])
    return out


def flux(net: Network, out: np.ndarray) -> np.ndarray:
    """(N, n + 1): the rate on each wire leaving each node, from the outputs `out` (N, n): its
    output shared among its wires; the extra column is 0, for unused slots, so that
    `flux[:, slots]` is the rate on each input slot."""
    wires = np.zeros((out.shape[0], net.n + 1))
    wires[:, : net.n] = out / np.maximum(net.outdeg, 1)
    return wires


def max_dt(net: Network) -> float:
    """The longest tick every law of the network is stable for [s]; no limit without one."""
    return min((law.max_dt for law, _, _ in net.laws), default=math.inf)


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
    with 0 < dt <= max_dt(net) (ValueError otherwise).
    """
    limit = max_dt(net)
    if not 0.0 < dt <= limit:
        raise ValueError(f"dt must be in (0, {limit:g}] s, what the laws allow, got {dt:g}")
    given = given_rates(net, eyes, sources)
    if y.shape != given.shape:
        raise ValueError(f"y must have shape {given.shape}, got {y.shape}")
    seen = np.where(net.given, given, y)  # the sensors' rates of this tick drive this tick
    wires = flux(net, outputs(net, seen))
    new = given.copy()  # a sensor's rate is given, already in [0, RATE_MAX]
    for law, nodes, slots in net.laws:
        new[:, nodes] = law.step(wires[:, slots], seen[:, nodes], dt)
    return np.clip(new, 0.0, RATE_MAX, out=new)


def wire_flux(net: Network, y: np.ndarray) -> np.ndarray:
    """(N, E): rate on each wire, in `net.edges` order."""
    sources = net.edges[:, 0]
    return outputs(net, y)[:, sources] / net.outdeg[sources]


def thrust_rates(net: Network, y: np.ndarray) -> np.ndarray:
    """(N, n_thrusters): the rate each thruster has; `net.facing` says where it pushes."""
    return outputs(net, y)[:, net.thrusters]
