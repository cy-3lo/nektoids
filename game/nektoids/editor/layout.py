"""Where everything sits on the 960 x 640 screen, editor or run, and what is under a pixel (D-051).

- Left, the activity bar: an icon for each drawer, Parts, Tools and Navigator at the top in the
  editor, Objectives, Inside, Score and Navigator in the run; Settings and Chapters at its foot,
  over the accented switch to the other environment (`Env`).
- Beside it, one drawer at a time, or none: its title, then rows all alike (icon, name, an
  info disc, then a count or a key). Parts: the groups (sensors, operators, actuators) that fold
  under their title, only the parts the level hands out; Tools: the tools, Edit (undo, redo),
  File (save and load, inactive until saving exists); Navigator: the view's buttons; Settings:
  what the player sets (D-054); Chapters: the levels, then the sandbox, which replaces the
  full-screen map. An arrow on the drawer's edge folds it.
- The rest is the main screen: the tabs over it (Editor, Run), the level's caption under them,
  then the board's hex grid, or in the run the arena with its controls under it; one status
  line at its foot. A drawer opening pushes the main screen aside.

The View says how big a hex is and where the grid sits in the board's area; zoom and pan change
only the View (D-013). Plain numbers and tuples, no pygame, so hit-testing is testable headless.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from nektoids.graph.board import Kind
from nektoids.graph.hexgrid import SQRT3, Cell, from_pixel, to_pixel

Rect = tuple[int, int, int, int]  # x, y, width, height [px]

SCREEN = (960, 640)  # [px]
BAR_WIDTH = 48  # the activity bar, down the left edge [px]
BAR_BUTTON = 40  # an icon's square in it [px]
BAR_PITCH = 48  # from one icon to the next [px]
SWITCH = 36  # the accented switch at its foot, square [px]; the main view's buttons too
DRAWER_WIDTH = 248  # [px]
DRAWER_TOP = 40  # the first row or section title, under the drawer's own title [px]
ROW_HEIGHT = 40  # a drawer's row [px]
OVERVIEW_HEIGHT = 168  # Navigator's overview, under its rows [px]
ZOOM_BUTTON = 28  # zoom out and in, either end of the zoom bar, under the overview [px]
FOOT_MARGIN = 6  # under the objectives, at the drawer's foot [px]
GOAL_HEIGHT = 48  # an objective's row in the run: its name, then its bar and count [px]
ROW_PITCH = 46  # from one row to the next [px]
ROW_INSET = 12  # a row's sides from the drawer's [px]
TITLE_HEIGHT = 24  # a group's or a section's title in a drawer [px]
SECTION_GAP = 6  # before a section title or a group [px]
INFO_AT = 156  # a row's info disc: its centre, this far from the row's left [px]
INFO_HIT = 20  # ... and the square a click on it falls in [px]
HANDLE = (14, 44)  # the arrow on the drawer's edge that folds it [px]
TABS_HEIGHT = 32  # the strip of tabs over the board [px]
CAPTION_HEIGHT = 26  # under the tabs, inside the Editor's: the level's title and spec [px]
TOP = TABS_HEIGHT + CAPTION_HEIGHT  # the board's top edge [px]
TAB_WIDTHS = (84, 64)  # Editor, Run [px]
STATUS_HEIGHT = 28  # [px]
CONTROLS_HEIGHT = 48  # the run's controls, a strip under the arena [px]
MARGIN = 16  # [px]
BUTTON = 40  # a palette button's side, in the run view [px]
PALETTE_TITLE = 24  # a section's title, in the run view and the drawers [px]
HEX_SIZE = 40.0  # centre-to-corner size of a hex in the default view [px]
MIN_HEX, MAX_HEX = 20.0, 80.0  # zoom limits [px]
ZOOM_STEP = 1.25  # hex size factor per click

MENU_GROUPS: tuple[tuple[str, tuple[Kind, ...]], ...] = (
    ("Sensors", (Kind.EYE, Kind.SOURCE)),
    ("Operators", (Kind.DOUBLE, Kind.HALVE, Kind.SUM, Kind.DIFFERENCE)),
    ("Actuators", (Kind.THRUSTER,)),
)


class Tool(Enum):
    ADD = "add"
    WIRE = "wire"
    MOVE = "move"
    DELETE = "delete"
    TURN_LEFT = "turn left"  # counter-clockwise, 60° a click
    TURN_RIGHT = "turn right"  # clockwise
    PAN = "pan"  # moves the view, not a component; the hand among the view buttons


PALETTE_TOOLS = (Tool.ADD, Tool.WIRE, Tool.MOVE, Tool.DELETE, Tool.TURN_LEFT, Tool.TURN_RIGHT)
TURNS = {Tool.TURN_LEFT: 1, Tool.TURN_RIGHT: -1}  # hex directions run counter-clockwise


class EditButton(Enum):
    UNDO = "undo"
    REDO = "redo"


class LevelButton(Enum):  # the accented switch at the bar's foot, to the other environment
    RUN = "run"  # in the editor: the board, swimming in its arena
    EDIT = "edit"  # in the run: back to the board as it was left


class FileButton(Enum):  # inactive: saving is not in the game yet
    SAVE = "save"
    LOAD = "load"


class ViewButton(Enum):
    ZOOM_IN = "zoom in"
    ZOOM_OUT = "zoom out"
    PAN = "pan"
    CENTRE = "centre"  # bring cell (0, 0) back to the middle, at the same zoom
    RAYS = "rays"  # the run's only: the light's rays, shown or not


class Drawer(Enum):  # D-051
    PARTS = "parts"  # the parts the level hands out, and what each does
    FILES = "files"  # this session's winning boards, to put one back (D-059)
    SENSE = "sense"  # the level, small, with the probe the Run preview runs at (D-058)
    INSIDE = "inside"  # the run's: the swimmer's wiring, live
    SCORE = "score"  # the run's: the level's wins this session
    NAVIGATOR = "navigator"  # zoom, hand, centre; the rays in the run
    SETTINGS = "settings"  # at the bar's foot: what the player sets (D-054)
    CHAPTERS = "chapters"  # at the bar's foot, over the switch: the levels and the sandbox


class MainView(Enum):  # what the editor's main screen shows (D-051, D-058)
    DIAGRAM = "diagram"  # the board on its hex grid, to edit
    PREVIEW = "preview"  # the Run preview: the board as it runs, where the probe stands


class Env(Enum):  # the environments, each a tab over the main screen (D-051)
    EDITOR = "editor"
    RUN = "run"


SENSE_MAP: Rect = (  # the level, small, in Sense, under its label: a square [px]
    BAR_WIDTH + MARGIN,
    DRAWER_TOP + TITLE_HEIGHT + 4,
    DRAWER_WIDTH - 2 * MARGIN,
    DRAWER_WIDTH - 2 * MARGIN,
)
DRAWERS = {  # each environment's drawers, in the bar's order from the top
    Env.EDITOR: (Drawer.PARTS, Drawer.FILES, Drawer.SENSE, Drawer.NAVIGATOR),  # tools in the ring
    Env.RUN: (Drawer.INSIDE, Drawer.SCORE, Drawer.NAVIGATOR),  # the objectives under each
}
FOOT = (Drawer.SETTINGS, Drawer.CHAPTERS)  # the drawers whose icons sit at the bar's foot
SWITCH_TO = {Env.EDITOR: LevelButton.RUN, Env.RUN: LevelButton.EDIT}


@dataclass(frozen=True)
class WinRow:
    """A row of Files: the level's win `index` this session, the fastest first (D-059)."""

    index: int


@dataclass(frozen=True)
class Goal:
    """A row of Objectives: the level's objective `index`, or, for None, the time left."""

    index: int | None


class Setting(Enum):  # the Settings drawer's rows (D-054)
    FAST = "fast"  # fast forward's speed
    HINTS = "hints"  # keys on the rows and in the tooltips
    TUTORIAL = "tutorial"  # Fear's tutorial again
    SOUND = "sound"  # locked: there is no sound yet
    MUSIC = "music"


# Shortcut keys, matched on the character typed (so they follow the keyboard layout) and shown
# in the tooltips. L and R turn left and right, here and in the arena view (D-025).
TOOL_KEYS = {
    Tool.ADD: "A",
    Tool.WIRE: "W",
    Tool.MOVE: "M",
    Tool.DELETE: "D",
    Tool.TURN_LEFT: "L",
    Tool.TURN_RIGHT: "R",
}
VIEW_KEYS = {
    ViewButton.ZOOM_IN: "+",
    ViewButton.ZOOM_OUT: "-",
    ViewButton.PAN: "H",
    ViewButton.CENTRE: "C",
    ViewButton.RAYS: "X",  # as in x-rays: L turns left (D-025)
}
# With Ctrl (Cmd on a Mac), matched on the key code, which follows the layout; Ctrl+Y redoes too.
EDIT_KEYS = {EditButton.UNDO: "Ctrl+Z", EditButton.REDO: "Ctrl+Y"}
# On the physical key: Space runs, as the arena's play (D-021); Tab, the levels, as in F3.
LEVEL_KEYS = {LevelButton.RUN: "Space", LevelButton.EDIT: "Esc"}
DRAWER_KEYS = {Drawer.CHAPTERS: "Tab"}  # Tab opens the levels, as it opened the map
KEY_ALIASES = {"=": "+", "_": "-"}  # the same keys, shift or not, on most layouts


@dataclass(frozen=True)
class Layout:
    env: Env  # the editor's frame, or the run's
    kinds: frozenset[Kind]  # the parts the level hands out: the only ones Parts shows
    drawer: Drawer | None  # the drawer open, if one is
    chapter: int  # how many levels the chapter has: Chapters' rows, then the sandbox's
    bar_area: Rect
    drawer_buttons: tuple[tuple[Drawer, Rect], ...]  # the bar's icons, top down
    level_buttons: tuple[tuple[LevelButton, Rect], ...]  # at the bar's foot: Chapters, the switch
    drawer_area: Rect | None
    fold_handle: Rect | None  # the arrow on the drawer's edge
    drawer_title_at: tuple[int, int]
    section_titles: tuple[tuple[str, Rect], ...]  # Tools, Edit, File; View
    group_titles: tuple[tuple[str, Rect], ...]  # Parts: click one to fold or unfold its group
    menu_items: tuple[tuple[Kind, Rect], ...]  # Parts' rows
    edit_buttons: tuple[tuple[EditButton, Rect], ...]  # undo, redo: the main screen's corner
    file_buttons: tuple[tuple[FileButton, Rect], ...]  # at Files' foot, inactive for now
    view_buttons: tuple[tuple[ViewButton, Rect], ...]  # Navigator's rows
    goal_rows: tuple[tuple[Goal, Rect], ...]  # in the run: each objective, the time left
    goal_area: Rect | None  # ... at the foot of the open drawer, whichever it is (D-065)
    win_rows: tuple[tuple[WinRow, Rect], ...]  # Files' rows: this session's wins of the level
    setting_rows: tuple[tuple[Setting, Rect], ...]  # Settings' rows
    chapter_rows: tuple[tuple[int, Rect], ...]  # Chapters' rows: a level's index; the sandbox last
    info_buttons: tuple[tuple[object, Rect], ...]  # one per row: what its info box tells of
    tabs: tuple[tuple[str, Rect], ...]  # "editor", "run"
    board_area: Rect  # the main screen: the board, or in the run the arena
    controls_area: Rect | None  # in the run, a strip under the arena: play, a step, the timeline
    view_switch: tuple[tuple[MainView, Rect], ...]  # in the editor, over the main screen's corner
    overview: Rect | None  # Navigator's: the whole board, or level, small (D-060)
    zoom_buttons: tuple[tuple[ViewButton, Rect], ...]  # under it, out and in (D-065)
    zoom_bar: Rect | None  # between them: the zoom, from the farthest to the nearest
    caption_at: tuple[int, int]  # top-left corner of the level's title and spec, under the tabs
    status_at: tuple[int, int]  # top-left corner of the status line


@dataclass(frozen=True)
class View:
    """How the grid is seen: the size of a hex and where cell (0, 0) sits on screen."""

    size: float  # centre-to-corner [px]
    origin: tuple[float, float]  # pixel centre of cell (0, 0) [px]


def make_layout(
    drawer: Drawer | None = Drawer.PARTS,
    folded: frozenset[str] = frozenset(),
    kinds: frozenset[Kind] = frozenset(Kind),
    chapter: int = 0,
    env: Env = Env.EDITOR,
    goals: int = 0,
    wins: int = 0,
) -> Layout:
    """The bar, the open drawer's rows and the main screen, for the editor or the run. folded:
    Parts' groups shown closed; kinds: the parts the level hands out, the only ones Parts shows
    (D-039); chapter: how many levels Chapters lists, before the sandbox; goals: how many
    objectives the level has, at the foot of each of the run's drawers, before the time left;
    wins: how many wins of the level Files lists."""
    width, height = SCREEN
    bar = (0, 0, BAR_WIDTH, height)
    side = (BAR_WIDTH - BAR_BUTTON) // 2
    top = DRAWERS[env]
    switch = ((BAR_WIDTH - SWITCH) // 2, height - SWITCH - 12, SWITCH, SWITCH)
    drawer_buttons = tuple(
        (d, (side, BAR_PITCH // 2 + 6 + k * BAR_PITCH - BAR_BUTTON // 2, BAR_BUTTON, BAR_BUTTON))
        for k, d in enumerate(top)
    ) + tuple(  # at the foot, over the switch, from the bottom up: Chapters, then Settings
        (d, (side, switch[1] - (len(FOOT) - k) * BAR_PITCH, BAR_BUTTON, BAR_BUTTON))
        for k, d in enumerate(FOOT)
    )
    left = BAR_WIDTH + (DRAWER_WIDTH if drawer is not None else 0)  # the board's left edge
    rows = _Rows()
    if drawer is Drawer.PARTS:
        rows.parts(folded, kinds)
    elif drawer is Drawer.NAVIGATOR:
        rows.view(env)
    elif drawer is Drawer.SENSE:
        rows.label("The level")
    elif drawer is Drawer.FILES:
        rows.label("Wins this session")
        for k in range(wins):
            rows._row(WinRow(k))
        rows.y = height - FOOT_MARGIN - TITLE_HEIGHT - len(FileButton) * ROW_PITCH  # its foot
        rows.label("File")
        for what in FileButton:
            rows._row(what)
    elif drawer is Drawer.INSIDE:  # a drawing under its title, not rows
        rows.label("The swimmer's wiring")
    elif drawer is Drawer.SCORE:
        rows.label("Your wins")
    elif drawer is Drawer.SETTINGS:
        rows.settings()
    elif drawer is Drawer.CHAPTERS:
        rows.chapters(chapter)
    goal_area = None
    if env is Env.RUN and drawer is not None:  # the objectives, at the foot of every drawer
        foot = _Rows()
        height_needed = TITLE_HEIGHT + (goals + 1) * (GOAL_HEIGHT + ROW_PITCH - ROW_HEIGHT)
        foot.y = height - FOOT_MARGIN - height_needed
        goal_area = (BAR_WIDTH, foot.y - 8, DRAWER_WIDTH, height - foot.y + 8)
        foot.label("Objectives")
        foot.goals(goals)
        rows.items += foot.items
        rows.sections += foot.sections
    tabs, x = [], left
    for name, w in zip(("editor", "run"), TAB_WIDTHS, strict=True):
        tabs.append((name, (x, 0, w, TABS_HEIGHT)))
        x += w
    open_ = drawer is not None
    main = height - STATUS_HEIGHT - (CONTROLS_HEIGHT if env is Env.RUN else 0)  # its foot
    return Layout(
        env=env,
        kinds=kinds,
        drawer=drawer,
        chapter=chapter,
        bar_area=bar,
        drawer_buttons=drawer_buttons,
        level_buttons=((SWITCH_TO[env], switch),),
        drawer_area=(BAR_WIDTH, 0, DRAWER_WIDTH, height) if open_ else None,
        fold_handle=(left - 1, height // 2 - HANDLE[1] // 2, *HANDLE) if open_ else None,
        drawer_title_at=(BAR_WIDTH + MARGIN, 9),
        section_titles=tuple(rows.sections),
        group_titles=tuple(rows.groups),
        menu_items=tuple(rows.of(Kind)),
        edit_buttons=tuple(
            (button, (width - 8 - (5 - k) * (SWITCH + 6) - 8, TOP + 8, SWITCH, SWITCH))
            for k, button in enumerate(EditButton)
        )
        if env is Env.EDITOR
        else (),
        file_buttons=tuple(rows.of(FileButton)),
        view_buttons=tuple(rows.of(ViewButton)),
        goal_rows=tuple(rows.of(Goal)),
        goal_area=goal_area,
        win_rows=tuple(rows.of(WinRow)),
        setting_rows=tuple(rows.of(Setting)),
        chapter_rows=tuple(rows.of(int)),
        info_buttons=tuple((what, _info_disc(what, rect)) for what, rect in rows.items),
        tabs=tuple(tabs),
        board_area=(left, TOP, width - left, main - TOP),
        controls_area=(left, main, width - left, CONTROLS_HEIGHT) if env is Env.RUN else None,
        overview=rows.overview,
        zoom_buttons=tuple(rows.zoom_buttons),
        zoom_bar=rows.zoom_bar,
        view_switch=tuple(
            (view, (width - 8 - (2 - k) * (SWITCH + 6) + 6, TOP + 8, SWITCH, SWITCH))
            for k, view in enumerate(MainView)
        )
        if env is Env.EDITOR
        else (),
        caption_at=(left + MARGIN, TABS_HEIGHT + 5),
        status_at=(left + MARGIN, height - STATUS_HEIGHT + 6),
    )


class _Rows:
    """A drawer's rows and titles, laid out from the top down."""

    def __init__(self) -> None:
        self.y = DRAWER_TOP
        self.items: list[tuple[object, Rect]] = []
        self.sections: list[tuple[str, Rect]] = []
        self.groups: list[tuple[str, Rect]] = []
        self.overview: Rect | None = None
        self.zoom_buttons: list[tuple[ViewButton, Rect]] = []
        self.zoom_bar: Rect | None = None

    def of(self, kind: type) -> list:
        return [(what, rect) for what, rect in self.items if isinstance(what, kind)]

    def _title(self, title: str, into: list) -> None:
        into.append((title, (BAR_WIDTH + MARGIN, self.y, DRAWER_WIDTH - 2 * MARGIN, TITLE_HEIGHT)))
        self.y += TITLE_HEIGHT

    def _row(self, what: object, height: int = ROW_HEIGHT) -> None:
        width = DRAWER_WIDTH - 2 * ROW_INSET
        self.items.append((what, (BAR_WIDTH + ROW_INSET, self.y, width, height)))
        self.y += height + ROW_PITCH - ROW_HEIGHT

    def parts(self, folded: frozenset[str], kinds: frozenset[Kind]) -> None:
        for title, group in MENU_GROUPS:
            shown = [kind for kind in group if kind in kinds]
            if not shown:
                continue  # a group with nothing in this level: no title either
            self._title(title, self.groups)
            for kind in () if title in folded else shown:
                self._row(kind)
            self.y += SECTION_GAP

    def view(self, env: Env) -> None:
        """The view's options as rows, the rays in the run; then the overview and, under it,
        the zoom: a bar between its two buttons (D-065)."""
        if env is Env.RUN:
            self._title("View", self.sections)
            self._row(ViewButton.RAYS)
            self.y += SECTION_GAP
        self._title("Overview", self.sections)
        x, width = BAR_WIDTH + MARGIN, DRAWER_WIDTH - 2 * MARGIN
        self.overview = (x, self.y + 4, width, OVERVIEW_HEIGHT)
        top = self.y + 4 + OVERVIEW_HEIGHT + 10
        self.zoom_buttons = [
            (ViewButton.ZOOM_OUT, (x, top, ZOOM_BUTTON, ZOOM_BUTTON)),
            (ViewButton.ZOOM_IN, (x + width - ZOOM_BUTTON, top, ZOOM_BUTTON, ZOOM_BUTTON)),
        ]
        bar = width - 2 * (ZOOM_BUTTON + 8)
        self.zoom_bar = (x + ZOOM_BUTTON + 8, top + (ZOOM_BUTTON - 16) // 2, bar, 16)

    def label(self, title: str) -> None:
        self._title(title, self.sections)

    def goals(self, n: int) -> None:
        for k in [*range(n), None]:
            self._row(Goal(k), GOAL_HEIGHT)

    def settings(self) -> None:
        """Its rows one under the other, no titles (D-067)."""
        for what in Setting:
            self._row(what)

    def chapters(self, levels: int) -> None:
        self._title("Chapter 1: light", self.sections)
        for k in range(levels):
            self._row(k)
        self.y += SECTION_GAP
        self._title("Free play", self.sections)
        self._row(levels)  # the sandbox


def _info_disc(what: object, row: Rect) -> Rect:
    """Where a row's info disc catches a click: INFO_AT into the row, on its middle; an
    objective's, whose count and bar run along its second line, at its first line's end."""
    x, y, w, h = row
    cx, cy = (x + w - 16, y + 14) if isinstance(what, Goal) else (x + INFO_AT, y + h // 2)
    return (cx - INFO_HIT // 2, cy - INFO_HIT // 2, INFO_HIT, INFO_HIT)


def win_row_at(layout: Layout, point: tuple[int, int]) -> int | None:
    """The win whose row in Files is under `point`: its index, the fastest first."""
    return next((w.index for w, rect in layout.win_rows if contains(rect, point)), None)


def goal_row_at(layout: Layout, point: tuple[int, int]) -> Goal | None:
    return next((g for g, rect in layout.goal_rows if contains(rect, point)), None)


def palette_target_at(
    layout: Layout, point: tuple[int, int]
) -> Drawer | LevelButton | MainView | EditButton | str | None:
    """What a tooltip would name under `point`: an icon of the bar, a main view's button, undo or
    redo, or the other environment's tab, by its name, which says what the switch says (D-060)."""
    tab = tab_at(layout, point)
    return (
        drawer_button_at(layout, point)
        or level_button_at(layout, point)
        or main_view_at(layout, point)
        or edit_button_at(layout, point)
        or (tab if tab is not None and tab != layout.env.value else None)
    )


def main_view_at(layout: Layout, point: tuple[int, int]) -> MainView | None:
    return next((v for v, rect in layout.view_switch if contains(rect, point)), None)


def drawer_button_at(layout: Layout, point: tuple[int, int]) -> Drawer | None:
    return next((d for d, rect in layout.drawer_buttons if contains(rect, point)), None)


def chapter_row_at(layout: Layout, point: tuple[int, int]) -> int | None:
    """The place whose row in Chapters is under `point`: a level's index, or the sandbox's."""
    return next((k for k, rect in layout.chapter_rows if contains(rect, point)), None)


def setting_row_at(layout: Layout, point: tuple[int, int]) -> Setting | None:
    return next((s for s, rect in layout.setting_rows if contains(rect, point)), None)


def tab_at(layout: Layout, point: tuple[int, int]) -> str | None:
    return next((name for name, rect in layout.tabs if contains(rect, point)), None)


def on_fold_handle(layout: Layout, point: tuple[int, int]) -> bool:
    return layout.fold_handle is not None and contains(layout.fold_handle, point)


def contains(rect: Rect, point: tuple[int, int]) -> bool:
    x, y, w, h = rect
    return x <= point[0] < x + w and y <= point[1] < y + h


def group_at(layout: Layout, point: tuple[int, int]) -> str | None:
    return next((title for title, rect in layout.group_titles if contains(rect, point)), None)


def info_at(layout: Layout, point: tuple[int, int]) -> object | None:
    """The row whose info disc is under `point`, if any: a part, a tool, a button."""
    return next((kind for kind, rect in layout.info_buttons if contains(rect, point)), None)


def menu_item_at(layout: Layout, point: tuple[int, int]) -> Kind | None:
    return next((kind for kind, rect in layout.menu_items if contains(rect, point)), None)


def view_button_at(layout: Layout, point: tuple[int, int]) -> ViewButton | None:
    return next((b for b, rect in layout.view_buttons if contains(rect, point)), None)


def edit_button_at(layout: Layout, point: tuple[int, int]) -> EditButton | None:
    return next((b for b, rect in layout.edit_buttons if contains(rect, point)), None)


def file_button_at(layout: Layout, point: tuple[int, int]) -> FileButton | None:
    return next((b for b, rect in layout.file_buttons if contains(rect, point)), None)


def level_button_at(layout: Layout, point: tuple[int, int]) -> LevelButton | None:
    return next((b for b, rect in layout.level_buttons if contains(rect, point)), None)


def zoom_button_at(layout: Layout, point: tuple[int, int]) -> ViewButton | None:
    return next((b for b, rect in layout.zoom_buttons if contains(rect, point)), None)


def zoom_bar_at(layout: Layout, point: tuple[int, int], grab: int = 6) -> float | None:
    """How far along the zoom bar a press at `point` falls, 0 the farthest, 1 the nearest;
    None off it."""
    if layout.zoom_bar is None:
        return None
    x, y, w, h = layout.zoom_bar
    if not (x - grab <= point[0] <= x + w + grab and y - grab <= point[1] <= y + h + grab):
        return None
    return min(1.0, max(0.0, (point[0] - x) / w))


def level_of(value: float, low: float, high: float) -> float:
    """Where `value` sits between `low` and `high`, on a log scale: a zoom as the bar shows it."""
    return min(1.0, max(0.0, math.log(value / low) / math.log(high / low)))


def value_at(level: float, low: float, high: float) -> float:
    """The value at `level` between `low` and `high`, on a log scale: `level_of` undone."""
    return low * (high / low) ** min(1.0, max(0.0, level))


Bounds = tuple[float, float, float, float]  # x0, y0, x1, y1 [hex sizes], cell (0, 0) at 0
ROOM = 1.5  # the overview shows this many times the zone, each way (D-066)


def board_extent(layout: Layout, cells: Sequence[Cell]) -> Bounds:
    """What the overview shows of the board, and the most the main screen may (D-066): the zone,
    its hexes whole, ROOM times over, and at least what the main screen shows at HEX_SIZE,
    centred on cell (0, 0) and widened to the main screen's aspect."""
    _, _, w, h = layout.board_area
    points = [to_pixel(cell, 1.0, (0.0, 0.0)) for cell in cells] or [(0.0, 0.0)]
    reach = 1.0  # a hex's own half, and a little [hex sizes]
    half_w = max(ROOM * (max(abs(x) for x, _ in points) + reach), w / HEX_SIZE / 2)
    half_h = max(ROOM * (max(abs(y) for _, y in points) + reach), h / HEX_SIZE / 2)
    half_w, half_h = max(half_w, half_h * w / h), max(half_h, half_w * h / w)
    return (-half_w, -half_h, half_w, half_h)


def board_view_of(area: Rect, bounds: Bounds) -> View:
    """The view that shows `bounds` whole in `area`, centred."""
    x, y, w, h = area
    x0, y0, x1, y1 = bounds
    size = min(w / (x1 - x0), h / (y1 - y0))
    return View(size, (x + w / 2 - size * (x0 + x1) / 2, y + h / 2 - size * (y0 + y1) / 2))


def kept_on_board(layout: Layout, view: View, bounds: Bounds) -> View:
    """The view, zoomed in if it showed more than `bounds`, slid so that it shows nothing
    outside them: what the overview frames stays inside it (D-066)."""
    least = board_view_of(layout.board_area, bounds).size
    x, y, w, h = layout.board_area
    if view.size < least:
        k = least / view.size
        cx, cy = x + w / 2, y + h / 2
        view = View(least, (cx + k * (view.origin[0] - cx), cy + k * (view.origin[1] - cy)))
    x0, y0, x1, y1 = bounds
    s, (ox, oy) = view.size, view.origin
    left, right, top, bottom = (x - ox) / s, (x + w - ox) / s, (y - oy) / s, (y + h - oy) / s
    dx = (x0 - left) if left < x0 else (x1 - right) if right > x1 else 0.0
    dy = (y0 - top) if top < y0 else (y1 - bottom) if bottom > y1 else 0.0
    return View(s, (ox - dx * s, oy - dy * s))


def overview_view(layout: Layout, cells: Sequence[Cell]) -> View:
    """The board's extent seen small in Navigator's overview (D-060, D-066)."""
    return board_view_of(layout.overview, board_extent(layout, cells))


def shown_frame(layout: Layout, view: View, small: View) -> Rect:
    """What the main screen shows of the board, as a frame in the overview seen through
    `small`."""
    x, y, w, h = layout.board_area
    k = small.size / view.size
    left = small.origin[0] + k * (x - view.origin[0])
    top = small.origin[1] + k * (y - view.origin[1])
    return (round(left), round(top), round(k * w), round(k * h))


def centred_on(layout: Layout, view: View, small: View, point: tuple[int, int]) -> View:
    """The view, at its zoom, centred where a press at `point` falls in the overview."""
    px = (point[0] - small.origin[0]) / small.size
    py = (point[1] - small.origin[1]) / small.size
    x, y, w, h = layout.board_area
    return View(view.size, (x + w / 2 - view.size * px, y + h / 2 - view.size * py))


def centred_view(layout: Layout, size: float = HEX_SIZE) -> View:
    """Cell (0, 0) at the centre of the board area."""
    x, y, w, h = layout.board_area
    return View(size, (x + w / 2, y + h / 2))


def moved_view(view: View, before: Layout, after: Layout) -> View:
    """The same view, slid with the board's centre when a drawer opens or folds."""
    (x0, y0, w0, h0), (x1, y1, w1, h1) = before.board_area, after.board_area
    dx, dy = (x1 + w1 / 2) - (x0 + w0 / 2), (y1 + h1 / 2) - (y0 + h0 / 2)
    return pan(view, dx, dy)


def fitted_view(area: Rect, points: Sequence[tuple[float, float]], margin: float) -> View:
    """The biggest view (up to MAX_HEX) that shows `points` with `margin` to spare, centred.

    points: pixel positions at hex size 1 with cell (0, 0) at the origin; margin in hex sizes.
    """
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    x, y, w, h = area
    wide, high = max(xs) - min(xs) + 2 * margin, max(ys) - min(ys) + 2 * margin
    size = min(MAX_HEX, w / wide, h / high)
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    return View(size, (x + w / 2 - size * cx, y + h / 2 - size * cy))


def zoom(view: View, factor: float, about: tuple[float, float]) -> View:
    """Scale the grid by `factor` (within the limits), keeping the point `about` in place."""
    size = min(MAX_HEX, max(MIN_HEX, view.size * factor))
    k = size / view.size
    ox, oy = view.origin
    return View(size, (about[0] + k * (ox - about[0]), about[1] + k * (oy - about[1])))


def pan(view: View, dx: float, dy: float) -> View:
    """Slide the grid by (dx, dy) [px]."""
    return View(view.size, (view.origin[0] + dx, view.origin[1] + dy))


def cell_at(layout: Layout, view: View, point: tuple[int, int]) -> Cell | None:
    """The hex under `point`, or None outside the board area (the caller checks the zone)."""
    if not contains(layout.board_area, point):
        return None
    return from_pixel(point[0], point[1], view.size, view.origin)


def visible_cells(layout: Layout, view: View) -> list[Cell]:
    """Every cell whose hex shows, at least in part, in the board area; row by row."""
    x, y, w, h = layout.board_area
    s, (ox, oy) = view.size, view.origin
    rows = range(math.floor((y - s - oy) / (1.5 * s)), math.ceil((y + h + s - oy) / (1.5 * s)) + 1)
    cells = []
    for r in rows:
        # Cell (q, r) is centred at x = ox + sqrt(3) s (q + r / 2).
        q_min = math.floor((x - s - ox) / (SQRT3 * s) - r / 2)
        q_max = math.ceil((x + w + s - ox) / (SQRT3 * s) - r / 2)
        cells += [(q, r) for q in range(q_min, q_max + 1)]
    return cells
