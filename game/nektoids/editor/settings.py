"""What the player sets in the Settings drawer (D-051, D-054): fast forward's speed, whether
the drawers show keys, how soon a tooltip shows. One object for the session, shared by the
editor and the run; nothing is kept after it. Pure Python, no pygame.
"""

from __future__ import annotations

from dataclasses import dataclass

# fast forward runs this many frames' worth of ticks a frame
FAST_CHOICES: tuple[int, ...] = 2, 4, 8
# a tooltip shows after the mouse rests this long [frames]
TOOLTIP_CHOICES: tuple[int, ...] = 30, 60, 90
FPS = 60  # the frames a second the tooltips' delay is counted in


@dataclass
class Settings:
    fast: int = 4
    key_hints: bool = True  # the keys shown on the drawers' rows and in the tooltips
    tooltip_frames: int = 60

    def next_fast(self) -> None:
        self.fast = _after(self.fast, FAST_CHOICES)

    def next_tooltip(self) -> None:
        self.tooltip_frames = _after(self.tooltip_frames, TOOLTIP_CHOICES)

    def toggle_hints(self) -> None:
        self.key_hints = not self.key_hints

    @property
    def tooltip_seconds(self) -> float:
        return self.tooltip_frames / FPS


def _after(value: int, choices: tuple[int, ...]) -> int:
    """The choice after `value`, round again after the last."""
    k = choices.index(value) if value in choices else -1
    return choices[(k + 1) % len(choices)]
