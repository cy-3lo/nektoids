"""Undo and redo (D-027). history.py imports no pygame."""

from nektoids.editor.history import History
from nektoids.graph.board import Board, Kind, Refused
from nektoids.graph.hexgrid import offset_rect

RECT = offset_rect(9, 7)


def test_a_snapshot_put_back_is_the_board_as_it_was_routes_and_stock_and_all():
    board = Board(RECT, {Kind.EYE: 2, Kind.THRUSTER: 2})
    eye = board.place(Kind.EYE, (0, 1))
    thruster = board.place(Kind.THRUSTER, (6, 3))
    assert not isinstance(board.connect(eye.id, thruster.id), Refused)
    then = board.snapshot()
    board.rotate(eye.id, 1)
    board.move_node(thruster.id, (6, 5))
    board.remove_node(eye.id)
    assert board.snapshot() != then
    board.restore(then)
    assert board.snapshot() == then
    assert board.nodes[eye.id] == eye and board.wires[0].path == then.wires[0].path
    assert board.remaining(Kind.EYE) == 1
    assert board.place(Kind.EYE, (0, 5)).id == 2  # a new id, not one put back


def test_undo_then_redo_walks_back_and_forth_through_the_states():
    a, b, c = (Board(RECT) for _ in range(3))
    b.place(Kind.EYE, (0, 1))
    c.place(Kind.EYE, (0, 1))
    c.place(Kind.SUM, (2, 1))
    states = [board.snapshot() for board in (a, b, c)]
    history = History()
    assert not history.can_undo and history.undo(states[0]) is None
    history.record(states[0])
    history.record(states[1])
    assert history.undo(states[2]) == states[1]
    assert history.undo(states[1]) == states[0]
    assert not history.can_undo and history.can_redo
    assert history.redo(states[0]) == states[1]
    assert history.redo(states[1]) == states[2]
    assert not history.can_redo and history.redo(states[2]) is None


def test_a_new_edit_after_an_undo_forgets_what_could_be_redone():
    one, two = Board(RECT), Board(RECT)
    two.place(Kind.EYE, (0, 1))
    history = History()
    history.record(one.snapshot())
    history.undo(two.snapshot())
    history.record(one.snapshot())
    assert not history.can_redo


def test_only_the_last_states_are_kept():
    history = History(limit=3)
    boards = [Board(RECT) for _ in range(5)]
    for k, board in enumerate(boards):
        board.place(Kind.EYE, (k, 1))
        history.record(board.snapshot())
    undone = [history.undo(boards[-1].snapshot()) for _ in range(4)]
    assert undone[:3] == [boards[k].snapshot() for k in (4, 3, 2)] and undone[3] is None
