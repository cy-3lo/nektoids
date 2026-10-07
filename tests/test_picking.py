"""What is picked on the Board (D-402): empty cells, or parts, in the order clicked."""

from nektoids.editor.picking import (
    NOTHING,
    Pick,
    Picked,
    begin,
    clicked,
    extend,
    kept,
    moved,
    of_parts,
    parts,
)
from nektoids.graph.board import Board, Kind
from nektoids.graph.hexgrid import hex_disc


def board_with_two_parts() -> Board:
    board = Board(hex_disc(2))
    board.place(Kind.EYE, (1, 0))
    board.place(Kind.SUM, (0, 0))
    return board


def test_a_click_picks_the_one_thing_clicked_and_the_only_one_picked_drops():
    board = board_with_two_parts()
    pick = clicked(NOTHING, board, (0, 1))
    assert pick == Pick(Picked.CELLS, ((0, 1),))
    assert clicked(pick, board, (-1, 1)) == Pick(Picked.CELLS, ((-1, 1),))  # switched, not added
    assert clicked(pick, board, (0, 1)) == NOTHING  # the only one picked: dropped
    assert clicked(pick, board, (5, 5)) == clicked(pick, board, None) == NOTHING  # off the zone
    on_part = clicked(pick, board, (1, 0))
    assert on_part == Pick(Picked.PARTS, ((1, 0),))  # a part: a pick of parts instead
    assert clicked(on_part, board, (0, 0)) == Pick(Picked.PARTS, ((0, 0),))
    assert not NOTHING and pick


def test_with_the_add_key_a_click_adds_to_the_pick_or_drops_from_it_in_the_order_picked():
    board = board_with_two_parts()
    pick = clicked(NOTHING, board, (0, 1), add=True)
    pick = clicked(pick, board, (-1, 1), add=True)
    assert pick == Pick(Picked.CELLS, ((0, 1), (-1, 1)))
    assert clicked(pick, board, (0, 1), add=True) == Pick(Picked.CELLS, ((-1, 1),))
    assert clicked(pick, board, (5, 5), add=True) == pick  # off the zone: as it was
    both = clicked(clicked(NOTHING, board, (1, 0), add=True), board, (0, 0), add=True)
    assert [n.kind for n in parts(both, board)] == [Kind.EYE, Kind.SUM]
    assert parts(pick, board) == []
    assert clicked(both, board, (0, 1), add=True) == Pick(Picked.CELLS, ((0, 1),))  # the other kind


def test_the_pick_follows_the_board_its_parts_moved_and_what_went_dropped():
    board = board_with_two_parts()
    both = of_parts([(1, 0), (0, 0)])
    assert moved(both, (0, -1)).cells == ((1, -1), (0, -1))
    board.remove_node(board.node_at((1, 0)).id)
    assert kept(both, board) == Pick(Picked.PARTS, ((0, 0),))
    cells = Pick(Picked.CELLS, ((0, 1), (-1, 1)))
    board.place(Kind.SUM, (0, 1))
    assert kept(cells, board) == Pick(Picked.CELLS, ((-1, 1),))  # filled: no longer empty
    assert of_parts([]) == NOTHING and kept(NOTHING, board) == NOTHING


def drag_over(board: Board, cells, add=False, before=NOTHING):
    drag = begin(before, board, cells[0], add)
    for cell in cells[1:]:
        drag = extend(drag, board, cell)
    return drag


def test_a_drag_picks_the_empty_cells_it_crosses_and_leaves_the_parts_out():
    board = board_with_two_parts()  # D-404
    drag = drag_over(board, [(-1, 0), (0, 0), (0, 1)])  # the sum between: left out
    assert drag.pick == Pick(Picked.CELLS, ((-1, 0), (0, 1)))
    assert extend(drag, board, (5, 5)) == drag  # off the zone


def test_a_drag_going_back_over_its_path_cuts_it_back_however_far():
    board = Board(hex_disc(3))
    line = [(-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0)]
    drag = drag_over(board, line)
    assert drag.pick.cells == tuple(line)
    assert extend(drag, board, (0, 0)).pick.cells == tuple(line[:3])  # two cells climbed at once
    assert extend(drag, board, (-2, 0)).pick.cells == (line[0],)  # back to where it began
    back = extend(extend(drag, board, (0, 0)), board, (0, 1))  # and on, another way
    assert back.pick.cells == (*line[:3], (0, 1))


def test_a_drag_from_a_part_picks_the_parts_and_skips_the_empty_cells():
    board = board_with_two_parts()
    board.place(Kind.DOUBLE, (-1, 0))
    drag = drag_over(board, [(1, 0), (0, 1), (0, 0), (-1, 0)])
    assert drag.pick == Pick(Picked.PARTS, ((1, 0), (0, 0), (-1, 0)))
    assert extend(drag, board, (0, 1)) == drag  # an empty cell: left out, the path stays


def test_with_the_add_key_a_drag_keeps_what_was_picked_and_only_its_own_path_is_cut():
    board = Board(hex_disc(3))
    before = Pick(Picked.CELLS, ((2, 0),))
    drag = drag_over(board, [(-1, 0), (0, 0), (1, 0)], add=True, before=before)
    assert drag.pick.cells == ((2, 0), (-1, 0), (0, 0), (1, 0))
    assert extend(drag, board, (-1, 0)).pick.cells == ((2, 0), (-1, 0))
    parts_before = Pick(Picked.PARTS, ((0, 1),))
    assert begin(parts_before, board, (-1, 0), add=True).pick.cells == ((-1, 0),)  # other kind
    assert begin(before, board, (-1, 0), add=False).pick.cells == ((-1, 0),)
