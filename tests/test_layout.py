"""Editor layout and hit-testing. layout.py imports no pygame, so this runs headless."""

from nektoids.editor.layout import (
    PALETTE_WIDTH,
    SCREEN,
    TOOLBAR_HEIGHT,
    Tool,
    cell_at,
    contains,
    make_layout,
    palette_item_at,
    tool_at,
)
from nektoids.graph.board import Kind
from nektoids.graph.hexgrid import offset_rect, to_pixel
from nektoids.levels.sandbox import free_board, tutorial_board

LAYOUT = make_layout(9, 7)


def centre(rect):
    x, y, w, h = rect
    return (x + w // 2, y + h // 2)


def test_every_cell_is_on_screen_and_clickable():
    for cell in offset_rect(9, 7):
        x, y = to_pixel(cell, LAYOUT.hex_size, LAYOUT.origin)
        point = (round(x), round(y))
        assert contains(LAYOUT.board_area, point)
        assert cell_at(LAYOUT, point) == cell


def test_palette_has_every_kind_once_inside_the_panel():
    kinds = [kind for kind, _ in LAYOUT.palette_items]
    assert sorted(kinds, key=lambda k: k.value) == sorted(Kind, key=lambda k: k.value)
    for kind, rect in LAYOUT.palette_items:
        x, y, w, h = rect
        assert x + w <= PALETTE_WIDTH and y + h <= SCREEN[1]
        assert palette_item_at(LAYOUT, centre(rect)) == kind


def test_tool_buttons_sit_in_the_toolbar():
    assert [tool for tool, _ in LAYOUT.tool_buttons] == list(Tool)
    for tool, rect in LAYOUT.tool_buttons:
        assert rect[1] + rect[3] <= TOOLBAR_HEIGHT
        assert tool_at(LAYOUT, centre(rect)) == tool
    assert tool_at(LAYOUT, (SCREEN[0] - 1, SCREEN[1] - 1)) is None


def test_sandbox_boards():
    free = free_board()
    assert free.nodes == {} and free.remaining(Kind.EYE) == free.total(Kind.EYE) == 2
    assert free.remaining(Kind.DOUBLE) is None
    tutorial = tutorial_board()
    assert len(tutorial.nodes) == 4 and all(node.locked for node in tutorial.nodes.values())
    assert tutorial.remaining(Kind.EYE) == 0
