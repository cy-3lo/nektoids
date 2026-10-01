"""Every tick of a run, as it was, so that the timeline can put the run anywhere in it (D-033).

A run is deterministic (invariant 1): from the same start, the same board gives the same ticks.
So the recording is the run, whatever the order it was watched in: going back restores a tick
kept, going ahead of the furthest tick run so far (the frontier) runs on from there, and both
give the run one would have seen playing it straight through. Moving the swimmer by hand, a
developer's tool, changes the run from that tick on: what was kept after it no longer holds.
Pure Python, no pygame; a frame of the run is whatever the scene keeps (`Snapshot`).
"""

from __future__ import annotations

from typing import Generic, TypeVar

Frame = TypeVar("Frame")


class Recording(Generic[Frame]):
    def __init__(self, start: Frame) -> None:
        self._frames: list[Frame] = [start]  # the frame of each tick, from 0

    @property
    def frontier(self) -> int:
        """The furthest tick run so far."""
        return len(self._frames) - 1

    def at(self, tick: int) -> Frame:
        """The run at `tick`, at most the frontier."""
        if not 0 <= tick <= self.frontier:
            raise IndexError(f"tick {tick} is not recorded (0 to {self.frontier})")
        return self._frames[tick]

    def add(self, frame: Frame) -> None:
        """The run one tick past the frontier."""
        self._frames.append(frame)

    def cut(self, tick: int, frame: Frame) -> None:
        """The run was changed by hand at `tick`, to `frame`: nothing after it holds any more."""
        del self._frames[tick:]
        self._frames.append(frame)
