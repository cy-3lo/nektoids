"""Rates through the graph (D-016).

Every node has an output rate y in [0, RATE_MAX] and no dynamics: rates are fractions of what
a wire can carry. A wire from j carries
y_j / outdeg_j. A node adds the rates of its wires (a Difference subtracts its second input) and
applies its gain and the cap: y = min(RATE_MAX, gain * |sum|). Eyes and sources are given.

A DAG is solved in one pass, in topological order (ties by node index). A loop is solved by
iteration when it is provably contractive and refused otherwise: a loop needs a state, and tanks
will be the only states. All rates are (N, n): N agents at once, rows independent. Inputs are
gathered slot by slot, never with `@`, so a row does not depend on the batch it is in.

Pure numpy, no pygame.
"""

from __future__ import annotations

import numpy as np

from nektoids.graph.network import Network, contraction_factor, topological_order

RATE_MAX = 1.0  # what one wire can carry: the unit of every rate
SOURCE_RATE = 1.0  # what a Source emits
TOLERANCE = 1e-12  # residual at which a loop counts as solved
MAX_SWEEPS = 10_000


class AlgebraicLoopError(ValueError):
    """A loop of operators with no provably unique solution."""


def _flux(net: Network, y: np.ndarray) -> np.ndarray:
    """(N, n + 1): rate on a wire leaving each node; the extra column is 0, for unused slots."""
    flux = np.zeros((y.shape[0], net.n + 1))
    flux[:, : net.n] = y / np.maximum(net.outdeg, 1)
    return flux


def _rates(net: Network, flux: np.ndarray, rows: np.ndarray) -> np.ndarray:
    """(N, len(rows)): the rate nodes `rows` take from the flux on their input wires."""
    total = 0.0
    for k in range(net.slots.shape[1]):
        total = total + net.signs[rows, k] * flux[:, net.slots[rows, k]]
    return np.minimum(RATE_MAX, net.gain[rows] * np.abs(total))


def _given(net: Network, eyes: np.ndarray, sources: np.ndarray | None) -> np.ndarray:
    """(N, n): the rates of the sensors, zero elsewhere."""
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


def sweep(net: Network, y: np.ndarray, given: np.ndarray) -> np.ndarray:
    """One application of F: every node's rate recomputed from `y`, sensors kept as given."""
    computed = _rates(net, _flux(net, y), np.arange(net.n))
    return np.where(net.gain > 0, computed, given)


def evaluate(net: Network, eyes: np.ndarray, sources: np.ndarray | None = None) -> np.ndarray:
    """Rate of every node, shape (N, n).

    eyes: (N, n_eyes) sensor rates, clipped to [0, RATE_MAX]. sources: override of SOURCE_RATE,
    (n_sources,) or (N, n_sources); only the developer view passes it. Raises AlgebraicLoopError
    for a loop that is not provably contractive.
    """
    given = _given(net, eyes, sources)
    order = topological_order(net)
    if order is not None:
        return _solve_dag(net, given, order)
    if contraction_factor(net) is None:
        raise AlgebraicLoopError("a loop of operators has loop gain 1 or more, or cannot be told")
    return _solve_loop(net, given)


def _solve_dag(net: Network, given: np.ndarray, order: tuple[int, ...]) -> np.ndarray:
    y = given.copy()
    divisor = np.maximum(net.outdeg, 1)
    flux = np.zeros((y.shape[0], net.n + 1))
    for i in order:
        if net.gain[i] > 0:
            y[:, i] = _rates(net, flux, np.array([i]))[:, 0]
        flux[:, i] = y[:, i] / divisor[i]
    return y


def _solve_loop(net: Network, given: np.ndarray) -> np.ndarray:
    y = given.copy()
    for _ in range(MAX_SWEEPS):
        nxt = sweep(net, y, given)
        settled = np.max(np.abs(nxt - y), initial=0.0) <= TOLERANCE
        y = nxt
        if settled:
            return y
    raise AlgebraicLoopError(
        f"a loop did not settle in {MAX_SWEEPS} sweeps: its gain is too close to 1"
    )


def wire_flux(net: Network, y: np.ndarray) -> np.ndarray:
    """(N, E): rate on each wire, in `net.edges` order."""
    sources = net.edges[:, 0]
    return y[:, sources] / net.outdeg[sources]


def thrust_rates(net: Network, y: np.ndarray) -> np.ndarray:
    """(N, n_thrusters): the rate each thruster receives; `net.facing` says where it pushes."""
    return y[:, net.thrusters]
