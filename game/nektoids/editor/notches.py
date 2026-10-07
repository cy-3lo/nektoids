"""The mouse wheel turning a part (D-402, D-405): a wheel's notch is one turn of 60°; a
trackpad's small scrolls add up until they make a notch, then rest a moment, so that one flick
of two fingers does not spin a part round. Pure Python, no pygame.
"""

from __future__ import annotations

from dataclasses import dataclass

NOTCH = 1.0  # a mouse wheel's notch, as pygame reports it: what the small scrolls add up to
REST = 9  # after a turn made of small scrolls, they are let go this long: 0.15 s [frames]
RUN = 30  # turns this close together, on the same parts, are one step for undo: 0.5 s [frames]


@dataclass
class Notches:
    total: float = 0.0  # the small scrolls added up since the last turn
    rest: int = 0  # frames left before small scrolls count again

    def feed(self, delta: float) -> int:
        """The turns one scroll makes, up positive: a wheel's whole notches at once, each a
        turn; small scrolls added up, one turn when they make a notch, then a rest."""
        if delta != 0 and delta == int(delta):  # a mouse wheel, notch by notch
            self.total = 0.0
            return int(delta)
        if self.rest > 0:
            return 0
        self.total += delta
        if abs(self.total) < NOTCH:
            return 0
        step = 1 if self.total > 0 else -1
        self.total, self.rest = 0.0, REST
        return step

    def tick(self) -> None:
        """Once a frame."""
        if self.rest > 0:
            self.rest -= 1
