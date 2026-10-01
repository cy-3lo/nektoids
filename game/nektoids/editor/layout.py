"""Where everything sits on the 960 x 640 editor screen, and what is under a given pixel.

Three columns, with vertical separators:
- left, the menu: component groups (sensors, operators, actuators) that fold under their title,
  each part's row with an info disc after its name (D-036); only the parts the level hands out,
  and no group left empty;
- centre, the hex grid, filling its column, the level's caption at its top, one status line at
  its foot;
- right, the palette, in titled sections of two buttons a row (D-025, D-027): the view (zoom
  in, zoom out, hand, centre), the tools (add, wire, move, delete, turn left, turn right), a
  colour picker, inactive until colours carry a meaning, editing (undo, redo, then save and
  load, inactive until saving exists), and the level (the map, and Run, lit) (D-037).

The screen regions are fixed; the View says how big a hex is and where the grid sits in its
column, and zoom and pan change only the View (D-013). Plain numbers and tuples, no pygame, so
hit-testing is testable headless.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from nektoids.graph.board import Kind
from nektoids.graph.hexgrid import SQRT3, Cell, from_pixel

Rect = tuple[int, int, int, int]  # x, y, width, height [px]

SCREEN = (960, 640)  # [px]
MENU_WIDTH = 200  # left column [px]
PALETTE_WIDTH = 120  # right column: two buttons a row [px]
STATUS_HEIGHT = 32  # [px]
MARGIN = 16  # [px]
BUTTON = 40  # palette button side [px]
BUTTON_STEP = 48  # palette button pitch [px]
ITEM_HEIGHT = 44  # menu row [px]
TITLE_HEIGHT = 28  # menu group title [px]
PALETTE_TITLE = 24  # palette section title [px]
SECTION_GAP = 8  # between palette sections [px]
SWATCH_HEIGHT = 14  # colour picker swatch, as wide as a button [px]
INFO_AT = 128  # a menu row's info disc: its centre, this far from the row's left [px]
INFO_HIT = 20  # ... and the square a click on it falls in [px]
SWATCHES = 6
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


class LevelButton(Enum):
    MAP = "map"  # the chapter's levels and the sandbox
    RUN = "run"  # the board, swimming in its arena


class FileButton(Enum):  # inactive: saving is not in the game yet
    SAVE = "save"
    LOAD = "load"


class ViewButton(Enum):
    ZOOM_IN = "zoom in"
    ZOOM_OUT = "zoom out"
    PAN = "pan"
    CENTRE = "centre"  # bring cell (0, 0) back to the middle, at the same zoom


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
}
# With Ctrl (Cmd on a Mac), matched on the key code, which follows the layout; Ctrl+Y redoes too.
EDIT_KEYS = {EditButton.UNDO: "Ctrl+Z", EditButton.REDO: "Ctrl+Shift+Z"}
# On the physical key: Space runs, as the arena's play (D-021); Tab, the levels, as in F3.
LEVEL_KEYS = {LevelButton.MAP: "Tab", LevelButton.RUN: "Space"}
KEY_ALIASES = {"=": "+", "_": "-"}  # the same keys, shift or not, on most layouts


@dataclass(frozen=True)
class Layout:
    kinds: frozenset[Kind]  # the parts the menu shows: what the level hands out
    menu_area: Rect
    board_area: Rect
    palette_area: Rect
    group_titles: tuple[tuple[str, Rect], ...]  # click one to fold or unfold its group
    menu_items: tuple[tuple[Kind, Rect], ...]
    info_buttons: tuple[tuple[Kind, Rect], ...]  # one per menu row, a click opens its box
    view_buttons: tuple[tuple[ViewButton, Rect], ...]
    tool_buttons: tuple[tuple[Tool, Rect], ...]
    palette_titles: tuple[tuple[str, Rect], ...]  # one above each section shown
    edit_buttons: tuple[tuple[EditButton, Rect], ...]
    file_buttons: tuple[tuple[FileButton, Rect], ...]  # inactive for now
    level_buttons: tuple[tuple[LevelButton, Rect], ...]
    swatches: tuple[Rect, ...]  # colour picker, inactive for now
    caption_at: tuple[int, int]  # top-left corner of the level's title and spec
    status_at: tuple[int, int]  # top-left corner of the status line


@dataclass(frozen=True)
class View:
    """How the grid is seen: the size of a hex and where cell (0, 0) sits on screen."""

    size: float  # centre-to-corner [px]
    origin: tuple[float, float]  # pixel centre of cell (0, 0) [px]


def make_layout(
    folded: frozenset[str] = frozenset(), kinds: frozenset[Kind] = frozenset(Kind)
) -> Layout:
    """The screen regions, menu rows and palette buttons. folded: menu groups shown closed;
    kinds: the parts the level hands out, the only ones the menu shows (D-039)."""
    width, height = SCREEN
    right = width - PALETTE_WIDTH  # palette's left edge
    menu = (0, 0, MENU_WIDTH, height)
    board = (MENU_WIDTH, 0, right - MENU_WIDTH, height - STATUS_HEIGHT)
    palette = (right, 0, PALETTE_WIDTH, height)

    titles, items = [], []
    y = MARGIN
    for title, group in MENU_GROUPS:
        shown = [kind for kind in group if kind in kinds]
        if not shown:
            continue  # a group with nothing in this level: no title either
        titles.append((title, (MARGIN, y, MENU_WIDTH - 2 * MARGIN, TITLE_HEIGHT - 4)))
        y += TITLE_HEIGHT
        for kind in () if title in folded else shown:
            items.append((kind, (MARGIN, y, MENU_WIDTH - 2 * MARGIN, ITEM_HEIGHT - 4)))
            y += ITEM_HEIGHT
        y += MARGIN

    y = MARGIN
    view, view_rects, y = _section(right, y, "View", len(ViewButton), BUTTON, BUTTON_STEP)
    tools, tool_rects, y = _section(right, y, "Tools", len(PALETTE_TOOLS), BUTTON, BUTTON_STEP)
    pitch = SWATCH_HEIGHT + 6
    colours, swatches, y = _section(right, y, "Colours", SWATCHES, SWATCH_HEIGHT, pitch)
    count = len(EditButton) + len(FileButton)  # undo and redo, then save and load
    edit, rects, y = _section(right, y, "Edit", count, BUTTON, BUTTON_STEP)
    edit_rects, file_rects = rects[: len(EditButton)], rects[len(EditButton) :]
    level, level_rects, y = _section(right, y, "Level", len(LevelButton), BUTTON, BUTTON_STEP)
    return Layout(
        kinds=kinds,
        menu_area=menu,
        board_area=board,
        palette_area=palette,
        group_titles=tuple(titles),
        menu_items=tuple(items),
        info_buttons=tuple(
            (kind, (x + INFO_AT - INFO_HIT // 2, y + (h - INFO_HIT) // 2, INFO_HIT, INFO_HIT))
            for kind, (x, y, _, h) in items
        ),
        view_buttons=tuple(zip(ViewButton, view_rects, strict=True)),
        tool_buttons=tuple(zip(PALETTE_TOOLS, tool_rects, strict=True)),
        edit_buttons=tuple(zip(EditButton, edit_rects, strict=True)),
        file_buttons=tuple(zip(FileButton, file_rects, strict=True)),
        level_buttons=tuple(zip(LevelButton, level_rects, strict=True)),
        palette_titles=(view, tools, colours, edit, level),
        swatches=tuple(swatches),
        caption_at=(MENU_WIDTH + MARGIN, 10),
        status_at=(MENU_WIDTH + MARGIN, height - STATUS_HEIGHT + 8),
    )


def _section(
    left: int, top: int, title: str, count: int, height: int, pitch: int
) -> tuple[tuple[str, Rect], list[Rect], int]:
    """A palette section from `top` in the column at `left`: its title and the area it covers,
    the rects of its `count` items, two a row `pitch` apart, and the top of the next section."""
    columns = (left + (PALETTE_WIDTH - BUTTON - BUTTON_STEP) // 2,)
    columns += (columns[0] + BUTTON_STEP,)
    rows = math.ceil(count / 2)
    first = top + PALETTE_TITLE
    items = [(columns[i % 2], first + (i // 2) * pitch, BUTTON, height) for i in range(count)]
    area = (left + MARGIN, top, PALETTE_WIDTH - 2 * MARGIN, PALETTE_TITLE + rows * pitch)
    return (title, area), items, first + rows * pitch + SECTION_GAP


def palette_target_at(
    layout: Layout, point: tuple[int, int]
) -> Tool | ViewButton | EditButton | FileButton | LevelButton | str | None:
    """What a tooltip would describe under `point`: a button, or "colours"."""
    target = (
        tool_at(layout, point)
        or view_button_at(layout, point)
        or edit_button_at(layout, point)
        or file_button_at(layout, point)
        or level_button_at(layout, point)
    )
    if target is None and any(contains(rect, point) for rect in layout.swatches):
        return "colours"
    return target


def contains(rect: Rect, point: tuple[int, int]) -> bool:
    x, y, w, h = rect
    return x <= point[0] < x + w and y <= point[1] < y + h


def group_at(layout: Layout, point: tuple[int, int]) -> str | None:
    return next((title for title, rect in layout.group_titles if contains(rect, point)), None)


def info_at(layout: Layout, point: tuple[int, int]) -> Kind | None:
    """The part whose info disc is under `point`, if any."""
    return next((kind for kind, rect in layout.info_buttons if contains(rect, point)), None)


def menu_item_at(layout: Layout, point: tuple[int, int]) -> Kind | None:
    return next((kind for kind, rect in layout.menu_items if contains(rect, point)), None)


def view_button_at(layout: Layout, point: tuple[int, int]) -> ViewButton | None:
    return next((b for b, rect in layout.view_buttons if contains(rect, point)), None)


def tool_at(layout: Layout, point: tuple[int, int]) -> Tool | None:
    return next((tool for tool, rect in layout.tool_buttons if contains(rect, point)), None)


def edit_button_at(layout: Layout, point: tuple[int, int]) -> EditButton | None:
    return next((b for b, rect in layout.edit_buttons if contains(rect, point)), None)


def file_button_at(layout: Layout, point: tuple[int, int]) -> FileButton | None:
    return next((b for b, rect in layout.file_buttons if contains(rect, point)), None)


def level_button_at(layout: Layout, point: tuple[int, int]) -> LevelButton | None:
    return next((b for b, rect in layout.level_buttons if contains(rect, point)), None)


def centred_view(layout: Layout, size: float = HEX_SIZE) -> View:
    """Cell (0, 0) at the centre of the board area."""
    x, y, w, h = layout.board_area
    return View(size, (x + w / 2, y + h / 2))


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
