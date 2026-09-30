"""The arena: a rectangle with point lights and disc obstacles (D-019).

Lengths in u, the base body radius; x right, y up. A level builds its arena once and nothing
changes it. The arrays the optics need are built once, read-only. Pure numpy, no pygame.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

import numpy as np

OBSTACLE_RADIUS = 1.0  # [u]


@dataclass(frozen=True)
class Light:
    x: float  # [u]
    y: float  # [u]
    power: float  # [u]: an eye looking straight at the light reads RATE_MAX this close to it


@dataclass(frozen=True)
class Disc:
    x: float  # [u]
    y: float  # [u]
    radius: float = OBSTACLE_RADIUS  # [u]


def _frozen(array: np.ndarray) -> np.ndarray:
    array.setflags(write=False)
    return array


@dataclass(frozen=True, eq=False)
class Arena:
    """[0, width] x [0, height]. Tuples, not sets: their order is the order of the arrays."""

    width: float  # [u]
    height: float  # [u]
    lights: tuple[Light, ...] = ()
    obstacles: tuple[Disc, ...] = ()

    def __post_init__(self) -> None:
        """ValueError for what no level should hold: a light off the arena or inside an obstacle,
        an obstacle not wholly inside the arena, a size or a power that is not positive."""
        if not (self.width > 0 and self.height > 0):
            raise ValueError("the arena needs a positive width and height")
        for light in self.lights:
            if not light.power > 0:
                raise ValueError(f"light at ({light.x}, {light.y}): power must be positive")
            if not (0 <= light.x <= self.width and 0 <= light.y <= self.height):
                raise ValueError(f"light at ({light.x}, {light.y}) is off the arena")
        for disc in self.obstacles:
            r = disc.radius
            if not r > 0:
                raise ValueError(f"obstacle at ({disc.x}, {disc.y}): radius must be positive")
            if not (r <= disc.x <= self.width - r and r <= disc.y <= self.height - r):
                raise ValueError(f"obstacle at ({disc.x}, {disc.y}) is not inside the arena")
            for light in self.lights:
                if (light.x - disc.x) ** 2 + (light.y - disc.y) ** 2 <= r * r:
                    raise ValueError(f"light at ({light.x}, {light.y}) is inside an obstacle")

    @cached_property
    def light_xy(self) -> np.ndarray:
        """(L, 2) [u]."""
        return _frozen(np.array([(s.x, s.y) for s in self.lights], dtype=np.float64).reshape(-1, 2))

    @cached_property
    def light_power(self) -> np.ndarray:
        """(L,) [u]."""
        return _frozen(np.array([s.power for s in self.lights], dtype=np.float64))

    @cached_property
    def disc_xy(self) -> np.ndarray:
        """(M, 2) centres of the obstacles [u]."""
        return _frozen(
            np.array([(d.x, d.y) for d in self.obstacles], dtype=np.float64).reshape(-1, 2)
        )

    @cached_property
    def disc_radius(self) -> np.ndarray:
        """(M,) [u]."""
        return _frozen(np.array([d.radius for d in self.obstacles], dtype=np.float64))
