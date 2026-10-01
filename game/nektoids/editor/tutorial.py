"""A level's tutorial: steps that show part of the screen, say something about it, and move on
when the player has done what they ask, or presses Next (D-039).

A level's data may carry one: its ghosts, the parts the tutorial builds drawn faintly in their
cells, facing the way they should, and its steps. A step says a few short lines; shows a target,
which the overlay leaves lit while it dims the rest: an area ("board", "menu", "palette"), a menu
row, a tool, a Level button, a cell, or a part of the run view ("arena", "timeline",
"objectives", "inside"); and waits, until a part is placed in a cell, a part faces a way, a tool
is taken, a wire runs from one cell to another, the run starts, or the run is won. A step with
no target is a hint: nothing is dimmed. A step with nothing to wait for waits for Next. The
first level's tutorial leads; later levels only hint (D-039).
Pure Python, no pygame: what the step waits for is read from a `Context`, the screen's
geometry from the layouts.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from nektoids.editor import arena_layout
from nektoids.editor.layout import SCREEN, Layout, LevelButton, Rect, Tool, View
from nektoids.editor.router import Screen
from nektoids.graph.board import FACING_NAMES, Board, Kind
from nektoids.graph.hexgrid import SQRT3, Cell, to_pixel
from nektoids.levels.objectives import Outcome

BOX_WIDTH = 360  # [px]
LINE = 19  # a line of the box [px]
PAD = 14  # inside the box [px]
BUTTON = (84, 28)  # Next, at the box's foot [px]
GAP = 14  # between the target and the box [px]
RUN_TARGETS = {
    "arena": arena_layout.ARENA_AREA,
    "timeline": arena_layout.TIMELINE,
    "objectives": arena_layout.SCORE_AREA,
    "inside": arena_layout.CIRCUIT_AREA,
}


@dataclass(frozen=True)
class Ghost:
    """A part the tutorial builds, drawn faintly where it goes, facing the way it should."""

    kind: Kind
    cell: Cell
    facing: int | None


@dataclass(frozen=True)
class Step:
    say: tuple[str, ...]
    show: Mapping | None = None  # None: a hint, nothing dimmed
    until: Mapping | None = None  # None: Next only


@dataclass(frozen=True)
class Context:
    """What a step may wait for: the board, the tool in hand, the screen, the run's end."""

    board: Board
    tool: Tool
    screen: Screen
    outcome: Outcome | None = None


class Tutorial:
    def __init__(self, ghosts: tuple[Ghost, ...], steps: tuple[Step, ...]) -> None:
        self.ghosts, self.steps = ghosts, steps
        self.index = 0

    @classmethod
    def from_dict(cls, data: Mapping) -> Tutorial:
        ghosts = tuple(
            Ghost(
                Kind(g["kind"]),
                (int(g["cell"][0]), int(g["cell"][1])),
                FACING_NAMES.index(g["facing"]) if g.get("facing") else None,
            )
            for g in data.get("ghosts", ())
        )
        steps = tuple(Step(tuple(s["say"]), s.get("show"), s.get("until")) for s in data["steps"])
        return cls(ghosts, steps)

    @property
    def step(self) -> Step | None:
        """The step showing now; None once the tutorial is over."""
        return self.steps[self.index] if self.index < len(self.steps) else None

    @property
    def leads(self) -> bool:
        """Whether this step shows a target, dimming the rest, rather than only hinting."""
        return self.step is not None and self.step.show is not None

    def next(self) -> None:
        """Next pressed: on to the following step."""
        if self.step is not None:
            self.index += 1

    def follow(self, context: Context) -> None:
        """On past every step whose wait is over: the player did what it asked."""
        while self.step is not None and self.step.until and met(self.step.until, context):
            self.index += 1


def met(until: Mapping, context: Context) -> bool:
    """Whether what a step waits for has happened."""
    board = context.board
    if "placed" in until:
        node = board.node_at(_cell(until["placed"]["cell"]))
        return node is not None and node.kind is Kind(until["placed"]["kind"])
    if "facing" in until:
        node = board.node_at(_cell(until["facing"]["cell"]))
        return node is not None and node.facing == FACING_NAMES.index(until["facing"]["facing"])
    if "tool" in until:
        return context.tool is Tool(until["tool"])
    if "wired" in until:
        source = board.node_at(_cell(until["wired"]["from"]))
        target = board.node_at(_cell(until["wired"]["to"]))
        return (
            source is not None
            and target is not None
            and any(w.source == source.id and w.target == target.id for w in board.wires)
        )
    if "screen" in until:
        return context.screen is Screen(until["screen"])
    if "outcome" in until:
        return context.outcome is Outcome(until["outcome"])
    raise ValueError(f"a step cannot wait for {dict(until)!r}")


# Where things are


def target_rect(show: Mapping | None, screen: Screen, layout: Layout, view: View) -> Rect | None:
    """The part of the screen a step shows, in the view now open; None if it is not there."""
    if show is None:
        return None
    if "run" in show:
        return RUN_TARGETS[show["run"]] if screen is Screen.RUN else None
    if screen is not Screen.EDIT:
        return None
    if "area" in show:
        return {
            "board": layout.board_area,
            "menu": layout.menu_area,
            "palette": layout.palette_area,
        }[show["area"]]
    if "menu" in show:
        return dict(layout.menu_items).get(Kind(show["menu"]))
    if "tool" in show:
        return dict(layout.tool_buttons)[Tool(show["tool"])]
    if "level" in show:
        return dict(layout.level_buttons)[LevelButton(show["level"])]
    if "cell" in show:
        x, y = to_pixel(_cell(show["cell"]), view.size, view.origin)
        half_w, half_h = SQRT3 / 2 * view.size, view.size
        return (round(x - half_w), round(y - half_h), round(2 * half_w), round(2 * half_h))
    raise ValueError(f"a step cannot show {dict(show)!r}")


def box_rect(target: Rect | None, lines: int, hint_at: Rect) -> Rect:
    """The step's box: beside its target, on whichever side has room, kept on screen; a hint's,
    with no target, at the foot of `hint_at` (the board or the arena)."""
    width, height = BOX_WIDTH, 2 * PAD + lines * LINE + 8 + BUTTON[1]
    sw, sh = SCREEN
    if target is None:
        x, y, w, h = hint_at
        return (x + 16, y + h - height - 16, width, height)
    tx, ty, tw, th = target
    if tx + tw + GAP + width <= sw - 8:  # to the right, level with it
        left, top = tx + tw + GAP, ty
    elif tx - GAP - width >= 8:  # to the left
        left, top = tx - GAP - width, ty
    else:  # under it, or over it when there is no room under
        left = min(max(8, tx), sw - 8 - width)
        below = ty + th + GAP
        top = below if below + height <= sh - 8 else ty - GAP - height
    return (left, max(8, min(top, sh - 8 - height)), width, height)


def next_rect(box: Rect) -> Rect:
    """Next, at the box's bottom right."""
    x, y, w, h = box
    bw, bh = BUTTON
    return (x + w - PAD - bw, y + h - PAD - bh, bw, bh)


def _cell(data) -> Cell:
    return (int(data[0]), int(data[1]))
