"""What a part does to the rates through it: its law (D-202).

Every node of the graph has a state y and a law. The law is the state's equation,
dy/dt = f(x, y), with x the rates on the node's wires in, slot by slot in the order of
`Network.slots`, and what the node sends out, o = g(y), shared among its wires out. The output
depends on the state alone, so a tick reads every output, then steps every state, and never
solves for one: a loop needs no special case (D-017). Each law owns its explicit step, so that
its arithmetic is fixed (invariant 1), and says the longest tick that step is stable for.

Every part of the jam relaxes: tau dy/dt = F(x) - y, o = y, with F one of the targets below,
capped at RATE_MAX, and tau = TAU, a lag of 17 ms. A tank is the same law with tau = 4 s
(ideas.md, stage 2); a part whose output is not its state, a bucket with a hole, takes a law of
its own. Pure numpy, no pygame.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

RATE_MAX = 1.0  # what one wire can carry: the unit of every rate
TAU = 1.0 / 60.0  # the lag of every part of the jam [s]


class Target(Protocol):
    """F, what a relaxing node goes to."""

    slope: float  # the most F moves per unit of one input: |dF/dx_k| <= slope

    def __call__(self, x: np.ndarray) -> np.ndarray:
        """F (N, m) from the rates in, x (N, m, K); unused slots carry 0."""
        ...

    def text(self, terms: list[str]) -> str:
        """F in ASCII, its inputs named by `terms`, at least one."""
        ...


class Law(Protocol):
    max_dt: float  # the longest tick its step is stable for [s]
    sends_state: bool  # what it sends out is its state, o = y: `output` need not be called
    slope: float  # how far its state follows one input, per unit: the weight of the loop bound

    def step(self, x: np.ndarray, y: np.ndarray, dt: float) -> np.ndarray:
        """The state (N, m) a tick of `dt` [s] later, from the rates in x (N, m, K) and the
        state now y (N, m); neither is changed. The caller keeps it in [0, RATE_MAX]."""
        ...

    def output(self, y: np.ndarray) -> np.ndarray:
        """What the node sends out (N, m) from its state."""
        ...

    def equation(self, name: str, terms: list[str]) -> str:
        """The node's equation in ASCII, its state named `name`, its inputs `terms`."""
        ...


def inflow(x: np.ndarray) -> np.ndarray:
    """(N, m): the sum of the rates in, slot by slot in order, never by a reduction whose order
    numpy picks, so a node's sum does not depend on the batch it is in (invariant 1). A node
    has one slot at least (`Network.slots`)."""
    total = 0.0
    for k in range(x.shape[2]):
        total = total + x[:, :, k]
    return total


@dataclass(frozen=True)
class Scaled:
    """F = gain * (the sum of the rates in): Double 2, Halve 1/2, Sum and Thruster 1."""

    gain: float

    @property
    def slope(self) -> float:
        return self.gain

    def __call__(self, x: np.ndarray) -> np.ndarray:
        return self.gain * np.abs(inflow(x))  # abs only clears the sign of a zero

    def text(self, terms: list[str]) -> str:
        inner = " + ".join(terms)
        if self.gain == 1.0:
            return inner
        if self.gain == 0.5:
            return f"{wrap(inner)}/2"
        return f"{self.gain:g}*{wrap(inner)}"


@dataclass(frozen=True)
class Difference:
    """F = |a - b|, the first input less the second, either way round; one input passes."""

    slope: float = 1.0

    def __call__(self, x: np.ndarray) -> np.ndarray:
        if x.shape[2] < 2:
            return np.abs(x[:, :, 0])
        return np.abs(x[:, :, 0] - x[:, :, 1])

    def text(self, terms: list[str]) -> str:
        return f"|{terms[0]} - {terms[1]}|" if len(terms) == 2 else " + ".join(terms)


@dataclass(frozen=True)
class Relax:
    """tau dy/dt = F(x) - y, o = y: the node follows F with a lag tau. One explicit Euler step
    is y + (dt / tau) (F - y), a weighted mean of y and F while dt <= tau. With dt = tau it is
    y <- F: a loop that settles in continuous time flickers then, so keep dt <= tau / 2."""

    target: Target
    tau: float = TAU  # [s]
    sends_state = True  # o = y

    @property
    def max_dt(self) -> float:
        return self.tau

    @property
    def slope(self) -> float:
        return self.target.slope

    def step(self, x: np.ndarray, y: np.ndarray, dt: float) -> np.ndarray:
        return y + (dt / self.tau) * (np.minimum(RATE_MAX, self.target(x)) - y)

    def output(self, y: np.ndarray) -> np.ndarray:
        return y

    def equation(self, name: str, terms: list[str]) -> str:
        lag = "tau" if self.tau == TAU else f"{self.tau:g} s *"
        aim = f"min(R, {self.target.text(terms)})" if terms else "0"
        return f"{lag} d{name}/dt = -{name} + {aim}"


def wrap(text: str) -> str:
    """Parentheses around a sum or difference, unless it is already inside a call or bars."""
    depth, inside_bars = 0, False
    for k, char in enumerate(text):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "|":
            inside_bars = not inside_bars
        elif depth == 0 and not inside_bars and text[k : k + 3] in (" + ", " - "):
            return f"({text})"
    return text
