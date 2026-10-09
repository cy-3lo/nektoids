"""Beads on the wires: the view of a rate, never read by the model (graph.md).

A wire that carries f beads/s shows beads `speed / f` apart, so the spacing shows the rate at
this moment along the whole wire (brief, legibility: spacing = rate). The only memory is one
phase per wire, the fraction of a bead released since the last whole one: phase += f dt, mod 1.
Bead k sits at (phase + k) * speed / f from the source. A bead leaves the source when the phase
wraps, and while f is steady the beads move at `speed`; when f changes the spacing follows it at
once and the phase keeps the pattern continuous, so nothing jumps. Positions are arc lengths in
hex sizes, so they do not depend on zoom. No randomness. Pure numbers, no pygame.

When the flux changes fast the lattice stretches about the source, and beads far from it move
many times `speed` (and backwards when the flux rises): the pattern is continuous, but it
whips. The `belt` style avoids it: fixed spacing, and the speed of the beads shows the rate.
"""

from __future__ import annotations

from collections.abc import Sequence

BEAD_SPEED = 2.1  # hex sizes per second (D-432): about 1.2 cells a second
BEAD_RATE_AT_FULL = 6.0  # beads a second on a wire at RATE_MAX: 0.35 hex sizes apart (D-416, D-432)


class Beads:
    def __init__(self, lengths: Sequence[float], speed: float = BEAD_SPEED):
        """lengths: length of each wire [hex sizes]."""
        self.lengths = list(lengths)
        self.speed = speed
        self.phase: list[float] = []  # fraction of a bead released on each wire, in [0, 1)
        self.reset()

    def reset(self) -> None:
        self.phase = [0.0] * len(self.lengths)

    def step(self, fluxes: Sequence[float], dt: float) -> None:
        """Advance every phase by `dt` seconds of the fluxes [beads/s]."""
        self.phase = [(p + f * dt) % 1.0 for p, f in zip(self.phase, fluxes, strict=True)]

    def positions(self, wire: int, flux: float, belt: bool = False) -> list[float]:
        """Arc length of each bead on `wire` carrying `flux` beads/s now, nearest the source first.

        Spacing shows the rate: `speed / flux` apart, the whole lattice stretching at once when
        the flux changes. With `belt` the spacing is fixed, `speed / BEAD_RATE_AT_FULL`, and it is
        the speed of the beads that shows the rate, `speed * flux / BEAD_RATE_AT_FULL`.
        """
        if flux <= 0.0:
            return []
        gap = self.speed / (BEAD_RATE_AT_FULL if belt else flux)
        found, k = [], 0
        while (x := (self.phase[wire] + k) * gap) < self.lengths[wire]:
            found.append(x)
            k += 1
        return found


class Travelling(Beads):
    """Beads that, once out, keep going at `speed` whatever the rate does after (D-082): the
    spacing along a wire is the rate when each bead left, so a change of rate runs down the wire
    as a front, and no bead ever goes backwards. A part's entry runs them; on a steady wire they
    sit where `Beads` would put them."""

    def __init__(self, lengths: Sequence[float], speed: float = BEAD_SPEED):
        super().__init__(lengths, speed)
        self.out: list[list[float]] = [[] for _ in self.lengths]  # each wire's beads, in order

    def fill(self, fluxes: Sequence[float]) -> None:
        """The wires full, as if the fluxes [beads/s] had been steady all along."""
        self.out = [Beads.positions(self, k, f) for k, f in enumerate(fluxes)]

    def step(self, fluxes: Sequence[float], dt: float) -> None:
        """The beads out move on by `speed` dt; a bead leaves each time a phase wraps, as far
        along as it has gone since."""
        for k, f in enumerate(fluxes):
            moved = [x + self.speed * dt for x in self.out[k]]
            phase, left = self.phase[k] + f * dt, []
            while phase >= 1.0:
                phase -= 1.0
                left.append(self.speed * phase / f)
            self.phase[k] = phase
            self.out[k] = [x for x in (*reversed(left), *moved) if x < self.lengths[k]]

    def positions(self, wire: int, flux: float, belt: bool = False) -> list[float]:
        """Where the beads on `wire` are, nearest the source first, whatever the flux now."""
        return self.out[wire]
