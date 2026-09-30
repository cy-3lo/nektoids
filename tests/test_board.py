from nektoids.graph.board import Board, Category, Kind, Refused, Wire, can_pass
from nektoids.graph.hexgrid import NE, NW, SE, SW, E, W, direction_to, offset_rect

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
    board.connect(other.id, half.id)  # runs straight down through (2, 3)
    assert board.move_node(eye.id, (2, 3)) == Refused("a wire runs here")
    assert board.move_node(eye.id, (4, 3)) == Refused("cell taken")
    assert board.move_node(eye.id, (20, 3)) == Refused("outside the zone")
    fixed = board.place(Kind.THRUSTER, (6, 3), locked=True)
    assert board.move_node(fixed.id, (6, 2)) == Refused("placed by the level")
    # Onto a cell its own wire crosses is fine: that wire is routed again.
    board.connect(eye.id, gain.id)
    assert board.move_node(eye.id, (2, 3)) == Refused("a wire runs here")  # still the other's
    assert board.move_node(eye.id, (1, 3)).cell == (1, 3)


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


def test_cannot_drop_a_component_on_a_wire():
    board, (eye, gain) = build([((0, 3), Kind.EYE), ((4, 3), Kind.DOUBLE)])
    board.connect(eye.id, gain.id)
    assert board.place(Kind.HALVE, (2, 3)) == Refused("a wire runs here")


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
