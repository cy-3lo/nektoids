"""Where everything sits on the 960 x 640 editor screen, and what is under a given pixel.

Hex grid on the left, filling its area, with a toolbar strip above and one status line below;
palette on the right: a row of view buttons (zoom, pan), then groups that fold under their
title. The screen regions are fixed; the View says how big a hex is and where the grid sits in
its area, and zoom and pan change only the View (D-013). Plain numbers and tuples, no
pygame, so hit-testing is testable headless.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from nektoids.graph.board import Kind
from nektoids.graph.hexgrid import SQRT3, Cell, from_pixel

Rect = tuple[int, int, int, int]  # x, y, width, height [px]

SCREEN = (960, 640)  # [px]
PALETTE_WIDTH = 240  # [px]
TOOLBAR_HEIGHT = 56  # [px]
STATUS_HEIGHT = 32  # [px]
MARGIN = 16  # [px]
BUTTON = 40  # toolbar button side [px]
ITEM_HEIGHT = 44  # palette row [px]
TITLE_HEIGHT = 28  # palette group title [px]
HEX_SIZE = 40.0  # centre-to-corner size of a hex in the default view [px]
MIN_HEX, MAX_HEX = 20.0, 80.0  # zoom limits [px]
ZOOM_STEP = 1.25  # hex size factor per click

PALETTE_GROUPS: tuple[tuple[str, tuple[Kind, ...]], ...] = (
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
    PAN = "pan"  # moves the view, not a component; chosen in the palette


TOOLBAR = (Tool.ADD, Tool.WIRE, Tool.ROTATE, Tool.MOVE, Tool.DELETE)


class ViewButton(Enum):
    ZOOM_IN = "zoom in"
    ZOOM_OUT = "zoom out"
    PAN = "pan"


@dataclass(frozen=True)
class Layout:
    board_area: Rect
    palette_area: Rect
    view_buttons: tuple[tuple[ViewButton, Rect], ...]
    group_titles: tuple[tuple[str, Rect], ...]  # click one to fold or unfold its group
    palette_items: tuple[tuple[Kind, Rect], ...]
    tool_buttons: tuple[tuple[Tool, Rect], ...]
    status_at: tuple[int, int]  # top-left corner of the status line


@dataclass(frozen=True)
class View:
    """How the grid is seen: the size of a hex and where cell (0, 0) sits on screen."""

    size: float  # centre-to-corner [px]
    origin: tuple[float, float]  # pixel centre of cell (0, 0) [px]


def make_layout(folded: frozenset[str] = frozenset()) -> Layout:
    """The screen regions and palette rows. folded: titles of the groups shown closed."""
    width, height = SCREEN
    left = width - PALETTE_WIDTH  # palette's left edge
    palette = (left, 0, PALETTE_WIDTH, height)
    area = (
        0,
        TOOLBAR_HEIGHT,
        width - PALETTE_WIDTH,
        height - TOOLBAR_HEIGHT - STATUS_HEIGHT,
    )
    view_buttons = tuple(
        (button, (left + MARGIN + i * (BUTTON + 8), MARGIN, BUTTON, BUTTON))
        for i, button in enumerate(ViewButton)
    )
    titles, items = [], []
    y = MARGIN + BUTTON + MARGIN
    for title, kinds in PALETTE_GROUPS:
        titles.append((title, (left + MARGIN, y, PALETTE_WIDTH - 2 * MARGIN, TITLE_HEIGHT - 4)))
        y += TITLE_HEIGHT
        for kind in () if title in folded else kinds:
            items.append((kind, (left + MARGIN, y, PALETTE_WIDTH - 2 * MARGIN, ITEM_HEIGHT - 4)))
            y += ITEM_HEIGHT
        y += MARGIN

    top = (TOOLBAR_HEIGHT - BUTTON) // 2
    buttons = tuple(
        (tool, (MARGIN + i * (BUTTON + 8), top, BUTTON, BUTTON)) for i, tool in enumerate(TOOLBAR)
    )
    return Layout(
        board_area=area,
        palette_area=palette,
        view_buttons=view_buttons,
        group_titles=tuple(titles),
        palette_items=tuple(items),
        tool_buttons=buttons,
        status_at=(MARGIN, height - STATUS_HEIGHT + 8),
    )


def contains(rect: Rect, point: tuple[int, int]) -> bool:
    x, y, w, h = rect
    return x <= point[0] < x + w and y <= point[1] < y + h


def group_at(layout: Layout, point: tuple[int, int]) -> str | None:
    return next((title for title, rect in layout.group_titles if contains(rect, point)), None)


def palette_item_at(layout: Layout, point: tuple[int, int]) -> Kind | None:
    return next((kind for kind, rect in layout.palette_items if contains(rect, point)), None)


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
