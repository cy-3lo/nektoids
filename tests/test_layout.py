"""Layout and hit-testing (D-051). layout.py imports no pygame, so this runs headless."""

import pytest

from nektoids.editor.arena_layout import BUTTON_KEYS
from nektoids.editor.buttons import FRAME, KEYS
from nektoids.editor.layout import (
    ACTION_WIDTH,
    BAR_WIDTH,
    BOARD_HEX,
    CAPTION_HEIGHT,
    DRAWER_KEYS,
    DRAWER_WIDTH,
    DRAWERS,
    EDIT_KEYS,
    EDITOR_VIEWS,
    FIELD_PAD,
    FOOT,
    FOOT_MARGIN,
    HINT_LINE,
    LEVEL_KEYS,
    MAX_HEX,
    MENU_GROUPS,
    MIN_HEX,
    PALETTE_TOOLS,
    RUN_VIEWS,
    SCREEN,
    SPEC_LINES,
    TAB_KEYS,
    TABS_HEIGHT,
    TOOL_KEYS,
    TURNS,
    VIEW_KEYS,
    Brief,
    Drawer,
    EditButton,
    Env,
    FileButton,
    Goal,
    GoalButton,
    HintRow,
    Knob,
    LevelButton,
    MadeGoal,
    MainView,
    Piece,
    Setting,
    Shown,
    Start,
    Stepper,
    Tool,
    ViewButton,
    action_at,
    along,
    bin_at,
    bin_rect,
    board_field_at,
    board_view,
    brief_field_at,
    cell_at,
    centred_view,
    chapter_row_at,
    contains,
    drawer_button_at,
    drawer_key,
    file_button_at,
    goal_button_at,
    goal_row_at,
    group_at,
    hint_row_at,
    info_at,
    knob_at,
    level_button_at,
    level_field_at,
    level_of,
    main_view_for,
    make_layout,
    menu_item_at,
    moved_view,
    on_fold_handle,
    palette_target_at,
    pan,
    passkey_at,
    piece_row_at,
    scroll_bar_at,
    scroll_for,
    scroll_thumb,
    setting_row_at,
    slider_parts,
    start_row_at,
    step_buttons,
    stepper_at,
    tab_at,
    tab_beside,
    tab_key_to,
    value_at,
    view_button_at,
    visible_cells,
    win_row_at,
    word_at,
    zoom,
    zoom_bar_at,
    zoom_button_at,
)
from nektoids.graph.board import Kind
from nektoids.graph.hexgrid import SQRT3, hex_disc, to_pixel
from nektoids.levels.arenas import arenas
from nektoids.levels.objectives import Count, Target, Verb
from nektoids.levels.sandbox import free_board, tutorial_board

LAYOUT = make_layout()  # Parts open, every part handed out, no Wheel under it (D-401)
VIEW = centred_view(LAYOUT)
FILES = make_layout(Drawer.FILES, files=(("1.2 Aggression", 2), ("1.1 Fear", 1)))
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
        (FILES, (*FILES.win_rows, *FILES.file_buttons)),
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
    kinds = [kind for kind, _ in LAYOUT.menu_items]
    assert sorted(kinds, key=lambda k: k.value) == sorted(Kind, key=lambda k: k.value)
    for kind, rect in LAYOUT.menu_items:
        assert menu_item_at(LAYOUT, (rect[0] + 20, rect[1] + rect[3] // 2)) == kind


def test_parts_lists_down_to_the_drawers_foot_with_no_wheel_under_it():
    _, ly, _, lh = LAYOUT.list_area  # the Wheel left the Board (D-401)
    assert LAYOUT.wheel_fold is None and LAYOUT.wheel_view is None
    assert ly + lh == SCREEN[1] - FOOT_MARGIN
    assert make_layout(Drawer.FILES).wheel_fold is None and FILES.wheel_view is None


def test_parts_lists_every_part_unscrolled_and_a_long_list_scrolls_by_its_bar():
    assert LAYOUT.scroll_max == 0 and LAYOUT.scroll_bar is None and scroll_thumb(LAYOUT) is None
    wins = (("1.1 Fear", 10), ("1.2 Aggression", 10))
    many = make_layout(Drawer.FILES, files=wins)
    assert many.scroll_max > 0 and many.scroll_bar is not None
    bottom = make_layout(Drawer.FILES, files=wins, scroll=10_000)
    assert bottom.scroll == many.scroll_max
    assert make_layout(Drawer.FILES, files=wins, scroll=-5).scroll == 0
    x, y, w, h = many.scroll_bar  # beside the rows, inside the drawer's edge
    assert x + w < BAR_WIDTH + DRAWER_WIDTH
    assert scroll_bar_at(many, (x + w // 2, y + h // 2)) and not scroll_bar_at(LAYOUT, (x, y))
    assert scroll_for(many, y) == 0 and scroll_for(many, y + h) == many.scroll_max
    _, top, _, length = scroll_thumb(many)
    assert top == y and scroll_thumb(bottom)[1] + length == y + h


def _shown_rows(layout):
    """Every row the open drawer holds, and what else scrolls with them, as rects."""
    rows = [
        rect
        for listed in (
            layout.menu_items,
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


MOST = {  # each drawer with the most it may show: 16 levels, 3 objectives, every hint taken
    "chapters": (("Chapter 0", 6), ("Chapter 1", 4), ("Chapter 2", 3), ("Chapter 3", 3)),
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


SEVEN = (("Chapter 1", 7),)  # a chapter of seven levels


def test_chapters_scrolls_in_the_run_and_its_rows_answer_only_where_they_show():
    chapters = make_layout(Drawer.CHAPTERS, env=Env.RUN, goals=3, chapters=SEVEN)
    assert chapters.scroll_max > 0 and scroll_bar_at(chapters, centre(chapters.scroll_bar))
    _, ly, _, lh = chapters.list_area
    hidden = [k for k, (_, y, _, h) in chapters.chapter_rows if y + h // 2 >= ly + lh]
    assert hidden and not passkey_at(chapters, centre(chapters.passkey_field))
    sandbox = dict(chapters.chapter_rows)[hidden[-1]]
    assert chapter_row_at(chapters, centre(sandbox)) is None  # out of sight, it does not answer
    end = make_layout(Drawer.CHAPTERS, env=Env.RUN, goals=3, chapters=SEVEN, scroll=10_000)
    assert end.scroll == chapters.scroll_max
    assert chapter_row_at(end, centre(dict(end.chapter_rows)[hidden[-1]])) == hidden[-1]
    assert passkey_at(end, centre(end.passkey_field))
    for goal, rect in end.goal_rows:  # the objectives stay put, and their info discs answer
        assert rect == dict(chapters.goal_rows)[goal] and goal_row_at(end, centre(rect)) == goal
    disc = dict(end.info_buttons)[Goal(0)]
    assert info_at(end, centre(disc)) == Goal(0)


def test_a_tutored_levels_parts_fit_unscrolled_so_a_steps_rows_would_show():
    for level in (level for level in arenas() if level.tutorial is not None):  # D-335
        board = level.new_board()
        kinds = frozenset(kind for kind in Kind if board.total(kind) != 0)
        assert make_layout(kinds=kinds).scroll_max == 0, level.title


def test_parts_lists_sensors_then_actuators_then_operators_and_the_numbers_follow():
    assert [title for title, _ in LAYOUT.group_titles] == ["Sensors", "Actuators", "Operators"]
    kinds = [kind for kind, _ in LAYOUT.menu_items]  # D-069: the thruster third, its key 3
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


def test_the_boards_drawers_are_parts_files_and_diagnostic_and_the_editor_has_its_action():
    # D-401: Tools, Navigator and the Wheel left the Board for the buttons round it
    assert DRAWERS[Env.BOARD] == (Drawer.PARTS, Drawer.FILES, Drawer.DIAGNOSTIC)
    for layout in (LAYOUT, FILES, make_layout(None)):
        assert layout.action_at is None and action_at(layout, centre(layout.board_area)) is None
        assert layout.edit_buttons == ()
    editor = make_layout(Drawer.OBJECTS, env=Env.EDITOR, editor=True)
    x, y, w, h = editor.action_at  # the Editor's, centred atop its main screen (D-314)
    bx, by, bw, _ = editor.board_area
    assert abs(x + w / 2 - (bx + bw / 2)) <= 1 and y > by and w == h == ACTION_WIDTH
    assert action_at(editor, (x + 5, y + 5)) is Shown.ACTION
    assert make_layout(env=Env.RUN).action_at is None
    assert [title for title, _ in FILES.section_titles] == ["Wins this session", "Save/Load"]
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
    keys = [TOOL_KEYS[tool] for tool in PALETTE_TOOLS]  # no view keys: the view is fixed (D-401)
    assert len(set(keys)) == len(keys)
    assert all(len(key) == 1 for key in keys if key != TOOL_KEYS[Tool.DELETE])  # one character
    assert TOOL_KEYS[Tool.DELETE] == "Del"  # Backspace and Delete, on the physical key (D-069)
    assert EDIT_KEYS == {EditButton.UNDO: "Ctrl+Z", EditButton.REDO: "Ctrl+Y"}
    assert (TOOL_KEYS[Tool.TURN_LEFT], TOOL_KEYS[Tool.TURN_RIGHT]) == ("L", "R")
    assert TURNS == {Tool.TURN_LEFT: 1, Tool.TURN_RIGHT: -1}  # directions run counter-clockwise
    assert [drawer for drawer, _ in LAYOUT.drawer_buttons] == [*DRAWERS[Env.BOARD], *FOOT]
    for drawer, rect in LAYOUT.drawer_buttons:
        assert drawer_button_at(LAYOUT, centre(rect)) is drawer
        assert palette_target_at(LAYOUT, centre(rect)) is drawer
        assert contains(LAYOUT.bar_area, rect[:2])
    assert palette_target_at(LAYOUT, centre(LAYOUT.board_area)) is None


def test_each_drawer_opens_by_its_initial_and_no_key_means_two_things_in_one_environment():
    # D-069: a letter may mean one thing on the Board and another in the run, never two in one
    assert set(DRAWER_KEYS) == {*(d for env in Env for d in DRAWERS[env]), *FOOT} == set(Drawer)
    for drawer, key in DRAWER_KEYS.items():
        named = Drawer.INSIDE  # shown as Diagnostic in the run: D, as the Board's (D-089)
        assert key == drawer.value[0].upper() or drawer in (Drawer.HINTS, named, *FOOT[1:])
    board_scene = [*(key for key in KEYS.values() if len(key) == 1), LEVEL_KEYS[LevelButton.RUN]]
    board_scene += [DRAWER_KEYS[d] for d in (*DRAWERS[Env.BOARD], *FOOT)]
    run = [*BUTTON_KEYS.values(), *(DRAWER_KEYS[d] for d in (*DRAWERS[Env.RUN], *FOOT))]
    editor = [TOOL_KEYS[t] for t in (Tool.MOVE, Tool.TURN_LEFT, Tool.TURN_RIGHT, Tool.LESS)]
    editor += [TOOL_KEYS[Tool.MORE], TOOL_KEYS[Tool.DELETE], "1", "2", LEVEL_KEYS[LevelButton.RUN]]
    editor += [VIEW_KEYS[b] for b in (*EDITOR_VIEWS, ViewButton.ZOOM_IN, ViewButton.ZOOM_OUT)]
    editor += [
        VIEW_KEYS[ViewButton.CENTRE],
        *(DRAWER_KEYS[d] for d in (*DRAWERS[Env.EDITOR], *FOOT)),
    ]
    for keys in (board_scene, run, editor):  # the Editor's: D-301
        assert len(set(keys)) == len(keys)
    assert drawer_key(Env.BOARD, "F") is Drawer.FILES and drawer_key(Env.RUN, "F") is None
    assert drawer_key(Env.RUN, "S") is Drawer.SCORE and drawer_key(Env.BOARD, "S") is None
    assert drawer_key(Env.BOARD, "D") is Drawer.DIAGNOSTIC
    assert drawer_key(Env.RUN, "D") is Drawer.INSIDE  # the run's Diagnostic (D-089)
    assert drawer_key(Env.BOARD, ",") is drawer_key(Env.RUN, ",") is Drawer.SETTINGS
    assert drawer_key(Env.BOARD, "?") is drawer_key(Env.RUN, "?") is Drawer.HINTS  # H: the hand


def test_hints_settings_chapters_and_the_run_switch_sit_at_the_bars_foot_with_their_keys():
    ((run, switch),) = LAYOUT.level_buttons
    assert run is LevelButton.RUN and switch[1] + switch[3] <= SCREEN[1] - 8
    icons = dict(LAYOUT.drawer_buttons)
    hints, settings, chapters = (icons[d] for d in (Drawer.HINTS, Drawer.SETTINGS, Drawer.CHAPTERS))
    assert hints[1] + hints[3] <= settings[1] and settings[1] + settings[3] <= chapters[1]
    assert chapters[1] + chapters[3] <= switch[1]
    lowest_top = max(icons[d][1] + icons[d][3] for d in DRAWERS[Env.BOARD])
    assert lowest_top < hints[1]  # at the foot, apart from the drawers above
    assert level_button_at(LAYOUT, centre(switch)) is run
    assert palette_target_at(LAYOUT, centre(switch)) is run
    assert contains(LAYOUT.bar_area, switch[:2])
    assert LEVEL_KEYS == {LevelButton.RUN: "Space", LevelButton.BOARD: "Tab"}  # D-304
    assert [DRAWER_KEYS[d] for d in FOOT] == ["?", ",", "Esc"]
    assert [name for name, _ in LAYOUT.tabs] == ["run", "board"]  # Run first (D-069)
    for name, rect in LAYOUT.tabs:
        assert tab_at(LAYOUT, centre(rect)) == name
    x, y = LAYOUT.caption_at  # under the tabs, inside the Board's, over the board (D-056)
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
    rows = dict(LAYOUT.menu_items)
    for kind, rect in LAYOUT.info_buttons:
        assert contains(rows[kind], rect[:2])
        assert contains(rows[kind], (rect[0] + rect[2] - 1, rect[1] + rect[3] - 1))
        assert info_at(LAYOUT, centre(rect)) is kind and menu_item_at(LAYOUT, centre(rect)) is kind
    assert info_at(LAYOUT, centre(rows[Kind.EYE])[:1] + (0,)) is None
    folded = make_layout(folded=frozenset({"Sensors"}))
    assert Kind.EYE not in dict(folded.info_buttons)


def test_the_menu_shows_only_the_parts_the_level_hands_out_and_no_empty_group():
    first = make_layout(kinds=frozenset({Kind.EYE, Kind.THRUSTER}))
    assert [kind for kind, _ in first.menu_items] == [Kind.EYE, Kind.THRUSTER]
    assert [title for title, _ in first.group_titles] == ["Sensors", "Actuators"]
    assert [kind for kind, _ in first.info_buttons] == [Kind.EYE, Kind.THRUSTER]


def test_chapters_lists_the_levels_then_the_sandbox_and_settings_its_rows_by_section():
    chapters = make_layout(Drawer.CHAPTERS, chapters=(("Chapter 1", 3),))
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
    assert [row for row, _ in fresh.hint_rows] == [HintRow(0), HintRow(1)]  # D-353
    assert fresh.hint_texts == () and fresh.shadow_picture is None
    for row, rect in fresh.hint_rows:
        assert hint_row_at(fresh, centre(rect)) == row and hint_row_at(LAYOUT, centre(rect)) is None
        assert info_at(fresh, centre(dict(fresh.info_buttons)[row])) == row
    taken = make_layout(Drawer.HINTS, hint_lines=(2, 0), shadow=True)
    rows, texts = [rect for _, rect in taken.hint_rows], dict(taken.hint_texts)
    assert list(texts) == [0]  # the shadow's says nothing: its picture does
    x, y, w, h = texts[0]
    assert rows[0][1] + rows[0][3] <= y and y + h < rows[1][1] and h == 2 * HINT_LINE
    assert contains(taken.drawer_area, (x, y)) and contains(taken.drawer_area, (x + w - 1, y))
    x, y, w, h = taken.shadow_picture
    assert w == h == DRAWER_WIDTH - 32 and rows[1][1] + rows[1][3] < y  # a square, under it
    assert y + h < SCREEN[1] and contains(taken.drawer_area, (x, y))
    lx, ly, lw, lh = taken.shadow_line  # under the picture: where to build it (D-088)
    assert y + h < ly and ly + lh < SCREEN[1] and lh == HINT_LINE
    assert contains(taken.drawer_area, (lx, ly)) and contains(taken.drawer_area, (lx + lw - 1, ly))
    hidden = make_layout(Drawer.HINTS, hint_lines=(2, 0))
    assert hidden.shadow_picture is None and hidden.shadow_line is None


def test_the_run_has_its_own_drawers_its_switch_back_and_its_controls_under_the_arena():
    run = make_layout(Drawer.INSIDE, env=Env.RUN, goals=2)
    assert [drawer for drawer, _ in run.drawer_buttons] == [*DRAWERS[Env.RUN], *FOOT]
    ((back, switch),) = run.level_buttons
    assert back is LevelButton.BOARD and level_button_at(run, centre(switch)) is back
    arena, controls = run.board_area, run.controls_area
    assert controls[1] == arena[1] + arena[3] and controls[0] == arena[0]
    assert controls[1] + controls[3] < run.status_at[1]  # the status line under both
    assert LAYOUT.controls_area is None  # the Board has none
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
    assert [name for name, _ in run.tabs] == ["run", "board"] and run.caption_at[1] < arena[1]
    folded = make_layout(None, env=Env.RUN)
    assert folded.board_area[2] - run.board_area[2] == run.drawer_area[2]


def test_the_main_screen_shows_the_run_preview_only_in_diagnostic():
    # D-069: no switch; the drawer says what the Board's main screen shows
    assert main_view_for(Drawer.DIAGNOSTIC) is MainView.PREVIEW
    for drawer in (Drawer.PARTS, Drawer.FILES, *FOOT, None):
        assert main_view_for(drawer) is MainView.DIAGRAM
    x, y, w, _ = LAYOUT.board_area  # nothing in the main screen's corner names a view any more
    assert palette_target_at(LAYOUT, (x + w - 30, y + 26)) is None


def test_files_has_each_levels_wins_under_its_title_a_group_that_folds():
    assert Drawer.FILES in DRAWERS[Env.BOARD] and Drawer.FILES not in DRAWERS[Env.RUN]
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


def test_files_list_scrolls_above_the_board_as_text_whose_save_and_field_still_answer():
    many = (("1.1 Fear", 10), ("1.2 Aggression", 10))
    files = make_layout(Drawer.FILES, files=many)
    _, ly, _, lh = files.list_area
    assert files.scroll_max > 0 and files.scroll_bar is not None
    (save, rect), field = files.file_buttons[0], files.board_field
    assert save is FileButton.SAVE and ly + lh < rect[1] < field[1]  # under the list (D-206)
    assert field[1] + field[3] <= SCREEN[1] - FOOT_MARGIN  # at the drawer's foot
    assert file_button_at(files, centre(rect)) is save and board_field_at(files, centre(field))
    assert info_at(files, centre(dict(files.info_buttons)[save])) is save  # never hidden
    assert LAYOUT.board_field is None and LAYOUT.file_buttons == ()  # Parts: not there
    hidden = files.win_rows[-1][1]
    assert hidden[1] > ly + lh and win_row_at(files, centre(hidden)) is None
    bottom = make_layout(Drawer.FILES, files=many, scroll=10_000)
    assert bottom.scroll == files.scroll_max
    assert win_row_at(bottom, centre(bottom.win_rows[-1][1])) == bottom.win_rows[-1][0]


def test_navigators_overview_sits_over_its_zoom_bar_between_its_buttons():
    for env in (Env.RUN, Env.EDITOR):  # the Board has none (D-401)
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
    assert make_layout(Drawer.PARTS).overview is None


def test_the_board_shows_at_one_size_centred_the_largest_zone_and_every_button_whole():
    # D-401: 38 px, cell (0, 0) at the centre, with a drawer open or not; nothing moves it
    for layout, side in ((make_layout(None), 159), (LAYOUT, 35)):
        view = board_view(layout)
        x, y, w, h = layout.board_area
        assert view.size == BOARD_HEX and view.origin == (x + w / 2, y + h / 2)
        points = [to_pixel(cell, view.size, view.origin) for cell in FRAME]
        reach_x, reach_y = SQRT3 / 2 * view.size, view.size  # a pointy-top hex's half
        left = min(px for px, _ in points) - reach_x - x
        right = x + w - max(px for px, _ in points) - reach_x
        top = min(py for _, py in points) - reach_y - y
        bottom = y + h - max(py for _, py in points) - reach_y
        assert min(top, bottom) >= 11 - 1e-9 and min(left, right) >= side


def test_the_sandbox_has_a_third_tab_the_editor_with_its_own_drawers_and_switch_to_the_run():
    for env in Env:  # D-301: every environment of the sandbox shows the three tabs
        layout = make_layout(None, env=env, editor=True)
        assert [name for name, _ in layout.tabs] == ["run", "board", "editor"]
        assert [TAB_KEYS[name] for name, _ in layout.tabs] == ["F1", "F2", "F3"]  # D-303
        for name, rect in layout.tabs:
            assert tab_at(layout, centre(rect)) == name and rect[1] + rect[3] == TABS_HEIGHT
    assert [name for name, _ in make_layout(None, env=Env.RUN).tabs] == ["run", "board"]
    editor = make_layout(Drawer.NAVIGATOR, env=Env.EDITOR, editor=True)
    objects = [Drawer.OBJECTS, Drawer.PARTS, Drawer.GOALS, Drawer.TEXT, Drawer.FILES]
    objects += [Drawer.NAVIGATOR]
    assert editor.editor and [d for d, _ in editor.drawer_buttons] == [*objects, *FOOT]
    assert [b for b, _ in editor.level_buttons] == [LevelButton.RUN]  # Space runs it
    assert [b for b, _ in editor.view_buttons] == [ViewButton.RAYS]
    assert editor.overview is not None and editor.zoom_bar is not None
    assert editor.controls_area is None and editor.action_at is not None  # the plane, D-314
    assert editor.board_area[1] + editor.board_area[3] == editor.status_at[1] - 6
    tabs = dict(editor.tabs)
    assert palette_target_at(editor, centre(tabs["run"])) == "run"
    assert palette_target_at(editor, centre(tabs["editor"])) is None  # this one
    assert drawer_key(Env.EDITOR, "N") is Drawer.NAVIGATOR and drawer_key(Env.EDITOR, "W") is None
    assert drawer_key(Env.EDITOR, "O") is Drawer.OBJECTS and drawer_key(Env.BOARD, "O") is None


def test_objects_lists_the_planes_objects_then_undo_and_redo_over_the_wheel_as_tools_does():
    layout = make_layout(Drawer.OBJECTS, env=Env.EDITOR, editor=True)  # D-301
    pieces = [Piece.LIGHT, Piece.OBSTACLE, Piece.MARK, Piece.START]  # D-306
    assert [p for p, _ in layout.piece_rows] == pieces
    assert [b for b, _ in layout.edit_buttons] == [EditButton.UNDO, EditButton.REDO]
    assert [t for t, _ in layout.section_titles] == ["Plane"]  # Undo and Redo need none
    assert layout.scroll_max == 0  # all of them over the Wheel, no scroll bar
    lowest = max(r[1] + r[3] for _, r in (*layout.piece_rows, *layout.edit_buttons))
    assert layout.wheel_view is not None and lowest < layout.wheel_fold[1]  # all over the Wheel
    for piece, rect in layout.piece_rows:
        assert piece_row_at(layout, centre(rect)) is piece and contains(
            layout.drawer_area, rect[:2]
        )
    assert piece_row_at(layout, centre(layout.board_area)) is None
    folded = make_layout(Drawer.OBJECTS, env=Env.EDITOR, editor=True, wheel_folded=True)
    assert folded.wheel_view is None and folded.wheel_fold[1] > layout.wheel_fold[1]
    assert LAYOUT.piece_rows == ()


def test_tab_goes_round_the_tabs_and_their_tooltips_name_tab_or_shift_tab_to_reach_them():
    level = {env: make_layout(None, env=env) for env in (Env.RUN, Env.BOARD)}  # D-304
    assert tab_beside(level[Env.RUN]) == tab_beside(level[Env.RUN], back=True) == "board"
    assert tab_beside(level[Env.BOARD]) == "run"
    assert (
        tab_key_to(level[Env.RUN], "board") == "Tab" and tab_key_to(level[Env.RUN], "run") is None
    )
    sandbox = {env: make_layout(None, env=env, editor=True) for env in Env}
    assert [tab_beside(sandbox[e]) for e in (Env.RUN, Env.BOARD, Env.EDITOR)] == [
        "board",
        "editor",
        "run",
    ]
    assert tab_beside(sandbox[Env.RUN], back=True) == "editor"
    assert tab_key_to(sandbox[Env.BOARD], "editor") == "Tab"
    assert tab_key_to(sandbox[Env.BOARD], "run") == "Shift+Tab"


def test_text_holds_the_title_a_row_high_the_spec_taller_then_the_author_under_their_labels():
    layout = make_layout(Drawer.TEXT, env=Env.EDITOR, editor=True)  # D-305, D-331
    (title, high), (spec, tall), (author, low) = layout.brief_fields
    assert (title, spec, author) == (Brief.TITLE, Brief.SPEC, Brief.AUTHOR)
    assert [t for t, _ in layout.section_titles] == ["Title", "Spec", "Author"]
    assert high[3] == make_layout(Drawer.OBJECTS, env=Env.EDITOR, editor=True).piece_rows[0][1][3]
    assert tall[3] == SPEC_LINES * HINT_LINE + 2 * FIELD_PAD and tall[1] > high[1] + high[3]
    assert low[3] == high[3] and low[1] > tall[1] + tall[3]
    for field, rect in layout.brief_fields:
        assert brief_field_at(layout, centre(rect)) is field and contains(
            layout.drawer_area, rect[:2]
        )
    assert brief_field_at(layout, centre(layout.board_area)) is None
    assert drawer_key(Env.EDITOR, "T") is Drawer.TEXT and drawer_key(Env.BOARD, "T") is None


def test_goals_shows_the_time_then_each_goals_name_over_its_words_and_a_slider_for_a_setting():
    two = make_layout(Drawer.GOALS, env=Env.EDITOR, editor=True, made=(True, False))  # D-308
    assert [t for t, _ in two.section_titles] == ["Time allowed"]  # the names title the goals
    assert [k for k, _ in two.knobs] == [Knob(None), Knob(0)]  # the second goal takes none
    assert [h for h, _ in two.goal_heads] == [MadeGoal(0), MadeGoal(1)] and not two.goal_buttons
    words = [w.word for w, _ in two.goal_words if w.goal == 0]
    assert words == [*Verb, *Count, *Target] and len(two.goal_words) == 18
    tops = sorted({rect[1] for w, rect in two.goal_words if w.goal == 0})
    assert len(tops) == 3  # a row each: the verbs, how many, the targets
    for top in tops:  # each row fills the drawer's width, its buttons apart
        row = sorted(rect for _, rect in two.goal_words if rect[1] == top)
        assert row[0][0] == two.goal_heads[0][1][0] and row[-1][0] + row[-1][2] == 284
        assert all(a[0] + a[2] < b[0] for a, b in zip(row, row[1:], strict=False))
    assert two.scroll_max == 0  # two goals and their settings fit, unscrolled
    one = make_layout(Drawer.GOALS, env=Env.EDITOR, editor=True, made=(False,), addable=True)
    assert [b for b, _ in one.goal_buttons] == [GoalButton.ADD]
    none = make_layout(Drawer.GOALS, env=Env.EDITOR, editor=True, addable=True)
    assert not none.goal_heads and [b for b, _ in none.goal_buttons] == [GoalButton.ADD]
    assert drawer_key(Env.EDITOR, "G") is Drawer.GOALS and drawer_key(Env.BOARD, "G") is None


def test_goals_finds_a_word_a_bin_add_and_a_sliders_track_apart_from_its_value():
    layout = make_layout(Drawer.GOALS, env=Env.EDITOR, editor=True, made=(True,), addable=True)
    for word, rect in layout.goal_words:
        assert word_at(layout, centre(rect)) == word and bin_at(layout, centre(rect)) is None
    head = layout.goal_heads[0][1]
    assert bin_at(layout, centre(bin_rect(head))) == 0 and bin_at(layout, head[:2]) is None
    assert word_at(layout, (head[0] + 1, head[1] + 1)) is None  # the name: no word
    add = layout.goal_buttons[0][1]
    assert goal_button_at(layout, centre(add)) is GoalButton.ADD
    knob, rect = layout.knobs[1]
    label, track, value = slider_parts(rect)
    assert knob_at(layout, centre(track)) == (knob, False)
    assert knob_at(layout, centre(value)) == (knob, True)  # its box: typed, not dragged
    assert label[0] < track[0] < track[0] + track[2] < value[0]
    assert along(track, track[0] - 9) == 0.0 and along(track, track[0] + track[2] + 9) == 1.0
    assert along(track, track[0] + track[2] / 2) == 0.5
    assert word_at(layout, centre(layout.board_area)) is None


def test_the_editors_files_holds_copy_the_level_then_a_field_to_paste_one_into():
    layout = make_layout(Drawer.FILES, env=Env.EDITOR, editor=True)  # D-310
    assert [t for t, _ in layout.section_titles] == ["Save/Load"]  # Start from: no title, D-322
    (button, row), (share, under), field = *layout.file_buttons, layout.level_field
    assert (button, share) == (FileButton.LEVEL, FileButton.SHARE)  # D-320: Share level
    note = layout.share_note  # under Copy and Paste, its line under it (D-321)
    assert field[1] + field[3] <= under[1] and under[1] + under[3] <= note[1]
    assert field[1] > row[1] + row[3] and field[3] == row[3] and not layout.win_rows
    assert level_field_at(layout, centre(field)) and not level_field_at(layout, centre(row))
    assert file_button_at(layout, centre(row)) is FileButton.LEVEL
    assert layout.board_field is None  # the board's, the Board's alone
    board_scene = make_layout(Drawer.FILES, env=Env.BOARD)
    assert board_scene.level_field is None and board_scene.board_field is not None
    assert drawer_key(Env.EDITOR, "F") is Drawer.FILES


def test_start_from_lists_a_blank_plane_then_every_shipped_level_under_the_paste_field():
    chapters = (("Chapter 1", 8),)  # D-310; the sandbox's plane no longer among them (D-342)
    layout = make_layout(Drawer.FILES, env=Env.EDITOR, editor=True, starts=8, chapters=chapters)
    starts = [s for s, _ in layout.start_rows]
    assert starts == [Start(None), *(Start(k) for k in range(8))]
    assert layout.start_rows[0][1][1] > layout.level_field[1] + layout.level_field[3]
    assert layout.scroll_max > 0  # the nine and Save/Load run past the foot: it scrolls (D-096)
    for start, rect in layout.start_rows:
        shown = contains(layout.list_area, centre(rect))
        assert start_row_at(layout, centre(rect)) == (start if shown else None)
    assert start_row_at(layout, centre(layout.level_field)) is None


def test_the_editors_parts_gives_the_board_size_then_each_part_a_row_with_minus_and_plus():
    layout = make_layout(Drawer.PARTS, env=Env.EDITOR, editor=True)  # D-315
    assert [t for t, _ in layout.section_titles] == ["Board"]
    assert [t for t, _ in layout.group_titles] == ["Sensors", "Actuators", "Operators"]
    order = [k for _, kinds in MENU_GROUPS for k in kinds]  # as the Board's Parts groups them
    assert [s for s, _ in layout.steppers] == [Stepper(None), *(Stepper(k) for k in order)]
    assert not layout.menu_items and layout.scroll_max == 0  # not the Board's, and it fits
    for what, row in layout.steppers:
        minus, plus = step_buttons(row)
        assert row[0] < minus[0] < plus[0] and plus[0] + plus[2] < row[0] + row[2]
        assert stepper_at(layout, centre(minus)) == (what, -1)
        assert stepper_at(layout, centre(plus)) == (what, 1)
        assert stepper_at(layout, (row[0] + 30, row[1] + 20)) is None  # its name: nothing
    assert drawer_key(Env.EDITOR, "P") is Drawer.PARTS
    shut = make_layout(Drawer.PARTS, frozenset({"Operators"}), env=Env.EDITOR, editor=True)
    unfolded = [k for title, kinds in MENU_GROUPS if title != "Operators" for k in kinds]
    assert [s.kind for s, _ in shut.steppers] == [None, *unfolded]  # the operators folded
    assert group_at(shut, centre(shut.group_titles[2][1])) == "Operators"


def test_files_ends_with_erase_all_under_the_field_to_paste_a_board():
    (save, top), (erase, rect) = FILES.file_buttons  # D-321, D-401
    assert (save, erase) == (FileButton.SAVE, FileButton.ERASE)
    field = FILES.board_field
    assert top[1] < field[1] < rect[1] and rect[1] + rect[3] <= SCREEN[1] - FOOT_MARGIN
    assert file_button_at(FILES, centre(rect)) is FileButton.ERASE
    assert info_at(FILES, centre(dict(FILES.info_buttons)[erase])) is erase


def test_a_title_of_chapters_scrolled_under_the_objectives_is_still_the_lists():
    chapters = make_layout(Drawer.CHAPTERS, env=Env.RUN, goals=3, chapters=SEVEN)  # D-333
    _, top, _, room = chapters.list_area
    under = [t for t, (_, y, _, _) in chapters.section_titles if y >= top + room]
    assert "Passkey" in under  # scrolled down, under the list's area, as far as the objectives
    assert [title for title, _ in chapters.foot_titles] == ["Objectives"]


SHIPPED = (("Chapter 0", 0), ("Chapter 1", 4), ("Chapter 2", 1), ("Chapter 3", 3))


def test_chapters_lists_each_chapter_with_levels_under_a_title_that_folds():
    chapters = make_layout(Drawer.CHAPTERS, chapters=SHIPPED)  # D-326
    titles = dict(chapters.group_titles)
    assert list(titles) == ["Chapter 1", "Chapter 2", "Chapter 3"]  # none for an empty chapter
    assert [k for k, _ in chapters.chapter_rows] == list(range(9))  # the sandbox last
    for title, rect in titles.items():
        assert group_at(chapters, centre(rect)) == title
    shut = make_layout(Drawer.CHAPTERS, frozenset({"Chapter 1", "Chapter 3"}), chapters=SHIPPED)
    assert [k for k, _ in shut.chapter_rows] == [4, 8] and shut.folded == {"Chapter 1", "Chapter 3"}
    assert [title for title, _ in shut.group_titles] == list(titles)  # its titles stay
    assert [title for title, _ in shut.section_titles] == ["Build your level", "Passkey"]  # D-341


def test_start_from_is_a_list_of_its_own_under_a_rule_its_chapters_folding():
    files = make_layout(Drawer.FILES, env=Env.EDITOR, editor=True, starts=8, chapters=SHIPPED)
    rule, area = files.files_rule, files.list_area  # D-322, D-326
    assert files.level_field[1] < files.share_note[1] < rule[1] < area[1]  # Save/Load stays above
    titles = ["Chapter 1", "Chapter 2", "Chapter 3"]  # no sandbox's plane (D-342)
    assert [t for t, _ in files.group_titles] == titles
    assert [s.index for s, _ in files.start_rows] == [None, *range(8)]  # Blank level first
    assert files.start_rows[0][1][1] >= area[1] and level_field_at(files, centre(files.level_field))
    shut = make_layout(
        Drawer.FILES,
        frozenset({"Chapter 1", "Chapter 3"}),
        env=Env.EDITOR,
        editor=True,
        starts=8,
        chapters=SHIPPED,
    )
    assert [s.index for s, _ in shut.start_rows] == [None, 4] and shut.scroll_max == 0
