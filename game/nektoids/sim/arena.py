"""The arena: an open plane with point lights and disc obstacles (D-019), no walls (D-028).

Lengths in u, the base body radius; x right, y up. A level builds its arena once. Its lights are
fixed; each obstacle sits on a spring and gives a little when a swimmer pushes on it (D-424):
`moved` is the same plane with each obstacle displaced from its rest, as a run carries it from
tick to tick. The arrays the optics need are built once for each, read-only. Pure numpy, no
pygame.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

import numpy as np

BASE_RADIUS = 1.0  # [u] every body's radius, whatever its board (D-045): the unit of length
LIGHT_RADIUS = BASE_RADIUS  # [u] a light is a disc as big as a swimmer; it shadows nothing
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
    """The plane and what sits in it. Tuples, not sets: their order is the order of the arrays."""

    lights: tuple[Light, ...] = ()
    obstacles: tuple[Disc, ...] = ()
    offsets: np.ndarray | None = None  # (M, 2) each obstacle from its rest, on its spring [u]

    def __post_init__(self) -> None:
        """ValueError for what no level should hold: a light touching an obstacle, a power or a
        radius not positive. A plane `moved` from a checked one is not checked again."""
        if self.offsets is not None:
            return
        for light in self.lights:
            if not light.power > 0:
                raise ValueError(f"light at ({light.x}, {light.y}): power must be positive")
        for disc in self.obstacles:
            r = disc.radius
            if not r > 0:
                raise ValueError(f"obstacle at ({disc.x}, {disc.y}): radius must be positive")
            for light in self.lights:
                clear = r + LIGHT_RADIUS
                if (light.x - disc.x) ** 2 + (light.y - disc.y) ** 2 <= clear * clear:
                    raise ValueError(f"light at ({light.x}, {light.y}) touches an obstacle")

    @cached_property
    def light_xy(self) -> np.ndarray:
        """(L, 2) [u]."""
        return _frozen(np.array([(s.x, s.y) for s in self.lights], dtype=np.float64).reshape(-1, 2))

    @cached_property
    def light_power(self) -> np.ndarray:
        """(L,) [u]."""
        return _frozen(np.array([s.power for s in self.lights], dtype=np.float64))

    @cached_property
    def rest_xy(self) -> np.ndarray:
        """(M, 2) centres of the obstacles at rest, where the level puts them [u]."""
        return _frozen(
            np.array([(d.x, d.y) for d in self.obstacles], dtype=np.float64).reshape(-1, 2)
        )

    @cached_property
    def disc_xy(self) -> np.ndarray:
        """(M, 2) centres of the obstacles, where their springs have them now [u]."""
        if self.offsets is None:
            return self.rest_xy
        return _frozen(self.rest_xy + self.offsets)

    @property
    def at_rest(self) -> np.ndarray:
        """(M, 2) zeros: every obstacle where the level puts it."""
        return np.zeros((len(self.obstacles), 2))

    def moved(self, offsets: np.ndarray) -> Arena:
        """The same plane, each obstacle `offsets` (M, 2) [u] from its rest."""
        return Arena(self.lights, self.obstacles, np.array(offsets, dtype=np.float64))

    @cached_property
    def disc_radius(self) -> np.ndarray:
        """(M,) [u]."""
        return _frozen(np.array([d.radius for d in self.obstacles], dtype=np.float64))
