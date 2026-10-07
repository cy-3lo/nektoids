"""What is picked on the Board (D-402): empty cells, or parts, in the order clicked."""

from nektoids.editor.picking import NOTHING, Pick, Picked, clicked, kept, moved, of_parts, parts
from nektoids.graph.board import Board, Kind
from nektoids.graph.hexgrid import hex_disc


def board_with_two_parts() -> Board:
    board = Board(hex_disc(2))
    board.place(Kind.EYE, (1, 0))
    board.place(Kind.SUM, (0, 0))
    return board


def test_clicks_pick_cells_one_after_another_and_drop_the_one_clicked_again():
    board = board_with_two_parts()
    pick = clicked(NOTHING, board, (0, 1))
    pick = clicked(pick, board, (-1, 1))
    assert pick == Pick(Picked.CELLS, ((0, 1), (-1, 1)))  # in the order clicked
    assert clicked(pick, board, (0, 1)) == Pick(Picked.CELLS, ((-1, 1),))
    assert clicked(clicked(NOTHING, board, (0, 1)), board, (0, 1)) == NOTHING
    assert clicked(pick, board, (5, 5)) == clicked(pick, board, None) == NOTHING  # off the zone
    assert not NOTHING and pick


def test_a_click_on_a_part_picks_parts_instead_the_first_click_saying_which():
    board = board_with_two_parts()
    cells = clicked(NOTHING, board, (0, 1))
    on_part = clicked(cells, board, (1, 0))
    assert on_part == Pick(Picked.PARTS, ((1, 0),))  # a pick of its own
    both = clicked(on_part, board, (0, 0))
    assert [n.kind for n in parts(both, board)] == [Kind.EYE, Kind.SUM]
    assert parts(cells, board) == []
    assert clicked(both, board, (0, 1)) == cells  # an empty cell: cells again, from there


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
