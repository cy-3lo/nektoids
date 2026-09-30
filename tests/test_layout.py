"""Editor layout and hit-testing. layout.py imports no pygame, so this runs headless."""

from nektoids.editor.layout import (
    MAX_HEX,
    MIN_HEX,
    PALETTE_TOOLS,
    SCREEN,
    TOOL_KEYS,
    VIEW_KEYS,
    Tool,
    ViewButton,
    cell_at,
    centred_view,
    contains,
    group_at,
    make_layout,
    menu_item_at,
    palette_target_at,
    pan,
    tool_at,
    view_button_at,
    visible_cells,
    zoom,
)
from nektoids.graph.board import Kind
from nektoids.graph.hexgrid import hex_disc, to_pixel
from nektoids.levels.sandbox import free_board, tutorial_board

LAYOUT = make_layout()
VIEW = centred_view(LAYOUT)


def centre(rect):
    x, y, w, h = rect
    return (x + w // 2, y + h // 2)


def test_every_cell_of_the_zone_is_on_screen_and_clickable():
    for cell in hex_disc(2):
        x, y = to_pixel(cell, VIEW.size, VIEW.origin)
        point = (round(x), round(y))
        assert contains(LAYOUT.board_area, point)
        assert cell_at(LAYOUT, VIEW, point) == cell


def test_the_grid_fills_the_board_area():
    shown = set(visible_cells(LAYOUT, VIEW))
    x0, y0, w, h = LAYOUT.board_area
    for x in range(x0, x0 + w, 7):
        for y in range(y0, y0 + h, 7):
            assert cell_at(LAYOUT, VIEW, (x, y)) in shown
    assert set(hex_disc(2)) <= shown


def test_three_columns_side_by_side():
    menu, board, palette = LAYOUT.menu_area, LAYOUT.board_area, LAYOUT.palette_area
    assert menu[0] == 0 and menu[0] + menu[2] == board[0]
    assert board[0] + board[2] == palette[0] and palette[0] + palette[2] == SCREEN[0]
    assert board[2] > menu[2] > palette[2]  # the grid gets the most room


def test_menu_has_every_kind_once_inside_its_column():
    kinds = [kind for kind, _ in LAYOUT.menu_items]
    assert sorted(kinds, key=lambda k: k.value) == sorted(Kind, key=lambda k: k.value)
    for kind, rect in LAYOUT.menu_items:
        assert contains(LAYOUT.menu_area, rect[:2])
        assert contains(LAYOUT.menu_area, (rect[0] + rect[2] - 1, rect[1] + rect[3] - 1))
        assert menu_item_at(LAYOUT, centre(rect)) == kind


def test_folding_a_group_hides_its_items_and_lifts_the_groups_below():
    folded = make_layout(frozenset({"Converters"}))
    kinds = [kind for kind, _ in folded.menu_items]
    assert Kind.DOUBLE not in kinds and Kind.HALVE not in kinds and Kind.EYE in kinds
    titles_open, titles_folded = dict(LAYOUT.group_titles), dict(folded.group_titles)
    assert titles_folded["Sensors"] == titles_open["Sensors"]
    assert titles_folded["Actuators"][1] < titles_open["Actuators"][1]
    assert folded.board_area == LAYOUT.board_area
    for title, rect in folded.group_titles:
        assert group_at(folded, centre(rect)) == title


def test_palette_stacks_view_buttons_then_tools_then_the_colour_picker():
    assert [button for button, _ in LAYOUT.view_buttons] == list(ViewButton)
    assert [tool for tool, _ in LAYOUT.tool_buttons] == list(PALETTE_TOOLS)
    assert Tool.PAN not in PALETTE_TOOLS  # the hand, among the view buttons
    rects = [r for _, r in LAYOUT.view_buttons] + [r for _, r in LAYOUT.tool_buttons]
    rects += list(LAYOUT.swatches)
    for rect in rects:
        assert contains(LAYOUT.palette_area, rect[:2])
        assert contains(LAYOUT.palette_area, (rect[0] + rect[2] - 1, rect[1] + rect[3] - 1))
    tops = [r[1] for r in rects]
    assert tops == sorted(tops)
    first_tool, last_view = LAYOUT.tool_buttons[0][1], LAYOUT.view_buttons[-1][1]
    assert last_view[1] + last_view[3] < LAYOUT.palette_rules[0] < first_tool[1]
    for button, rect in LAYOUT.view_buttons:
        assert view_button_at(LAYOUT, centre(rect)) == button
    for tool, rect in LAYOUT.tool_buttons:
        assert tool_at(LAYOUT, centre(rect)) == tool
    assert tool_at(LAYOUT, centre(LAYOUT.board_area)) is None


def test_sandbox_boards():
    free = free_board()
    assert free.nodes == {} and free.remaining(Kind.EYE) == free.total(Kind.EYE) == 2
    assert free.remaining(Kind.DOUBLE) is None
    tutorial = tutorial_board()
    assert len(tutorial.nodes) == 4 and all(node.locked for node in tutorial.nodes.values())
    assert tutorial.remaining(Kind.EYE) == 0


def test_zoom_keeps_its_anchor_and_stays_within_limits():
    anchor = (300.0, 250.0)
    cell = cell_at(LAYOUT, VIEW, (300, 250))
    closer = zoom(VIEW, 1.25, anchor)
    assert closer.size == 1.25 * VIEW.size
    assert cell_at(LAYOUT, closer, (300, 250)) == cell
    assert zoom(VIEW, 100.0, anchor).size == MAX_HEX
    assert zoom(VIEW, 0.01, anchor).size == MIN_HEX


def test_pan_slides_the_grid_under_the_mouse():
    moved = pan(VIEW, 30.0, -12.0)
    assert moved.size == VIEW.size
    assert cell_at(LAYOUT, moved, (330, 238)) == cell_at(LAYOUT, VIEW, (300, 250))


def test_the_grid_still_fills_the_area_zoomed_out():
    far = zoom(VIEW, 0.01, (0.0, 0.0))
    shown = set(visible_cells(LAYOUT, far))
    x0, y0, w, h = LAYOUT.board_area
    for x in range(x0, x0 + w, 5):
        for y in range(y0, y0 + h, 5):
            assert cell_at(LAYOUT, far, (x, y)) in shown


def test_the_palette_fits_on_screen():
    rects = [r for _, r in LAYOUT.view_buttons] + [r for _, r in LAYOUT.tool_buttons]
    assert max(y + h for _, y, _, h in [*rects, *LAYOUT.swatches]) <= SCREEN[1] - 8


def test_every_palette_button_has_its_own_key_and_tooltip_target():
    keys = [TOOL_KEYS[tool] for tool in PALETTE_TOOLS] + [VIEW_KEYS[b] for b in ViewButton]
    assert len(set(keys)) == len(keys) and all(len(key) == 1 for key in keys)
    for target, rect in [*LAYOUT.tool_buttons, *LAYOUT.view_buttons]:
        assert palette_target_at(LAYOUT, centre(rect)) == target
    assert palette_target_at(LAYOUT, centre(LAYOUT.swatches[2])) == "colours"
    assert palette_target_at(LAYOUT, centre(LAYOUT.board_area)) is None
