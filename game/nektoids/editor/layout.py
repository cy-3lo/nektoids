"""Where everything sits on the 960 x 640 editor screen, and what is under a given pixel.

Palette on the left, toolbar strip above the hex board, one status line below it. Plain
numbers and tuples, no pygame, so hit-testing is testable headless.
"""

from __future__ import annotations

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

PALETTE_GROUPS: tuple[tuple[str, tuple[Kind, ...]], ...] = (
    ("Sensors", (Kind.SENSOR_L, Kind.SENSOR_R)),
    ("Converters", (Kind.DOUBLE, Kind.HALVE)),
    ("Actuators", (Kind.THRUSTER_L, Kind.THRUSTER_R)),
)


class Tool(Enum):
    ADD = "add"
    WIRE = "wire"
    ROTATE = "rotate"
    DELETE = "delete"


@dataclass(frozen=True)
class Layout:
    hex_size: float  # centre-to-corner [px]
    origin: tuple[float, float]  # pixel centre of cell (0, 0) [px]
    board_area: Rect
    group_titles: tuple[tuple[str, tuple[int, int]], ...]  # text and its top-left corner
    palette_items: tuple[tuple[Kind, Rect], ...]
    tool_buttons: tuple[tuple[Tool, Rect], ...]
    status_at: tuple[int, int]  # top-left corner of the status line


def make_layout(cols: int, rows: int) -> Layout:
    """Fit a cols x rows board into the space right of the palette, centred."""
    width, height = SCREEN
    area = (
        PALETTE_WIDTH,
        TOOLBAR_HEIGHT,
        width - PALETTE_WIDTH,
        height - TOOLBAR_HEIGHT - STATUS_HEIGHT,
    )
    # Bounding box of an odd-r board, in units of the hex size.
    span_x = SQRT3 * (cols + 0.5)
    span_y = 1.5 * (rows - 1) + 2.0
    size = min((area[2] - 2 * MARGIN) / span_x, (area[3] - 2 * MARGIN) / span_y)
    origin = (
        area[0] + 0.5 * (area[2] - size * span_x) + 0.5 * SQRT3 * size,
        area[1] + 0.5 * (area[3] - size * span_y) + size,
    )

    titles, items = [], []
    y = MARGIN
    for title, kinds in PALETTE_GROUPS:
        titles.append((title, (MARGIN, y)))
        y += TITLE_HEIGHT
        for kind in kinds:
            items.append((kind, (MARGIN, y, PALETTE_WIDTH - 2 * MARGIN, ITEM_HEIGHT - 4)))
            y += ITEM_HEIGHT
        y += MARGIN

    top = (TOOLBAR_HEIGHT - BUTTON) // 2
    buttons = tuple(
        (tool, (PALETTE_WIDTH + MARGIN + i * (BUTTON + 8), top, BUTTON, BUTTON))
        for i, tool in enumerate(Tool)
    )
    return Layout(
        hex_size=size,
        origin=origin,
        board_area=area,
        group_titles=tuple(titles),
        palette_items=tuple(items),
        tool_buttons=buttons,
        status_at=(PALETTE_WIDTH + MARGIN, height - STATUS_HEIGHT + 8),
    )


def contains(rect: Rect, point: tuple[int, int]) -> bool:
    x, y, w, h = rect
    return x <= point[0] < x + w and y <= point[1] < y + h


def palette_item_at(layout: Layout, point: tuple[int, int]) -> Kind | None:
    return next((kind for kind, rect in layout.palette_items if contains(rect, point)), None)


def tool_at(layout: Layout, point: tuple[int, int]) -> Tool | None:
    return next((tool for tool, rect in layout.tool_buttons if contains(rect, point)), None)


def cell_at(layout: Layout, point: tuple[int, int]) -> Cell | None:
    """The hex under `point`, or None outside the board area (the caller checks the board)."""
    if not contains(layout.board_area, point):
        return None
    return from_pixel(point[0], point[1], layout.hex_size, layout.origin)
