"""Editor layout and hit-testing (D-051). layout.py imports no pygame, so this runs headless."""

import pytest

from nektoids.editor.arena_layout import BUTTON_KEYS
from nektoids.editor.layout import (
    ACTION_WIDTH,
    BAR_WIDTH,
    CAPTION_HEIGHT,
    DRAWER_KEYS,
    DRAWER_WIDTH,
    DRAWERS,
    EDIT_KEYS,
    FOOT,
    FOOT_MARGIN,
    HEX_SIZE,
    HINT_LINE,
    LEVEL_KEYS,
    MAX_HEX,
    MIN_HEX,
    MODE_KEY,
    PALETTE_TOOLS,
    RUN_VIEWS,
    SCREEN,
    TABS_HEIGHT,
    TOOL_KEYS,
    TURNS,
    VIEW_KEYS,
    WHEEL_HEIGHT,
    Drawer,
    EditButton,
    Env,
    Goal,
    HintRow,
    LevelButton,
    MainView,
    Mode,
    Setting,
    Shown,
    Tool,
    View,
    ViewButton,
    action_at,
    board_extent,
    board_view_of,
    cell_at,
    centred_on,
    centred_view,
    chapter_row_at,
    contains,
    drawer_button_at,
    drawer_key,
    edit_button_at,
    goal_row_at,
    group_at,
    hint_row_at,
    info_at,
    kept_on_board,
    level_button_at,
    level_of,
    main_view_for,
    make_layout,
    menu_item_at,
    mode_button_at,
    moved_view,
    on_fold_handle,
    overview_view,
    palette_target_at,
    pan,
    passkey_at,
    scroll_bar_at,
    scroll_for,
    scroll_thumb,
    setting_row_at,
    shown_frame,
    tab_at,
    value_at,
    view_button_at,
    visible_cells,
    wheel_fold_at,
    win_row_at,
    zoom,
    zoom_bar_at,
    zoom_button_at,
)
from nektoids.graph.board import Kind
from nektoids.graph.hexgrid import hex_disc, to_pixel
from nektoids.levels.arenas import arenas
from nektoids.levels.sandbox import free_board, tutorial_board

LAYOUT = make_layout()  # Parts open, every part handed out, the cell under the list
LIST = make_layout(wheel_folded=True)  # the same, the cell folded: the whole list shows
VIEW = centred_view(LAYOUT)
FILES = make_layout(Drawer.FILES, files=(("1.2 Aggression", 2), ("1.1 Fear", 1)))
NAVIGATOR = make_layout(Drawer.NAVIGATOR)
FOLDED = make_layout(None)
RUN_NAVIGATOR = make_layout(Drawer.NAVIGATOR, env=Env.RUN)  # its rays, its objectives


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


def test_the_bar_the_drawer_and_the_board_side_by_side_the_tabs_over_the_board():
    bar, drawer, board = LAYOUT.bar_area, LAYOUT.drawer_area, LAYOUT.board_area
    assert bar[0] == 0 and bar[0] + bar[2] == drawer[0] and drawer[0] + drawer[2] == board[0]
    assert board[0] + board[2] == SCREEN[0] and board[2] > drawer[2] > bar[2]
    for _, (x, y, _, h) in LAYOUT.tabs:
        assert y == 0 and y + h + CAPTION_HEIGHT == board[1] and board[0] <= x  # over the board
    assert (
        contains(board, LAYOUT.status_at) is False and LAYOUT.status_at[1] > board[1] + board[3] - 1
    )
    assert FOLDED.drawer_area is None and FOLDED.fold_handle is None
    assert FOLDED.board_area[0] == bar[2] and FOLDED.board_area[2] > board[2]  # the room it frees


def test_only_the_open_drawer_has_rows_each_inside_it_and_on_screen():
    for layout, rows in (
        (LAYOUT, LAYOUT.menu_items),
        (FILES, FILES.win_rows),
        (RUN_NAVIGATOR, (*RUN_NAVIGATOR.view_buttons, *RUN_NAVIGATOR.goal_rows)),
    ):
        assert len(layout.info_buttons) == len(rows) > 0
        for _, rect in rows:
            assert contains(layout.drawer_area, rect[:2])
            assert contains(layout.drawer_area, (rect[0] + rect[2] - 1, rect[1] + rect[3] - 1))
            assert rect[1] + rect[3] <= SCREEN[1] - 8
        tops = [rect[1] for _, rect in rows]
        assert tops == sorted(tops) and len(set(tops)) == len(tops)  # one under the other
    assert LAYOUT.win_rows == () and FILES.menu_items == () and FOLDED.info_buttons == ()


def test_parts_has_every_kind_once_and_a_click_on_a_row_picks_it():
    kinds = [kind for kind, _ in LIST.menu_items]
    assert sorted(kinds, key=lambda k: k.value) == sorted(Kind, key=lambda k: k.value)
    for kind, rect in LIST.menu_items:
        assert menu_item_at(LIST, (rect[0] + 20, rect[1] + rect[3] // 2)) == kind


def test_parts_holds_the_cell_under_its_list_and_the_cells_title_folds_it():
    _, ly, _, lh = LAYOUT.list_area  # D-069
    _, fy, _, fh = LAYOUT.wheel_fold
    cx, cy, cw, ch = LAYOUT.wheel_view
    assert ly == LIST.list_area[1] and ly + lh < fy and fy + fh == cy and cy + ch <= SCREEN[1]
    assert contains(LAYOUT.drawer_area, (cx, cy)) and cw >= 200 and ch == WHEEL_HEIGHT
    assert wheel_fold_at(LAYOUT, centre(LAYOUT.wheel_fold))
    assert group_at(LAYOUT, centre(LAYOUT.wheel_fold)) is None  # not one of the list's groups
    assert LIST.wheel_view is None and LIST.wheel_fold[1] + LIST.wheel_fold[3] < SCREEN[1]
    assert LIST.wheel_fold[1] > fy and LIST.list_area[3] > lh  # at the foot: the list has the room
    tools = make_layout(Drawer.TOOLS)  # its rows fit above the Wheel: nothing to scroll (D-096)
    _, ty, _, th = tools.list_area
    assert ty + th < tools.wheel_fold[1] and tools.scroll_bar is None and tools.scroll_max == 0
    assert make_layout(Drawer.FILES).wheel_fold is None and FILES.wheel_view is None


def test_parts_list_scrolls_when_it_does_not_fit_and_its_rows_answer_only_where_they_show():
    assert LAYOUT.scroll_max > 0 and LAYOUT.scroll_bar is not None
    assert LIST.scroll_max == 0 and LIST.scroll_bar is None and scroll_thumb(LIST) is None
    bottom = make_layout(scroll=10_000)
    assert bottom.scroll == LAYOUT.scroll_max and make_layout(scroll=-5).scroll == 0
    eye_top = dict(LAYOUT.menu_items)[Kind.EYE][1]
    assert eye_top - dict(bottom.menu_items)[Kind.EYE][1] == bottom.scroll
    _, ly, _, lh = LAYOUT.list_area
    last = dict(LAYOUT.menu_items)[Kind.DIFFERENCE]
    assert last[1] + last[3] // 2 > ly + lh  # out of sight at first: it does not answer
    assert menu_item_at(LAYOUT, centre(last)) is None
    assert info_at(LAYOUT, centre(dict(LAYOUT.info_buttons)[Kind.DIFFERENCE])) is None
    last = dict(bottom.menu_items)[Kind.DIFFERENCE]
    assert menu_item_at(bottom, centre(last)) is Kind.DIFFERENCE  # in sight once scrolled
    x, y, w, h = LAYOUT.scroll_bar  # beside the rows, inside the drawer's edge
    assert x >= max(r[0] + r[2] for _, r in LAYOUT.menu_items) and x + w < BAR_WIDTH + DRAWER_WIDTH
    assert scroll_bar_at(LAYOUT, (x + w // 2, y + h // 2)) and not scroll_bar_at(LIST, (x, y))
    assert scroll_for(LAYOUT, y) == 0 and scroll_for(LAYOUT, y + h) == LAYOUT.scroll_max
    _, top, _, length = scroll_thumb(LAYOUT)
    assert top == y and scroll_thumb(bottom)[1] + length == y + h


def _shown_rows(layout):
    """Every row the open drawer holds, and what else scrolls with them, as rects."""
    rows = [
        rect
        for listed in (
            layout.menu_items,
            layout.mode_buttons,
            layout.edit_buttons,
            layout.view_buttons,
            layout.win_rows,
            layout.setting_rows,
            layout.hint_rows,
            layout.chapter_rows,
        )
        for _, rect in listed
    ]
    extra = (layout.passkey_field, layout.overview, layout.shadow_picture)
    return rows + [rect for rect in extra if rect is not None]


def _inside(rect, area):
    x, y, w, h = rect
    ax, ay, aw, ah = area
    return ax <= x and x + w <= ax + aw and ay <= y and y + h <= ay + ah


MOST = {  # each drawer with the most it may show: 7 levels, 3 objectives, every hint taken
    "chapter": 7,
    "hint_lines": (2, 2, 0),
    "shadow": True,
    "files": (("1.7", 5), ("1.6", 5), ("1.5", 5)),
}


@pytest.mark.parametrize("env", list(Env))
def test_every_drawers_rows_show_within_it_scrolled_into_view_if_they_do_not_fit(env):
    goals = 3 if env is Env.RUN else 0
    for drawer in (*DRAWERS[env], *FOOT):
        first = make_layout(drawer, env=env, goals=goals, **MOST)
        rows = _shown_rows(first)
        if not rows:
            continue  # a drawing that fits its room: Diagnostic, Inside, Score (D-096)
        area = first.list_area
        assert area is not None and _inside(area, first.drawer_area), drawer
        bottom = area[1] + area[3]
        if first.goal_area is not None:
            assert bottom <= first.goal_area[1], drawer  # above the objectives (D-065)
        if first.wheel_fold is not None:
            assert bottom <= first.wheel_fold[1], drawer  # above the Wheel (D-069)
        assert bottom <= SCREEN[1] - FOOT_MARGIN, drawer
        shown = set()
        for scroll in [*range(0, first.scroll_max, 20), first.scroll_max]:
            layout = make_layout(drawer, env=env, goals=goals, scroll=scroll, **MOST)
            shown |= {k for k, rect in enumerate(_shown_rows(layout)) if _inside(rect, area)}
        assert shown == set(range(len(rows))), drawer  # each row shows, scrolled far enough
        assert (first.scroll_bar is None) == (first.scroll_max == 0), drawer


def test_chapters_scrolls_in_the_run_and_its_rows_answer_only_where_they_show():
    chapters = make_layout(Drawer.CHAPTERS, env=Env.RUN, goals=3, chapter=7)
    assert chapters.scroll_max > 0 and scroll_bar_at(chapters, centre(chapters.scroll_bar))
    _, ly, _, lh = chapters.list_area
    hidden = [k for k, (_, y, _, h) in chapters.chapter_rows if y + h // 2 >= ly + lh]
    assert hidden and not passkey_at(chapters, centre(chapters.passkey_field))
    sandbox = dict(chapters.chapter_rows)[hidden[-1]]
    assert chapter_row_at(chapters, centre(sandbox)) is None  # out of sight, it does not answer
    end = make_layout(Drawer.CHAPTERS, env=Env.RUN, goals=3, chapter=7, scroll=10_000)
    assert end.scroll == chapters.scroll_max
    assert chapter_row_at(end, centre(dict(end.chapter_rows)[hidden[-1]])) == hidden[-1]
    assert passkey_at(end, centre(end.passkey_field))
    for goal, rect in end.goal_rows:  # the objectives stay put, and their info discs answer
        assert rect == dict(chapters.goal_rows)[goal] and goal_row_at(end, centre(rect)) == goal
    disc = dict(end.info_buttons)[Goal(0)]
    assert info_at(end, centre(disc)) == Goal(0)


def test_the_first_levels_parts_fit_with_the_cell_open_so_a_steps_rows_would_show():
    for level in arenas()[:2]:  # Fear and Aggression, whose old tutorials showed Parts' rows
        board = level.new_board()
        kinds = frozenset(kind for kind in Kind if board.total(kind) != 0)
        assert make_layout(kinds=kinds).scroll_max == 0, level.title


def test_parts_lists_sensors_then_actuators_then_operators_and_the_numbers_follow():
    assert [title for title, _ in LIST.group_titles] == ["Sensors", "Actuators", "Operators"]
    kinds = [kind for kind, _ in LIST.menu_items]  # D-069: the thruster third, its key 3
    assert kinds[:3] == [Kind.EYE, Kind.SOURCE, Kind.THRUSTER]


def test_folding_a_group_hides_its_items_and_lifts_the_groups_below():
    folded = make_layout(folded=frozenset({"Actuators"}))
    kinds = [kind for kind, _ in folded.menu_items]
    assert Kind.THRUSTER not in kinds and Kind.EYE in kinds and Kind.DOUBLE in kinds
    titles_open, titles_folded = dict(LAYOUT.group_titles), dict(folded.group_titles)
    assert titles_folded["Sensors"] == titles_open["Sensors"]
    assert titles_folded["Operators"][1] < titles_open["Operators"][1]
    assert folded.board_area == LAYOUT.board_area
    for title, rect in folded.group_titles:
        assert group_at(folded, centre(rect)) == title


def test_tools_holds_write_delete_undo_redo_then_the_cell_and_the_action_sits_atop():
    tools = make_layout(Drawer.TOOLS)  # D-068: first in the bar
    assert DRAWERS[Env.EDITOR][0] is Drawer.TOOLS
    assert [title for title, _ in tools.section_titles] == ["Mode", "Edit"]
    rows = [*tools.mode_buttons, *tools.edit_buttons]
    assert [b for b, _ in rows] == [Mode.WRITE, Mode.DELETE, EditButton.UNDO, EditButton.REDO]
    assert rows[-1][1][1] + rows[-1][1][3] < tools.wheel_fold[1]  # the cell at the foot, as Parts'
    assert tools.wheel_fold == LAYOUT.wheel_fold and tools.wheel_view == LAYOUT.wheel_view
    folded = make_layout(Drawer.TOOLS, wheel_folded=True)
    assert folded.wheel_view is None and folded.wheel_fold == LIST.wheel_fold
    for button, rect in rows:
        found = mode_button_at(tools, centre(rect)) or edit_button_at(tools, centre(rect))
        assert found is button
    for layout in (tools, LAYOUT, make_layout(None)):  # the action, centred atop the main screen
        x, y, w, h = layout.action_at  # as tall as the disc drawn there: its line clear of it
        bx, by, bw, _ = layout.board_area
        assert abs(x + w / 2 - (bx + bw / 2)) <= 1 and y > by and w == h == ACTION_WIDTH
        assert action_at(layout, (x + 5, y + 5)) is Shown.ACTION
    assert LAYOUT.mode_buttons == LAYOUT.edit_buttons == ()  # Parts open: Tools' rows are not
    assert make_layout(env=Env.RUN).action_at is None
    assert [title for title, _ in FILES.section_titles] == ["Wins this session"]  # D-093
    assert [title for title, _ in NAVIGATOR.section_titles] == ["Overview"]  # no option yet
    assert NAVIGATOR.view_buttons == ()  # the editor's view has no option yet (D-065)
    run = make_layout(Drawer.NAVIGATOR, env=Env.RUN)
    assert [title for title, _ in run.section_titles] == ["View", "Overview", "Objectives"]
    assert [button for button, _ in run.view_buttons] == list(RUN_VIEWS)  # rays, motion, streams
    for button, rect in run.view_buttons:
        assert view_button_at(run, (rect[0] + 20, rect[1] + rect[3] // 2)) == button


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


def test_every_tool_and_view_button_has_its_own_key_and_the_bar_its_tooltips():
    views = [VIEW_KEYS[b] for b in ViewButton if b not in RUN_VIEWS]  # the editor's own
    keys = [TOOL_KEYS[tool] for tool in PALETTE_TOOLS] + views
    keys.append(MODE_KEY)  # Write and Delete in turn (D-068)
    assert len(set(keys)) == len(keys)
    assert all(len(key) == 1 for key in keys if key != TOOL_KEYS[Tool.DELETE])  # one character
    assert TOOL_KEYS[Tool.DELETE] == "Del"  # Backspace and Delete, on the physical key (D-069)
    assert EDIT_KEYS == {EditButton.UNDO: "Ctrl+Z", EditButton.REDO: "Ctrl+Y"}
    assert (TOOL_KEYS[Tool.TURN_LEFT], TOOL_KEYS[Tool.TURN_RIGHT]) == ("L", "R")
    assert TURNS == {Tool.TURN_LEFT: 1, Tool.TURN_RIGHT: -1}  # directions run counter-clockwise
    assert [drawer for drawer, _ in LAYOUT.drawer_buttons] == [*DRAWERS[Env.EDITOR], *FOOT]
    for drawer, rect in LAYOUT.drawer_buttons:
        assert drawer_button_at(LAYOUT, centre(rect)) is drawer
        assert palette_target_at(LAYOUT, centre(rect)) is drawer
        assert contains(LAYOUT.bar_area, rect[:2])
    assert palette_target_at(LAYOUT, centre(LAYOUT.board_area)) is None


def test_each_drawer_opens_by_its_initial_and_no_key_means_two_things_in_one_environment():
    # D-069: a letter may mean one thing in the editor and another in the run, never two in one
    assert set(DRAWER_KEYS) == {*DRAWERS[Env.EDITOR], *DRAWERS[Env.RUN], *FOOT} == set(Drawer)
    for drawer, key in DRAWER_KEYS.items():
        named = Drawer.INSIDE  # shown as Diagnostic in the run: D, as the editor's (D-089)
        assert key == drawer.value[0].upper() or drawer in (Drawer.HINTS, named, *FOOT[1:])
    views = [VIEW_KEYS[b] for b in ViewButton if b not in RUN_VIEWS]  # rays, motion: the run's
    editor = [*(TOOL_KEYS[t] for t in PALETTE_TOOLS), *views, MODE_KEY, LEVEL_KEYS[LevelButton.RUN]]
    editor += [DRAWER_KEYS[d] for d in (*DRAWERS[Env.EDITOR], *FOOT)]
    run = [*BUTTON_KEYS.values(), *(DRAWER_KEYS[d] for d in (*DRAWERS[Env.RUN], *FOOT))]
    for keys in (editor, run):
        assert len(set(keys)) == len(keys)
    assert drawer_key(Env.EDITOR, "F") is Drawer.FILES and drawer_key(Env.RUN, "F") is None
    assert drawer_key(Env.RUN, "S") is Drawer.SCORE and drawer_key(Env.EDITOR, "S") is None
    assert drawer_key(Env.EDITOR, "D") is Drawer.DIAGNOSTIC
    assert drawer_key(Env.RUN, "D") is Drawer.INSIDE  # the run's Diagnostic (D-089)
    assert drawer_key(Env.EDITOR, ",") is drawer_key(Env.RUN, ",") is Drawer.SETTINGS
    assert drawer_key(Env.EDITOR, "?") is drawer_key(Env.RUN, "?") is Drawer.HINTS  # H: the hand


def test_hints_settings_chapters_and_the_run_switch_sit_at_the_bars_foot_with_their_keys():
    ((run, switch),) = LAYOUT.level_buttons
    assert run is LevelButton.RUN and switch[1] + switch[3] <= SCREEN[1] - 8
    icons = dict(LAYOUT.drawer_buttons)
    hints, settings, chapters = (icons[d] for d in (Drawer.HINTS, Drawer.SETTINGS, Drawer.CHAPTERS))
    assert hints[1] + hints[3] <= settings[1] and settings[1] + settings[3] <= chapters[1]
    assert chapters[1] + chapters[3] <= switch[1]
    lowest_top = max(icons[d][1] + icons[d][3] for d in DRAWERS[Env.EDITOR])
    assert lowest_top < hints[1]  # at the foot, apart from the drawers above
    assert level_button_at(LAYOUT, centre(switch)) is run
    assert palette_target_at(LAYOUT, centre(switch)) is run
    assert contains(LAYOUT.bar_area, switch[:2])
    assert LEVEL_KEYS == {LevelButton.RUN: "Space", LevelButton.EDIT: "Esc"}
    assert [DRAWER_KEYS[d] for d in FOOT] == ["?", ",", "Tab"]
    assert [name for name, _ in LAYOUT.tabs] == ["run", "editor"]  # Run first (D-069)
    for name, rect in LAYOUT.tabs:
        assert tab_at(LAYOUT, centre(rect)) == name
    x, y = LAYOUT.caption_at  # under the tabs, inside the Editor's, over the board (D-056)
    assert x > LAYOUT.board_area[0] and TABS_HEIGHT < y < LAYOUT.board_area[1]
    assert LAYOUT.board_area[1] == TABS_HEIGHT + CAPTION_HEIGHT


def test_the_fold_handle_sits_on_the_drawers_edge_and_the_view_keeps_its_centre():
    handle = LAYOUT.fold_handle
    assert on_fold_handle(LAYOUT, centre(handle)) and not on_fold_handle(FOLDED, centre(handle))
    assert handle[0] == LAYOUT.drawer_area[0] + LAYOUT.drawer_area[2] - 1
    moved = moved_view(VIEW, LAYOUT, FOLDED)
    middle_before, middle_after = centre(LAYOUT.board_area), centre(FOLDED.board_area)
    assert cell_at(LAYOUT, VIEW, middle_before) == cell_at(FOLDED, moved, middle_after)
    assert moved.size == VIEW.size


def test_each_menu_row_has_its_info_disc_inside_it_and_unfolding_moves_it_along():
    rows = dict(LIST.menu_items)
    for kind, rect in LIST.info_buttons:
        assert contains(rows[kind], rect[:2])
        assert contains(rows[kind], (rect[0] + rect[2] - 1, rect[1] + rect[3] - 1))
        assert info_at(LIST, centre(rect)) is kind and menu_item_at(LIST, centre(rect)) is kind
    assert info_at(LIST, centre(rows[Kind.EYE])[:1] + (0,)) is None
    folded = make_layout(folded=frozenset({"Sensors"}))
    assert Kind.EYE not in dict(folded.info_buttons)


def test_the_menu_shows_only_the_parts_the_level_hands_out_and_no_empty_group():
    first = make_layout(kinds=frozenset({Kind.EYE, Kind.THRUSTER}))
    assert [kind for kind, _ in first.menu_items] == [Kind.EYE, Kind.THRUSTER]
    assert [title for title, _ in first.group_titles] == ["Sensors", "Actuators"]
    assert [kind for kind, _ in first.info_buttons] == [Kind.EYE, Kind.THRUSTER]


def test_chapters_lists_the_levels_then_the_sandbox_and_settings_its_rows_by_section():
    chapters = make_layout(Drawer.CHAPTERS, chapter=3)
    assert [k for k, _ in chapters.chapter_rows] == [0, 1, 2, 3]  # the sandbox last
    settings = make_layout(Drawer.SETTINGS)
    assert [what for what, _ in settings.setting_rows] == list(Setting)
    assert settings.section_titles == ()  # its rows, no titles (D-067)
    for layout, rows, row_at in (
        (chapters, chapters.chapter_rows, chapter_row_at),
        (settings, settings.setting_rows, setting_row_at),
    ):
        for what, rect in rows:
            assert row_at(layout, centre(rect)) == what
            assert contains(layout.drawer_area, rect[:2]) and rect[1] + rect[3] <= SCREEN[1]
            assert row_at(LAYOUT, centre(rect)) is None  # rows only in the open drawer
            assert info_at(layout, centre(dict(layout.info_buttons)[what])) == what
    assert chapters.setting_rows == () and settings.chapter_rows == ()


def test_hints_lists_its_rows_each_taken_ones_lines_under_it_and_the_shadow_last():
    assert make_layout(Drawer.HINTS).hint_rows == ()  # a level with none: a note only (D-078)
    fresh = make_layout(Drawer.HINTS, hint_lines=())
    assert [row for row, _ in fresh.hint_rows] == [HintRow(0), HintRow(1), HintRow(2)]
    assert fresh.hint_texts == () and fresh.shadow_picture is None
    for row, rect in fresh.hint_rows:
        assert hint_row_at(fresh, centre(rect)) == row and hint_row_at(LAYOUT, centre(rect)) is None
        assert info_at(fresh, centre(dict(fresh.info_buttons)[row])) == row
    taken = make_layout(Drawer.HINTS, hint_lines=(1, 2, 0), shadow=True)
    rows, texts = [rect for _, rect in taken.hint_rows], dict(taken.hint_texts)
    assert list(texts) == [0, 1]  # the shadow's says nothing: its picture does
    for k, lines in ((0, 1), (1, 2)):
        x, y, w, h = texts[k]
        assert rows[k][1] + rows[k][3] <= y and y + h < rows[k + 1][1] and h == lines * HINT_LINE
        assert contains(taken.drawer_area, (x, y)) and contains(taken.drawer_area, (x + w - 1, y))
    x, y, w, h = taken.shadow_picture
    assert w == h == DRAWER_WIDTH - 32 and rows[2][1] + rows[2][3] < y  # a square, under it
    assert y + h < SCREEN[1] and contains(taken.drawer_area, (x, y))
    lx, ly, lw, lh = taken.shadow_line  # under the picture: where to build it (D-088)
    assert y + h < ly and ly + lh < SCREEN[1] and lh == HINT_LINE
    assert contains(taken.drawer_area, (lx, ly)) and contains(taken.drawer_area, (lx + lw - 1, ly))
    hidden = make_layout(Drawer.HINTS, hint_lines=(1, 2, 0))
    assert hidden.shadow_picture is None and hidden.shadow_line is None


def test_the_run_has_its_own_drawers_its_switch_back_and_its_controls_under_the_arena():
    run = make_layout(Drawer.INSIDE, env=Env.RUN, goals=2)
    assert [drawer for drawer, _ in run.drawer_buttons] == [*DRAWERS[Env.RUN], *FOOT]
    ((back, switch),) = run.level_buttons
    assert back is LevelButton.EDIT and level_button_at(run, centre(switch)) is back
    arena, controls = run.board_area, run.controls_area
    assert controls[1] == arena[1] + arena[3] and controls[0] == arena[0]
    assert controls[1] + controls[3] < run.status_at[1]  # the status line under both
    assert LAYOUT.controls_area is None  # the editor has none
    assert [goal for goal, _ in run.goal_rows] == [Goal(0), Goal(1), Goal(None)]  # time last
    for goal, rect in run.goal_rows:
        assert goal_row_at(run, centre(rect)) == goal and contains(run.drawer_area, rect[:2])
    for drawer in (*DRAWERS[Env.RUN], *FOOT):  # the objectives, at the foot of every drawer (D-065)
        layout = make_layout(drawer, env=Env.RUN, goals=2)
        x, y, w, h = layout.goal_area
        assert y + h == SCREEN[1] and [g for g, _ in layout.goal_rows] == [
            Goal(0),
            Goal(1),
            Goal(None),
        ]
        above = [r for _, r in (*layout.setting_rows, *layout.chapter_rows, *layout.view_buttons)]
        assert all(r[1] + r[3] < y for r in above)  # under what the drawer holds
        assert layout.overview is None or layout.zoom_bar[1] + layout.zoom_bar[3] < y
    assert make_layout(None, env=Env.RUN, goals=2).goal_rows == ()  # folded: by the timeline
    assert Drawer.INSIDE in DRAWERS[Env.RUN] and len(DRAWERS[Env.RUN]) == 3
    navigator = make_layout(Drawer.NAVIGATOR, env=Env.RUN)
    assert [b for b, _ in navigator.view_buttons] == list(RUN_VIEWS)
    assert [name for name, _ in run.tabs] == ["run", "editor"] and run.caption_at[1] < arena[1]
    folded = make_layout(None, env=Env.RUN)
    assert folded.board_area[2] - run.board_area[2] == run.drawer_area[2]


def test_the_main_screen_shows_the_run_preview_only_in_diagnostic_and_navigator_keeps_it():
    # D-069: no switch; the drawer says what the editor's main screen shows
    assert main_view_for(Drawer.DIAGNOSTIC, MainView.DIAGRAM) is MainView.PREVIEW
    for last in MainView:
        assert main_view_for(Drawer.NAVIGATOR, last) is last  # it only moves the view
    for drawer in (Drawer.TOOLS, Drawer.PARTS, Drawer.FILES, *FOOT, None):
        assert main_view_for(drawer, MainView.PREVIEW) is MainView.DIAGRAM
    x, y, w, _ = LAYOUT.board_area  # nothing in the main screen's corner names a view any more
    assert palette_target_at(LAYOUT, (x + w - 30, y + 26)) is None


def test_files_has_each_levels_wins_under_its_title_a_group_that_folds():
    assert Drawer.FILES in DRAWERS[Env.EDITOR] and Drawer.FILES not in DRAWERS[Env.RUN]
    assert [title for title, _ in FILES.group_titles] == ["1.2 Aggression", "1.1 Fear"]
    assert [(row.group, row.index) for row, _ in FILES.win_rows] == [(0, 0), (0, 1), (1, 0)]
    (_, aggression), (_, fear) = FILES.group_titles
    assert aggression[1] < FILES.win_rows[0][1][1] < FILES.win_rows[1][1][1] < fear[1]
    for row, rect in FILES.win_rows:
        assert win_row_at(FILES, centre(rect)) == row and contains(FILES.drawer_area, rect[:2])
        assert info_at(FILES, centre(dict(FILES.info_buttons)[row])) == row
    assert group_at(FILES, centre(fear)) == "1.1 Fear"
    folded = make_layout(
        Drawer.FILES, frozenset({"1.2 Aggression"}), files=(("1.2 Aggression", 2), ("1.1 Fear", 1))
    )
    assert [(row.group, row.index) for row, _ in folded.win_rows] == [(1, 0)]
    assert make_layout(Drawer.FILES).win_rows == () and LAYOUT.win_rows == ()
    assert make_layout(Drawer.FILES).group_titles == ()  # no title for a level with no win


def test_files_list_scrolls_down_to_the_drawers_foot_and_its_rows_answer_where_they_show():
    many = (("1.1 Fear", 10), ("1.2 Aggression", 10))
    files = make_layout(Drawer.FILES, files=many)
    _, ly, _, lh = files.list_area
    assert files.scroll_max > 0 and files.scroll_bar is not None
    assert ly + lh == SCREEN[1] - FOOT_MARGIN  # no File under it any more (D-093)
    hidden = files.win_rows[-1][1]
    assert hidden[1] > ly + lh and win_row_at(files, centre(hidden)) is None
    bottom = make_layout(Drawer.FILES, files=many, scroll=10_000)
    assert bottom.scroll == files.scroll_max
    assert win_row_at(bottom, centre(bottom.win_rows[-1][1])) == bottom.win_rows[-1][0]


def test_navigators_overview_frames_what_the_main_screen_shows_and_a_press_moves_it_there():
    for env in Env:
        layout = make_layout(Drawer.NAVIGATOR, env=env)
        x, y, w, h = layout.overview
        above = [rect[1] + rect[3] for _, rect in layout.view_buttons] or [0]
        assert y > max(above) and contains(layout.drawer_area, (x + w, y + h))
        (out, (ox, oy, ow, oh)), (inward, (ix, _, iw, _)) = layout.zoom_buttons
        bx, by, bw, bh = layout.zoom_bar  # under the overview, between its buttons (D-065)
        assert (out, inward) == (ViewButton.ZOOM_OUT, ViewButton.ZOOM_IN) and oy > y + h
        assert ox + ow < bx and bx + bw < ix and contains(layout.drawer_area, (ix + iw, oy + oh))
        assert zoom_button_at(layout, (ix + 3, oy + 3)) is ViewButton.ZOOM_IN
        assert zoom_bar_at(layout, (bx, by + bh // 2)) == 0.0
        assert zoom_bar_at(layout, (bx + bw, by + bh // 2)) == 1.0
        assert zoom_bar_at(layout, (bx, oy + oh + 20)) is None
    assert level_of(MIN_HEX, MIN_HEX, MAX_HEX) == 0.0 and level_of(MAX_HEX, MIN_HEX, MAX_HEX) == 1
    assert value_at(level_of(34.0, MIN_HEX, MAX_HEX), MIN_HEX, MAX_HEX) == pytest.approx(34.0)
    small = overview_view(NAVIGATOR, list(hex_disc(2)))
    frame = shown_frame(NAVIGATOR, VIEW, small)
    centre_cell = to_pixel((0, 0), small.size, small.origin)
    assert contains(frame, (round(centre_cell[0]), round(centre_cell[1])))  # the view shows it
    moved = centred_on(NAVIGATOR, VIEW, small, (round(centre_cell[0]) + 10, round(centre_cell[1])))
    assert moved.size == VIEW.size and moved.origin[0] < VIEW.origin[0]  # the board slides left
    assert make_layout(Drawer.PARTS).overview is None


def test_the_overview_shows_the_zone_half_as_much_again_and_the_view_never_shows_more():
    big = list(hex_disc(5))  # a zone bigger than what HEX_SIZE shows
    bounds = board_extent(NAVIGATOR, big)
    x0, y0, x1, y1 = bounds
    reach = max(abs(to_pixel(c, 1.0, (0.0, 0.0))[0]) for c in big) + 1.0
    assert x1 >= 1.5 * reach and x0 == -x1 and y0 == -y1  # 150 % of the zone, or more (D-066)
    _, _, w, h = NAVIGATOR.board_area
    assert (x1 - x0) / (y1 - y0) == pytest.approx(w / h)  # the main screen's shape
    far = View(MIN_HEX, VIEW.origin)
    kept = kept_on_board(NAVIGATOR, far, bounds)
    assert kept.size == pytest.approx(board_view_of(NAVIGATOR.board_area, bounds).size)
    off = kept_on_board(NAVIGATOR, View(60.0, (VIEW.origin[0] + 5000, VIEW.origin[1])), bounds)
    small = overview_view(NAVIGATOR, big)
    frame = shown_frame(NAVIGATOR, off, small)
    ox, oy, ow, oh = NAVIGATOR.overview
    assert ox - 1 <= frame[0] and frame[0] + frame[2] <= ox + ow + 1  # its frame inside
    small_zone = board_extent(NAVIGATOR, list(hex_disc(1)))
    assert small_zone[2] == pytest.approx(w / HEX_SIZE / 2)  # at least what HEX_SIZE shows
