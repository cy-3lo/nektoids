"""Tutorials and hints (D-039). tutorial.py imports no pygame."""

from nektoids.editor.layout import SCREEN, Tool, centred_view, contains, make_layout
from nektoids.editor.router import Screen
from nektoids.editor.tutorial import (
    Context,
    Tutorial,
    box_rect,
    met,
    next_rect,
    skip_rect,
    target_rects,
)
from nektoids.graph.board import Kind
from nektoids.graph.hexgrid import NW, SW
from nektoids.levels.arenas import arenas
from nektoids.levels.objectives import Outcome

LAYOUT = make_layout()
VIEW = centred_view(LAYOUT)
LEVELS = {level.title: level for level in arenas()}


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
                assert all(on_screen(r) for r in target_rects(step.show, screen, LAYOUT, VIEW))


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
    assert tutorial.step.until == {"outcome": "won"}
    tutorial.follow(context(screen=Screen.RUN, outcome=Outcome.WON))
    assert tutorial.step.until is None and tutorial.leads
    tutorial.next()
    assert tutorial.step is None and not tutorial.leads
    assert [g.facing for g in tutorial.ghosts][:2] == [NW, SW]


def test_the_box_sits_beside_its_targets_on_screen_clear_of_them_with_next_inside_it():
    eye_row = dict(LAYOUT.menu_items)[Kind.EYE]
    box = box_rect([eye_row], 3, LAYOUT.board_area)
    assert box[0] > eye_row[0] + eye_row[2] and on_screen(box)  # right of the menu
    tool = dict(LAYOUT.tool_buttons)[Tool.WIRE]
    box = box_rect([tool], 3, LAYOUT.board_area)
    assert box[0] + box[2] < tool[0] and on_screen(box)  # left of the palette
    hint = box_rect([], 2, LAYOUT.board_area)
    assert contains(LAYOUT.board_area, hint[:2]) and on_screen(hint)
    nx, ny, nw, nh = next_rect(box)
    assert contains(box, (nx, ny)) and contains(box, (nx + nw - 1, ny + nh - 1))
    for step in Tutorial.from_dict(LEVELS["Fear"].tutorial).steps:  # never over what it shows
        for screen in (Screen.EDIT, Screen.RUN):
            targets = target_rects(step.show, screen, LAYOUT, VIEW)
            if len(targets) > 1 or (targets and targets[0][2] < 400):
                box = box_rect(targets, len(step.say), LAYOUT.board_area)
                assert on_screen(box) and not any(overlap(box, t) for t in targets), step.say


def overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def test_skip_ends_the_tutorial_and_a_restart_passes_over_what_the_board_holds():
    level = LEVELS["Fear"]
    tutorial, board = Tutorial.from_dict(level.tutorial), level.new_board()
    tutorial.skip()
    assert tutorial.step is None and tutorial.skipped
    board.place(Kind.EYE, (2, -1))  # built while the tutorial was off
    tutorial.restart()
    assert tutorial.index == 0 and not tutorial.skipped
    context = Context(board, Tool.ADD, Screen.EDIT)
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
