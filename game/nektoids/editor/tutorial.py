"""A level's tutorial: steps that show part of the screen, say something about it, and move on when
the player has done what they ask, or presses Next (D-039).

A level's data may carry one: its ghosts, the parts the tutorial builds drawn faintly in their
cells, facing the way they should, and its steps. A step says a few short lines; shows a target,
or a list of them, which the overlay leaves lit while it dims the rest: an area ("board",
"parts", "bar"), a part's row, a drawer's icon, the switch, a cell, or a part of the run ("arena",
"controls", "play", "timeline", and the drawers "objectives", "inside", "score"); and waits,
until a part is placed in a cell, a part faces a way, a tool is taken, a wire runs from one cell
to another, the run starts, or the run is won. A step with no target is a hint: nothing is
dimmed. A step with nothing to wait for waits for Next, and only such a step has a Next: one
that waits for an action moves on when it is done, never before (D-048). Only Fear has one, an
introduction that builds nothing and shows once a session (D-079); every level's hints are asked
for in the Hints drawer (`hints.py`, D-078). What a tutorial that builds needs, the waits for a
part placed, turned or wired, the ghosts, the Wheel's icons as targets, stays, for chapter 0's
first two levels, which lead the player through what they teach (D-334), and is tested on the
tutorials Fear and Aggression had (`tests/data`). Skip ends a tutorial, its ghosts with it;
closed on its last card, its ghosts stay on the board (D-351). Settings' Tutorial
starts the open level's again. On a step that waits for Next, any key or click moves
on and does nothing else, but a click on Skip (D-081). While a step leads, only the means to
what it waits for go through (`allows`); the editor and the run ask before they act. Pure
Python, no pygame: what the step waits for is read from a `Context`, the screen's geometry from
the layouts.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache

from nektoids.editor import arena_layout
from nektoids.editor.layout import (
    DRAWERS,
    SCREEN,
    TURNS,
    Drawer,
    Env,
    Layout,
    LevelButton,
    Rect,
    Tool,
    View,
)
from nektoids.editor.router import Screen
from nektoids.editor.wheel import ICON, WHEEL_HEX, Slot
from nektoids.graph.board import FACING_NAMES, Board, Kind
from nektoids.graph.hexgrid import SQRT3, Cell, to_pixel
from nektoids.levels.level import known
from nektoids.levels.objectives import Outcome

CHARS = 48  # a line of the box, at most: the paragraphs are wrapped to it (D-094)
MARK = "**"  # round a game's word in a step's text: drawn in the accent (D-337)
BOX_WIDTH = 464  # CHARS characters of Plex Mono and the padding (D-055) [px]
LINE = 22  # a line of the box [px]
PAD = 14  # inside the box [px]
BUTTON = (84, 28)  # Next, and Skip left of it, at the box's foot [px]
BUTTON_GAP = 8  # between Skip and Next [px]
GAP = 14  # between the target and the box [px]
PATH_MARGIN = 20  # the hand's way from one target to the next, this wide on either side [px]
AREA = 400  # a target this wide, and half as tall, is an area: the box may lie over it [px]
GRID = 16  # the pitch of the spots tried over the screen when none beside a target is clear [px]
EDGE = 3  # an outline keeps this far inside the screen's edges [px] (D-071)
REFUSAL = "do what the box says, or press Skip"  # an action a leading step does not let through
RUN_PANELS = {"arena", "controls", "objectives", "inside", "score"}  # the rest are buttons
RUN_DRAWERS = {"inside": Drawer.INSIDE, "score": Drawer.SCORE}  # the objectives are in each


@dataclass(frozen=True)
class Ghost:
    """A part the tutorial builds, drawn faintly where it goes, facing the way it should."""

    kind: Kind
    cell: Cell
    facing: int | None


@dataclass(frozen=True)
class Step:
    say: tuple[str, ...]  # its paragraphs, each on a new line (D-094)
    show: Mapping | list | None = None  # a target or a list of them; None: a hint, nothing dimmed
    until: Mapping | list | None = None  # None: Next only; a list: all of them (D-071)

    @property
    def lines(self) -> tuple[str, ...]:
        """What the box shows: each paragraph wrapped to CHARS of what shows, ragged right
        (D-094), a game's word marked "**Editor**" keeping its marks for the accent (D-337)."""
        return tuple(line for text in self.say for line in _wrapped(text))


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
    """What a step may wait for: the board, the tool in hand, the screen, the run's end, how
    long the run has played."""

    board: Board
    tool: Tool
    screen: Screen
    outcome: Outcome | None = None
    time: float = 0.0  # the run's time [s] (D-071)
    drawer: Drawer | None = None  # the drawer open on the screen shown (D-074)


@dataclass(frozen=True)
class Live:
    """What the scene on screen shows now that its layout cannot say: in the editor, the Wheel's
    icons round the focused cell (D-070); in the run, the swimmer, a box round it (D-071)."""

    wheel: tuple[Slot, ...] = ()
    focused: Cell | None = None
    swimmer: Rect | None = None


NOTHING_LIVE = Live()  # a scene that shows nothing a step needs beyond its layout


class Tutorial:
    def __init__(
        self,
        ghosts: tuple[Ghost, ...],
        steps: tuple[Step, ...],
        ghost_wires: tuple[tuple[Cell, Cell], ...] = (),
        starts_in: Drawer | None = None,
    ) -> None:
        self.ghosts, self.steps = ghosts, steps
        self.ghost_wires = ghost_wires  # the model's wires, from a cell to a cell (D-074)
        self.starts_in = starts_in  # the editor's drawer it begins in; None: the run (D-103)
        self.index = 0
        self.skipped = False  # Skip ended it: its ghosts go with it (D-351)

    @classmethod
    def from_dict(cls, data: Mapping) -> Tutorial:
        """ValueError for a key it does not know, refused, not ignored (D-201, D-328)."""
        known(data, ("starts_in", "ghosts", "ghost_wires", "steps"), "a tutorial")
        for step in data["steps"]:
            known(step, ("say", "show", "until"), "a tutorial's step")
        steps = tuple(Step(tuple(s["say"]), s.get("show"), s.get("until")) for s in data["steps"])
        starts_in = Drawer(data["starts_in"]) if "starts_in" in data else None
        return cls(ghosts_from(data), steps, ghost_wires_from(data), starts_in)

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
    def lasting(self) -> bool:
        """Whether it is over, closed on its last card, not skipped: its ghosts stay on the board
        (D-351)."""
        return self.step is None and not self.skipped

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
        self.index, self.skipped = len(self.steps), True

    def restart(self) -> None:
        """From the first step again, finished or skipped, `follow` passing over what the board
        already holds."""
        self.index, self.skipped = 0, False

    def follow(self, context: Context) -> None:
        """On past every step whose wait is over: the player did what it asked."""
        while self.step is not None and self.step.until and met(self.step.until, context):
            self.index += 1


def panels(tutorial: Tutorial | None) -> frozenset[str]:
    """What a leading step shows, by name, drawn in the accent, the only highlight (D-050,
    D-336): an area, a drawer or a part of the run by its own name, its titles lit; a drawer's
    icon in the bar by the drawer's name, the bar lighting them all; a tab as "tab:editor"; the
    switch as "level:edit", a row of Parts as "menu:eye", a Wheel's icon as "wheel:turn left"."""
    if tutorial is None or not tutorial.leads:
        return frozenset()
    names = set()
    for one in _shows(tutorial.step):
        names.add(one.get("area") or one.get("drawer") or one.get("run") or one.get("icon"))
        for key in ("tab", "level", "menu", "wheel"):
            names.add(f"{key}:{one[key]}" if key in one else None)
    return frozenset(names - {None})


def focus_cells(tutorial: Tutorial | None) -> frozenset[Cell]:
    """The cells a step that asks for an action shows: the board fills them in the accent, and
    nothing is dimmed (D-063). A step that explains dims the rest instead (D-050)."""
    if tutorial is None or not tutorial.leads or tutorial.explains:
        return frozenset()
    show = tutorial.step.show
    shows = show if isinstance(show, list) else [show]
    return frozenset(_cell(one["cell"]) for one in shows if "cell" in one)


def drawer_for(step: Step | None, open_now: Drawer | None = None) -> Drawer | None:
    """The drawer a step's targets are in, which it opens as it shows: the drawer it explains;
    Parts for a part's row; for a Wheel's icon, Tools or Parts, whichever is open (`open_now`),
    else Tools; the run's drawer it explains; None if it needs none (D-051, D-057, D-070)."""
    shows = _shows(step)
    explained = next((Drawer(one["drawer"]) for one in shows if "drawer" in one), None)
    awaited = {Drawer(u["drawer"]) for u in _conditions(step) if "drawer" in u}
    if explained is not None and explained not in awaited:  # the player opens that one
        return explained
    if any("menu" in one or one.get("area") == "parts" for one in shows):
        return Drawer.PARTS
    if shows_wheel(step):  # the Wheel is at the foot of both
        return open_now if open_now in (Drawer.TOOLS, Drawer.PARTS) else Drawer.TOOLS
    return next((RUN_DRAWERS[one["run"]] for one in shows if one.get("run") in RUN_DRAWERS), None)


def shows_wheel(step: Step | None) -> bool:
    """Whether a step shows one of the Wheel's icons: the Wheel, folded, unfolds for it."""
    return any("wheel" in one for one in _shows(step))


def _conditions(step: Step | None) -> list:
    """What a step waits for, one or several, as a list."""
    until = None if step is None else step.until
    return [] if not until else until if isinstance(until, list) else [until]


def _shows(step: Step | None) -> list:
    shows = [] if step is None or step.show is None else step.show
    return shows if isinstance(shows, list) else [shows]


def allows(step: Step | None, action: Action) -> bool:
    """Whether `step` lets `action` through (D-048). No step, or a hint, lets all through. A step
    that leads lets through only the means to what it waits for: picking that part (from the
    menu or by its key) and placing it on that cell; moving a part, to move one there (D-338);
    a turn tool, or L and R, on that part; that tool; the Wire tool and that wire, either way
    round (D-026); Run. While it waits for a win, or
    for the run to play a while, running, playing and going back to edit. A step that waits for
    several things lets through the means to any of them (D-071). A step that waits for Next
    lets nothing through. Zoom, the view's centre, info boxes and folding the menu change none
    of this, and are not asked."""
    if step is None or step.show is None:
        return True
    if isinstance(step.until, list):
        return any(_allows(until, action) for until in step.until)
    return _allows(step.until or {}, action)


def _allows(until: Mapping, action: Action) -> bool:
    verb = action.verb
    if "placed" in until:
        kind, cell = Kind(until["placed"]["kind"]), _cell(until["placed"]["cell"])
        return (
            (verb == "pick" and action.kind is kind)
            or (verb == "tool" and action.tool is Tool.ADD)
            or (verb == "place" and action.kind is kind and action.cell == cell)
        )
    if "moved" in until:  # a part moved there: the Move tool, a drag (D-338)
        return (verb == "tool" and action.tool is Tool.MOVE) or verb == "move"
    if "facing" in until:
        cell = _cell(until["facing"]["cell"])
        return (verb == "tool" and action.tool in TURNS) or (verb == "turn" and action.cell == cell)
    if "tool" in until:
        return verb == "tool" and action.tool is Tool(until["tool"])
    if "wired" in until:
        ends = {_cell(until["wired"]["from"]), _cell(until["wired"]["to"])}
        wire = verb == "wire" and {action.cell, action.other} == ends
        return wire or (verb == "tool" and action.tool is Tool.WIRE)
    if "screen" in until:  # the way there: Run, or back to the editor (D-060)
        return verb == {Screen.RUN: "run", Screen.EDIT: "edit"}.get(Screen(until["screen"]))
    if "drawer" in until:  # a drawer to open: Diagnostic asks to (D-058, D-074)
        return verb == "view"
    if "outcome" in until or "time" in until:  # the run and its controls, and back to the editor
        return verb in ("run", "edit", "play")
    return False


def met(until: Mapping | list, context: Context) -> bool:
    """Whether what a step waits for has happened: each of them, for a list (D-071)."""
    if isinstance(until, list):
        return all(met(one, context) for one in until)
    board = context.board
    if "time" in until:  # the run has played this long [s]
        return context.time >= until["time"]
    if "drawer" in until:  # that drawer is open (D-074)
        return context.drawer is Drawer(until["drawer"])
    if "placed" in until or "moved" in until:  # a part of that kind on that cell (D-338)
        where = until.get("placed") or until["moved"]
        node = board.node_at(_cell(where["cell"]))
        return node is not None and node.kind is Kind(where["kind"])
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


def target_rects(
    show: Mapping | list | None,
    screen: Screen,
    layout: Layout,
    view: View,
    live: Live = NOTHING_LIVE,
) -> list:
    """Every target a step shows that is on the screen now open, in the step's order."""
    return [rect for rect, _ in target_spots(show, screen, layout, view, live)]


def target_spots(
    show: Mapping | list | None,
    screen: Screen,
    layout: Layout,
    view: View,
    live: Live = NOTHING_LIVE,
) -> list:
    """The same, each with the shape the overlay outlines: "disc" round a cell, "icon" round
    a Wheel's icon, "panel" for an area or a part of the run view, on its own edges, a `Page`
    for a page and its tab, a `Docked` for a drawer and its icon, "spot" round anything else, a
    button, a row, the swimmer (D-048, D-050, D-062, D-070, D-071). `live`: what the scene shows
    that its layout cannot say."""
    shows = [] if show is None else show if isinstance(show, list) else [show]
    cells = frozenset(_cell(one["cell"]) for one in shows if "cell" in one)
    running, editing = screen is Screen.RUN, screen is Screen.EDIT
    spots = []
    for one in shows:
        if one.get("run") == "arena" and running and layout.env is Env.RUN:
            spots += _page(layout, Env.RUN)
        elif one.get("page") == "editor":  # the Editor tab, the level's line, the board
            spots += _page(layout, Env.EDITOR) if editing and layout.env is Env.EDITOR else []
        elif one.get("run") == "swimmer":  # a box round it, nothing else (D-071)
            spots.append((live.swimmer if running else None, "spot"))
        elif one.get("area") == "bar":  # its two groups of icons, each on its own (D-080)
            on = running or editing
            spots += [(group, "spot") for group in _bar_groups(layout)] if on else []
        elif "drawer" in one:  # the drawer joined to its icon in the bar (D-071)
            spots.append(_docked(layout, Drawer(one["drawer"])))
        elif "wheel" in one:
            on = editing and (not cells or live.focused in cells)
            icon = _wheel_icon(one["wheel"], live.wheel) if on else None
            spots.append((icon, "icon"))
            if icon is not None and (_wheel_area(layout), "none") not in spots:
                spots.append((_wheel_area(layout), "none"))  # the box keeps clear of the Wheel
        else:
            spots.append((target_rect(one, screen, layout, view), _shape(one)))
    return [(rect, shape) for rect, shape in spots if rect is not None]


@dataclass(frozen=True)
class Page:
    """A page as a step explains it, the run's (D-062) or the editor's (D-071): its tab on top,
    then the level's line and the arena or the board, outlined as one shape."""

    tab: Rect


@dataclass(frozen=True)
class Docked:
    """A drawer as a step explains it (D-071): the drawer, and its icon in the bar beside it,
    outlined as one shape."""

    icon: Rect


def _page(layout: Layout, env: Env) -> list:
    """A page, its tab, the level's line and the main screen, and its header, the tabs and the
    level's line, which the box keeps clear of."""
    x, _, w, _ = layout.board_area
    bottom = layout.board_area[1] + layout.board_area[3]
    page, header = (x, 0, w, bottom), (x, 0, w, layout.board_area[1])
    return [(page, Page(dict(layout.tabs)[env.value])), (header, "none")]


def _docked(layout: Layout, drawer: Drawer) -> tuple:
    """The drawer, while it is open, with its icon in the bar: a `Docked` shape; while it is
    closed, its icon alone, to open it (D-074); not in this environment's bar, nothing."""
    icon = dict(layout.drawer_buttons).get(drawer)
    if icon is None:
        return (None, "spot")
    return (layout.drawer_area, Docked(icon)) if layout.drawer is drawer else (icon, "spot")


def _bar_groups(layout: Layout) -> tuple[Rect, Rect]:
    """The activity bar's two groups of icons: the drawers at its top; at its foot, the drawers
    there and the switch to the other environment."""
    top = set(DRAWERS[layout.env])
    upper = [rect for drawer, rect in layout.drawer_buttons if drawer in top]
    lower = [rect for drawer, rect in layout.drawer_buttons if drawer not in top]
    return _around(upper), _around([*lower, *(rect for _, rect in layout.level_buttons)])


def _around(rects: list[Rect]) -> Rect:
    """The smallest rectangle round `rects`."""
    left, top = min(r[0] for r in rects), min(r[1] for r in rects)
    right, bottom = max(r[0] + r[2] for r in rects), max(r[1] + r[3] for r in rects)
    return (left, top, right - left, bottom - top)


def _shape(show: Mapping) -> str:
    if "cell" in show:
        return "disc"
    if "wheel" in show:
        return "icon"
    if "area" in show or show.get("run") in RUN_PANELS:
        return "panel"
    return "spot"


def target_rect(show: Mapping | None, screen: Screen, layout: Layout, view: View) -> Rect | None:
    """The part of the screen a step shows, in the view now open; None if it is not there."""
    if show is None:
        return None
    if "run" in show:
        return _run_target(show["run"], layout) if screen is Screen.RUN else None
    if "tab" in show:  # over the main screen, in the editor and in the run alike
        return dict(layout.tabs)[show["tab"]] if screen in (Screen.EDIT, Screen.RUN) else None
    if "level" in show:  # the switch, Run in the editor, Editor in the run
        on = screen in (Screen.EDIT, Screen.RUN)
        return dict(layout.level_buttons).get(LevelButton(show["level"])) if on else None
    if "icon" in show:  # a drawer's icon in the bar, alone: it opens nothing (D-079)
        on = screen in (Screen.EDIT, Screen.RUN)
        return dict(layout.drawer_buttons).get(Drawer(show["icon"])) if on else None
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
    if "cell" in show:
        x, y = to_pixel(_cell(show["cell"]), view.size, view.origin)
        half_w, half_h = SQRT3 / 2 * view.size, view.size
        return (round(x - half_w), round(y - half_h), round(2 * half_w), round(2 * half_h))
    raise ValueError(f"a step cannot show {dict(show)!r}")


def _wheel_area(layout: Layout) -> Rect:
    """The Wheel at the drawer's foot, its title and the rule over it included (D-071)."""
    x, top, w, _ = layout.wheel_fold
    _, y, _, h = layout.wheel_view
    return (x, top - 4, w, y + h - top + 4)


def _wheel_icon(name: str, wheel: tuple[Slot, ...]) -> Rect | None:
    """A Wheel's icon, a part or an action, by its name, while the Wheel shows it on its rim
    (D-070): the square round its disc. Not on the rim, or not offered: not on screen."""
    what = Kind(name) if name in {kind.value for kind in Kind} else Tool(name)
    slot = next((s for s in wheel if s.what is what and not s.depth), None)
    if slot is None:
        return None
    r, (x, y) = ICON * WHEEL_HEX, slot.at
    return (round(x - r), round(y - r), round(2 * r), round(2 * r))


def _run_target(name: str, layout: Layout) -> Rect | None:
    """A part of the run in its frame (D-057): a drawer, or its icon while it is closed."""
    if layout.env is not Env.RUN:
        return None
    if name in RUN_DRAWERS:
        drawer = RUN_DRAWERS[name]
        return (
            layout.drawer_area if layout.drawer is drawer else dict(layout.drawer_buttons)[drawer]
        )
    if name == "objectives":  # at the foot of the open drawer (D-065)
        return layout.goal_area
    if name == "play":
        return dict(arena_layout.control_rects(layout))[arena_layout.ArenaButton.PLAY]
    if name == "timeline":
        return arena_layout.timeline_rect(layout)
    return {"arena": layout.board_area, "controls": layout.controls_area}[name]


def box_rect(
    targets: list, lines: int, hint_at: Rect, before: list = (), clear_of: list = ()
) -> Rect:
    """The step's box. A hint's, with no target, at the foot of `hint_at` (the board or the
    arena). A leading step's keeps clear of its targets, of the hand's way from each to the
    next, of the same for the step `before`, the work just done (D-048), and of `clear_of`,
    what it must not hide, the parts on the board (D-103): beside a target,
    the last first, trying its right, its left, under it, over it; else the clear spot of a
    grid over the screen nearest the last target. Each spot is brought onto the screen. An area
    (the board, the arena) is too big to keep clear of: the box may lie over part of it."""
    height = 2 * PAD + lines * LINE + 8 + BUTTON[1]
    if not targets:
        x, y, w, h = hint_at
        return (x + 16, y + h - height - 16, BOX_WIDTH, height)
    parts = tuple(map(tuple, clear_of))
    return _placed(tuple(map(tuple, targets)), tuple(map(tuple, before)), height, parts)


@lru_cache(maxsize=32)  # drawn every frame; the grid is slow to search
def _placed(targets: tuple, before: tuple, height: int, clear_of: tuple = ()) -> Rect:
    kept, kept_before = _narrow(targets), _narrow(before)  # an area cannot be cleared
    rects, paths = (*kept, *kept_before, *clear_of), (*_paths(kept), *_paths(kept_before))

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


def is_area(rect: Rect) -> bool:
    """A target too big to keep clear of, the board or the arena; the run's controls, wide but
    low, are not one (D-057)."""
    return rect[2] >= AREA and rect[3] >= AREA // 2


def _narrow(rects: tuple) -> tuple:
    return tuple(rect for rect in rects if not is_area(rect))


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
    the run sees it: "skip" on Skip; on a step that waits for Next, "next" at any other key or
    click, which does nothing else (D-081); otherwise None, and the press goes on."""
    last = tutorial.index == len(tutorial.steps) - 1
    if click is not None and not last and _inside(skip_rect(box), click):
        return "skip"
    return "next" if tutorial.waits_for_next else None


def _inside(rect: Rect, point: tuple[int, int]) -> bool:
    x, y, w, h = rect
    return x <= point[0] < x + w and y <= point[1] < y + h


def skip_rect(box: Rect) -> Rect:
    """Skip, left of Next."""
    x, y, w, h = next_rect(box)
    return (x - BUTTON_GAP - w, y, w, h)


def outline_kept(rect: Rect) -> Rect:
    """`rect` cut to the screen less EDGE all round: the outline round a target at the screen's
    edge, a tab at its top, the switch by its left, the objectives at its foot, stays on it and
    clear of its first and last rows and columns (D-071)."""
    x, y, w, h = rect
    left, top = max(x, EDGE), max(y, EDGE)
    right, bottom = min(x + w, SCREEN[0] - EDGE), min(y + h, SCREEN[1] - EDGE)
    return (left, top, right - left, bottom - top)


def ghosts_from(data: Mapping) -> tuple[Ghost, ...]:
    """The ghosts of a tutorial's data, or of a hint's shadow (D-078): each its kind, its cell
    and the way it faces, if it turns."""
    return tuple(
        Ghost(
            Kind(g["kind"]),
            _cell(g["cell"]),
            FACING_NAMES.index(g["facing"]) if g.get("facing") else None,
        )
        for g in data.get("ghosts", ())
    )


def ghost_wires_from(data: Mapping) -> tuple[tuple[Cell, Cell], ...]:
    """The ghost wires of a tutorial's data, or of a hint's shadow: each from a cell to a cell."""
    return tuple((_cell(w["from"]), _cell(w["to"])) for w in data.get("ghost_wires", ()))


def _wrapped(text: str) -> list[str]:
    """`text` wrapped to CHARS, word by word, a word's length what shows of it, its marks not
    counted (D-337); a marked phrase may run on to the next line, its marks with it."""
    lines, line, size = [], [], 0
    for word in text.split():
        length = len(word.replace(MARK, ""))
        if line and size + 1 + length > CHARS:
            lines.append(" ".join(line))
            line, size = [], 0
        size += length + (1 if line else 0)
        line.append(word)
    return [*lines, " ".join(line)] if line else lines


def shown(line: str) -> str:
    """What shows of a line of a step: its marks taken out."""
    return line.replace(MARK, "")


def runs(line: str, marked: bool = False) -> list[tuple[str, bool]]:
    """A line of a step as runs of text, each marked or not, `marked` if the line starts inside
    a marked phrase; the marks toggle it (D-337)."""
    found = []
    for k, text in enumerate(line.split(MARK)):
        marked = marked if k == 0 else not marked
        if text:
            found.append((text, marked))
    return found


def _cell(data) -> Cell:
    return (int(data[0]), int(data[1]))
