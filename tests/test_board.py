import json

import pytest

from nektoids.graph.board import (
    FACING_NAMES,
    Board,
    Kind,
    Refused,
    Wire,
    can_pass,
    complexity,
)
from nektoids.graph.hexgrid import NE, NW, SE, SW, E, W, direction_to, hex_disc, offset_rect
from nektoids.graph.kinds import Category

RECT = offset_rect(9, 7)  # a 9 x 7 zone for most tests

# Row 3 of a 9 x 7 board runs from (-1, 3) to (7, 3) along the E-W axis.


def bends(path):
    return sum(
        direction_to(a, b) != direction_to(b, c)
        for a, b, c in zip(path, path[1:], path[2:], strict=False)
    )


def build(cells_and_kinds, cols=9, rows=7):
    board = Board(offset_rect(cols, rows))
    nodes = [board.place(kind, cell) for cell, kind in cells_and_kinds]
    return board, nodes


# Kinds


def test_sensors_only_emit_and_thrusters_only_receive():
    assert Kind.EYE.category is Category.SENSOR
    assert Kind.EYE.emits and not Kind.EYE.receives
    assert Kind.DOUBLE.emits and Kind.DOUBLE.receives
    assert Kind.THRUSTER.receives and not Kind.THRUSTER.emits


# Complexity


def test_complexity_counts_the_parts_locked_or_not_and_not_the_wires():
    board, (eye, thruster) = build([((0, 0), Kind.EYE), ((4, 0), Kind.THRUSTER)])
    assert complexity(board) == 2
    board.place(Kind.SOURCE, (2, 2), locked=True)
    assert complexity(board) == 3
    assert not isinstance(board.connect(eye.id, thruster.id), Refused)
    assert complexity(board) == 3  # a wire costs nothing, however long (D-045)


# Placement


def test_eyes_and_thrusters_point_where_placed_operators_nowhere():
    board = Board(RECT)
    assert board.place(Kind.EYE, (0, 1)).facing == E  # the kind's default: forward
    assert board.place(Kind.EYE, (0, 3), facing=W).facing == W
    assert board.place(Kind.THRUSTER, (4, 1), locked=True, facing=SE).facing == SE
    assert board.place(Kind.DOUBLE, (2, 3), facing=E).facing is None


def test_rotate_turns_eyes_and_thrusters_in_place_only():
    board = Board(RECT)
    eye = board.place(Kind.EYE, (0, 1))
    assert board.rotate(eye.id, -1).facing == SE  # from E, one step clockwise
    assert board.rotate(eye.id, -1).facing == SW
    assert board.rotate(eye.id, 8).facing == E  # two steps back, plus a full turn
    assert board.nodes[eye.id].cell == (0, 1)
    gain = board.place(Kind.DOUBLE, (2, 3))
    assert board.rotate(gain.id, 1) == Refused("doubles have no direction")
    source = board.place(Kind.SOURCE, (4, 3))
    assert source.facing is None
    assert board.rotate(source.id, 1) == Refused("sources have no direction")
    fixed = board.place(Kind.THRUSTER, (6, 1), locked=True)
    assert board.rotate(fixed.id, 1) == Refused("placed by the level")


def test_moving_a_component_reroutes_its_wires_only():
    board, (eye, gain, other, half) = build(
        [((0, 3), Kind.EYE), ((4, 3), Kind.DOUBLE), ((2, 1), Kind.EYE), ((2, 5), Kind.HALVE)]
    )
    mine = board.connect(eye.id, gain.id)
    theirs = board.connect(other.id, half.id)
    moved = board.move_node(gain.id, (4, 1))
    assert moved.cell == (4, 1) and board.node_at((4, 3)) is None
    assert board.wires[0].path[0] == (0, 3) and board.wires[0].path[-1] == (4, 1)
    assert board.wires[0] != mine
    assert board.wires[1] == theirs  # not attached: untouched, still second


def test_a_move_its_wires_cannot_follow_changes_nothing():
    board, (eye, gain, _) = build(
        [((0, 0), Kind.EYE), ((1, 0), Kind.DOUBLE), ((2, 0), Kind.HALVE)], cols=4, rows=1
    )
    wire = board.connect(eye.id, gain.id)
    assert board.move_node(gain.id, (3, 0)) == Refused("its wires would find no free path")
    assert board.nodes[gain.id].cell == (1, 0)
    assert board.wires == [wire]


def test_move_refusals():
    board, (eye, gain, other, half) = build(
        [((0, 3), Kind.EYE), ((4, 3), Kind.DOUBLE), ((2, 1), Kind.EYE), ((2, 5), Kind.HALVE)]
    )
    assert board.move_node(eye.id, (4, 3)) == Refused("cell taken")
    assert board.move_node(eye.id, (20, 3)) == Refused("outside the zone")
    fixed = board.place(Kind.THRUSTER, (6, 3), locked=True)
    assert board.move_node(fixed.id, (6, 2)) == Refused("placed by the level")
    # Onto a cell its own wire crosses is fine: that wire is routed again.
    board.connect(eye.id, gain.id)
    assert board.move_node(eye.id, (1, 3)).cell == (1, 3)


def test_a_part_moved_onto_a_wire_has_it_routed_round():
    board, (eye, _, other, half) = build(
        [((0, 3), Kind.EYE), ((4, 3), Kind.DOUBLE), ((2, 1), Kind.EYE), ((2, 5), Kind.HALVE)]
    )
    board.connect(other.id, half.id)  # runs straight down through (2, 3)
    assert board.move_node(eye.id, (2, 3)).cell == (2, 3)  # D-086
    (wire,) = board.wires
    assert (2, 3) not in wire.path and (wire.source, wire.target) == (other.id, half.id)
    # A part whose cell a wire crosses with no way round: nothing changes.
    board, (eye, gain, spare) = build(
        [((0, 0), Kind.EYE), ((2, 0), Kind.DOUBLE), ((3, 0), Kind.HALVE)], cols=4, rows=1
    )
    wire = board.connect(eye.id, gain.id)
    refused = Refused("the wires here would find no way round")
    assert board.move_node(spare.id, (1, 0)) == refused
    assert board.nodes[spare.id].cell == (3, 0) and board.wires == [wire]


def test_place_refuses_off_board_and_taken_cells():
    board = Board(RECT)
    node = board.place(Kind.DOUBLE, (2, 3))
    assert board.node_at((2, 3)) == node
    assert board.place(Kind.HALVE, (2, 3)) == Refused("cell taken")
    assert board.place(Kind.HALVE, (20, 3)) == Refused("outside the zone")


def test_stock_runs_out_and_comes_back_on_removal():
    board = Board(RECT, stock={Kind.EYE: 1, Kind.DOUBLE: None})
    eye = board.place(Kind.EYE, (0, 3))
    assert board.remaining(Kind.EYE) == 0
    assert board.place(Kind.EYE, (1, 3)) == Refused("none left")
    assert board.place(Kind.HALVE, (1, 3)) == Refused("none left")  # not in the stock at all
    assert board.remaining(Kind.DOUBLE) is None
    assert board.total(Kind.EYE) == 1 and board.total(Kind.HALVE) == 0
    assert board.remove_node(eye.id) is None
    assert board.remaining(Kind.EYE) == 1


def test_locked_nodes_use_no_stock_and_cannot_be_removed():
    board = Board(RECT, stock={})
    eye = board.place(Kind.EYE, (0, 3), locked=True)
    assert eye.locked
    assert board.remove_node(eye.id) == Refused("placed by the level")
    assert board.node_at((0, 3)) == eye


def test_a_part_put_on_a_wire_has_the_wire_routed_round_it():
    board, (eye, gain) = build([((0, 3), Kind.EYE), ((4, 3), Kind.DOUBLE)])
    straight = board.connect(eye.id, gain.id)
    assert (2, 3) in straight.path
    assert board.place(Kind.HALVE, (2, 3)).cell == (2, 3)  # D-086
    (wire,) = board.wires
    assert (wire.source, wire.target) == (eye.id, gain.id) and (2, 3) not in wire.path
    assert len(wire.path) == len(straight.path) + 1  # the shortest way round: one step more


def test_the_wires_crossing_a_part_go_round_in_the_order_drawn_each_in_its_place():
    board, (west, east, north, south, low, high) = build(
        [
            ((0, 3), Kind.EYE),
            ((4, 3), Kind.DOUBLE),
            ((2, 1), Kind.EYE),
            ((2, 5), Kind.HALVE),
            ((0, 6), Kind.EYE),
            ((4, 6), Kind.SUM),
        ]
    )
    apart = board.connect(low.id, high.id)  # along the bottom row, nowhere near (2, 3)
    board.connect(west.id, east.id)  # across (2, 3)
    board.connect(north.id, south.id)  # down through (2, 3), on another axis
    board.place(Kind.DIFFERENCE, (2, 3))
    assert board.wires[0] == apart  # untouched
    ends = [(w.source, w.target) for w in board.wires]
    assert ends == [(low.id, high.id), (west.id, east.id), (north.id, south.id)]
    assert all((2, 3) not in w.path for w in board.wires)


def test_a_part_whose_wires_find_no_way_round_is_refused_and_nothing_changes():
    board = Board(offset_rect(3, 1), stock={Kind.EYE: 1, Kind.DOUBLE: 1, Kind.HALVE: 1})
    eye, gain = board.place(Kind.EYE, (0, 0)), board.place(Kind.DOUBLE, (2, 0))
    wire = board.connect(eye.id, gain.id)
    refused = Refused("the wires here would find no way round")
    assert board.place(Kind.HALVE, (1, 0)) == refused
    assert board.wires == [wire] and board.node_at((1, 0)) is None
    assert board.remaining(Kind.HALVE) == 1  # the part is still to place


def test_removing_a_node_removes_its_wires_and_frees_their_cells():
    board, (eye, gain) = build([((0, 3), Kind.EYE), ((4, 3), Kind.DOUBLE)])
    board.connect(eye.id, gain.id)
    board.remove_node(gain.id)
    assert board.wires == []
    assert board.wires_in((2, 3)) == []
    assert isinstance(board.place(Kind.HALVE, (2, 3)), type(eye))


# Wire validity


def test_wires_run_from_outputs_to_inputs_without_loops():
    board, (eye, gain, half, thrust) = build(
        [
            ((0, 1), Kind.EYE),
            ((2, 3), Kind.DOUBLE),
            ((4, 3), Kind.HALVE),
            ((6, 1), Kind.THRUSTER),
        ]
    )
    assert board.connect(thrust.id, gain.id) == Refused("thrusters have no output")
    assert board.connect(gain.id, eye.id) == Refused("sensors have no input")
    assert board.connect(gain.id, gain.id) == Refused("same component")
    assert not isinstance(board.connect(gain.id, half.id), Refused)
    assert board.connect(gain.id, half.id) == Refused("already wired")
    assert board.connect(half.id, gain.id) == Refused("would close a loop")
    assert len(board.wires) == 1


def test_sum_and_difference_take_two_inputs_and_give_one_output():
    board, (a, b, c, total, left, right) = build(
        [
            ((0, 1), Kind.SOURCE),
            ((0, 3), Kind.EYE),
            ((0, 5), Kind.EYE),
            ((3, 3), Kind.SUM),
            ((6, 1), Kind.THRUSTER),
            ((6, 5), Kind.THRUSTER),
        ]
    )
    assert Kind.SOURCE.emits and not Kind.SOURCE.receives
    assert not isinstance(board.connect(a.id, total.id), Refused)
    assert not isinstance(board.connect(b.id, total.id), Refused)
    assert board.connect(c.id, total.id) == Refused("a sum takes two inputs")
    assert not isinstance(board.connect(total.id, left.id), Refused)
    assert board.connect(total.id, right.id) == Refused("a sum has one output")
    # Other parts keep fanning out and in freely.
    assert not isinstance(board.connect(c.id, right.id), Refused)
    assert not isinstance(board.connect(c.id, left.id), Refused)


def test_a_part_swapped_keeps_its_cell_and_the_wires_it_can_take():
    board, (a, b, c, double, left) = build(
        [
            ((0, 1), Kind.SOURCE),
            ((0, 3), Kind.EYE),
            ((0, 5), Kind.EYE),
            ((3, 3), Kind.DOUBLE),
            ((6, 3), Kind.THRUSTER),
        ]
    )
    for part in (a, b, c):
        board.connect(part.id, double.id)
    board.connect(double.id, left.id)
    node, lost = board.replace(double.id, Kind.SUM)  # D-068
    assert node.cell == (3, 3) and node.kind is Kind.SUM and double.id not in board.nodes
    assert lost == 1  # a sum takes two inputs: the third wire goes, the others follow
    ends = sorted((w.source, w.target) for w in board.wires)
    assert ends == sorted([(a.id, node.id), (b.id, node.id), (node.id, left.id)])
    source, _ = board.replace(b.id, Kind.SOURCE)
    assert source.facing is None  # an eye's facing goes to a part that has none


def test_a_swap_needs_one_left_and_leaves_a_locked_part_alone():
    board = Board(offset_rect(9, 7), {Kind.EYE: 1, Kind.SOURCE: 0})
    eye = board.place(Kind.EYE, (0, 3))
    before = board.snapshot()
    assert board.replace(eye.id, Kind.SOURCE) == Refused("none left")
    assert board.snapshot() == before
    locked = board.place(Kind.THRUSTER, (4, 3), locked=True)
    assert board.replace(locked.id, Kind.THRUSTER) == Refused("placed by the level")


# Routing


def test_adjacent_components_are_wired_with_no_cell_between():
    board, (eye, gain) = build([((0, 3), Kind.EYE), ((1, 3), Kind.DOUBLE)])
    assert board.connect(eye.id, gain.id).path == ((0, 3), (1, 3))


def test_open_board_gives_a_straight_wire():
    board, (eye, gain) = build([((0, 3), Kind.EYE), ((5, 3), Kind.DOUBLE)])
    path = board.connect(eye.id, gain.id).path
    assert path == tuple((q, 3) for q in range(6))


def test_detour_is_shortest_then_straightest():
    # Pinned: if this route changes, every player's layout changes with it.
    board, (eye, gain, _) = build([((0, 3), Kind.EYE), ((5, 3), Kind.DOUBLE), ((2, 3), Kind.HALVE)])
    path = board.connect(eye.id, gain.id).path
    assert path == ((0, 3), (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (5, 3))
    assert (len(path) - 1, bends(path)) == (6, 2)


def test_wires_cross_straight_on_different_axes():
    board, (eye, gain, other_eye, half) = build(
        [
            ((0, 3), Kind.EYE),
            ((6, 3), Kind.DOUBLE),
            ((3, 1), Kind.EYE),
            ((3, 5), Kind.HALVE),
        ]
    )
    board.connect(eye.id, gain.id)
    crossing = board.connect(other_eye.id, half.id)
    assert crossing.path == ((3, 1), (3, 2), (3, 3), (3, 4), (3, 5))
    assert len(board.wires_in((3, 3))) == 2


def test_can_pass_rules():
    # Empty cell: straight, 60° or 120° turn; never a U-turn.
    assert can_pass(set(), E, E)
    assert can_pass(set(), E, NE)
    assert can_pass(set(), E, NW)
    assert not can_pass(set(), E, W)
    # A wire heading E comes in by the W edge and leaves by the E edge.
    straight = {W, E}
    assert can_pass(straight, NE, NE)  # crossing on another axis: SW and NE edges
    assert not can_pass(straight, E, E)  # superposed
    assert not can_pass(straight, NE, E)  # would leave by the E edge
    # A wire turning from the W edge to the NW edge leaves four edges free.
    turn = {W, NW}
    assert can_pass(turn, NE, E)  # SW edge in, E edge out: a second turn in the same cell
    assert can_pass(turn, NW, NE)  # SE edge in, NE edge out: a third
    assert not can_pass(turn, E, NE)  # would come in by the W edge


def hand_drawn(board, path):
    """Add a wire along a given path, between two operators placed at its ends."""
    source = board.place(Kind.DOUBLE, path[0])
    target = board.place(Kind.HALVE, path[-1])
    wire = Wire(source.id, target.id, path)
    board.wires.append(wire)
    return wire


def test_a_wire_crosses_straight_where_another_turns():
    board = Board(RECT)
    hand_drawn(board, ((2, 3), (3, 3), (3, 2)))  # turns in (3, 3): W edge to NW edge
    eye, gain = board.place(Kind.EYE, (2, 4)), board.place(Kind.DOUBLE, (4, 2))
    assert board.connect(eye.id, gain.id).path == ((2, 4), (3, 3), (4, 2))  # SW edge to NE edge


def test_two_wires_turn_in_the_same_cell():
    board = Board(RECT)
    hand_drawn(board, ((2, 3), (3, 3), (3, 2)))  # turns in (3, 3): W edge to NW edge
    board.place(Kind.HALVE, (3, 4))  # blocks the other shortest path, via (3, 4)
    eye, gain = board.place(Kind.EYE, (2, 4)), board.place(Kind.DOUBLE, (4, 3))
    assert board.connect(eye.id, gain.id).path == ((2, 4), (3, 3), (4, 3))  # SW edge to E edge


def test_no_free_path_leaves_the_board_unchanged():
    board, (eye, _, gain) = build(
        [((0, 0), Kind.EYE), ((1, 0), Kind.HALVE), ((2, 0), Kind.DOUBLE)], cols=3, rows=1
    )
    assert board.connect(eye.id, gain.id) == Refused("no free path")
    assert board.wires == []


# Many wires at once

LAYOUT = [
    ((0, 1), Kind.EYE),
    ((-2, 5), Kind.EYE),
    ((8, 1), Kind.THRUSTER),
    ((6, 5), Kind.THRUSTER),
    ((1, 3), Kind.DOUBLE),
    ((3, 3), Kind.HALVE),
    ((5, 3), Kind.DOUBLE),
    ((4, 1), Kind.HALVE),
    ((2, 5), Kind.DOUBLE),
]


def wire_everything():
    """Try every ordered pair of components, in id order."""
    board, nodes = build(LAYOUT)
    for source in nodes:
        for target in nodes:
            board.connect(source.id, target.id)
    return board


def test_many_wires_never_share_an_edge():
    board = wire_everything()
    assert len(board.wires) >= 10  # enough wires for the check below to mean something
    component_cells = {node.cell for node in board.nodes.values()}
    edges = []  # (cell, edge) for every edge any wire goes through, counted with repeats
    for wire in board.wires:
        path = wire.path
        assert path[0] == board.nodes[wire.source].cell
        assert path[-1] == board.nodes[wire.target].cell
        assert all(cell in board.cells for cell in path)
        for a, b, c in zip(path, path[1:], path[2:], strict=False):
            assert b not in component_cells
            entry, exit_ = direction_to(b, a), direction_to(b, c)
            assert entry != exit_  # no U-turn
            edges += [(b, entry), (b, exit_)]
    assert len(edges) == len(set(edges))


def test_same_moves_give_the_same_wires():
    assert wire_everything().wires == wire_everything().wires


def test_a_wire_drawn_backwards_is_turned_round_only_when_the_kinds_say_so():
    board, (eye, other_eye, double, total, thruster, other_thruster) = build(
        [
            ((0, 1), Kind.EYE),
            ((0, 5), Kind.EYE),
            ((3, 1), Kind.DOUBLE),
            ((3, 5), Kind.SUM),
            ((6, 1), Kind.THRUSTER),
            ((6, 5), Kind.THRUSTER),
        ]
    )
    turned = {
        (thruster, eye): (eye, thruster),  # from a thruster
        (double, eye): (eye, double),  # into a sensor
        (thruster, double): (double, thruster),
    }
    as_drawn = [
        (eye, thruster),
        (double, total),  # two operators: the way it is drawn
        (total, double),
        (eye, other_eye),  # neither way: left for connect to refuse
        (thruster, other_thruster),
    ]
    for (a, b), (source, target) in turned.items():
        assert board.orient(a.id, b.id) == (source.id, target.id)
    for a, b in as_drawn:
        assert board.orient(a.id, b.id) == (a.id, b.id)
    assert isinstance(board.connect(*board.orient(eye.id, other_eye.id)), Refused)


def test_a_wire_drawn_backwards_is_the_wire_drawn_forwards_route_and_all():
    # From (0, 0) to (2, 1) the route heads E first, from (2, 1) to (0, 0) it heads SE (D-007).
    forwards, (eye, thruster) = build([((0, 0), Kind.EYE), ((2, 1), Kind.THRUSTER)])
    backwards, _ = build([((0, 0), Kind.EYE), ((2, 1), Kind.THRUSTER)])
    drawn = forwards.connect(eye.id, thruster.id)
    turned = backwards.connect(*backwards.orient(thruster.id, eye.id))
    assert turned == drawn
    assert drawn.path == ((0, 0), (1, 0), (2, 0), (2, 1))
    # Routed the way it was drawn, from the thruster, it would have been another wire.
    assert backwards.route((2, 1), (0, 0)) != tuple(reversed(drawn.path))


# As plain data (D-024)


def test_direction_names_follow_the_hex_directions():
    assert [FACING_NAMES.index(name) for name in ("E", "NE", "NW", "W", "SW", "SE")] == [
        E,
        NE,
        NW,
        W,
        SW,
        SE,
    ]


def test_a_board_saved_and_loaded_is_the_same_board_and_survives_json():
    board = Board(RECT, {Kind.EYE: 2, Kind.SOURCE: 1, Kind.HALVE: None, Kind.THRUSTER: 2})
    eye = board.place(Kind.EYE, (0, 1), facing=NE)
    source = board.place(Kind.SOURCE, (0, 5))
    half = board.place(Kind.HALVE, (3, 3))
    thruster = board.place(Kind.THRUSTER, (6, 3), facing=SW)
    for a, b in ((eye, half), (half, thruster), (source, thruster)):
        assert not isinstance(board.connect(a.id, b.id), Refused)
    data = board.to_dict()
    loaded = Board.from_dict(json.loads(json.dumps(data)))
    assert loaded.to_dict() == data
    assert loaded.nodes == board.nodes and loaded.wires == board.wires
    assert loaded.remaining(Kind.EYE) == board.remaining(Kind.EYE) == 1
    assert data["parts"][0] == {"kind": "eye", "cell": [0, 1], "facing": "NE", "locked": False}
    assert data["parts"][1]["facing"] is None


def test_ids_left_by_a_deleted_part_close_up_on_loading():
    board = Board(RECT)
    first, gone, last = (board.place(Kind.EYE, (q, 1)) for q in (0, 2, 4))
    thruster = board.place(Kind.THRUSTER, (4, 3))
    board.connect(last.id, thruster.id)
    board.remove_node(gone.id)
    loaded = Board.from_dict(board.to_dict())
    assert sorted(loaded.nodes) == [0, 1, 2]
    assert [(w.source, w.target) for w in loaded.wires] == [(1, 2)]


def test_data_no_board_could_hold_is_an_error():
    data = Board(RECT).to_dict()
    data["parts"] = [{"kind": "eye", "cell": [99, 99], "facing": "E", "locked": False}]
    with pytest.raises(ValueError, match="outside the zone"):
        Board.from_dict(data)


def detour():
    """An eye and a thruster on row 3, their wire drawn round a Double then deleted: the wire
    keeps its detour, which the router would not take now."""
    board = Board(RECT)
    eye, thruster = board.place(Kind.EYE, (0, 3)), board.place(Kind.THRUSTER, (4, 3))
    block = board.place(Kind.DOUBLE, (2, 3))
    wire = board.connect(eye.id, thruster.id)
    board.remove_node(block.id)
    assert wire.path != board.route(eye.cell, thruster.cell)  # straight along the row, now
    return board, wire


def test_a_board_comes_back_with_its_wires_on_their_saved_paths_even_off_the_router():
    board, wire = detour()
    loaded = Board.from_dict(json.loads(json.dumps(board.to_dict())))  # D-204
    assert loaded.wires == board.wires and loaded.wires[0].path == wire.path


def test_a_wire_saved_without_its_path_is_routed():
    board, _ = detour()
    data = board.to_dict()
    del data["wires"][0]["path"]
    loaded = Board.from_dict(data)
    assert loaded.wires[0].path == board.route((0, 3), (4, 3))


@pytest.mark.parametrize(
    ("path", "reason"),
    [
        ([[0, 3], [1, 3], [2, 3], [3, 3]], "does not join its ends"),
        ([[0, 3], [2, 3], [3, 3], [4, 3]], "jumps a cell"),
        ([[0, 3], [1, 3], [2, 3], [3, 3], [4, 3]], None),  # the straight one: allowed
    ],
)
def test_a_saved_path_is_checked_against_the_board(path, reason):
    board, _ = detour()
    data = board.to_dict()
    data["wires"][0]["path"] = path
    if reason is None:
        assert Board.from_dict(data).wires[0].path == tuple(map(tuple, path))
    else:
        with pytest.raises(ValueError, match=reason):
            Board.from_dict(data)


def test_a_saved_path_may_not_cross_a_part_leave_the_zone_or_take_another_wires_edge():
    board = Board(hex_disc(1))  # seven cells round (0, 0)
    eye, other = board.place(Kind.EYE, (-1, 0)), board.place(Kind.EYE, (0, -1))
    thruster = board.place(Kind.THRUSTER, (1, 0))
    first = board.connect(eye.id, thruster.id)
    assert first.path == ((-1, 0), (0, 0), (1, 0))  # through the centre, by its W and E edges
    for path, reason in (
        (((0, -1), (-1, 0), (0, 0), (1, 0)), "its path crosses a part"),
        (((0, -1), (1, -2), (1, -1), (1, 0)), "its path leaves the zone"),
        (((0, -1), (0, 0), (1, 0)), "its path takes an edge another wire has"),  # E of (0, 0)
    ):
        assert board.connect(other.id, thruster.id, path) == Refused(reason)
    assert board.connect(other.id, thruster.id, ((0, -1), (1, -1), (1, 0))).path[1] == (1, -1)


def a_vehicle(stock):
    """Two eyes wired to two thrusters on a 9 x 7 board handing out `stock`."""
    board = Board(RECT, stock)
    left, right = board.place(Kind.EYE, (0, 2)), board.place(Kind.EYE, (0, 4))
    back_left, back_right = board.place(Kind.THRUSTER, (4, 2)), board.place(Kind.THRUSTER, (4, 4))
    board.connect(left.id, back_left.id)
    board.connect(right.id, back_right.id)
    return board


def test_adopt_puts_another_levels_board_on_this_one_its_stock_counted_again():
    fear = a_vehicle({Kind.EYE: 2, Kind.THRUSTER: 2}).snapshot()  # D-092
    shadows = Board(RECT, {Kind.EYE: 2, Kind.SOURCE: 1, Kind.SUM: None, Kind.THRUSTER: 2})
    assert shadows.adopt(fear) is None
    assert (shadows.snapshot().nodes, shadows.snapshot().wires) == (fear.nodes, fear.wires)
    assert shadows.remaining(Kind.EYE) == 0 and shadows.remaining(Kind.SOURCE) == 1
    assert shadows.remaining(Kind.SUM) is None
    source = shadows.place(Kind.SOURCE, (2, 0))  # a fresh id, past every adopted one
    assert source.id not in {node.id for node in fear.nodes} and len(shadows.nodes) == 5


def test_adopt_refuses_a_board_this_level_cannot_hold_and_changes_nothing():
    love = a_vehicle({Kind.EYE: 2, Kind.SUM: 2, Kind.THRUSTER: 2})
    love.place(Kind.SUM, (2, 0))
    fear = Board(RECT, {Kind.EYE: 2, Kind.THRUSTER: 2})
    before = fear.snapshot()
    assert fear.adopt(love.snapshot()) == Refused("this level hands out no sums")
    one_eye = Board(RECT, {Kind.EYE: 1, Kind.THRUSTER: 2})
    reason = "this level hands out one eye; the board has two"
    assert one_eye.adopt(a_vehicle(None).snapshot()) == Refused(reason)
    small = Board(offset_rect(3, 7))  # the thrusters at column 4 are off its zone
    assert small.adopt(a_vehicle(None).snapshot()).reason.startswith("the board goes outside")
    locked = Board(RECT)
    assert locked.place(Kind.EYE, (6, 3), locked=True).locked
    assert locked.adopt(a_vehicle(None).snapshot()) == Refused("this level places other parts")
    assert fear.snapshot() == before and small.nodes == {}


def test_a_board_handed_out_anew_keeps_its_parts_unless_they_no_longer_fit():
    board = Board(hex_disc(2), {Kind.EYE: 2, Kind.THRUSTER: 2})  # D-315: the Editor's Parts
    eye = board.place(Kind.EYE, (2, 0))
    board.place(Kind.EYE, (0, 0))
    board.connect(eye.id, board.place(Kind.THRUSTER, (1, 0)).id)
    before = board.snapshot()
    fewer = board.rehand(Board(hex_disc(2), {Kind.EYE: 1}))
    assert fewer.reason == "this level hands out one eye; the board has two"
    assert "outside" in board.rehand(Board(hex_disc(1), {Kind.EYE: 9, Kind.THRUSTER: 9})).reason
    assert board.snapshot() == before  # refused: nothing changed
    assert board.rehand(Board(hex_disc(3), {Kind.EYE: 3, Kind.THRUSTER: None})) is None
    assert len(board.cells) == 37 and board.remaining(Kind.EYE) == 1
    assert board.remaining(Kind.THRUSTER) is None and board.remaining(Kind.SUM) == 0
    assert len(board.nodes) == 3 and len(board.wires) == 1
    board.restore(before)  # a state from before: its stock left counted again from the new
    assert board.remaining(Kind.EYE) == 1 and board.total(Kind.EYE) == 3


def test_a_part_locked_is_the_levels_using_no_stock_and_freed_uses_one_again():
    board = Board(hex_disc(2), {Kind.EYE: 1, Kind.THRUSTER: 2})  # D-319
    eye = board.place(Kind.EYE, (0, 0))
    assert board.remaining(Kind.EYE) == 0 and board.lock(eye.id) is None
    assert board.nodes[eye.id].locked and board.remaining(Kind.EYE) == 1  # its stock back
    assert board.remove_node(eye.id).reason == "placed by the level"
    other = board.place(Kind.EYE, (1, 0))  # the one handed out, now free to place
    refused = board.lock(eye.id, locked=False)
    assert "no more eyes" in refused.reason and board.nodes[eye.id].locked  # none left
    board.remove_node(other.id)
    assert board.lock(eye.id, locked=False) is None and board.remaining(Kind.EYE) == 0


def test_a_board_handed_out_anew_takes_the_parts_the_level_places_locked():
    board = Board(hex_disc(2), {Kind.EYE: 2, Kind.THRUSTER: 2})  # D-319
    kept = board.place(Kind.EYE, (-1, -1), locked=True, facing=NE)
    freed = board.place(Kind.THRUSTER, (2, -1), locked=True, facing=E)
    board.connect(kept.id, freed.id)
    level = Board(hex_disc(2), {Kind.EYE: 2, Kind.THRUSTER: 2})
    level.place(Kind.EYE, (-1, -1), locked=True, facing=NE)  # the same: stays, wired
    level.place(Kind.THRUSTER, (1, 1), locked=True, facing=E)  # new: put down
    assert board.rehand(level) is None
    assert board.nodes[kept.id].locked and not board.nodes[freed.id].locked  # freed, kept
    placed = [n for n in board.nodes.values() if n.cell == (1, 1)]
    assert len(placed) == 1 and placed[0].locked and placed[0].facing == E
    assert len(board.wires) == 1 and board.remaining(Kind.THRUSTER) == 1
    blocked = Board(hex_disc(2), {Kind.EYE: 2, Kind.THRUSTER: 2})
    blocked.place(Kind.EYE, (2, -1), locked=True, facing=NE)  # where the freed thruster is
    before = board.snapshot()
    assert "where the level places an eye" in board.rehand(blocked).reason
    assert board.snapshot() == before


def test_erase_all_takes_every_wire_and_every_part_but_the_levels_own():
    board = Board(hex_disc(2), {Kind.EYE: 2, Kind.THRUSTER: 2})  # D-321
    eye = board.place(Kind.EYE, (-1, -1), locked=True, facing=NE)
    thruster = board.place(Kind.THRUSTER, (2, -1), facing=E)
    board.connect(eye.id, thruster.id)
    board.place(Kind.EYE, (0, 0))
    assert board.clear() == (2, 1) and list(board.nodes) == [eye.id] and not board.wires
    assert board.remaining(Kind.EYE) == 2 and board.remaining(Kind.THRUSTER) == 2
    assert board.clear() == (0, 0)  # nothing left to erase


def test_a_group_moves_together_its_wires_following_or_not_at_all():
    board = Board(hex_disc(2))  # D-402: picked parts move together
    eye, total, thruster = (
        board.place(k, c)
        for k, c in ((Kind.EYE, (1, 0)), (Kind.SUM, (0, 0)), (Kind.THRUSTER, (-1, 0)))
    )
    board.connect(eye.id, total.id)
    board.connect(total.id, thruster.id)
    assert board.move_group([eye.id, total.id], (0, -1)) is None  # up and to the right, both
    assert board.nodes[eye.id].cell == (1, -1) and board.nodes[total.id].cell == (0, -1)
    assert all(w.path[0] == board.nodes[w.source].cell for w in board.wires)  # wires follow
    assert len(board.wires) == 2
    before = board.snapshot()
    assert board.move_group([eye.id, total.id], (2, 0)).reason == "outside the zone"
    assert board.move_group([eye.id, total.id], (-1, 1)).reason == "cell taken"  # the thruster
    assert board.snapshot() == before  # refused whole: nothing moved
    assert board.move_group([eye.id, total.id], (0, 0)) is None and board.snapshot() == before
    locked = board.place(Kind.SOURCE, (0, 1), locked=True)
    assert board.move_group([locked.id], (0, 1)).reason == "placed by the level"


def test_a_part_the_player_locks_stays_put_its_wires_free_and_survives_erase_all_and_saving():
    board = Board(hex_disc(2))  # D-406
    eye, total = board.place(Kind.EYE, (0, 0)), board.place(Kind.SUM, (1, 0))
    assert board.pin(eye.id) is None and board.nodes[eye.id].fixed
    for refused in (
        board.move_node(eye.id, (0, 1)),
        board.rotate(eye.id, 1),
        board.remove_node(eye.id),
        board.replace(eye.id, Kind.SOURCE),
        board.move_group([eye.id, total.id], (0, 1)),
    ):
        assert refused.reason == "locked: free it first"
    assert not isinstance(board.connect(eye.id, total.id), Refused)  # its wires come and go
    saved = Board.from_dict(board.to_dict())
    assert [n.pinned for n in saved.nodes.values()] == [True, False]
    assert board.clear() == (1, 1) and list(board.nodes) == [eye.id]  # Erase all spares it
    assert board.pin(eye.id, False) is None and board.remove_node(eye.id) is None
    level = board.place(Kind.EYE, (0, 1), locked=True)
    assert board.pin(level.id).reason == "placed by the level"
