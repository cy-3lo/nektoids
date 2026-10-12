"""What the player sets in the Settings drawer (D-051, D-054, D-067): fast forward's speed,
whether the drawers show keys; how soon a tooltip shows, fixed for now. And what the run's
Navigator shows of the swimmer at work, its motion, its flames and the light its eyes draw in
(D-076), and the flow (D-608). One object for the session, shared by the Board and the run;
nothing is kept after it. Pure Python, no pygame.
"""

from __future__ import annotations

from dataclasses import dataclass

# fast forward runs this many frames' worth of ticks a frame
FAST_CHOICES: tuple[int, ...] = 2, 4, 8


@dataclass
class Settings:
    fast: int = 4
    key_hints: bool = True  # the keys shown on the drawers' rows and in the tooltips
    tooltip_frames: int = 30  # a tooltip shows after the mouse rests this long: 0.5 s [frames]
    motion: bool = True  # the swimmer's velocity and spin, in the run (D-076)
    flames: bool = True  # its thrusters' flames, in the run (D-608)
    intake: bool = True  # the light its eyes draw in, in the run
    flow: bool = False  # the flow round it, its tracers, in the run (D-608)

    def next_fast(self) -> None:
        self.fast = _after(self.fast, FAST_CHOICES)

    def toggle_hints(self) -> None:
        self.key_hints = not self.key_hints


def _after(value: int, choices: tuple[int, ...]) -> int:
    """The choice after `value`, round again after the last."""
    k = choices.index(value) if value in choices else -1
    return choices[(k + 1) % len(choices)]
