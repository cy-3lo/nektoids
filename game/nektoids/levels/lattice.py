"""The lattice a made level's values sit on (D-301): positions every 0.5 u, headings every 15°,
and each setting within its range, by its step. A lattice keeps a level's text short and its
layout legible; invariant 4 binds only the player's graph. A shipped level's values may lie off
it: they stay so until the Maker changes them. Pure numbers.
"""

from __future__ import annotations

from dataclasses import dataclass

POSITION = 0.5  # a position's step, each way [u]
HEADING = 15.0  # a heading's step [degrees]


def snap(value: float, step: float) -> float:
    """The multiple of `step` nearest `value`, never -0.0 (it would be written so)."""
    return round(value / step) * step + 0.0


def snapped(at: tuple[float, float]) -> tuple[float, float]:
    """The lattice point nearest `at` [u]."""
    return (snap(at[0], POSITION), snap(at[1], POSITION))


@dataclass(frozen=True)
class Range:
    """What a setting may be: `lo` to `hi`, by `step`, in `unit`."""

    lo: float
    hi: float
    step: float
    unit: str = ""

    def clamp(self, value: float) -> float:
        """`value` on the lattice and within the range."""
        return min(self.hi, max(self.lo, snap(value, self.step)))

    def stepped(self, value: float, steps: int) -> float:
        """`value` moved by `steps` steps, from the lattice point nearest it, within the range."""
        return self.clamp(snap(value, self.step) + steps * self.step)
