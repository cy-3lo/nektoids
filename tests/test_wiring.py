"""A wiring chain (D-402): each part wired to the one before, a wire there taken away instead,
and going back along the chain undoes what it did."""

from nektoids.editor.wiring import Chain, Did, between, chain_to
from nektoids.graph.board import Board, Kind, Refused
from nektoids.graph.hexgrid import hex_disc


def board_and_parts():
    board = Board(hex_disc(3))
    eye, total, double, thruster = (
        board.place(k, c)
        for k, c in (
            (Kind.EYE, (-2, 0)),
            (Kind.SUM, (-1, 0)),
            (Kind.DOUBLE, (0, 0)),
            (Kind.THRUSTER, (1, 0)),
        )
    )
    return board, eye.id, total.id, double.id, thruster.id


def make_on(board):
    def make(a, b):
        result = board.connect(*board.orient(a, b))
        return None if isinstance(result, Refused) else result

    def cut(wire):
        board.remove_wire(wire)
        return True

    return make, cut


def run(board, start, *ids):
    make, cut = make_on(board)
    chain = Chain((start,))
    for i in ids:
        chain = chain_to(chain, board, i, make, cut)
        if chain is None:
            return None
    return chain


def pairs(board):
    return {(w.source, w.target) for w in board.wires}


def test_a_chain_wires_each_part_to_the_one_before():
    board, eye, total, double, thruster = board_and_parts()
    chain = run(board, eye, total, double, thruster)
    assert pairs(board) == {(eye, total), (total, double), (double, thruster)}
    assert chain.path == (eye, total, double, thruster)
    assert [did for did, _ in chain.steps] == [Did.MADE] * 3


def test_going_back_along_the_chain_undoes_its_wires_however_far():
    board, eye, total, double, thruster = board_and_parts()
    make, cut = make_on(board)
    chain = run(board, eye, total, double, thruster)
    back = chain_to(chain, board, total, make, cut)  # two parts back at once
    assert pairs(board) == {(eye, total)} and back.path == (eye, total)
    again = chain_to(back, board, double, make, cut)  # and on again
    assert pairs(board) == {(eye, total), (total, double)} and again.path == (eye, total, double)
    assert chain_to(again, board, double, make, cut) == again  # the last part: nothing


def test_wiring_over_a_wire_takes_it_away_and_going_back_puts_it_back():
    board, eye, total, double, thruster = board_and_parts()
    run(board, total, double)  # a wire already there
    make, cut = make_on(board)
    chain = run(board, eye, total, double)  # eye to sum made, sum to double taken away
    assert pairs(board) == {(eye, total)}
    assert [did for did, _ in chain.steps] == [Did.MADE, Did.CUT]
    chain_to(chain, board, total, make, cut)  # back: the wire taken away comes back
    assert pairs(board) == {(eye, total), (total, double)}
    assert between(board, double, total) is not None  # either way round


def test_a_wire_refused_ends_the_chain():
    board, eye, total, double, thruster = board_and_parts()
    other = board.place(Kind.THRUSTER, (2, 0)).id
    assert run(board, thruster, other) is None  # a thruster has no output, nor takes one twice
