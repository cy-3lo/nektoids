"""What drives the developer view: the clock, the sensor sliders and the waveforms (D-016).

Developer tools only: the player's graph has no slider (brief: "No sliders"). Time is an integer
tick count, so pausing, stepping and resetting never accumulate float error. Pure numbers, no
pygame.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from nektoids.graph.dynamics import RATE_MAX

SIM_HZ = 120  # ticks per second
DT = 1.0 / SIM_HZ  # [s]
TICKS_PER_FRAME = 2  # at 60 frames per second; main.py checks the product
WAVES = ("hold", "step", "sine", "square")
STEP_AT = 1.0  # the step wave jumps from 0 to the slider level after this long [s]
PERIOD = 4.0  # of the sine and square waves [s]

SLIDER_HEIGHT = 1.6  # hex sizes
SLIDER_OFFSET = 1.5  # left of the part's centre [hex sizes]
SLIDER_GRAB = 12.0  # how far from the track a press still grabs the knob [px]


def waveform(name: str, level: float, tick: int) -> float:
    """Rate an eye sends at `tick` when its slider is at `level`; between 0 and `level`."""
    t = tick * DT
    if name == "hold":
        return level
    if name == "step":
        return 0.0 if t < STEP_AT else level
    if name == "sine":
        return level * 0.5 * (1.0 - math.cos(2.0 * math.pi * t / PERIOD))
    if name == "square":
        return level if (t % PERIOD) >= PERIOD / 2.0 else 0.0
    raise ValueError(f"unknown waveform {name!r}")


def next_wave(name: str) -> str:
    return WAVES[(WAVES.index(name) + 1) % len(WAVES)]


class Clock:
    """Which ticks to run in this frame: two while it runs (times `speed`), none while paused,
    unless stepped: a step is always one frame's two ticks."""

    def __init__(self) -> None:
        self.tick = 0
        self.paused = False
        self.speed = 1  # frames' worth of ticks per frame while running: fast forward if > 1
        self._stepped = False

    def frame(self) -> range:
        """The ticks to run now, in order; the clock moves past them."""
        if self._stepped:
            count = TICKS_PER_FRAME
        else:
            count = 0 if self.paused else TICKS_PER_FRAME * self.speed
        self._stepped = False
        first = self.tick
        self.tick += count
        return range(first, self.tick)

    def toggle_pause(self) -> None:
        self.paused = not self.paused

    def step(self) -> None:
        """While paused, run one frame's worth of ticks at the next frame."""
        self._stepped = True

    def reset(self) -> None:
        self.tick = 0

    @property
    def seconds(self) -> float:
        return self.tick * DT


@dataclass(frozen=True)
class Track:
    """A vertical slider: where it stands and how far it runs [px, screen y down]."""

    x: float
    top: float  # level RATE_MAX
    bottom: float  # level 0


def track_for(centre: tuple[float, float], size: float) -> Track:
    """The slider of a sensor drawn at `centre`, to its left."""
    half = 0.5 * SLIDER_HEIGHT * size
    return Track(centre[0] - SLIDER_OFFSET * size, centre[1] - half, centre[1] + half)


def knob_y(track: Track, level: float) -> float:
    return track.bottom - (track.bottom - track.top) * level / RATE_MAX


def level_at(track: Track, y: float) -> float:
    """The level whose knob sits at `y`, clamped to [0, RATE_MAX]."""
    fraction = (track.bottom - y) / (track.bottom - track.top)
    return RATE_MAX * min(1.0, max(0.0, fraction))


def on_track(track: Track, point: tuple[float, float]) -> bool:
    """Whether a press at `point` grabs the knob: near the track, or just beyond its ends."""
    return (
        abs(point[0] - track.x) <= SLIDER_GRAB
        and track.top - SLIDER_GRAB <= point[1] <= track.bottom + SLIDER_GRAB
    )
