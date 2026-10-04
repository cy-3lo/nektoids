"""The kinds of part, one entry each (D-202): what the board, the dynamics and the editor need to
know of a part, in one table, `SPEC`, which a test checks whole.

An entry says where the part stands (sensor, operator, actuator), how it is wired (inputs and
outputs at most), where it points until turned (D-009), its law, what it does to the rates
through it (`laws.py`; a sensor has none), a sensor's sense, which gives its rate, and an
actuator's action, what it does to the body (`sim/world.py`, D-203), and how the player reads
it: a letter for the panels, a name and a paragraph for its info box (D-036, D-094), the icon
on it and its outline, each by name, for the editor to draw. The table's order is the order of
the parts within each group of the menu (D-069). Pure Python, no pygame.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from nektoids.graph.hexgrid import E
from nektoids.graph.laws import Difference, Law, Relax, Scaled


class Category(Enum):
    SENSOR = "sensor"
    OPERATOR = "operator"
    ACTUATOR = "actuator"


class Kind(Enum):
    EYE = "eye"
    SOURCE = "source"  # produces a signal of its own; senses nothing
    DOUBLE = "double"
    HALVE = "halve"
    SUM = "sum"
    DIFFERENCE = "difference"
    THRUSTER = "thruster"

    @property
    def spec(self) -> KindSpec:
        return SPEC[self]

    @property
    def category(self) -> Category:
        return SPEC[self].category

    @property
    def emits(self) -> bool:
        return self.category is not Category.ACTUATOR

    @property
    def receives(self) -> bool:
        return self.category is not Category.SENSOR

    @property
    def default_facing(self) -> int | None:
        """Hex direction on the body until the player turns it (forward = E); None for operators.

        Where an eye looks, or which way a thruster pushes (D-009).
        """
        return SPEC[self].facing

    @property
    def max_inputs(self) -> int | None:
        """How many wires may come in; None means no limit (D-014)."""
        return SPEC[self].max_inputs

    @property
    def max_outputs(self) -> int | None:
        """How many wires may go out; None means no limit (D-014)."""
        return SPEC[self].max_outputs


@dataclass(frozen=True)
class KindSpec:
    category: Category
    letter: str  # its node's label in the panels: E0, T6
    name: str  # as the menu and the info box name it
    what: str  # what it does, a paragraph the info box wraps to its width (D-094)
    law: Law | None = None  # None for a sensor: its rate is given, not computed
    facing: int | None = None  # where it points until turned; None: it has no direction
    max_inputs: int | None = None  # None: any number
    max_outputs: int | None = None  # None: any number
    icon: str | None = None  # drawn on it, by its name in `editor/glyphs.py`; None: blank
    shape: str = "diamond"  # its outline, by its name in `editor/geometry.py`'s SHAPES
    sense: str | None = None  # a sensor's: what gives its rate, by name (`sim/world.py`, SENSES)
    action: str | None = None  # an actuator's: what it does, by name (`sim/world.py`, ACTIONS)


SPEC: dict[Kind, KindSpec] = {
    Kind.EYE: KindSpec(
        Category.SENSOR,
        "E",
        "Eye",
        "Senses the light that falls on its flat face: more from a light near it and in front "
        "of it.",
        facing=E,
        icon="eye",
        shape="eye disc",
        sense="light",
    ),
    Kind.SOURCE: KindSpec(
        Category.SENSOR,
        "S",
        "Source",
        "Senses nothing: it sends a steady signal.",
        shape="disc",  # a blank sensor: it senses nothing
        sense="steady",
    ),
    Kind.DOUBLE: KindSpec(
        Category.OPERATOR,
        "D",
        "Double",
        "Sends twice what comes in.",
        Relax(Scaled(2.0)),
        icon="angles-up",
    ),
    Kind.HALVE: KindSpec(
        Category.OPERATOR,
        "H",
        "Halve",
        "Sends half what comes in.",
        Relax(Scaled(0.5)),
        icon="angles-down",
    ),
    Kind.SUM: KindSpec(
        Category.OPERATOR,
        "P",
        "Sum",
        "Sums its two inputs.",
        Relax(Scaled(1.0)),
        max_inputs=2,
        max_outputs=1,
        icon="plus",
    ),
    Kind.DIFFERENCE: KindSpec(
        Category.OPERATOR,
        "M",
        "Diff",
        "Difference of its two inputs.",
        Relax(Difference()),
        max_inputs=2,
        max_outputs=1,
        icon="minus",
    ),
    Kind.THRUSTER: KindSpec(
        Category.ACTUATOR,
        "T",
        "Thruster",
        "Pushes the body the way it points. Off centre, it turns the body too.",
        Relax(Scaled(1.0)),
        facing=E,
        icon="rocket",
        shape="square point",
        action="push",
    ),
}
