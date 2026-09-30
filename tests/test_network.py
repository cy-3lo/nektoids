import numpy as np
import pytest

from nektoids.graph.board import Board, Kind, Wire
from nektoids.graph.hexgrid import SE, offset_rect
from nektoids.graph.network import (
    Network,
    components,
    cyclic_components,
    topological_order,
)

EYE, SRC, DBL, HLV, SUM, DIF, THR = (
    Kind.EYE,
    Kind.SOURCE,
    Kind.DOUBLE,
    Kind.HALVE,
    Kind.SUM,
    Kind.DIFFERENCE,
    Kind.THRUSTER,
)


def build(cells_and_kinds):
    board = Board(offset_rect(9, 7))
    return board, [board.place(kind, cell) for cell, kind in cells_and_kinds]


def ring(kinds):
    """A loop through every node in turn, which no Board would draw."""
    n = len(kinds)
    return Network.from_edges(kinds, [(i, (i + 1) % n) for i in range(n)])


# Compiling a board


def test_nodes_are_numbered_by_id_and_wires_keep_their_drawing_order():
    board, (eye, src, dbl, thr) = build(
        [((0, 1), EYE), ((0, 3), SRC), ((3, 2), DBL), ((6, 2), THR)]
    )
    board.connect(src.id, dbl.id)
    board.connect(eye.id, dbl.id)
    board.connect(dbl.id, thr.id)
    net = Network.from_board(board)
    assert net.ids == (eye.id, src.id, dbl.id, thr.id)
    assert net.kinds == (EYE, SRC, DBL, THR)
    assert net.edges.tolist() == [[1, 2], [0, 2], [2, 3]]
    assert (
        net.eyes.tolist() == [0] and net.sources.tolist() == [1] and net.thrusters.tolist() == [3]
    )
    assert net.sensors.tolist() == [0, 1]
    assert net.outdeg.tolist() == [1, 1, 1, 0]
    assert net.gain.tolist() == [0.0, 0.0, 2.0, 1.0]


def test_facing_is_read_from_the_board():
    board, (eye, thr) = build([((0, 1), EYE), ((6, 2), THR)])
    board.rotate(thr.id, -1)
    net = Network.from_board(board)
    assert net.facing == (eye.facing, SE)


def test_inputs_are_sorted_by_source_whatever_the_drawing_order():
    cells = [((0, 1), EYE), ((0, 3), SRC), ((3, 2), SUM)]
    first, (a, b, total) = build(cells)
    first.connect(a.id, total.id)
    first.connect(b.id, total.id)
    second, (a, b, total) = build(cells)
    second.connect(b.id, total.id)
    second.connect(a.id, total.id)
    one, two = Network.from_board(first), Network.from_board(second)
    assert one.slots.tolist() == two.slots.tolist() == [[3, 3], [3, 3], [0, 1]]
    assert one.edges.tolist() != two.edges.tolist()


def test_a_difference_subtracts_its_second_input_and_a_lone_input_passes():
    net = Network.from_edges([EYE, SRC, DIF, EYE, DIF], [(1, 2), (0, 2), (3, 4)])
    assert net.slots[2].tolist() == [0, 1] and net.signs[2].tolist() == [1.0, -1.0]
    assert net.signs[4].tolist() == [1.0, 0.0]


def test_a_loop_drawn_by_hand_compiles():
    board, (eye, dbl, hlv) = build([((0, 3), EYE), ((3, 3), DBL), ((3, 1), HLV)])
    board.wires.append(Wire(dbl.id, hlv.id, board.route(dbl.cell, hlv.cell)))
    board.wires.append(Wire(hlv.id, dbl.id, board.route(hlv.cell, dbl.cell)))
    assert cyclic_components(Network.from_board(board)) == ((1, 2),)


def test_arrays_cannot_be_written():
    net = Network.from_edges([EYE, THR], [(0, 1)])
    for array in (net.edges, net.slots, net.signs, net.gain, net.outdeg, net.eyes):
        with pytest.raises(ValueError, match="read-only"):
            array[...] = 0


# What no board could hold


@pytest.mark.parametrize(
    ("kinds", "edges", "message"),
    [
        ([EYE, THR], [(0, 1), (0, 1)], "duplicate"),
        ([EYE, THR], [(0, 2)], "leaves the graph"),
        ([EYE, THR], [(1, 0)], "no output"),
        ([EYE, SRC], [(0, 1)], "no input"),
        ([EYE, EYE, EYE, SUM], [(0, 3), (1, 3), (2, 3)], "at most 2 inputs"),
    ],
)
def test_impossible_wires_are_refused(kinds, edges, message):
    with pytest.raises(ValueError, match=message):
        Network.from_edges(kinds, edges)


def test_ids_and_facing_need_one_entry_per_node():
    with pytest.raises(ValueError, match="one entry per node"):
        Network.from_edges([EYE, THR], [], ids=[0])


# Degenerate graphs are valid


def test_empty_isolated_and_dangling_graphs_compile():
    empty = Network.from_edges([], [])
    assert empty.n == 0 and empty.slots.shape == (0, 1)
    assert topological_order(empty) == () and components(empty) == ()
    lone = Network.from_edges([THR, SUM, DBL], [])
    assert lone.slots.tolist() == [[3], [3], [3]]
    assert topological_order(lone) == (0, 1, 2)
    assert cyclic_components(lone) == ()


# Order and loops


def test_topological_order_puts_sources_first_and_breaks_ties_by_index():
    net = Network.from_edges([THR, DBL, EYE, SRC], [(3, 1), (1, 0), (2, 0)])
    assert topological_order(net) == (2, 3, 1, 0)


def test_topological_order_is_none_when_there_is_a_loop():
    assert topological_order(ring([DBL, HLV])) is None
    assert topological_order(ring([DBL])) is None


def test_components_group_the_loop_and_leave_the_rest_alone():
    net = Network.from_edges([EYE, SUM, DBL, HLV, THR], [(0, 1), (1, 2), (2, 3), (3, 1), (3, 4)])
    assert components(net) == ((0,), (1, 2, 3), (4,))
    assert cyclic_components(net) == ((1, 2, 3),)


def test_a_wire_from_a_node_to_itself_is_a_loop_and_a_dag_has_none():
    assert cyclic_components(ring([DBL])) == ((0,),)
    dag = Network.from_edges([EYE, DBL, THR], [(0, 1), (1, 2)])
    assert cyclic_components(dag) == ()


def test_components_of_a_long_chain_with_a_loop_at_the_end():
    n = 40
    kinds = [EYE] + [DBL] * (n - 1)
    edges = [(i, i + 1) for i in range(n - 1)] + [(n - 1, n - 2)]
    net = Network.from_edges(kinds, edges)
    assert cyclic_components(net) == ((n - 2, n - 1),)
    assert np.all(net.outdeg[: n - 2] == 1)
