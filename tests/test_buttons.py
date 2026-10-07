"""The Board's buttons (D-401): their places round the board, the same on every level."""

from nektoids.editor.buttons import (
    FRAME,
    PLACES,
    Button,
    State,
    button_at,
    key_of,
    shown,
    states,
    swaps,
)
from nektoids.editor.layout import board_view, make_layout
from nektoids.graph.board import Board, Kind
from nektoids.graph.hexgrid import hex_disc, hex_distance, to_pixel
from nektoids.levels.arenas import sandbox


def test_every_button_and_part_has_a_place_of_its_own_off_the_largest_zone():
    assert set(PLACES) == {*Button, *Kind}
    assert len(set(PLACES.values())) == len(PLACES)
    zone = set(hex_disc(3))
    assert all(cell not in zone for cell in PLACES.values())
    assert all(hex_distance(cell, (0, 0)) in (4, 5) for cell in PLACES.values())  # round it
    assert set(FRAME) == zone | set(PLACES.values())


def test_the_tools_sit_at_n_and_s_in_rows_and_the_pairs_side_by_side():
    n = [Button.SELECT, Button.MOVE, Button.LOCK]
    s = [Button.UNDO, Button.REDO, Button.DELETE]
    for row, r in ((n, -4), (s, 4)):
        cells = [PLACES[b] for b in row]
        assert all(cell[1] == r for cell in cells)
        assert [q for q, _ in cells] == list(range(cells[0][0], cells[0][0] + len(cells)))
    xs = [to_pixel(PLACES[b], 1.0, (0.0, 0.0))[0] for b in s]
    assert sum(xs) / len(xs) == 0.0  # S centred under the board
    pairs = (
        (Button.TURN_LEFT, Button.TURN_RIGHT),
        (Kind.DOUBLE, Kind.HALVE),
        (Kind.SUM, Kind.DIFFERENCE),
        (Button.UNDO, Button.REDO),
    )
    for left, right in pairs:  # side by side in a row, the first on the left
        (q0, r0), (q1, r1) = PLACES[left], PLACES[right]
        assert r0 == r1 and q1 == q0 + 1
    assert all(PLACES[k][0] > 0 for k in Kind)  # the parts at E
    assert all(PLACES[b][0] < 0 for b in (Button.TURN_LEFT, Button.TURN_RIGHT, Button.WIRE))


def test_a_level_shows_its_own_parts_and_lock_only_on_the_editors_board():
    kinds = frozenset({Kind.EYE, Kind.SUM})
    level = shown(kinds, editor=False)
    assert Button.LOCK not in level and Button.SELECT in level
    assert [b for b in level if isinstance(b, Kind)] == [Kind.EYE, Kind.SUM]
    assert Button.LOCK in shown(kinds, editor=True)


def test_a_click_finds_the_button_under_it_and_nothing_between_or_off_them():
    view = board_view(make_layout(None))
    buttons = shown(frozenset(Kind), editor=True)
    for b in buttons:
        x, y = to_pixel(PLACES[b], view.size, view.origin)
        assert button_at(buttons, view.size, view.origin, (x, y)) is b
        assert (
            button_at(buttons, view.size, view.origin, (x + view.size, y)) is not b
        )  # past its side
    x, y = to_pixel((0, 0), view.size, view.origin)
    assert button_at(buttons, view.size, view.origin, (x, y)) is None  # the board's centre
    level = shown(frozenset({Kind.EYE}), editor=False)
    x, y = to_pixel(PLACES[Button.LOCK], view.size, view.origin)
    assert button_at(level, view.size, view.origin, (x, y)) is None  # not shown: an empty place


def test_each_button_has_its_own_key():
    kinds = frozenset(Kind)
    keys = [key_of(b, kinds) for b in shown(kinds, editor=True)]
    assert len(set(keys)) == len(keys)
    assert key_of(Button.SELECT, kinds) == "Esc" and key_of(Kind.EYE, kinds) == "1"


def test_a_button_greys_when_it_cannot_act_and_lights_when_it_acts_on_the_focus():
    board = Board(hex_disc(2), {Kind.EYE: 2, Kind.SUM: None, Kind.DOUBLE: None, Kind.SOURCE: 0})
    kinds = frozenset({Kind.EYE, Kind.SUM, Kind.DOUBLE, Kind.SOURCE})
    buttons = shown(kinds, editor=True)

    def look(focused=None, chosen=Button.SELECT, undo=False, redo=False):
        return states(board, buttons, chosen, focused, undo, redo, kinds)

    empty = look()  # nothing on the board, nothing focused
    assert empty[Button.SELECT] is State.CHOSEN
    for b in (Button.UNDO, Button.REDO, Button.MOVE, Button.TURN_LEFT, Button.WIRE, Kind.SOURCE):
        assert empty[b] is State.GREYED
    assert empty[Kind.EYE] is State.PLAIN and look(undo=True)[Button.UNDO] is State.PLAIN
    on_cell = look((0, 0))  # an empty cell focused: the parts left may go there
    assert on_cell[Kind.EYE] is State.LIT and on_cell[Kind.SOURCE] is State.GREYED
    assert on_cell[Button.MOVE] is State.GREYED and on_cell[Button.LOCK] is State.GREYED
    board.place(Kind.SUM, (0, 0))
    board.place(Kind.EYE, (1, 0))
    on_sum = look((0, 0))  # a sum focused: it moves, wires, may become a Double, never turns
    assert on_sum[Button.MOVE] is on_sum[Button.WIRE] is on_sum[Kind.DOUBLE] is State.LIT
    assert on_sum[Button.TURN_LEFT] is State.GREYED
    assert on_sum[Kind.EYE] is on_sum[Kind.SUM] is State.PLAIN  # picked, for the clicks
    assert look((1, 0))[Button.TURN_RIGHT] is State.LIT  # an eye turns
    assert look()[Button.TURN_LEFT] is State.PLAIN  # an eye on the board: Turn may act
    assert look(chosen=Kind.EYE)[Kind.EYE] is State.CHOSEN


def test_a_part_may_be_swapped_for_another_of_its_group_left_in_parts_order():
    board = sandbox().new_board()
    total, eye, thruster = (
        board.place(k, c)
        for k, c in ((Kind.SUM, (0, 0)), (Kind.EYE, (1, 0)), (Kind.THRUSTER, (2, 0)))
    )
    assert swaps(board, total.cell, frozenset(Kind)) == (Kind.DOUBLE, Kind.HALVE, Kind.DIFFERENCE)
    assert swaps(board, eye.cell, frozenset({Kind.EYE, Kind.THRUSTER})) == ()  # no source here
    assert swaps(board, thruster.cell, frozenset(Kind)) == ()  # alone in its group
