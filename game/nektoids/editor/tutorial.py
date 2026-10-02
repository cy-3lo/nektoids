"""A level's tutorial: steps that show part of the screen, say something about it, and move on when
the player has done what they ask, or presses Next (D-039).

A level's data may carry one: its ghosts, the parts the tutorial builds drawn faintly in their
cells, facing the way they should, and its steps. A step says a few short lines; shows a target,
or a list of them, which the overlay leaves lit while it dims the rest: an area ("board",
"menu", "palette"), a menu row, a tool, a Level button, a cell, or a part of the run view
("arena", "timeline", "objectives", "inside"); and waits, until a part is placed in a cell, a
part faces a way, a tool is taken, a wire runs from one cell to another, the run starts, or the
run is won. A step with no target is a hint: nothing is dimmed. A step with nothing to wait for
waits for Next, and only such a step has a Next: one that waits for an action moves on when it
is done, never before (D-048). The first level's tutorial leads; later levels only hint (D-039).
Skip ends a tutorial; going to the map starts every tutorial again from its beginning (D-048).
On a step that leads and waits for Next, any key or click moves on, but a click on Skip. While a
step leads, only the means to what it waits for go through (`allows`); the editor and the run
ask before they act. Pure Python, no pygame: what the step waits for is read from a `Context`,
the screen's geometry from the layouts.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache

from nektoids.editor import arena_layout
from nektoids.editor.layout import SCREEN, TURNS, Drawer, Layout, LevelButton, Rect, Tool, View
from nektoids.editor.router import Screen
from nektoids.graph.board import FACING_NAMES, Board, Kind
from nektoids.graph.hexgrid import SQRT3, Cell, to_pixel
from nektoids.levels.objectives import Outcome

BOX_WIDTH = 464  # 48 characters of Plex Mono and the padding (D-055) [px]
LINE = 22  # a line of the box [px]
PAD = 14  # inside the box [px]
BUTTON = (84, 28)  # Next, and Skip left of it, at the box's foot [px]
BUTTON_GAP = 8  # between Skip and Next [px]
GAP = 14  # between the target and the box [px]
PATH_MARGIN = 20  # the hand's way from one target to the next, this wide on either side [px]
AREA = 400  # a target this wide is an area, lit whole: the box may lie over part of it [px]
GRID = 16  # the pitch of the spots tried over the screen when none beside a target is clear [px]
REFUSAL = "do what the box says, or press Skip"  # an action a leading step does not let through
_COLUMN = (arena_layout.PANEL_LEFT, arena_layout.PANEL_WIDTH)
_LOWER = (*_COLUMN[:1], arena_layout.RULES[1], _COLUMN[1], SCREEN[1] - arena_layout.RULES[1])
RUN_PANELS = {"arena", "controls", "objectives", "inside", "wins"}  # the rest are controls
RUN_TARGETS = {  # the run view's parts, each with its title (D-050)
    "arena": arena_layout.ARENA_AREA,
    "controls": (_COLUMN[0], 0, _COLUMN[1], arena_layout.RULES[0]),  # buttons and timeline
    "play": dict(arena_layout.button_rects())[arena_layout.ArenaButton.PLAY],
    "timeline": arena_layout.TIMELINE,
    "objectives": arena_layout.SCORE_AREA,
    "inside": _LOWER,  # the wiring, until a won run puts its wins there
    "wins": _LOWER,
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
    show: Mapping | list | None = None  # a target or a list of them; None: a hint, nothing dimmed
    until: Mapping | None = None  # None: Next only


@dataclass(frozen=True)
class Action:
    """What the player asks for that would change the board, the tool in hand or the screen.
    `verb`: pick, place, tool, turn, wire, move, delete, undo, redo, run, map, edit, next."""

    verb: str
    kind: Kind | None = None  # pick, place
    cell: Cell | None = None  # place, turn, move, delete; one end of a wire
    other: Cell | None = None  # the other end of a wire
    tool: Tool | None = None


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
    def before(self) -> Step | None:
        """The step just done, if the player did something for it: the box keeps clear of it."""
        done = self.steps[self.index - 1] if 0 < self.index <= len(self.steps) else None
        return done if done is not None and done.until else None

    @property
    def leads(self) -> bool:
        """Whether this step shows a target, dimming the rest, rather than only hinting."""
        return self.step is not None and self.step.show is not None

    @property
    def explains(self) -> bool:
        """Whether this step explains what it shows: it leads and waits for Next. It holds the run
        still, which goes on when a step asks for Play, and outlines its panels (D-050)."""
        return self.leads and self.waits_for_next

    @property
    def waits_for_next(self) -> bool:
        """Whether this step has a Next: it waits for nothing the player does."""
        return self.step is not None and not self.step.until

    def next(self) -> None:
        """Next pressed: on to the following step, if this one waits for it. A step that waits
        for an action stays until it is done, so no action is left behind that a later step
        needs."""
        if self.waits_for_next:
            self.index += 1

    def skip(self) -> None:
        """Skip pressed: the tutorial ends here, its ghosts with it."""
        self.index = len(self.steps)

    def restart(self) -> None:
        """A place chosen in Chapters: from the first step again, finished or skipped, `follow`
        passing over what the board already holds."""
        self.index = 0

    def follow(self, context: Context) -> None:
        """On past every step whose wait is over: the player did what it asked."""
        while self.step is not None and self.step.until and met(self.step.until, context):
            self.index += 1


def panels(tutorial: Tutorial | None) -> frozenset[str]:
    """The panels a step explains, outlined and their titles lit (D-050): the areas and run parts
    it shows, if it leads and waits for Next. A step that asks for an action only dims."""
    if tutorial is None or not tutorial.explains:
        return frozenset()
    show = tutorial.step.show
    shows = show if isinstance(show, list) else [show]
    return frozenset(one.get("area") or one.get("run") for one in shows) - {None}


def drawer_for(step: Step | None) -> Drawer | None:
    """The drawer a step's targets are in, which it opens as it shows: Parts for a part's row,
    Tools for a tool; None if it needs none (D-051)."""
    shows = [] if step is None or step.show is None else step.show
    shows = shows if isinstance(shows, list) else [shows]
    if any("menu" in one or one.get("area") == "parts" for one in shows):
        return Drawer.PARTS
    if any("tool" in one for one in shows):
        return Drawer.TOOLS
    return None


def guided(data: Mapping | None) -> bool:
    """Whether a level's tutorial data leads somewhere, rather than only hinting: such a level
    starts afresh, board and all, each time a place is chosen in Chapters (D-050, D-054)."""
    return data is not None and any(step.get("show") for step in data["steps"])


def allows(step: Step | None, action: Action) -> bool:
    """Whether `step` lets `action` through (D-048). No step, or a hint, lets all through. A step
    that leads lets through only the means to what it waits for: picking that part (from the
    menu or by its key) and placing it on that cell; a turn tool, or L and R, on that part; that
    tool; the Wire tool and that wire, either way round (D-026); Run. While it waits for a win,
    running and going back to edit. A step that waits for Next lets nothing through. Zoom, the
    view's centre, info boxes and folding the menu change none of this, and are not asked."""
    if step is None or step.show is None:
        return True
    until, verb = step.until or {}, action.verb
    if "placed" in until:
        kind, cell = Kind(until["placed"]["kind"]), _cell(until["placed"]["cell"])
        return (
            (verb == "pick" and action.kind is kind)
            or (verb == "tool" and action.tool is Tool.ADD)
            or (verb == "place" and action.kind is kind and action.cell == cell)
        )
    if "facing" in until:
        cell = _cell(until["facing"]["cell"])
        return (verb == "tool" and action.tool in TURNS) or (verb == "turn" and action.cell == cell)
    if "tool" in until:
        return verb == "tool" and action.tool is Tool(until["tool"])
    if "wired" in until:
        ends = {_cell(until["wired"]["from"]), _cell(until["wired"]["to"])}
        wire = verb == "wire" and {action.cell, action.other} == ends
        return wire or (verb == "tool" and action.tool is Tool.WIRE)
    if "screen" in until:
        return verb == "run" and Screen(until["screen"]) is Screen.RUN
    if "outcome" in until:
        return verb in ("run", "edit")
    return False


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


def target_rects(show: Mapping | list | None, screen: Screen, layout: Layout, view: View) -> list:
    """Every target a step shows that is on the screen now open, in the step's order."""
    return [rect for rect, _ in target_spots(show, screen, layout, view)]


def target_spots(show: Mapping | list | None, screen: Screen, layout: Layout, view: View) -> list:
    """The same, each with the shape the overlay gives it: "disc" round a cell, "panel" for an
    area or a part of the run view, cut and outlined on its own edges, "spot" round anything
    else, a button or a menu row (D-048, D-050)."""
    shows = [] if show is None else show if isinstance(show, list) else [show]
    spots = [(target_rect(one, screen, layout, view), _shape(one)) for one in shows]
    return [(rect, shape) for rect, shape in spots if rect is not None]


def _shape(show: Mapping) -> str:
    if "cell" in show:
        return "disc"
    if "area" in show or show.get("run") in RUN_PANELS:
        return "panel"
    return "spot"


def target_rect(show: Mapping | None, screen: Screen, layout: Layout, view: View) -> Rect | None:
    """The part of the screen a step shows, in the view now open; None if it is not there."""
    if show is None:
        return None
    if "run" in show:
        return RUN_TARGETS[show["run"]] if screen is Screen.RUN else None
    if screen is not Screen.EDIT:
        return None
    if "area" in show:  # the board, the Parts drawer, the activity bar (D-051)
        return {
            "board": layout.board_area,
            "parts": layout.drawer_area if layout.drawer is Drawer.PARTS else None,
            "bar": layout.bar_area,
        }[show["area"]]
    if "menu" in show:  # a part's row in the Parts drawer
        return dict(layout.menu_items).get(Kind(show["menu"]))
    if "tool" in show:  # its row in the Tools drawer, or the drawer's icon while it is closed
        rows, icons = dict(layout.tool_buttons), dict(layout.drawer_buttons)
        return rows.get(Tool(show["tool"])) or icons[Drawer.TOOLS]
    if "level" in show:
        return dict(layout.level_buttons)[LevelButton(show["level"])]
    if "cell" in show:
        x, y = to_pixel(_cell(show["cell"]), view.size, view.origin)
        half_w, half_h = SQRT3 / 2 * view.size, view.size
        return (round(x - half_w), round(y - half_h), round(2 * half_w), round(2 * half_h))
    raise ValueError(f"a step cannot show {dict(show)!r}")


def box_rect(targets: list, lines: int, hint_at: Rect, before: list = ()) -> Rect:
    """The step's box. A hint's, with no target, at the foot of `hint_at` (the board or the
    arena). A leading step's keeps clear of its targets, of the hand's way from each to the
    next, and of the same for the step `before`, the work just done (D-048): beside a target,
    the last first, trying its right, its left, under it, over it; else the clear spot of a
    grid over the screen nearest the last target. Each spot is brought onto the screen. An area
    (the board, the arena) is too big to keep clear of: the box may lie over part of it."""
    height = 2 * PAD + lines * LINE + 8 + BUTTON[1]
    if not targets:
        x, y, w, h = hint_at
        return (x + 16, y + h - height - 16, BOX_WIDTH, height)
    return _placed(tuple(map(tuple, targets)), tuple(map(tuple, before)), height)


@lru_cache(maxsize=32)  # drawn every frame; the grid is slow to search
def _placed(targets: tuple, before: tuple, height: int) -> Rect:
    kept, kept_before = _narrow(targets), _narrow(before)  # an area cannot be cleared
    rects, paths = (*kept, *kept_before), (*_paths(kept), *_paths(kept_before))

    def clear(spot: Rect) -> bool:
        return not any(_meet(spot, r) for r in rects) and not any(_crosses(spot, *p) for p in paths)

    beside = [
        _kept_on_screen(spot)
        for target in reversed(targets)
        for spot in _beside(target, BOX_WIDTH, height)
    ]
    for spot in beside:
        if clear(spot):
            return spot
    goal = _centre(targets[-1])
    grid = [
        (x, y, BOX_WIDTH, height)
        for y in range(8, SCREEN[1] - 8 - height + 1, GRID)
        for x in range(8, SCREEN[0] - 8 - BOX_WIDTH + 1, GRID)
    ]
    free = [spot for spot in grid if clear(spot)]
    if not free:
        return beside[0]
    return min(free, key=lambda s: (math.dist(_centre(s), goal), s[1], s[0]))


def _narrow(rects: tuple) -> tuple:
    return tuple(rect for rect in rects if rect[2] < AREA)


def _paths(targets: tuple) -> list:
    """The hand's way through a step's targets, in the step's order: from each to the next."""
    return list(zip(targets, targets[1:], strict=False))


def _centre(rect: Rect) -> tuple[float, float]:
    x, y, w, h = rect
    return (x + w / 2, y + h / 2)


def _crosses(box: Rect, a: Rect, b: Rect) -> bool:
    """Whether the straight way from the centre of `a` to that of `b` comes within PATH_MARGIN of
    `box` (Liang-Barsky: the segment clipped by the box grown by the margin)."""
    (x0, y0), (x1, y1) = _centre(a), _centre(b)
    bx, by, bw, bh = box
    left, top = bx - PATH_MARGIN, by - PATH_MARGIN
    right, bottom = bx + bw + PATH_MARGIN, by + bh + PATH_MARGIN
    dx, dy = x1 - x0, y1 - y0
    enter, leave = 0.0, 1.0
    for p, q in ((-dx, x0 - left), (dx, right - x0), (-dy, y0 - top), (dy, bottom - y0)):
        if p == 0:
            if q < 0:
                return False  # parallel to this side, and outside it
            continue
        t = q / p
        if p < 0:
            enter = max(enter, t)
        else:
            leave = min(leave, t)
        if enter > leave:
            return False
    return True


def _beside(target: Rect, width: int, height: int) -> list:
    tx, ty, tw, th = target
    across = tx + tw // 2 - width // 2
    return [
        (tx + tw + GAP, ty, width, height),  # to the right, level with it
        (tx - GAP - width, ty, width, height),  # to the left
        (across, ty + th + GAP, width, height),  # under it
        (across, ty - GAP - height, width, height),  # over it
    ]


def _meet(a: Rect, b: Rect) -> bool:
    """Whether two rects overlap, the second grown by the lit margin round a target."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw + GAP and bx - GAP < ax + aw and ay < by + bh + GAP and by - GAP < ay + ah


def _kept_on_screen(rect: Rect) -> Rect:
    x, y, w, h = rect
    return (min(max(8, x), SCREEN[0] - 8 - w), min(max(8, y), SCREEN[1] - 8 - h), w, h)


def next_rect(box: Rect) -> Rect:
    """Next, at the box's bottom right."""
    x, y, w, h = box
    bw, bh = BUTTON
    return (x + w - PAD - bw, y + h - PAD - bh, bw, bh)


def answer(tutorial: Tutorial, box: Rect, click: tuple[int, int] | None) -> str | None:
    """What a key (`click` None) or a click at `click` does to the tutorial, before the editor or
    the run sees it: "skip" on Skip; on a step that waits for Next, "next" on Next, and, on a
    step that also leads, at any key or any click; otherwise None, and the press goes on."""
    last = tutorial.index == len(tutorial.steps) - 1
    if click is not None and not last and _inside(skip_rect(box), click):
        return "skip"
    if not tutorial.waits_for_next:
        return None
    if tutorial.leads or (click is not None and _inside(next_rect(box), click)):
        return "next"
    return None


def _inside(rect: Rect, point: tuple[int, int]) -> bool:
    x, y, w, h = rect
    return x <= point[0] < x + w and y <= point[1] < y + h


def skip_rect(box: Rect) -> Rect:
    """Skip, left of Next."""
    x, y, w, h = next_rect(box)
    return (x - BUTTON_GAP - w, y, w, h)


def _cell(data) -> Cell:
    return (int(data[0]), int(data[1]))
