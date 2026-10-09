"""A button held down (D-412, D-426): after a moment it acts again, and again, at a steady pace,
until it is let go; the Editor's − and + in Parts. Pure Python, no pygame.
"""

from __future__ import annotations

from dataclasses import dataclass

HOLD = 24  # held this long, a button acts again: 0.4 s [frames]
EVERY = 6  # then once every so often: 10 a second [frames]


@dataclass
class Hold:
    target: object = None  # what is held, None when nothing is
    frames: int = 0  # frames it has been held

    def press(self, target: object) -> None:
        self.target, self.frames = target, 0

    def release(self) -> None:
        self.target, self.frames = None, 0

    def tick(self) -> bool:
        """Once a frame: whether what is held acts again now."""
        if self.target is None:
            return False
        self.frames += 1
        return self.frames >= HOLD and (self.frames - HOLD) % EVERY == 0
