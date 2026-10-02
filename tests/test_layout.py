"""Editor layout and hit-testing (D-051). layout.py imports no pygame, so this runs headless."""

from nektoids.editor.layout import (
    CAPTION_HEIGHT,
    DRAWER_KEYS,
    DRAWERS,
    EDIT_KEYS,
    FOOT,
    LEVEL_KEYS,
    MAX_HEX,
    MIN_HEX,
    PALETTE_TOOLS,
    SCREEN,
    TABS_HEIGHT,
    TOOL_KEYS,
    TURNS,
    VIEW_KEYS,
    Drawer,
    EditButton,
    Env,
    FileButton,
    Goal,
    LevelButton,
    MainView,
    Setting,
    Tool,
    ViewButton,
    cell_at,
    centred_on,
    centred_view,
    chapter_row_at,
    contains,
    drawer_button_at,
    goal_row_at,
    group_at,
    info_at,
    level_button_at,
    main_view_at,
    make_layout,
    menu_item_at,
    moved_view,
    on_fold_handle,
    overview_view,
    palette_target_at,
    pan,
    setting_row_at,
    shown_frame,
    tab_at,
    tool_at,
    view_button_at,
    visible_cells,
    win_row_at,
    zoom,
)
from nektoids.graph.board import Kind
from nektoids.graph.hexgrid import hex_disc, to_pixel
from nektoids.levels.sandbox import free_board, tutorial_board

LAYOUT = make_layout()  # Parts open, as the editor opens
VIEW = centred_view(LAYOUT)
TOOLS = make_layout(Drawer.TOOLS)
NAVIGATOR = make_layout(Drawer.NAVIGATOR)
FOLDED = make_layout(None)


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
    tools_rows = [*TOOLS.tool_buttons, *TOOLS.edit_buttons, *TOOLS.file_buttons]
    for layout, rows in (
        (LAYOUT, LAYOUT.menu_items),
        (TOOLS, tools_rows),
        (NAVIGATOR, NAVIGATOR.view_buttons),
    ):
        assert len(layout.info_buttons) == len(rows) > 0
        for _, rect in rows:
            assert contains(layout.drawer_area, rect[:2])
            assert contains(layout.drawer_area, (rect[0] + rect[2] - 1, rect[1] + rect[3] - 1))
            assert rect[1] + rect[3] <= SCREEN[1] - 8
        tops = [rect[1] for _, rect in rows]
        assert tops == sorted(tops) and len(set(tops)) == len(tops)  # one under the other
    assert LAYOUT.tool_buttons == () and TOOLS.menu_items == () and FOLDED.info_buttons == ()


def test_parts_has_every_kind_once_and_a_click_on_a_row_picks_it():
    kinds = [kind for kind, _ in LAYOUT.menu_items]
    assert sorted(kinds, key=lambda k: k.value) == sorted(Kind, key=lambda k: k.value)
    for kind, rect in LAYOUT.menu_items:
        assert menu_item_at(LAYOUT, (rect[0] + 20, rect[1] + rect[3] // 2)) == kind


def test_folding_a_group_hides_its_items_and_lifts_the_groups_below():
    folded = make_layout(folded=frozenset({"Operators"}))
    kinds = [kind for kind, _ in folded.menu_items]
    assert Kind.DOUBLE not in kinds and Kind.HALVE not in kinds and Kind.EYE in kinds
    titles_open, titles_folded = dict(LAYOUT.group_titles), dict(folded.group_titles)
    assert titles_folded["Sensors"] == titles_open["Sensors"]
    assert titles_folded["Actuators"][1] < titles_open["Actuators"][1]
    assert folded.board_area == LAYOUT.board_area
    for title, rect in folded.group_titles:
        assert group_at(folded, centre(rect)) == title


def test_tools_runs_its_tools_then_edit_then_file_and_the_navigator_holds_the_view():
    assert [title for title, _ in TOOLS.section_titles] == ["Tools", "Edit", "File"]
    assert [tool for tool, _ in TOOLS.tool_buttons] == list(PALETTE_TOOLS)
    assert [button for button, _ in TOOLS.edit_buttons] == list(EditButton)
    assert [button for button, _ in TOOLS.file_buttons] == list(FileButton)
    assert Tool.PAN not in PALETTE_TOOLS  # the hand, in the Navigator
    sections = dict(TOOLS.section_titles)
    for title, rows in (
        ("Tools", TOOLS.tool_buttons),
        ("Edit", TOOLS.edit_buttons),
        ("File", TOOLS.file_buttons),
    ):
        _, y, _, h = sections[title]
        assert all(y + h <= rect[1] for _, rect in rows)  # under its title
    assert [title for title, _ in NAVIGATOR.section_titles] == ["View", "Overview"]
    assert [button for button, _ in NAVIGATOR.view_buttons] == [
        b
        for b in ViewButton
        if b is not ViewButton.RAYS  # the run's only
    ]
    for tool, rect in TOOLS.tool_buttons:
        assert tool_at(TOOLS, (rect[0] + 20, rect[1] + rect[3] // 2)) == tool
    for button, rect in NAVIGATOR.view_buttons:
        assert view_button_at(NAVIGATOR, (rect[0] + 20, rect[1] + rect[3] // 2)) == button
    assert tool_at(TOOLS, centre(TOOLS.board_area)) is None


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
    keys = [TOOL_KEYS[tool] for tool in PALETTE_TOOLS] + [VIEW_KEYS[b] for b in ViewButton]
    assert len(set(keys)) == len(keys) and all(len(key) == 1 for key in keys)
    assert EDIT_KEYS == {EditButton.UNDO: "Ctrl+Z", EditButton.REDO: "Ctrl+Y"}
    assert (TOOL_KEYS[Tool.TURN_LEFT], TOOL_KEYS[Tool.TURN_RIGHT]) == ("L", "R")
    assert TURNS == {Tool.TURN_LEFT: 1, Tool.TURN_RIGHT: -1}  # directions run counter-clockwise
    assert [drawer for drawer, _ in LAYOUT.drawer_buttons] == [*DRAWERS[Env.EDITOR], *FOOT]
    for drawer, rect in LAYOUT.drawer_buttons:
        assert drawer_button_at(LAYOUT, centre(rect)) is drawer
        assert palette_target_at(LAYOUT, centre(rect)) is drawer
        assert contains(LAYOUT.bar_area, rect[:2])
    assert palette_target_at(LAYOUT, centre(LAYOUT.board_area)) is None


def test_settings_chapters_and_the_run_switch_sit_at_the_bars_foot_with_their_keys():
    ((run, switch),) = LAYOUT.level_buttons
    assert run is LevelButton.RUN and switch[1] + switch[3] <= SCREEN[1] - 8
    icons = dict(LAYOUT.drawer_buttons)
    settings, chapters = icons[Drawer.SETTINGS], icons[Drawer.CHAPTERS]
    assert settings[1] + settings[3] <= chapters[1] and chapters[1] + chapters[3] <= switch[1]
    lowest_top = max(icons[d][1] + icons[d][3] for d in DRAWERS[Env.EDITOR])
    assert lowest_top < settings[1]  # at the foot, apart from the drawers above
    assert level_button_at(LAYOUT, centre(switch)) is run
    assert palette_target_at(LAYOUT, centre(switch)) is run
    assert contains(LAYOUT.bar_area, switch[:2])
    assert LEVEL_KEYS == {LevelButton.RUN: "Space", LevelButton.EDIT: "Esc"}
    assert DRAWER_KEYS == {Drawer.CHAPTERS: "Tab"}
    assert [name for name, _ in LAYOUT.tabs] == ["editor", "run"]
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
    chapters = make_layout(Drawer.CHAPTERS, chapter=3)
    assert [k for k, _ in chapters.chapter_rows] == [0, 1, 2, 3]  # the sandbox last
    settings = make_layout(Drawer.SETTINGS)
    assert [what for what, _ in settings.setting_rows] == list(Setting)
    assert [title for title, _ in settings.section_titles] == ["Run", "Display", "Help", "Sound"]
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


def test_the_run_has_its_own_drawers_its_switch_back_and_its_controls_under_the_arena():
    run = make_layout(Drawer.OBJECTIVES, env=Env.RUN, goals=2)
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
    navigator = make_layout(Drawer.NAVIGATOR, env=Env.RUN)
    assert [b for b, _ in navigator.view_buttons][-1] is ViewButton.RAYS
    assert [name for name, _ in run.tabs] == ["editor", "run"] and run.caption_at[1] < arena[1]
    folded = make_layout(None, env=Env.RUN)
    assert folded.board_area[2] - run.board_area[2] == run.drawer_area[2]


def test_the_editor_has_two_main_views_in_its_main_screens_corner_and_the_run_none():
    rects = dict(LAYOUT.view_switch)  # the Diagram view and the Run preview (D-058)
    assert list(rects) == list(MainView)
    (x1, y1, w1, _), (x2, y2, _, _) = rects.values()
    assert y1 == y2 and x1 + w1 < x2
    for view, (x, y, w, h) in rects.items():
        assert contains(LAYOUT.board_area, (x, y)) and contains(LAYOUT.board_area, (x + w, y + h))
        assert main_view_at(LAYOUT, (x + w // 2, y + h // 2)) is view
        assert palette_target_at(LAYOUT, (x + w // 2, y + h // 2)) is view  # its tooltip
    assert make_layout(env=Env.RUN).view_switch == ()


def test_files_has_a_row_per_win_under_its_label_in_the_editors_bar():
    files = make_layout(Drawer.FILES, wins=3)
    assert Drawer.FILES in DRAWERS[Env.EDITOR] and Drawer.FILES not in DRAWERS[Env.RUN]
    assert [title for title, _ in files.section_titles] == ["Wins this session"]
    assert [row.index for row, _ in files.win_rows] == [0, 1, 2]
    for row, rect in files.win_rows:
        assert win_row_at(files, centre(rect)) == row.index and contains(
            files.drawer_area, rect[:2]
        )
    assert make_layout(Drawer.FILES).win_rows == () and LAYOUT.win_rows == ()


def test_navigators_overview_frames_what_the_main_screen_shows_and_a_press_moves_it_there():
    for env in Env:
        layout = make_layout(Drawer.NAVIGATOR, env=env)
        x, y, w, h = layout.overview
        last = layout.view_buttons[-1][1]
        assert y > last[1] + last[3] and contains(layout.drawer_area, (x + w, y + h))
    small = overview_view(list(hex_disc(2)), NAVIGATOR.overview)
    frame = shown_frame(NAVIGATOR, VIEW, small)
    centre_cell = to_pixel((0, 0), small.size, small.origin)
    assert contains(frame, (round(centre_cell[0]), round(centre_cell[1])))  # the view shows it
    moved = centred_on(NAVIGATOR, VIEW, small, (round(centre_cell[0]) + 10, round(centre_cell[1])))
    assert moved.size == VIEW.size and moved.origin[0] < VIEW.origin[0]  # the board slides left
    assert make_layout(Drawer.PARTS).overview is None
