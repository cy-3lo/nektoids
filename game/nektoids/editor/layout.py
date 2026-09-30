"""Where everything sits on the 960 x 640 editor screen, and what is under a given pixel.

Hex board on the left with a toolbar strip above and one status line below; palette on the
right, in groups that fold under their title. Plain numbers and tuples, no pygame, so
hit-testing is testable headless.
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


@dataclass(frozen=True)
class Layout:
    hex_size: float  # centre-to-corner [px]
    origin: tuple[float, float]  # pixel centre of cell (0, 0) [px]
    board_area: Rect
    palette_area: Rect
    group_titles: tuple[tuple[str, Rect], ...]  # click one to fold or unfold its group
    palette_items: tuple[tuple[Kind, Rect], ...]
    tool_buttons: tuple[tuple[Tool, Rect], ...]
    status_at: tuple[int, int]  # top-left corner of the status line


def make_layout(cols: int, rows: int, folded: frozenset[str] = frozenset()) -> Layout:
    """Fit a cols x rows board into the space left of the palette, centred.

    folded: titles of the palette groups shown closed, their items hidden.
    """
    width, height = SCREEN
    left = width - PALETTE_WIDTH  # palette's left edge
    palette = (left, 0, PALETTE_WIDTH, height)
    area = (
        0,
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
        titles.append((title, (left + MARGIN, y, PALETTE_WIDTH - 2 * MARGIN, TITLE_HEIGHT - 4)))
        y += TITLE_HEIGHT
        for kind in () if title in folded else kinds:
            items.append((kind, (left + MARGIN, y, PALETTE_WIDTH - 2 * MARGIN, ITEM_HEIGHT - 4)))
            y += ITEM_HEIGHT
        y += MARGIN

    top = (TOOLBAR_HEIGHT - BUTTON) // 2
    buttons = tuple(
        (tool, (MARGIN + i * (BUTTON + 8), top, BUTTON, BUTTON)) for i, tool in enumerate(Tool)
    )
    return Layout(
        hex_size=size,
        origin=origin,
        board_area=area,
        palette_area=palette,
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


def tool_at(layout: Layout, point: tuple[int, int]) -> Tool | None:
    return next((tool for tool, rect in layout.tool_buttons if contains(rect, point)), None)


def cell_at(layout: Layout, point: tuple[int, int]) -> Cell | None:
    """The hex under `point`, or None outside the board area (the caller checks the board)."""
    if not contains(layout.board_area, point):
        return None
    return from_pixel(point[0], point[1], layout.hex_size, layout.origin)
