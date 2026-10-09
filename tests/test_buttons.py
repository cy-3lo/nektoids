"""The Board's buttons (D-401): their places round the board, the same on every level."""

from nektoids.editor.buttons import (
    FRAME,
    PLACES,
    Button,
    State,
    board_view,
    button_at,
    key_of,
    shown,
    states,
    swaps,
    tip,
)
from nektoids.editor.layout import make_layout
from nektoids.editor.picking import NOTHING, clicked, crossing
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


def test_the_tools_sit_at_n_in_a_row_undo_across_from_sum_and_the_pairs_side_by_side():
    n = [Button.SELECT, Button.LOCK, Button.DELETE]
    cells = [PLACES[b] for b in n]
    assert all(cell[1] == -4 for cell in cells)
    assert [q for q, _ in cells] == list(range(cells[0][0], cells[0][0] + len(cells)))
    undo, diff = (
        to_pixel(PLACES[Button.UNDO], 1.0, (0.0, 0.0)),
        to_pixel(PLACES[Kind.DIFFERENCE], 1.0, (0.0, 0.0)),
    )
    assert undo == (-diff[0], diff[1])  # Undo and Redo at SW, mirroring Sum and Difference
    pairs = (
        (Button.TURN_LEFT, Button.TURN_RIGHT),
        (Kind.DOUBLE, Kind.HALVE),
        (Kind.SUM, Kind.DIFFERENCE),
        (Button.UNDO, Button.REDO),
    )
    for left, right in pairs:  # side by side in a row, the first on the left
        (q0, r0), (q1, r1) = PLACES[left], PLACES[right]
        assert r0 == r1 and q1 == q0 + 1
    colour = (Kind.TINT, Kind.FILTER, Kind.SWAP)  # under Paint, at W (D-507)
    assert all(PLACES[k][0] > 0 for k in Kind if k not in colour)  # the other parts at E
    assert all(PLACES[k][0] < 0 for k in colour)
    assert all(PLACES[b][0] < 0 for b in (Button.TURN_LEFT, Button.TURN_RIGHT, Button.WIRE))


def test_a_level_shows_its_own_parts_and_every_tool_lock_included():
    kinds = frozenset({Kind.EYE, Kind.SUM})
    level = shown(kinds, editor=False)
    assert Button.LOCK in level and Button.SELECT in level  # the player's lock (D-406)
    assert [b for b in level if isinstance(b, Kind)] == [Kind.EYE, Kind.SUM]
    assert shown(kinds, editor=True) == level


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
    x, y = to_pixel(PLACES[Kind.SUM], view.size, view.origin)
    assert button_at(level, view.size, view.origin, (x, y)) is None  # not shown: an empty place


def test_each_button_has_its_own_key():
    kinds = frozenset(Kind)
    keys = [key_of(b, kinds) for b in shown(kinds, editor=True)]
    assert len(set(keys)) == len(keys)
    assert key_of(Button.SELECT, kinds) == "S" and key_of(Kind.EYE, kinds) == "1"


def test_a_button_greys_when_it_cannot_act_and_lights_when_it_acts_on_the_pick():
    board = Board(hex_disc(2), {Kind.EYE: 2, Kind.SUM: None, Kind.DOUBLE: None, Kind.SOURCE: 0})
    kinds = frozenset({Kind.EYE, Kind.SUM, Kind.DOUBLE, Kind.SOURCE})
    buttons = shown(kinds, editor=True)

    def look(*cells, held=Button.SELECT, undo=False, redo=False):
        pick = NOTHING
        for cell in cells:
            pick = clicked(pick, board, cell)
        return states(board, buttons, held, pick, undo, redo, kinds)

    empty = look()  # nothing on the board, nothing picked
    assert empty[Button.SELECT] is State.CHOSEN
    for b in (Button.UNDO, Button.REDO, Button.DELETE, Button.TURN_LEFT, Button.WIRE, Kind.SOURCE):
        assert empty[b] is State.GREYED
    assert empty[Kind.EYE] is State.PLAIN and look(undo=True)[Button.UNDO] is State.PLAIN
    cells = look((0, 0), (1, 0))  # empty cells picked: the parts left may fill them
    assert cells[Kind.EYE] is State.LIT and cells[Kind.SOURCE] is State.GREYED
    assert cells[Button.DELETE] is State.GREYED and cells[Button.LOCK] is State.GREYED
    board.place(Kind.SUM, (0, 0))
    board.place(Kind.EYE, (1, 0))
    on_sum = look((0, 0))  # a sum picked: it goes, wires, may become a Double, never turns
    assert on_sum[Button.DELETE] is on_sum[Button.WIRE] is on_sum[Kind.DOUBLE] is State.LIT
    assert on_sum[Button.TURN_LEFT] is State.GREYED
    assert on_sum[Kind.EYE] is on_sum[Kind.SUM] is State.PLAIN  # held, for the clicks
    assert on_sum[Button.PAINT] is State.GREYED  # an operator takes no paint (D-502)
    both = look((0, 0), (1, 0))  # the eye with it: Turn and Paint act on the eye
    assert both[Button.TURN_RIGHT] is both[Button.DELETE] is both[Button.PAINT] is State.LIT
    board.lock(board.node_at((1, 0)).id)
    assert look()[Button.TURN_LEFT] is State.GREYED  # the only eye is the level's now
    assert look()[Button.PAINT] is State.PLAIN  # nothing picked: it switches its colour (D-503)
    assert look(held=Kind.EYE)[Kind.EYE] is State.CHOSEN


def test_a_part_may_be_swapped_for_another_of_its_group_left_in_parts_order():
    board = sandbox().new_board()
    total, eye, thruster = (
        board.place(k, c)
        for k, c in ((Kind.SUM, (0, 0)), (Kind.EYE, (1, 0)), (Kind.THRUSTER, (2, 0)))
    )
    operators = (Kind.DOUBLE, Kind.HALVE, Kind.DIFFERENCE, Kind.TANK)  # the Tank too (D-501),
    operators += (Kind.TINT, Kind.FILTER, Kind.SWAP)  # and the colour operators (D-507)
    assert swaps(board, total.cell, frozenset(Kind)) == operators
    assert swaps(board, eye.cell, frozenset({Kind.EYE, Kind.THRUSTER})) == ()  # no source here
    assert swaps(board, thruster.cell, frozenset(Kind)) == ()  # alone in its group


def test_a_tooltip_names_the_button_its_key_and_what_is_left_of_a_part():
    board = Board(hex_disc(2), {Kind.EYE: 2, Kind.SUM: None, Kind.DOUBLE: None})
    kinds = frozenset({Kind.EYE, Kind.SUM, Kind.DOUBLE})
    assert tip(Button.UNDO, board, kinds) == "Undo (Ctrl+Z)"
    assert tip(Button.TURN_LEFT, board, kinds) == "Turn left (L)"
    assert tip(Button.UNDO, board, kinds, key_hints=False) == "Undo"
    assert tip(Kind.EYE, board, kinds) == "Eye (1), 2 left"
    assert tip(Kind.SUM, board, kinds, key_hints=False) == "Sum"  # unlimited: no count


def test_empty_cells_picked_light_delete_when_a_wire_crosses_them_and_it_takes_those():
    board = Board(hex_disc(2))
    kinds = frozenset({Kind.SUM, Kind.DOUBLE})
    buttons = shown(kinds, editor=True)
    total, double = board.place(Kind.SUM, (-2, 0)), board.place(Kind.DOUBLE, (2, 0))
    wire = board.connect(total.id, double.id)
    through = wire.path[1]  # a free cell the wire crosses
    pick = clicked(clicked(NOTHING, board, through), board, wire.path[2])  # two of its cells
    looks = states(board, buttons, Button.SELECT, pick, False, False, kinds)
    assert looks[Button.DELETE] is State.LIT and looks[Button.LOCK] is State.GREYED  # D-431
    assert looks[Button.WIRE] is State.PLAIN  # held, the pick dropped
    assert crossing(pick, board) == [wire]  # once, though it crosses both
    off = next(c for c in board.cells if c not in wire.path)
    lone = clicked(NOTHING, board, off)
    alone = states(board, buttons, Button.SELECT, lone, False, False, kinds)
    assert alone[Button.DELETE] is alone[Button.WIRE] is State.PLAIN  # held, the pick dropped
    assert alone[Button.TURN_LEFT] is State.GREYED
