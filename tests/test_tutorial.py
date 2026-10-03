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
    Docked,
    Live,
    Step,
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
    outline_kept,
    panels,
    shows_wheel,
    skip_rect,
    target_rects,
    target_spots,
)
from nektoids.editor.wheel import ICON, WHEEL_HEX, centre_in, offer, slots
from nektoids.graph.board import Kind
from nektoids.graph.hexgrid import NW, SW
from nektoids.levels.arenas import arenas
from nektoids.levels.objectives import Outcome

LAYOUT = make_layout()
VIEW = centred_view(LAYOUT)
RUN_LAYOUT = make_layout(Drawer.INSIDE, env=Env.RUN, goals=1)  # the run's frame (D-057)


def layout_on(screen: Screen, step=None):
    """The editor's layout with the drawer `step` opens (Parts if none), or the run's."""
    if screen is not Screen.RUN:
        return make_layout(drawer_for(step) or Drawer.PARTS, kinds=FEAR_KINDS)
    return make_layout(drawer_for(step) or Drawer.INSIDE, env=Env.RUN, goals=1)


LEVELS = {level.title: level for level in arenas()}
FEAR = Tutorial.from_dict(LEVELS["Fear"].tutorial).steps
FEAR_KINDS = frozenset({Kind.EYE, Kind.THRUSTER})  # what Fear hands out


def fear(until=None, show=None) -> int:
    """Where Fear's step is that waits for `until`, or else shows `show`: found by what it is,
    so that the steps may move (D-070)."""
    return next(k for k, s in enumerate(FEAR) if (s.until == until if until else s.show == show))


TAB = fear({"screen": "edit"})  # from the run to the editor (D-060)
BOARD, TOOLS = fear(show={"page": "editor"}), fear(show={"drawer": "tools"})
PARTS = fear(show={"drawer": "parts"})
EYE = fear({"placed": {"kind": "eye", "cell": [2, -1]}})  # from the Wheel
TURN = fear({"facing": {"cell": [2, -1], "facing": "NW"}})
SECOND = fear(  # the second eye, placed and turned on one card (D-071)
    [{"placed": {"kind": "eye", "cell": [1, 1]}}, {"facing": {"cell": [1, 1], "facing": "SW"}}]
)
THRUSTER = fear(  # both thrusters, from Parts, on one card
    [
        {"placed": {"kind": "thruster", "cell": [1, -2]}},
        {"placed": {"kind": "thruster", "cell": [-1, 2]}},
    ]
)
WIRE = fear({"wired": {"from": [2, -1], "to": [1, -2]}})
RUN, PLAY = fear({"screen": "run"}), fear({"time": 1.0})  # Run, then Play: 1 s of it
INSIDE, WIN = fear(show={"run": "inside"}), fear({"outcome": "won"})


def conditions(step) -> list:
    """What `step` waits for, one or several (D-071), as a list."""
    until = step.until or []
    return until if isinstance(until, list) else [until]


def wheel_for(step, layout):
    """The Wheel as it shows while `step` waits, round its cell, and that cell: the parts for
    an empty cell, the eye's actions for an eye to turn; none for a step that shows no Wheel."""
    if not shows_wheel(step) or layout.wheel_view is None:
        return Live()
    board = LEVELS["Fear"].new_board()
    cell = next(tuple(one["cell"]) for one in step.show if "cell" in one)
    if any("facing" in until for until in conditions(step)) and not any(
        "placed" in until for until in conditions(step)
    ):
        board.place(Kind.EYE, cell)  # an eye to turn; a card that also places it starts empty
    items = offer(board, cell, FEAR_KINDS)
    return Live(slots(items, centre_in(layout.wheel_view), WHEEL_HEX, FEAR_KINDS), cell)


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

    def context(tool=Tool.ADD, screen=Screen.EDIT, outcome=None, time=0.0):
        return Context(board, tool, screen, outcome, time)

    for shown in ("swimmer", "objectives"):  # in the run, nothing dimmed (D-071): Next
        tutorial.follow(context(screen=Screen.RUN))
        assert tutorial.step.show == {"run": shown} and tutorial.explains
        tutorial.next()
    assert tutorial.step.until == {"screen": "edit"}  # the Editor tab
    for _ in range(2):  # the editor's page, Tools and its Wheel: Next
        tutorial.follow(context())
        tutorial.next()
    assert tutorial.step.until == {"placed": {"kind": "eye", "cell": [2, -1]}}
    assert_wheel_offers(tutorial.step, board)  # the Eye, round the empty cell (D-070)
    upper = board.place(Kind.EYE, (2, -1))
    tutorial.follow(context())
    assert "facing" in tutorial.step.until
    assert_wheel_offers(tutorial.step, board)  # Turn left, round the eye
    board.rotate(upper.id, 1)  # NE: not yet
    tutorial.follow(context(Tool.TURN_LEFT))
    assert "facing" in tutorial.step.until
    board.rotate(upper.id, 1)  # NW
    tutorial.follow(context(Tool.TURN_LEFT))
    assert tutorial.index == SECOND  # the second eye: one card to place and turn it (D-071)
    assert_wheel_offers(tutorial.step, board)  # the Eye first
    lower = board.place(Kind.EYE, (1, 1))
    tutorial.follow(context())
    assert tutorial.index == SECOND  # placed, not turned yet
    assert_wheel_offers(tutorial.step, board)  # then Turn right
    board.rotate(lower.id, -1)
    board.rotate(lower.id, -1)  # SW
    tutorial.follow(context())
    assert tutorial.step.show == {"drawer": "parts"} and tutorial.explains  # then Parts: Next
    tutorial.next()
    assert tutorial.index == THRUSTER  # both thrusters on one card
    left = board.place(Kind.THRUSTER, (1, -2))
    tutorial.follow(context())
    assert tutorial.index == THRUSTER  # one of the two
    right = board.place(Kind.THRUSTER, (-1, 2))
    board.connect(upper.id, left.id)
    board.connect(lower.id, right.id)
    tutorial.follow(context(Tool.WIRE))
    assert tutorial.step.until == {"screen": "run"}
    tutorial.follow(context(screen=Screen.RUN))
    assert tutorial.index == PLAY and not tutorial.explains  # Play first
    tutorial.follow(context(screen=Screen.RUN, time=0.5))
    assert tutorial.index == PLAY
    tutorial.follow(context(screen=Screen.RUN, time=1.0))  # 1 s on: the run waits, Inside
    assert tutorial.step.show == {"run": "inside"} and tutorial.explains
    tutorial.next()  # Next: the run goes on to the win
    assert tutorial.step.until == {"outcome": "won"} and not tutorial.explains
    tutorial.follow(context(screen=Screen.RUN, outcome=Outcome.WON))
    assert tutorial.step.show == {"run": "score"} and tutorial.explains  # the score, last
    tutorial.next()
    assert tutorial.step is None and not tutorial.leads
    assert [g.facing for g in tutorial.ghosts][:2] == [NW, SW]


def assert_wheel_offers(step, board):
    """Every Wheel's icon `step` shows for the stage its cell is at, a part to place on it while
    it is empty, an action once a part is on it, is one the Wheel offers there on `board`."""
    cell = next(tuple(one["cell"]) for one in step.show if "cell" in one)
    offered = {what.value for what in offer(board, cell, FEAR_KINDS)}
    parts = {kind.value for kind in Kind}
    empty = board.node_at(cell) is None
    icons = [one["wheel"] for one in step.show if "wheel" in one]
    stage = [icon for icon in icons if (icon in parts) == empty]
    assert stage and all(icon in offered for icon in stage), (stage, offered)


def test_the_box_sits_beside_its_targets_on_screen_clear_of_them_with_next_inside_it():
    eye_row = dict(LAYOUT.menu_items)[Kind.EYE]
    box = box_rect([eye_row], 3, LAYOUT.board_area)
    assert box[0] > eye_row[0] + eye_row[2] and on_screen(box)  # right of the drawer
    hint = box_rect([], 2, LAYOUT.board_area)
    assert contains(LAYOUT.board_area, hint[:2]) and on_screen(hint)
    nx, ny, nw, nh = next_rect(box)
    assert contains(box, (nx, ny)) and contains(box, (nx + nw - 1, ny + nh - 1))
    for step in Tutorial.from_dict(LEVELS["Fear"].tutorial).steps:  # never over what it shows
        for screen in (Screen.EDIT, Screen.RUN):
            layout = layout_on(screen, step)
            targets = target_rects(step.show, screen, layout, VIEW, wheel_for(step, layout))
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
    for _ in range(2):  # the editor's page, Tools: Next
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
    steps = FEAR
    place = steps[EYE]  # an eye on (2, -1)
    assert allows(place, Action("pick", kind=Kind.EYE))
    assert allows(place, Action("place", kind=Kind.EYE, cell=(2, -1)))
    assert not allows(place, Action("place", kind=Kind.EYE, cell=(1, 1)))  # another cell
    assert not allows(place, Action("pick", kind=Kind.THRUSTER))
    assert not any(allows(place, Action(verb)) for verb in ("run", "map", "undo", "redo"))
    assert not allows(place, Action("tool", tool=Tool.WIRE))
    turn = steps[TURN]  # the eye on (2, -1) to face NW
    assert allows(turn, Action("tool", tool=Tool.TURN_LEFT))
    assert allows(turn, Action("tool", tool=Tool.TURN_RIGHT))  # four turns right get there too
    assert allows(turn, Action("turn", cell=(2, -1)))
    assert not allows(turn, Action("turn", cell=(1, 1)))
    wire = steps[WIRE]  # the upper eye to the upper thruster
    assert allows(wire, Action("tool", tool=Tool.WIRE))
    assert allows(wire, Action("wire", cell=(1, -2), other=(2, -1)))  # either way round (D-026)
    assert not allows(wire, Action("wire", cell=(2, -1), other=(-1, 2)))
    run, watch = steps[RUN], steps[WIN]
    assert allows(steps[PLAY], Action("play")) and not allows(steps[PLAY], Action("map"))
    assert allows(run, Action("run")) and not allows(run, Action("map"))
    assert allows(watch, Action("run")) and allows(watch, Action("edit"))
    assert allows(watch, Action("play")) and not allows(steps[TAB], Action("play"))
    assert not allows(watch, Action("next"))
    tab = steps[TAB]  # to the editor, from the run: the tab, Esc or the switch (D-060)
    assert allows(tab, Action("edit")) and not allows(tab, Action("run"))


def test_a_step_that_waits_for_next_lets_nothing_through_and_a_hint_lets_all():
    for waits_for_next in [step for step in FEAR if not step.until]:
        assert not any(allows(waits_for_next, action) for action in ANYTHING)
    hint = Tutorial.from_dict(LEVELS["Love"].tutorial).steps[0]
    assert all(allows(hint, action) for action in ANYTHING)
    assert all(allows(None, action) for action in ANYTHING)  # no tutorial, or over


def test_a_placing_step_shows_where_its_part_comes_from_its_row_or_the_wheel():
    for step in FEAR:  # the eyes from the Wheel, the thrusters from Parts (D-070)
        for until in conditions(step):
            if "placed" in until:
                kind = until["placed"]["kind"]
                assert {"menu": kind} in step.show or {"wheel": kind} in step.show
    assert {"wheel": "eye"} in FEAR[EYE].show and {"menu": "thruster"} in FEAR[THRUSTER].show


def test_the_overlay_knows_a_cell_a_panel_and_anything_else():
    step = FEAR[THRUSTER]  # the Thruster's row in Parts, its cell
    layout = make_layout(kinds=frozenset({Kind.EYE, Kind.THRUSTER}))
    spots = target_spots(step.show, Screen.EDIT, layout, centred_view(layout))
    assert [shape for _, shape in spots] == ["spot", "disc", "disc"]  # the row, the two cells
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
    view = centred_view(LAYOUT)
    tutorial = Tutorial.from_dict(level.tutorial)
    for index in range(len(tutorial.steps)):  # each step, as it shows once the one before is done
        tutorial.index = index
        step, done = tutorial.step, tutorial.before
        for screen in (Screen.EDIT, Screen.RUN):
            frame = layout_on(screen, step)
            live = wheel_for(step, frame)  # the Wheel's icon it shows, as it sits (D-070)
            targets = target_rects(step.show, screen, frame, view, live)
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
    tutorial.index = BOARD
    for _ in range(2):  # the editor's page, Tools
        assert tutorial.waits_for_next
        tutorial.next()
    assert not tutorial.waits_for_next  # place an eye: there is no Next
    tutorial.next()
    assert tutorial.index == EYE == BOARD + 2


def test_a_step_that_leads_and_waits_for_next_moves_on_at_any_key_or_click_but_on_skip():
    tutorial = Tutorial.from_dict(LEVELS["Fear"].tutorial)
    box = (300, 300, 360, 100)
    skip, nxt = skip_rect(box), next_rect(box)
    centre = lambda r: (r[0] + r[2] // 2, r[1] + r[3] // 2)  # noqa: E731
    assert answer(tutorial, box, None) == "next"  # the board: any key
    assert answer(tutorial, box, (5, 5)) == "next"  # ... or a click anywhere
    assert answer(tutorial, box, centre(skip)) == "skip"
    tutorial.index = TOOLS  # after the Editor tab: only Next or Enter (D-060)
    assert answer(tutorial, box, None) is None and answer(tutorial, box, (5, 5)) is None
    assert answer(tutorial, box, None, enter=True) == "next"
    assert answer(tutorial, box, centre(nxt)) == "next"
    tutorial.index = EYE  # place an eye: the press is the editor's, but Skip
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
    expected = {0: {"swimmer"}, 1: {"objectives"}, TAB: set(), BOARD: set(), TOOLS: {"tools"}}
    expected |= {PARTS: {"parts"}, EYE: set(), RUN: set(), PLAY: set(), INSIDE: {"inside"}}
    for index, names in expected.items():
        tutorial.index = index
        assert panels(tutorial) == names, index
    tutorial.index = len(tutorial.steps) - 1
    assert panels(tutorial) == {"score"} and panels(None) == frozenset()


def test_a_step_opens_the_drawer_its_targets_are_in():
    steps = FEAR
    assert drawer_for(steps[PARTS]) is Drawer.PARTS and drawer_for(steps[TOOLS]) is Drawer.TOOLS
    assert drawer_for(steps[THRUSTER]) is Drawer.PARTS  # its row, then its cell
    assert drawer_for(steps[EYE]) is Drawer.TOOLS  # the Wheel: Tools, or Parts if open (D-070)
    assert drawer_for(steps[EYE], Drawer.PARTS) is Drawer.PARTS
    assert drawer_for(steps[1]) is None  # the objectives, under any drawer (D-065)
    assert drawer_for(steps[BOARD]) is drawer_for(steps[RUN]) is drawer_for(None) is None
    shown = {drawer_for(step) for step in steps if step.show and "run" in str(step.show)}
    assert shown == {None, Drawer.INSIDE, Drawer.SCORE}  # the run's (D-057, D-065)


def test_a_leading_step_keeps_the_board_on_screen():
    tutorial = Tutorial.from_dict(LEVELS["Fear"].tutorial)
    tutorial.index = EYE  # an Eye to place on its cell
    assert not allows(tutorial.step, Action("view"))  # no Run preview while it leads (D-058)
    assert allows(None, Action("view"))


def test_fear_sends_the_player_from_the_run_to_the_editor_by_its_tab():
    tutorial = Tutorial.from_dict(LEVELS["Fear"].tutorial)  # every level opens on its run
    ways = tutorial.steps[TAB].show  # the Editor tab and the switch at the bar's foot
    switch = dict(RUN_LAYOUT.level_buttons)[LevelButton.EDIT]
    assert target_rects(ways, Screen.RUN, RUN_LAYOUT, VIEW) == [
        dict(RUN_LAYOUT.tabs)["editor"],
        switch,
    ]
    assert target_rects(ways, Screen.EDIT, LAYOUT, VIEW) == [dict(LAYOUT.tabs)["editor"]]


def test_the_runs_page_is_outlined_with_its_tab_and_the_box_keeps_under_its_header():
    from nektoids.editor.tutorial import Page

    spots = target_spots({"run": "arena"}, Screen.RUN, RUN_LAYOUT, None)
    (page, shape), (header, none) = spots
    assert shape == Page(dict(RUN_LAYOUT.tabs)["run"]) and none == "none"  # D-062
    arena = RUN_LAYOUT.board_area
    assert page == (arena[0], 0, arena[2], arena[1] + arena[3]) and header[3] == arena[1]
    box = box_rect([page, header], 3, arena)
    assert box[1] >= header[3] + GAP and contains(page, box[:2])  # inside, under the title


def test_a_step_that_asks_for_an_action_lights_its_cells_and_one_that_explains_none():
    from nektoids.editor.tutorial import focus_cells

    tutorial = Tutorial.from_dict(LEVELS["Fear"].tutorial)
    tutorial.index = EYE  # an Eye onto (2, -1)
    assert focus_cells(tutorial) == {(2, -1)}  # filled in the accent, nothing dimmed (D-063)
    tutorial.index = WIRE  # the upper eye to the upper thruster
    assert focus_cells(tutorial) == {(2, -1), (1, -2)}
    tutorial.index = BOARD  # the board, explained: dimmed round it instead
    assert focus_cells(tutorial) == frozenset() and focus_cells(None) == frozenset()


def test_a_wheel_icon_is_a_target_while_the_steps_cell_is_focused_and_only_then():
    # D-070: the Wheel at the drawer's foot, round the focused cell
    board, cell, kinds = LEVELS["Fear"].new_board(), (2, -1), frozenset({Kind.EYE, Kind.THRUSTER})
    tools = make_layout(Drawer.TOOLS, kinds=kinds)
    wheel = tuple(slots(offer(board, cell, kinds), centre_in(tools.wheel_view), WHEEL_HEX, kinds))
    show = [{"cell": [2, -1]}, {"wheel": "eye"}]
    spots = target_spots(show, Screen.EDIT, tools, VIEW, Live(wheel, focused=cell))
    (_, disc), (icon, shape), (wheel_area, none) = spots  # the box keeps clear of the Wheel
    assert none == "none" and wheel_area[1] < tools.wheel_fold[1]  # its title and rule too
    assert contains(wheel_area, tools.wheel_view[:2]) and contains(wheel_area, icon[:2])
    eye = next(slot for slot in wheel if slot.what is Kind.EYE)
    r = ICON * WHEEL_HEX
    assert shape == "icon" and disc == "disc" and icon[2] == icon[3] == round(2 * r)
    assert contains(icon, tuple(round(v) for v in eye.at)) and contains(tools.drawer_area, icon[:2])
    elsewhere = target_rects(show, Screen.EDIT, tools, VIEW, Live(wheel, focused=(1, 1)))
    assert len(elsewhere) == 1  # on another cell the Wheel's Eye would place there: not shown
    assert target_rects(show, Screen.RUN, tools, VIEW, Live(wheel, focused=cell)) == []
    assert (
        target_rects([{"wheel": "turn left"}], Screen.EDIT, tools, VIEW, Live(wheel)) == []
    )  # not offered


def test_a_drawer_a_step_explains_is_outlined_with_its_icon_and_a_wheels_step_keeps_it():
    tools, parts = make_layout(Drawer.TOOLS), make_layout(Drawer.PARTS)
    explain = {"drawer": "tools"}  # D-071: the drawer joined to its icon in the bar
    ((rect, shape),) = target_spots(explain, Screen.EDIT, tools, VIEW)
    assert rect == tools.drawer_area and shape == Docked(dict(tools.drawer_buttons)[Drawer.TOOLS])
    assert target_rects(explain, Screen.EDIT, parts, VIEW) == []  # Tools is not open
    assert drawer_for(Step(("Tools",), explain)) is Drawer.TOOLS
    place = Step(("Place",), [{"cell": [2, -1]}, {"wheel": "eye"}], {"placed": {}})
    assert shows_wheel(place) and not shows_wheel(Step(("Tools",), explain))
    assert drawer_for(place, Drawer.PARTS) is Drawer.PARTS  # the Wheel is at the foot of both
    assert drawer_for(place, Drawer.TOOLS) is Drawer.TOOLS
    assert drawer_for(place, Drawer.FILES) is drawer_for(place) is Drawer.TOOLS


def test_the_editors_page_is_outlined_with_its_tab_and_the_swimmer_by_a_box_from_the_run():
    from nektoids.editor.tutorial import Page

    (page, shape), (header, none) = target_spots({"page": "editor"}, Screen.EDIT, LAYOUT, VIEW)
    board = LAYOUT.board_area  # D-071: the Editor tab, the level's line, the board, one shape
    assert shape == Page(dict(LAYOUT.tabs)["editor"]) and none == "none"
    assert page == (board[0], 0, board[2], board[1] + board[3]) and header[3] == board[1]
    assert target_rects({"page": "editor"}, Screen.RUN, RUN_LAYOUT, VIEW) == []
    box = (500, 300, 40, 40)
    swimmer = target_spots({"run": "swimmer"}, Screen.RUN, RUN_LAYOUT, None, Live(swimmer=box))
    assert swimmer == [(box, "spot")]
    assert target_rects({"run": "swimmer"}, Screen.EDIT, LAYOUT, VIEW, Live(swimmer=box)) == []


def test_a_step_may_wait_for_several_things_and_for_the_run_to_have_played_a_while():
    board = LEVELS["Fear"].new_board()  # D-071
    both = [
        {"placed": {"kind": "thruster", "cell": [1, -2]}},
        {"placed": {"kind": "thruster", "cell": [-1, 2]}},
    ]
    step = Step(("Both thrusters",), [{"menu": "thruster"}], both)
    for cell in ((1, -2), (-1, 2)):  # either cell, the thruster only
        assert allows(step, Action("place", kind=Kind.THRUSTER, cell=cell))
    assert allows(step, Action("pick", kind=Kind.THRUSTER))
    assert not allows(step, Action("place", kind=Kind.EYE, cell=(1, -2)))
    context = Context(board, Tool.ADD, Screen.EDIT)
    board.place(Kind.THRUSTER, (1, -2))
    assert not met(both, context)  # one of the two
    board.place(Kind.THRUSTER, (-1, 2))
    assert met(both, context)
    eye = [
        {"placed": {"kind": "eye", "cell": [1, 1]}},
        {"facing": {"cell": [1, 1], "facing": "SW"}},
    ]
    card = Step(("The second eye",), [{"cell": [1, 1]}], eye)  # placed, then turned: one card
    assert allows(card, Action("place", kind=Kind.EYE, cell=(1, 1)))
    assert allows(card, Action("turn", cell=(1, 1))) and not allows(
        card, Action("turn", cell=(2, -1))
    )
    lower = board.place(Kind.EYE, (1, 1))
    assert not met(eye, context)  # placed, not turned yet
    board.rotate(lower.id, -1)
    board.rotate(lower.id, -1)
    assert met(eye, context)
    played = {"time": 1.0}  # the run has played 1 s
    assert not met(played, Context(board, Tool.ADD, Screen.RUN, time=0.5))
    assert met(played, Context(board, Tool.ADD, Screen.RUN, time=1.0))
    waiting = Step(("Play",), [{"run": "play"}], played)
    assert allows(waiting, Action("play")) and not allows(waiting, Action("pick", kind=Kind.EYE))


def test_an_outline_at_the_screens_edge_keeps_inside_it_clear_of_its_first_rows_and_columns():
    tab = dict(RUN_LAYOUT.tabs)["editor"]  # D-071: a tab at the top, the switch by the left
    x, y, w, h = tab
    assert outline_kept((x - 6, y - 6, w + 12, h + 12))[1] == 3  # not above the screen
    sx, sy, sw, sh = dict(RUN_LAYOUT.level_buttons)[LevelButton.EDIT]
    assert outline_kept((sx - 6, sy - 6, sw + 12, sh + 12))[0] == 3  # nor on its first column
    foot = outline_kept(RUN_LAYOUT.goal_area)
    assert foot[1] + foot[3] == SCREEN[1] - 3  # nor on its last row
    inside = (100, 100, 50, 40)
    assert outline_kept(inside) == inside  # away from the edges: as it is
