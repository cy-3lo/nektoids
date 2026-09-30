"""Beads on the wires: the view of a rate, never read by the model (graph.md).

A wire that carries f beads/s sends out one bead every 1/f seconds, and beads travel at a fixed
speed, so their spacing is speed / f: density shows magnitude, spacing shows rate (brief,
legibility).
Positions are arc lengths in hex sizes, so they do not depend on zoom. No randomness: the same
fluxes give the same beads. Pure numbers, no pygame.

The model couples wires instantly; a bead takes length / speed to arrive. The node meters show the
rate at the node, the beads show how it got there (D-016).
"""

from __future__ import annotations

from collections.abc import Sequence

BEAD_SPEED = 7.0  # hex sizes per second: about 4 cells per second
BEAD_RATE_AT_FULL = 8.0  # beads a second on a wire that carries RATE_MAX: the view's scale


class Beads:
    def __init__(self, lengths: Sequence[float], speed: float = BEAD_SPEED):
        """lengths: length of each wire [hex sizes]."""
        self.lengths = list(lengths)
        self.speed = speed
        self.phase: list[float] = []  # beads owed on each wire, in [0, 1)
        self.spawned: list[int] = []  # beads sent onto each wire so far
        self.positions: list[list[float]] = []  # arc length of each bead, per wire
        self.reset()

    def reset(self) -> None:
        self.phase = [0.0] * len(self.lengths)
        self.spawned = [0] * len(self.lengths)
        self.positions = [[] for _ in self.lengths]

    def step(self, fluxes: Sequence[float], dt: float) -> None:
        """Advance every bead by `dt` seconds and send out the ones the fluxes owe [beads/s]."""
        for w, (flux, length) in enumerate(zip(fluxes, self.lengths, strict=True)):
            moved = [s + self.speed * dt for s in self.positions[w]]
            self.phase[w] += flux * dt
            while self.phase[w] >= 1.0:
                self.phase[w] -= 1.0
                # It left the source this long ago, part-way through the step.
                moved.append(self.speed * self.phase[w] / flux)
                self.spawned[w] += 1
            self.positions[w] = [s for s in moved if s < length]
