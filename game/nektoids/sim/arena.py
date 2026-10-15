"""The arena: an open plane with point lights and disc obstacles (D-019), no walls (D-028), and
pumps and sources that stir its fluid (D-700).

Lengths in u, the base body radius; x right, y up. A level builds its arena once. Its lights are
fixed; each obstacle sits on a spring and gives a little when a swimmer pushes on it (D-424):
`moved` is the same plane with each obstacle displaced from its rest, as a run carries it from
tick to tick. The arrays the optics need are built once for each, read-only; the inverse mobility of
its lights and obstacles at rest, which the flow needs (D-601), and their reactions to the
pumps' and sources' flow, once for the level and handed on by `moved`. Pumps and sources are
fixed spheres of radius STIR_RADIUS, solid to a swimmer as a light is. Pure numpy, no pygame.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import cached_property

import numpy as np

from nektoids.graph.kinds import Hue

BASE_RADIUS = 1.0  # [u] every body's radius, whatever its board (D-045): the unit of length
LIGHT_RADIUS = BASE_RADIUS  # [u] a light is a disc as big as a swimmer; it shadows nothing
OBSTACLE_RADIUS = 1.0  # [u]
STIR_RADIUS = 0.5  # [u] a pump or a source: a sphere this big, for the fluid and for a swimmer
STIR_STEP = np.pi / 3  # a pump's facing d points at 60° * d (D-009)


class Colour(Enum):
    """A light's colour (D-506): amber or violet, one channel, or white, both; an eye sees the
    lights that shine in its own colour. Its place here is its code in a level's word."""

    WHITE = "white"
    AMBER = "amber"
    VIOLET = "violet"

    @property
    def channels(self) -> tuple[bool, ...]:
        """Whether it shines in each channel, in `Hue`'s order."""
        return tuple(self is Colour.WHITE or self.value == hue.value for hue in Hue)


@dataclass(frozen=True)
class Light:
    x: float  # [u]
    y: float  # [u]
    power: float  # [u]: an eye looking straight at the light reads RATE_MAX this close to it
    colour: Colour = Colour.WHITE  # the eyes it is seen by: of its colour, or all (D-506)


@dataclass(frozen=True)
class Disc:
    x: float  # [u]
    y: float  # [u]
    radius: float = OBSTACLE_RADIUS  # [u]


@dataclass(frozen=True)
class Pump:
    """A point force on the fluid, held in place, its holder taking the reaction (D-700)."""

    x: float  # [u]
    y: float  # [u]
    facing: int  # hex direction: it pushes the fluid at 60° * facing
    force: float  # [f] how hard


@dataclass(frozen=True)
class Source:
    """A point source of fluid, or with a negative rate a sink (D-700)."""

    x: float  # [u]
    y: float  # [u]
    rate: float  # [u^3/s] the volume it gives a second; negative, it takes


def _frozen(array: np.ndarray) -> np.ndarray:
    array.setflags(write=False)
    return array


@dataclass(frozen=True, eq=False)
class Arena:
    """The plane and what sits in it. Tuples, not sets: their order is the order of the arrays."""

    lights: tuple[Light, ...] = ()
    obstacles: tuple[Disc, ...] = ()
    offsets: np.ndarray | None = None  # (M, 2) each obstacle from its rest, on its spring [u]
    inverse: np.ndarray | None = None  # (3K, 3K) `clamped_inverse` handed on; None: not yet built
    pumps: tuple[Pump, ...] = ()
    sources: tuple[Source, ...] = ()
    held: np.ndarray | None = None  # (K, 3) `stirred_reactions` handed on; None: not yet built

    def __post_init__(self) -> None:
        """ValueError for what no level should hold: a light touching an obstacle, a power or a
        radius not positive, a pump or a source touching anything. A plane `moved` from a checked
        one is not checked again."""
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
        placed = [(s.x, s.y, LIGHT_RADIUS) for s in self.lights]
        placed += [(d.x, d.y, d.radius) for d in self.obstacles]
        for stir in self.pumps + self.sources:
            for x, y, r in placed:
                clear = r + STIR_RADIUS
                if (stir.x - x) ** 2 + (stir.y - y) ** 2 <= clear * clear:
                    raise ValueError(f"pump or source at ({stir.x}, {stir.y}) touches another item")
            placed.append((stir.x, stir.y, STIR_RADIUS))

    @cached_property
    def light_xy(self) -> np.ndarray:
        """(L, 2) [u]."""
        return _frozen(np.array([(s.x, s.y) for s in self.lights], dtype=np.float64).reshape(-1, 2))

    @cached_property
    def light_power(self) -> np.ndarray:
        """(L,) [u]."""
        return _frozen(np.array([s.power for s in self.lights], dtype=np.float64))

    @cached_property
    def light_channels(self) -> np.ndarray:
        """(L, C) bool: whether each light shines in each channel, by its colour (D-506)."""
        rows = [s.colour.channels for s in self.lights]
        return _frozen(np.array(rows, dtype=bool).reshape(len(self.lights), len(Hue)))

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
        return Arena(
            self.lights,
            self.obstacles,
            np.array(offsets, dtype=np.float64),
            self.clamped_inverse,
            self.pumps,
            self.sources,
            self.stirred_reactions,
        )

    @cached_property
    def pump_xy(self) -> np.ndarray:
        """(P, 2) [u]."""
        return _frozen(np.array([(p.x, p.y) for p in self.pumps], dtype=np.float64).reshape(-1, 2))

    @cached_property
    def pump_force(self) -> np.ndarray:
        """(P, 2) [f]: what each pump pushes the fluid with."""
        angle = STIR_STEP * np.array([p.facing for p in self.pumps], dtype=np.float64)
        force = np.array([p.force for p in self.pumps], dtype=np.float64)
        return _frozen(np.stack((force * np.cos(angle), force * np.sin(angle)), axis=1))

    @cached_property
    def source_xy(self) -> np.ndarray:
        """(S, 2) [u]."""
        rows = [(s.x, s.y) for s in self.sources]
        return _frozen(np.array(rows, dtype=np.float64).reshape(-1, 2))

    @cached_property
    def source_rate(self) -> np.ndarray:
        """(S,) [u^3/s]."""
        return _frozen(np.array([s.rate for s in self.sources], dtype=np.float64))

    @cached_property
    def solid_xy(self) -> np.ndarray:
        """(F, 2) [u]: what a swimmer meets and cannot move, lights, then pumps, then sources."""
        return _frozen(np.concatenate((self.light_xy, self.pump_xy, self.source_xy)))

    @cached_property
    def solid_radius(self) -> np.ndarray:
        """(F,) [u], in `solid_xy`'s order."""
        stirs = len(self.pumps) + len(self.sources)
        return _frozen(
            np.concatenate((np.full(len(self.lights), LIGHT_RADIUS), np.full(stirs, STIR_RADIUS)))
        )

    @cached_property
    def stirred_reactions(self) -> np.ndarray:
        """(K, 3): the force [f] and torque [f u] the pumps' and sources' flow puts on each light
        and obstacle at rest, held, solved once with `clamped_inverse` and handed on by `moved`;
        read-only (D-700)."""
        if self.held is not None:
            return self.held
        from nektoids.sim import flow

        return _frozen(flow.stirred_reactions(self))

    @cached_property
    def clamped_inverse(self) -> np.ndarray:
        """(3K, 3K): the inverse grand mobility of the K lights and obstacles at rest, the
        clamped spheres of the flow (D-601), built once and handed on by `moved`; read-only."""
        if self.inverse is not None:
            return self.inverse
        from nektoids.sim import flow  # flow needs motion, which needs this module

        return _frozen(flow.clamped_inverse(self))

    @cached_property
    def disc_radius(self) -> np.ndarray:
        """(M,) [u]."""
        return _frozen(np.array([d.radius for d in self.obstacles], dtype=np.float64))
