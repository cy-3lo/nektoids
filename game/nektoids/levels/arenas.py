"""Arenas to try a swimmer in, until the real levels exist (D-019).

Lengths in u, the base body radius; 40 x 38 u fills the arena view at 16 px/u. Swimmers, lights
and obstacles are all unit discs to start with. The swimmer runs whatever board is in
the editor. Each asks it to visit every light within the level's time (D-023).
"""

from __future__ import annotations

from dataclasses import dataclass

from nektoids.levels.objectives import Objective, VisitLights
from nektoids.sim.arena import Arena, Disc, Light

WIDTH, HEIGHT = 40.0, 38.0  # [u]


@dataclass(frozen=True)
class Level:
    title: str
    arena: Arena
    start: tuple[float, float, float]  # x, y [u] and heading [degrees, counter-clockwise from +x]
    time_limit: float  # the run is over after this long [s]
    objectives: tuple[Objective, ...] = ()


def arenas() -> list[Level]:
    return [
        Level(
            "One light",
            Arena(WIDTH, HEIGHT, lights=(Light(27.0, 21.0, 8.0),)),
            start=(9.0, 15.0, 0.0),
            time_limit=20.0,  # crossed wiring touches it in 8.7 s (D-022)
            objectives=(VisitLights(),),
        ),
        Level(
            "Two lights, four obstacles",
            Arena(
                WIDTH,
                HEIGHT,
                lights=(Light(27.5, 24.0, 8.0), Light(7.5, 7.5, 4.0)),
                obstacles=(
                    Disc(21.0, 21.0),
                    Disc(24.0, 15.0),
                    Disc(14.0, 27.5),
                    Disc(31.0, 10.0),
                ),
            ),
            start=(15.0, 19.0, 20.0),
            time_limit=45.0,  # a one-eyed circler visits both in 23.1 s (test_determinism)
            objectives=(VisitLights(),),
        ),
    ]
