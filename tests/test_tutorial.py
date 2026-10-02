"""Tutorials and hints (D-039). tutorial.py imports no pygame."""

from nektoids.editor.layout import (
    SCREEN,
    Drawer,
    Env,
    LevelButton,
    Tool,
    centred_view,
    contains,
    make_layout,
)
from nektoids.editor.router import Screen
from nektoids.editor.tutorial import (
    GAP,
    Action,
    Context,
    Tutorial,
    _crosses,
    allows,
    answer,
    box_rect,
    drawer_for,
    guided,
    is_area,
    met,
    next_rect,
    panels,
    skip_rect,
    target_rects,
    target_spots,
)
from nektoids.graph.board import Kind
from nektoids.graph.hexgrid import NW, SW
from nektoids.levels.arenas import arenas
from nektoids.levels.objectives import Outcome

LAYOUT = make_layout()
VIEW = centred_view(LAYOUT)
RUN_LAYOUT = make_layout(Drawer.OBJECTIVES, env=Env.RUN, goals=1)  # the run's frame (D-057)


def layout_on(screen: Screen, step=None):
    """The editor's layout, or the run's with the drawer `step` opens."""
    if screen is not Screen.RUN:
        return LAYOUT
    return make_layout(drawer_for(step) or Drawer.OBJECTIVES, env=Env.RUN, goals=1)


LEVELS = {level.title: level for level in arenas()}
R = 3  # Fear's steps in the run, before the editor's (D-060): the swimmer, Objectives, the tab


def on_screen(rect):
    x, y, w, h = rect
    return 0 <= x and x + w <= SCREEN[0] and 0 <= y and y + h <= SCREEN[1]


def test_every_shipped_tutorial_reads_and_every_step_can_be_shown_and_waited_for():
    for level in arenas():
        assert level.tutorial is not None, level.title  # the first leads, the rest hint
        tutorial = Tutorial.from_dict(level.tutorial)
        context = Context(level.new_board(), Tool.ADD, Screen.EDIT)
        for step in tutorial.steps:
            assert step.say and all(len(line) <= 48 for line in step.say)
            if step.until:
                met(step.until, context)  # a condition it knows
            for screen in (Screen.EDIT, Screen.RUN):
                layout = layout_on(screen, step)
                assert all(on_screen(r) for r in target_rects(step.show, screen, layout, VIEW))


def test_only_the_first_level_leads_the_later_ones_only_hint():
    first, *later = arenas()
    assert any(step.show for step in Tutorial.from_dict(first.tutorial).steps)
    for level in later:
        assert not any(step.show or step.until for step in Tutorial.from_dict(level.tutorial).steps)


def test_the_fear_tutorial_moves_on_as_the_player_builds_the_board():
    level = LEVELS["Fear"]
    tutorial, board = Tutorial.from_dict(level.tutorial), level.new_board()
    context = lambda tool=Tool.ADD, screen=Screen.EDIT, outcome=None: Context(  # noqa: E731
        board, tool, screen, outcome
    )
    for _ in range(2):  # in the run: the swimmer, Objectives: Next
        tutorial.follow(context(screen=Screen.RUN))
        tutorial.next()
    tutorial.follow(context(screen=Screen.RUN))
    assert tutorial.step.until == {"screen": "edit"}  # the Editor tab
    for _ in range(3):  # the board, the menu, the palette: Next
        tutorial.follow(context())
        tutorial.next()
    assert tutorial.step.until == {"placed": {"kind": "eye", "cell": [2, -1]}}
    upper = board.place(Kind.EYE, (2, -1))
    tutorial.follow(context())
    assert "facing" in tutorial.step.until
    board.rotate(upper.id, 1)  # NE: not yet
    tutorial.follow(context(Tool.TURN_LEFT))
    assert "facing" in tutorial.step.until
    board.rotate(upper.id, 1)  # NW
    tutorial.follow(context(Tool.TURN_LEFT))
    lower = board.place(Kind.EYE, (1, 1), facing=SW)  # placed already turned: two steps at once
    tutorial.follow(context())
    assert tutorial.step.until == {"placed": {"kind": "thruster", "cell": [1, -2]}}
    left, right = board.place(Kind.THRUSTER, (1, -2)), board.place(Kind.THRUSTER, (-1, 2))
    board.connect(upper.id, left.id)
    board.connect(lower.id, right.id)
    tutorial.follow(context(Tool.WIRE))
    assert tutorial.step.until == {"screen": "run"}
    tutorial.follow(context(screen=Screen.RUN))
    for shown in ("controls", "inside"):  # the run held still: Next
        assert tutorial.step.show == {"run": shown} and tutorial.explains
        tutorial.next()
    assert tutorial.step.until == {"outcome": "won"} and not tutorial.explains  # Play
    tutorial.follow(context(screen=Screen.RUN, outcome=Outcome.WON))
    assert tutorial.step.show == {"run": "score"} and tutorial.explains  # the score, last
    tutorial.next()
    assert tutorial.step is None and not tutorial.leads
    assert [g.facing for g in tutorial.ghosts][:2] == [NW, SW]


def test_the_box_sits_beside_its_targets_on_screen_clear_of_them_with_next_inside_it():
    eye_row = dict(LAYOUT.menu_items)[Kind.EYE]
    box = box_rect([eye_row], 3, LAYOUT.board_area)
    assert box[0] > eye_row[0] + eye_row[2] and on_screen(box)  # right of the drawer
    tools = make_layout(Drawer.TOOLS)
    tool = dict(tools.tool_buttons)[Tool.WIRE]
    box = box_rect([tool], 3, tools.board_area)
    assert box[0] > tool[0] + tool[2] and on_screen(box)  # right of the drawer too
    hint = box_rect([], 2, LAYOUT.board_area)
    assert contains(LAYOUT.board_area, hint[:2]) and on_screen(hint)
    nx, ny, nw, nh = next_rect(box)
    assert contains(box, (nx, ny)) and contains(box, (nx + nw - 1, ny + nh - 1))
    for step in Tutorial.from_dict(LEVELS["Fear"].tutorial).steps:  # never over what it shows
        for screen in (Screen.EDIT, Screen.RUN):
            layout = layout_on(screen, step)
            targets = target_rects(step.show, screen, layout, VIEW)
            narrow = [t for t in targets if not is_area(t)]  # an area may lie under the box
            if narrow:
                box = box_rect(targets, len(step.say), layout.board_area)
                assert on_screen(box) and not any(overlap(box, t) for t in narrow), step.say


def overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def test_skip_ends_the_tutorial_and_a_restart_passes_over_what_the_board_holds():
    level = LEVELS["Fear"]
    tutorial, board = Tutorial.from_dict(level.tutorial), level.new_board()
    tutorial.skip()
    assert tutorial.step is None
    board.place(Kind.EYE, (2, -1))  # built while the tutorial was off
    tutorial.restart()  # the map opened
    assert tutorial.index == 0
    context = Context(board, Tool.ADD, Screen.EDIT)
    for _ in range(2):  # the swimmer, Objectives: Next; the tab, met in the editor
        tutorial.next()
    for _ in range(3):  # the board, the menu, the palette: Next
        tutorial.follow(context)
        tutorial.next()
    tutorial.follow(context)
    assert "facing" in tutorial.step.until  # the eye is there already: on to turning it


def test_skip_sits_left_of_next_both_inside_the_box():
    box = (100, 100, 360, 120)
    skip, nxt = skip_rect(box), next_rect(box)
    assert skip[0] + skip[2] < nxt[0] and skip[1] == nxt[1]
    for x, y, w, h in (skip, nxt):
        assert 100 <= x and x + w <= 460 and 100 <= y and y + h <= 220


ANYTHING = [
    Action("pick", kind=Kind.EYE),
    Action("place", kind=Kind.EYE, cell=(2, -1)),
    Action("tool", tool=Tool.WIRE),
    Action("turn", cell=(2, -1)),
    Action("wire", cell=(2, -1), other=(1, -2)),
    Action("move", cell=(2, -1)),
    Action("delete", cell=(2, -1)),
    *(Action(verb) for verb in ("undo", "redo", "run", "map", "edit", "next", "play", "view")),
]


def test_a_leading_step_lets_through_only_the_means_to_what_it_waits_for():
    steps = Tutorial.from_dict(LEVELS["Fear"].tutorial).steps
    place = steps[R + 3]  # an eye on (2, -1)
    assert allows(place, Action("pick", kind=Kind.EYE))
    assert allows(place, Action("place", kind=Kind.EYE, cell=(2, -1)))
    assert not allows(place, Action("place", kind=Kind.EYE, cell=(1, 1)))  # another cell
    assert not allows(place, Action("pick", kind=Kind.THRUSTER))
    assert not any(allows(place, Action(verb)) for verb in ("run", "map", "undo", "redo"))
    assert not allows(place, Action("tool", tool=Tool.WIRE))
    turn = steps[R + 4]  # the eye on (2, -1) to face NW
    assert allows(turn, Action("tool", tool=Tool.TURN_LEFT))
    assert allows(turn, Action("tool", tool=Tool.TURN_RIGHT))  # four turns right get there too
    assert allows(turn, Action("turn", cell=(2, -1)))
    assert not allows(turn, Action("turn", cell=(1, 1)))
    wire = steps[R + 9]  # the upper eye to the upper thruster
    assert allows(wire, Action("tool", tool=Tool.WIRE))
    assert allows(wire, Action("wire", cell=(1, -2), other=(2, -1)))  # either way round (D-026)
    assert not allows(wire, Action("wire", cell=(2, -1), other=(-1, 2)))
    run, watch = steps[R + 11], steps[R + 14]
    assert allows(run, Action("run")) and not allows(run, Action("map"))
    assert allows(watch, Action("run")) and allows(watch, Action("edit"))
    assert allows(watch, Action("play")) and not allows(steps[R - 1], Action("play"))
    assert not allows(watch, Action("next"))
    tab = steps[R - 1]  # to the editor, from the run: the tab, Esc or the switch (D-060)
    assert allows(tab, Action("edit")) and not allows(tab, Action("run"))


def test_a_step_that_waits_for_next_lets_nothing_through_and_a_hint_lets_all():
    steps = Tutorial.from_dict(LEVELS["Fear"].tutorial).steps
    for waits_for_next in (steps[0], steps[1], steps[R], steps[R + 1], steps[R + 12]):
        assert not any(allows(waits_for_next, action) for action in ANYTHING)
    hint = Tutorial.from_dict(LEVELS["Love"].tutorial).steps[0]
    assert all(allows(hint, action) for action in ANYTHING)
    assert all(allows(None, action) for action in ANYTHING)  # no tutorial, or over


def test_a_placing_step_lights_the_menu_row_its_part_comes_from():
    for step in Tutorial.from_dict(LEVELS["Fear"].tutorial).steps:
        if step.until and "placed" in step.until:
            assert {"menu": step.until["placed"]["kind"]} in step.show


def test_the_overlay_knows_a_cell_a_panel_and_anything_else():
    step = Tutorial.from_dict(LEVELS["Fear"].tutorial).steps[R + 3]  # the Eye's row, its cell
    layout = make_layout(kinds=frozenset({Kind.EYE, Kind.THRUSTER}))
    spots = target_spots(step.show, Screen.EDIT, layout, centred_view(layout))
    assert [shape for _, shape in spots] == ["spot", "disc"]  # the Eye's row, its cell
    assert [rect for rect, _ in spots] == target_rects(
        step.show, Screen.EDIT, layout, centred_view(layout)
    )
    panel = target_spots({"area": "bar"}, Screen.EDIT, layout, centred_view(layout))
    run = target_spots([{"run": "play"}, {"run": "inside"}], Screen.RUN, RUN_LAYOUT, None)
    assert [shape for _, shape in panel + run] == ["panel", "spot", "panel"]


def test_the_way_between_two_targets_crosses_a_box_in_its_path_and_not_one_beside_it():
    menu, cell = (16, 44, 168, 40), (600, 200, 70, 80)  # centres (100, 64) and (635, 240)
    assert _crosses((300, 100, 100, 60), menu, cell)  # the line passes through it
    assert not _crosses((300, 300, 100, 60), menu, cell)  # well under it
    assert not _crosses((700, 20, 100, 60), menu, cell)  # beyond the end


def test_every_box_keeps_clear_of_its_targets_the_way_between_them_and_the_work_just_done():
    level = LEVELS["Fear"]
    layout = make_layout(kinds=frozenset({Kind.EYE, Kind.THRUSTER}))
    view = centred_view(layout)
    tutorial = Tutorial.from_dict(level.tutorial)
    for index in range(len(tutorial.steps)):  # each step, as it shows once the one before is done
        tutorial.index = index
        step, done = tutorial.step, tutorial.before
        for screen in (Screen.EDIT, Screen.RUN):
            frame = layout if screen is Screen.EDIT else layout_on(screen, step)
            targets = target_rects(step.show, screen, frame, view)
            before = [] if done is None else target_rects(done.show, screen, frame, view)
            narrow = [t for t in targets if not is_area(t)]  # an area (board, arena) may lie under
            if not narrow:
                continue
            box = box_rect(targets, len(step.say), frame.board_area, before)
            assert on_screen(box), step.say
            for rects in (narrow, [t for t in before if not is_area(t)]):
                assert not any(overlap(box, grown(t, GAP)) for t in rects), step.say
                assert not any(
                    _crosses(box, a, b) for a, b in zip(rects, rects[1:], strict=False)
                ), step.say


def grown(rect, by):
    x, y, w, h = rect
    return (x - by, y - by, w + 2 * by, h + 2 * by)


def test_next_moves_on_only_from_a_step_that_waits_for_it_never_past_an_action_left_undone():
    tutorial = Tutorial.from_dict(LEVELS["Fear"].tutorial)
    for _ in range(2):  # the swimmer, Objectives
        assert tutorial.waits_for_next
        tutorial.next()
    assert not tutorial.waits_for_next  # the Editor tab: there is no Next
    tutorial.index = R
    for _ in range(3):  # the board, the menu, the palette
        assert tutorial.waits_for_next
        tutorial.next()
    assert not tutorial.waits_for_next  # place an eye: there is no Next
    tutorial.next()
    assert tutorial.index == R + 3 and tutorial.step.until == {
        "placed": {"kind": "eye", "cell": [2, -1]}
    }


def test_a_step_that_leads_and_waits_for_next_moves_on_at_any_key_or_click_but_on_skip():
    tutorial = Tutorial.from_dict(LEVELS["Fear"].tutorial)
    box = (300, 300, 360, 100)
    skip, nxt = skip_rect(box), next_rect(box)
    centre = lambda r: (r[0] + r[2] // 2, r[1] + r[3] // 2)  # noqa: E731
    assert answer(tutorial, box, None) == "next"  # the board: any key
    assert answer(tutorial, box, (5, 5)) == "next"  # ... or a click anywhere
    assert answer(tutorial, box, centre(skip)) == "skip"
    tutorial.index = R + 3  # place an eye: the press is the editor's, but Skip
    assert answer(tutorial, box, None) is None and answer(tutorial, box, centre(nxt)) is None
    assert answer(tutorial, box, centre(skip)) == "skip"
    tutorial.index = len(tutorial.steps) - 1  # the last: Close, any key or click; no Skip
    assert answer(tutorial, box, centre(skip)) == "next"
    hint = Tutorial.from_dict(LEVELS["Love"].tutorial)  # a hint takes only its own buttons
    assert answer(hint, box, None) is None and answer(hint, box, (5, 5)) is None
    assert answer(hint, box, centre(nxt)) == "next"


def test_only_the_first_level_is_guided_and_so_starts_afresh_at_the_map():
    first, *later = arenas()
    assert guided(first.tutorial) and not any(guided(level.tutorial) for level in later)
    assert not guided(None)


def test_a_step_that_explains_names_its_panels_and_one_that_asks_for_an_action_none():
    tutorial = Tutorial.from_dict(LEVELS["Fear"].tutorial)
    expected = {0: {"arena"}, 1: {"objectives"}, 2: {"tab:editor"}, R + 1: {"parts"}}
    expected |= {R + 2: {"bar"}}
    expected |= {R + 3: set(), R + 11: set(), R + 12: {"controls"}, R + 14: set()}
    for index, names in expected.items():
        tutorial.index = index
        assert panels(tutorial) == names, index
    tutorial.index = len(tutorial.steps) - 1
    assert panels(tutorial) == {"score"} and panels(None) == frozenset()


def test_a_step_opens_the_drawer_its_targets_are_in():
    steps = Tutorial.from_dict(LEVELS["Fear"].tutorial).steps
    assert drawer_for(steps[R + 1]) is Drawer.PARTS  # Parts, the drawer
    assert drawer_for(steps[R + 3]) is Drawer.PARTS  # an Eye's row, then its cell
    assert drawer_for(steps[R + 4]) is Drawer.TOOLS  # Turn left
    assert drawer_for(steps[1]) is Drawer.OBJECTIVES  # the run's first drawer (D-060)
    assert (
        drawer_for(steps[R]) is None
        and drawer_for(steps[R + 11]) is None
        and drawer_for(None) is None
    )
    shown = {drawer_for(step) for step in steps if step.show and "run" in str(step.show)}
    assert shown == {None, Drawer.OBJECTIVES, Drawer.INSIDE, Drawer.SCORE}  # the run's (D-057)


def test_a_tool_shown_while_tools_is_closed_lights_the_drawers_icon():
    parts, tools = make_layout(Drawer.PARTS), make_layout(Drawer.TOOLS)
    show = {"tool": "wire"}
    assert target_rects(show, Screen.EDIT, parts, VIEW) == [
        dict(parts.drawer_buttons)[Drawer.TOOLS]
    ]
    assert target_rects(show, Screen.EDIT, tools, VIEW) == [dict(tools.tool_buttons)[Tool.WIRE]]


def test_a_leading_step_keeps_the_board_on_screen():
    tutorial = Tutorial.from_dict(LEVELS["Fear"].tutorial)
    tutorial.index = R + 3  # an Eye to drag onto its cell
    assert not allows(tutorial.step, Action("view"))  # no Run preview while it leads (D-058)
    assert allows(None, Action("view"))


def test_fear_starts_in_the_run_and_sends_the_player_to_the_editor_by_its_tab():
    tutorial = Tutorial.from_dict(LEVELS["Fear"].tutorial)
    assert (
        tutorial.start is Screen.RUN
        and Tutorial.from_dict(LEVELS["Love"].tutorial).start is Screen.EDIT
    )
    ways = tutorial.steps[R - 1].show  # the Editor tab and the switch at the bar's foot
    switch = dict(RUN_LAYOUT.level_buttons)[LevelButton.EDIT]
    assert target_rects(ways, Screen.RUN, RUN_LAYOUT, VIEW) == [
        dict(RUN_LAYOUT.tabs)["editor"],
        switch,
    ]
    assert target_rects(ways, Screen.EDIT, LAYOUT, VIEW) == [dict(LAYOUT.tabs)["editor"]]
