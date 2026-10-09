"""The graph as a system of ODEs from the sensors to the actuators (D-017, D-202).

Every node has a rate y in [0, RATE_MAX], its state, and its kind's law (`laws.py`): an equation
for the state, dy/dt = f(x, y), from x, the rates on its wires in, and what it sends out,
o = g(y). A wire from j carries o_j / outdeg_j. Every part of the jam relaxes:

    TAU dy_i/dt = F_i(x) - y_i,   o_i = y_i,   F_i = min(RATE_MAX, gain_i * |sum of x|)

or |x_1 - x_2| for a Difference. Eyes and sources are given, not computed. The system is one set
of equations, so a loop is no special case: it is just a feedback that the state remembers, and
it can settle, hold a value, latch or oscillate.

The state is `y` of shape (N, n, C) for N agents, C = CHANNELS: each node's rate in red and in
blue, white being both (D-501), each channel following the same equations on its own. The caller
keeps it from tick to tick, and it belongs in the hash of the run. A white part reads `white(y)`,
the mean of the channels. A tick reads every output, then steps every state by its law,
each from the same y, so the order in which kinds are stepped cannot change a result. The tick
is at most the shortest `max_dt` of the network's laws: TAU for the jam's parts, whose step is
then y <- F(y); keep it well under (dt <= TAU / 2, see `laws.Relax`).

Inputs are gathered slot by slot, never with `@`, so a row does not depend on the batch it is
in (invariant 1). Pure numpy, no pygame.
"""

from __future__ import annotations

import math

import numpy as np

from nektoids.graph.laws import BLUE, CHANNELS, RATE_MAX, RED
from nektoids.graph.laws import TAU as TAU  # re-exported: the lag of every part of the jam
from nektoids.graph.network import Network

SOURCE_RATE = 1.0  # what a Source emits


def white(y: np.ndarray) -> np.ndarray:
    """What a white part reads of rates y (..., C): the mean of red and blue (D-501). White
    light gives both channels the same rate x, and (x + x) / 2 is x exactly."""
    return 0.5 * (y[..., RED] + y[..., BLUE])


def outputs(net: Network, y: np.ndarray) -> np.ndarray:
    """(N, n[, C]): what each node sends out, by its law from its state y (N, n[, C]); a sensor
    its rate. `y` itself when every law sends its state, as every part of the jam does."""
    out = y
    for law, nodes, _ in net.laws:
        if not law.sends_state:
            out = out.copy() if out is y else out
            out[:, nodes] = law.output(y[:, nodes])
    return out


def flux(net: Network, out: np.ndarray) -> np.ndarray:
    """(N, n + 1, C): the rate on each wire leaving each node, from the outputs `out` (N, n, C):
    its output shared among its wires; the extra column is 0, for unused slots, so that
    `flux[:, slots]` is the rate on each input slot."""
    wires = np.zeros((out.shape[0], net.n + 1, CHANNELS))
    wires[:, : net.n] = out / np.maximum(net.outdeg, 1)[:, None]
    return wires


def max_dt(net: Network) -> float:
    """The longest tick every law of the network is stable for [s]; no limit without one."""
    return min((law.max_dt for law, _, _ in net.laws), default=math.inf)


def given_rates(net: Network, eyes: np.ndarray, sources: np.ndarray | None = None) -> np.ndarray:
    """(N, n, C): the rates of the sensors, zero elsewhere.

    eyes: (N, n_eyes, C), or (N, n_eyes) for white, the same rate in every channel; clipped to
    [0, RATE_MAX]. sources: override of SOURCE_RATE, white, (n_sources,) or (N, n_sources); only
    the developer view passes it.
    """
    eyes = np.asarray(eyes, dtype=np.float64)
    if eyes.ndim == 2:
        eyes = np.repeat(eyes[:, :, None], CHANNELS, axis=2)
    if eyes.ndim != 3 or eyes.shape[1:] != (len(net.eyes), CHANNELS):
        raise ValueError(
            f"eyes must have shape (N, {len(net.eyes)}[, {CHANNELS}]), got {eyes.shape}"
        )
    agents = eyes.shape[0]
    given = np.zeros((agents, net.n, CHANNELS))
    given[:, net.eyes] = np.clip(eyes, 0.0, RATE_MAX)
    if sources is None:
        sources = np.full(len(net.sources), SOURCE_RATE)
    sources = np.broadcast_to(np.asarray(sources, dtype=np.float64), (agents, len(net.sources)))
    given[:, net.sources] = np.clip(sources, 0.0, RATE_MAX)[:, :, None]
    return given


def initial_state(net: Network, agents: int = 1) -> np.ndarray:
    """Everything at rest: every rate 0, shape (agents, n, C)."""
    return np.zeros((agents, net.n, CHANNELS))


def step(
    net: Network,
    y: np.ndarray,
    eyes: np.ndarray,
    dt: float,
    sources: np.ndarray | None = None,
) -> np.ndarray:
    """`step_given` with the jam's two senses given as they are: eyes (N, n_eyes[, C]), and the
    sources at SOURCE_RATE unless `sources` says otherwise (`given_rates`). The Board's demos,
    its probe and the tests drive the graph so; a run reads every sense (`sim.world`, D-203)."""
    return step_given(net, y, given_rates(net, eyes, sources), dt)


def step_given(net: Network, y: np.ndarray, given: np.ndarray, dt: float) -> np.ndarray:
    """The rates one tick later: a new array, `y` is not changed.

    y: (N, n, C) rates now. given: (N, n, C) the sensors' rates during this tick, in
    [0, RATE_MAX], in their rows; the other rows are not read. dt: the tick [s], with
    0 < dt <= max_dt(net) (ValueError otherwise).
    """
    limit = max_dt(net)
    if not 0.0 < dt <= limit:
        raise ValueError(f"dt must be in (0, {limit:g}] s, what the laws allow, got {dt:g}")
    if y.shape != given.shape:
        raise ValueError(f"y must have shape {given.shape}, got {y.shape}")
    sensor = net.given[:, None]  # (n, 1): over both channels
    seen = np.where(sensor, given, y)  # the sensors' rates of this tick drive this tick
    wires = flux(net, outputs(net, seen))
    new = np.where(sensor, given, 0.0)  # a sensor's rate is given, already in [0, RATE_MAX]
    for law, nodes, slots in net.laws:
        new[:, nodes] = law.step(wires[:, slots], seen[:, nodes], dt)
    return np.clip(new, 0.0, RATE_MAX, out=new)


def wire_flux(net: Network, y: np.ndarray) -> np.ndarray:
    """(N, E[, C]): rate on each wire, in `net.edges` order, from rates y (N, n[, C]): in each
    channel, or white."""
    sources = net.edges[:, 0]
    out, outdeg = outputs(net, y), net.outdeg[sources]
    return out[:, sources] / outdeg.reshape(outdeg.shape + (1,) * (out.ndim - 2))


def thrust_rates(net: Network, y: np.ndarray) -> np.ndarray:
    """(N, n_thrusters, C): the rate each thruster has; `net.facing` says where it pushes."""
    return outputs(net, y)[:, net.thrusters]
