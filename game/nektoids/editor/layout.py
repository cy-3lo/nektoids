"""Where everything sits on the 960 x 640 editor screen, and what is under a given pixel.

Three columns, with vertical separators:
- left, the menu: component groups (sensors, converters, actuators) that fold under their title;
- centre, the hex grid, filling its column, with one status line at its foot;
- right, the palette: view buttons (zoom in, zoom out, hand, centre), then the editing tools,
  then a colour picker, inactive until colours carry a meaning.

The screen regions are fixed; the View says how big a hex is and where the grid sits in its
column, and zoom and pan change only the View (D-013). Plain numbers and tuples, no pygame, so
hit-testing is testable headless.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from nektoids.graph.board import Kind
from nektoids.graph.hexgrid import SQRT3, Cell, from_pixel

Rect = tuple[int, int, int, int]  # x, y, width, height [px]

SCREEN = (960, 640)  # [px]
MENU_WIDTH = 200  # left column [px]
PALETTE_WIDTH = 72  # right column [px]
STATUS_HEIGHT = 32  # [px]
MARGIN = 16  # [px]
BUTTON = 40  # palette button side [px]
BUTTON_STEP = 48  # palette button pitch [px]
ITEM_HEIGHT = 44  # menu row [px]
TITLE_HEIGHT = 28  # menu group title [px]
SWATCH_HEIGHT = 14  # colour picker swatch, as wide as a button [px]
SWATCHES = 6
HEX_SIZE = 40.0  # centre-to-corner size of a hex in the default view [px]
MIN_HEX, MAX_HEX = 20.0, 80.0  # zoom limits [px]
ZOOM_STEP = 1.25  # hex size factor per click

MENU_GROUPS: tuple[tuple[str, tuple[Kind, ...]], ...] = (
    ("Sensors", (Kind.EYE,)),
    ("Converters", (Kind.DOUBLE, Kind.HALVE)),
    ("Actuators", (Kind.THRUSTER,)),
)


class Tool(Enum):
    ADD = "add"
    WIRE = "wire"
    ROTATE = "rotate"
    MOVE = "move"
    DELETE = "delete"
    PAN = "pan"  # moves the view, not a component; the hand among the view buttons


PALETTE_TOOLS = (Tool.ADD, Tool.WIRE, Tool.ROTATE, Tool.MOVE, Tool.DELETE)


class ViewButton(Enum):
    ZOOM_IN = "zoom in"
    ZOOM_OUT = "zoom out"
    PAN = "pan"
    CENTRE = "centre"  # bring cell (0, 0) back to the middle, at the same zoom


# Shortcut keys, matched on the character typed (so they follow the keyboard layout) and shown
# in the tooltips.
TOOL_KEYS = {Tool.ADD: "A", Tool.WIRE: "W", Tool.ROTATE: "R", Tool.MOVE: "M", Tool.DELETE: "D"}
VIEW_KEYS = {
    ViewButton.ZOOM_IN: "+",
    ViewButton.ZOOM_OUT: "-",
    ViewButton.PAN: "H",
    ViewButton.CENTRE: "C",
}
KEY_ALIASES = {"=": "+", "_": "-"}  # the same keys, shift or not, on most layouts


@dataclass(frozen=True)
class Layout:
    menu_area: Rect
    board_area: Rect
    palette_area: Rect
    group_titles: tuple[tuple[str, Rect], ...]  # click one to fold or unfold its group
    menu_items: tuple[tuple[Kind, Rect], ...]
    view_buttons: tuple[tuple[ViewButton, Rect], ...]
    tool_buttons: tuple[tuple[Tool, Rect], ...]
    palette_rules: tuple[int, ...]  # y of the short separators between the palette's sets
    swatches: tuple[Rect, ...]  # colour picker, inactive for now
    status_at: tuple[int, int]  # top-left corner of the status line


@dataclass(frozen=True)
class View:
    """How the grid is seen: the size of a hex and where cell (0, 0) sits on screen."""

    size: float  # centre-to-corner [px]
    origin: tuple[float, float]  # pixel centre of cell (0, 0) [px]


def make_layout(folded: frozenset[str] = frozenset()) -> Layout:
    """The screen regions, menu rows and palette buttons. folded: menu groups shown closed."""
    width, height = SCREEN
    right = width - PALETTE_WIDTH  # palette's left edge
    menu = (0, 0, MENU_WIDTH, height)
    board = (MENU_WIDTH, 0, right - MENU_WIDTH, height - STATUS_HEIGHT)
    palette = (right, 0, PALETTE_WIDTH, height)

    titles, items = [], []
    y = MARGIN
    for title, kinds in MENU_GROUPS:
        titles.append((title, (MARGIN, y, MENU_WIDTH - 2 * MARGIN, TITLE_HEIGHT - 4)))
        y += TITLE_HEIGHT
        for kind in () if title in folded else kinds:
            items.append((kind, (MARGIN, y, MENU_WIDTH - 2 * MARGIN, ITEM_HEIGHT - 4)))
            y += ITEM_HEIGHT
        y += MARGIN

    x = right + (PALETTE_WIDTH - BUTTON) // 2
    y = MARGIN
    view_buttons = []
    for button in ViewButton:
        view_buttons.append((button, (x, y, BUTTON, BUTTON)))
        y += BUTTON_STEP
    rules = [y]
    y += MARGIN
    tool_buttons = []
    for tool in PALETTE_TOOLS:
        tool_buttons.append((tool, (x, y, BUTTON, BUTTON)))
        y += BUTTON_STEP
    rules.append(y)
    y += MARGIN
    swatches = tuple(
        (x, y + i * (SWATCH_HEIGHT + 6), BUTTON, SWATCH_HEIGHT) for i in range(SWATCHES)
    )
    return Layout(
        menu_area=menu,
        board_area=board,
        palette_area=palette,
        group_titles=tuple(titles),
        menu_items=tuple(items),
        view_buttons=tuple(view_buttons),
        tool_buttons=tuple(tool_buttons),
        palette_rules=tuple(rules),
        swatches=swatches,
        status_at=(MENU_WIDTH + MARGIN, height - STATUS_HEIGHT + 8),
    )


def palette_target_at(layout: Layout, point: tuple[int, int]) -> Tool | ViewButton | str | None:
    """What a tooltip would describe under `point`: a tool, a view button, or "colours"."""
    target = tool_at(layout, point) or view_button_at(layout, point)
    if target is None and any(contains(rect, point) for rect in layout.swatches):
        return "colours"
    return target


def contains(rect: Rect, point: tuple[int, int]) -> bool:
    x, y, w, h = rect
    return x <= point[0] < x + w and y <= point[1] < y + h


def group_at(layout: Layout, point: tuple[int, int]) -> str | None:
    return next((title for title, rect in layout.group_titles if contains(rect, point)), None)


def menu_item_at(layout: Layout, point: tuple[int, int]) -> Kind | None:
    return next((kind for kind, rect in layout.menu_items if contains(rect, point)), None)


def view_button_at(layout: Layout, point: tuple[int, int]) -> ViewButton | None:
    return next((b for b, rect in layout.view_buttons if contains(rect, point)), None)


def tool_at(layout: Layout, point: tuple[int, int]) -> Tool | None:
    return next((tool for tool, rect in layout.tool_buttons if contains(rect, point)), None)


def centred_view(layout: Layout, size: float = HEX_SIZE) -> View:
    """Cell (0, 0) at the centre of the board area."""
    x, y, w, h = layout.board_area
    return View(size, (x + w / 2, y + h / 2))


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
