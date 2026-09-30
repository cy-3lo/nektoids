import hashlib

import numpy as np
import pytest

from nektoids.graph.board import Board, Kind
from nektoids.graph.evaluate import (
    RATE_MAX,
    SOURCE_RATE,
    AlgebraicLoopError,
    evaluate,
    sweep,
    thrust_rates,
    wire_flux,
)
from nektoids.graph.hexgrid import offset_rect
from nektoids.graph.network import Network, abs_coupling, contraction_factor

EYE, SRC, DBL, HLV, SUM, DIF, THR = (
    Kind.EYE,
    Kind.SOURCE,
    Kind.DOUBLE,
    Kind.HALVE,
    Kind.SUM,
    Kind.DIFFERENCE,
    Kind.THRUSTER,
)
KINDS = [EYE, SRC, DBL, HLV, SUM, DIF, THR]
GAINS = {DBL: 2.0, HLV: 0.5, SUM: 1.0, DIF: 1.0, THR: 1.0}


def run(kinds, edges, *eyes, sources=None):
    """Rates of one agent, as a list, for a network given by kinds and (source, target) wires."""
    net = Network.from_edges(kinds, edges)
    return evaluate(net, np.array([eyes], dtype=float).reshape(1, -1), sources)[0].tolist()


def reference(kinds, edges, eyes, sources):
    """The model of D-016 written recursively, independently of the code under test."""
    n = len(kinds)
    feeders = {i: sorted(a for a, b in edges if b == i) for i in range(n)}
    outdeg = {i: sum(a == i for a, _ in edges) for i in range(n)}
    eye_at = {i: k for k, i in enumerate(i for i in range(n) if kinds[i] is EYE)}
    source_at = {i: k for k, i in enumerate(i for i in range(n) if kinds[i] is SRC)}
    memo = {}

    def rate(i):
        if i not in memo:
            kind = kinds[i]
            if kind is EYE:
                memo[i] = min(max(eyes[eye_at[i]], 0.0), RATE_MAX)
            elif kind is SRC:
                memo[i] = min(max(sources[source_at[i]], 0.0), RATE_MAX)
            else:
                into = [rate(a) / outdeg[a] for a in feeders[i]]
                if kind is DIF and len(into) == 2:
                    total = into[0] - into[1]
                else:
                    total = sum(into)
                memo[i] = min(RATE_MAX, GAINS[kind] * abs(total))
        return memo[i]

    return [rate(i) for i in range(n)]


def random_dag(rng, n):
    """Random kinds and wires that a board could hold, on randomly permuted node numbers."""
    kinds = [KINDS[rng.integers(len(KINDS))] for _ in range(n)]
    edges = []
    for target, kind in enumerate(kinds):
        if not kind.receives:
            continue
        emitters = [i for i in range(target) if kinds[i].emits]
        wanted = rng.integers(0, (kind.max_inputs or 3) + 1)
        for source in rng.choice(emitters, size=min(wanted, len(emitters)), replace=False):
            edges.append((int(source), target))
    perm = rng.permutation(n)
    shuffled = [None] * n
    for old, new in enumerate(perm):
        shuffled[new] = kinds[old]
    return shuffled, [(int(perm[a]), int(perm[b])) for a, b in edges]


def random_inputs(rng, kinds, agents=1):
    eyes = rng.uniform(-3.0, 2.0 * RATE_MAX, size=(agents, kinds.count(EYE)))
    sources = rng.uniform(-1.0, 2.0 * RATE_MAX, size=kinds.count(SRC))
    return eyes, sources


# The rule at one node


def test_operators_apply_their_gain_to_the_rate_they_receive():
    assert run([EYE, DBL], [(0, 1)], 0.25)[1] == 0.5
    assert run([EYE, HLV], [(0, 1)], 0.25)[1] == 0.125
    assert run([EYE, SUM], [(0, 1)], 0.25)[1] == 0.25  # one input passes
    assert run([EYE, DIF], [(0, 1)], 0.25)[1] == 0.25
    assert run([EYE, THR], [(0, 1)], 0.25)[1] == 0.25


def test_sum_adds_and_difference_takes_the_gap_in_either_order():
    assert run([EYE, EYE, SUM], [(0, 2), (1, 2)], 0.375, 0.125)[2] == 0.5
    assert run([EYE, EYE, DIF], [(0, 2), (1, 2)], 0.375, 0.125)[2] == 0.25
    assert run([EYE, EYE, DIF], [(0, 2), (1, 2)], 0.125, 0.375)[2] == 0.25


def test_several_wires_into_a_doubler_or_a_thruster_are_added_first():
    assert run([EYE, EYE, DBL], [(0, 2), (1, 2)], 0.125, 0.0625)[2] == 0.375
    assert run([EYE, EYE, THR], [(0, 2), (1, 2)], 0.125, 0.0625)[2] == 0.1875


def test_a_node_with_nothing_wired_in_has_rate_zero():
    assert run([SUM, DBL, THR], []) == [0.0, 0.0, 0.0]


def test_a_source_emits_its_rate_unless_the_developer_overrides_it():
    assert run([SRC, THR], [(0, 1)])[1] == SOURCE_RATE
    assert run([SRC, THR], [(0, 1)], sources=[0.375])[1] == 0.375


def test_the_empty_network_has_no_rates():
    net = Network.from_edges([], [])
    assert evaluate(net, np.zeros((3, 0))).shape == (3, 0)


# Split


def test_a_fork_shares_the_rate_between_its_wires():
    # One eye feeding two thrusters: each gets half.
    assert run([EYE, THR, THR], [(0, 1), (0, 2)], 0.75) == [0.75, 0.375, 0.375]
    # Three wires: a third each, which a cap at two outputs would have forbidden.
    rates = run([EYE, THR, THR, THR], [(0, 1), (0, 2), (0, 3)], 0.75)
    assert rates[1:] == [0.25, 0.25, 0.25]


def test_the_flux_leaving_a_node_adds_up_to_its_rate():
    rng = np.random.default_rng(1)
    for _ in range(50):
        kinds, edges = random_dag(rng, 12)
        net = Network.from_edges(kinds, edges)
        eyes, sources = random_inputs(rng, kinds)
        y = evaluate(net, eyes, sources)
        flux = wire_flux(net, y)
        for i in range(net.n):
            leaving = flux[:, net.edges[:, 0] == i].sum(axis=1)
            if net.outdeg[i]:
                assert leaving == pytest.approx(y[:, i], rel=1e-12, abs=1e-12)


# Cap


def test_no_rate_exceeds_the_cap_and_none_is_negative():
    rng = np.random.default_rng(2)
    for _ in range(200):
        kinds, edges = random_dag(rng, 14)
        net = Network.from_edges(kinds, edges)
        eyes, sources = random_inputs(rng, kinds, agents=4)
        y = evaluate(net, eyes, sources)
        assert y.min() >= 0.0 and y.max() <= RATE_MAX


def test_doublers_in_a_row_saturate_at_the_cap():
    kinds = [EYE] + [DBL] * 5
    edges = [(i, i + 1) for i in range(5)]
    for x in (0.0, 0.01, 0.03, 0.125, 0.5):
        assert run(kinds, edges, x)[-1] == min(RATE_MAX, 32 * x)


def test_the_order_of_a_sum_and_a_gain_matters_at_the_cap():
    # Halve after a Sum, or a Halve before each input of the Sum: 4 against 8 when both are full.
    after = run([EYE, EYE, SUM, HLV], [(0, 2), (1, 2), (2, 3)], 1.0, 1.0)[3]
    before = run([EYE, EYE, HLV, HLV, SUM], [(0, 2), (1, 3), (2, 4), (3, 4)], 1.0, 1.0)[4]
    assert (after, before) == (0.5, 1.0)
    # Same for a Double and a Difference: the Double caps each input first.
    after = run([EYE, EYE, DIF, DBL], [(0, 2), (1, 2), (2, 3)], 1.0, 0.75)[3]
    before = run([EYE, EYE, DBL, DBL, DIF], [(0, 2), (1, 3), (2, 4), (3, 4)], 1.0, 0.75)[4]
    assert (after, before) == (0.5, 0.0)


def test_eyes_beyond_their_range_are_clipped():
    assert run([EYE, THR], [(0, 1)], 100.0)[1] == RATE_MAX
    assert run([EYE, THR], [(0, 1)], -5.0)[1] == 0.0


# The DAG against an independent evaluator


def test_random_dags_agree_with_the_reference_evaluator():
    rng = np.random.default_rng(3)
    for _ in range(300):
        kinds, edges = random_dag(rng, int(rng.integers(1, 16)))
        net = Network.from_edges(kinds, edges)
        eyes, sources = random_inputs(rng, kinds)
        expected = reference(kinds, edges, eyes[0], sources)
        np.testing.assert_allclose(evaluate(net, eyes, sources)[0], expected, rtol=1e-12)


# Braitenberg


def test_crossed_and_uncrossed_wiring_swap_the_thrusters():
    eyes = [EYE, EYE, THR, THR]
    uncrossed = run(eyes, [(0, 2), (1, 3)], 0.75, 0.25)
    crossed = run(eyes, [(0, 3), (1, 2)], 0.75, 0.25)
    assert uncrossed[2:] == [0.75, 0.25] and crossed[2:] == [0.25, 0.75]


def test_a_difference_does_not_care_which_input_is_which_bit_for_bit():
    net = Network.from_edges([EYE, EYE, DIF], [(0, 2), (1, 2)])
    rng = np.random.default_rng(8)
    for a, b in rng.uniform(0.0, RATE_MAX, size=(100, 2)):
        assert evaluate(net, np.array([[a, b]]))[0, 2] == evaluate(net, np.array([[b, a]]))[0, 2]


def test_a_mirrored_board_gives_mirrored_thrusters_bit_for_bit():
    kinds = [EYE, EYE, HLV, HLV, THR, THR]
    edges = [(0, 2), (1, 3), (2, 4), (3, 5)]
    net = Network.from_edges(kinds, edges)
    a = evaluate(net, np.array([[0.53, 0.21]]))[0]
    b = evaluate(net, np.array([[0.21, 0.53]]))[0]
    assert (a[4], a[5]) == (b[5], b[4])


# Determinism


def trajectory_hash(net, eyes):
    return hashlib.sha256(evaluate(net, eyes).tobytes()).hexdigest()


def test_two_runs_give_the_same_bytes():
    rng = np.random.default_rng(4)
    kinds, edges = random_dag(rng, 15)
    net = Network.from_edges(kinds, edges)
    eyes, _ = random_inputs(rng, kinds, agents=9)
    assert trajectory_hash(net, eyes) == trajectory_hash(net, eyes)


def test_the_order_wires_were_drawn_in_changes_nothing():
    rng = np.random.default_rng(5)
    for _ in range(50):
        kinds, edges = random_dag(rng, 12)
        eyes, sources = random_inputs(rng, kinds, agents=3)
        shuffled = [edges[i] for i in rng.permutation(len(edges))]
        one = evaluate(Network.from_edges(kinds, edges), eyes, sources)
        two = evaluate(Network.from_edges(kinds, shuffled), eyes, sources)
        assert np.array_equal(one, two)


def test_an_agent_gets_the_same_rates_alone_or_in_a_crowd():
    rng = np.random.default_rng(6)
    for _ in range(30):
        kinds, edges = random_dag(rng, 14)
        net = Network.from_edges(kinds, edges)
        eyes, sources = random_inputs(rng, kinds, agents=7)
        crowd = evaluate(net, eyes, sources)
        for row in range(7):
            assert np.array_equal(crowd[row], evaluate(net, eyes[row : row + 1], sources)[0])


def test_a_board_evaluates_like_the_network_of_its_wires():
    board = Board(offset_rect(9, 7))
    eye = board.place(EYE, (0, 1))
    half = board.place(HLV, (3, 1))
    thruster = board.place(THR, (6, 1))
    board.connect(eye.id, half.id)
    board.connect(half.id, thruster.id)
    y = evaluate(Network.from_board(board), np.array([[0.75]]))
    assert thrust_rates(Network.from_board(board), y).tolist() == [[0.375]]


# Input shapes


@pytest.mark.parametrize("eyes", [np.zeros(2), np.zeros((1, 3)), np.zeros((2, 1, 2))])
def test_eyes_must_be_one_row_per_agent_and_one_column_per_eye(eyes):
    net = Network.from_edges([EYE, EYE, THR], [(0, 2)])
    with pytest.raises(ValueError, match="eyes must have shape"):
        evaluate(net, eyes)


# Loops


def halve_ring():
    """A Sum fed by an eye and by its own output, halved: y = min(R, eye + y / 2)."""
    return Network.from_edges([EYE, SUM, HLV], [(0, 1), (1, 2), (2, 1)])


def test_a_contractive_loop_settles_on_the_solution_of_its_linear_system():
    net = halve_ring()
    assert 0.0 < contraction_factor(net) < 1.0
    y = evaluate(net, np.array([[0.375]]))[0]
    assert y[1] == pytest.approx(0.75, abs=1e-9) and y[2] == pytest.approx(0.375, abs=1e-9)


def test_a_contractive_loop_saturates_instead_of_running_away():
    y = evaluate(halve_ring(), np.array([[RATE_MAX]]))[0]
    assert y[1] == RATE_MAX and y[2] == RATE_MAX / 2


def test_a_loop_of_gain_one_is_refused():
    net = Network.from_edges([EYE, SUM, DBL, HLV], [(0, 1), (1, 2), (2, 3), (3, 1)])
    assert contraction_factor(net) is None
    with pytest.raises(AlgebraicLoopError):
        evaluate(net, np.array([[1.0]]))


def test_a_loop_of_gain_above_one_is_refused_even_at_zero_input():
    net = Network.from_edges([DBL, DBL], [(0, 1), (1, 0)])
    with pytest.raises(AlgebraicLoopError):
        evaluate(net, np.zeros((1, 0)))


def test_a_loop_through_a_difference_is_refused_when_its_gain_is_one_or_more():
    # y = |eye - z| with z = 2 y: two solutions, z = 2/3 eye and z = 2 eye.
    net = Network.from_edges([EYE, DIF, DBL], [(0, 1), (2, 1), (1, 2)])
    assert contraction_factor(net) is None
    with pytest.raises(AlgebraicLoopError):
        evaluate(net, np.array([[1.0]]))


def test_a_difference_loop_below_gain_one_is_unique_and_found():
    # y = |eye - y / 2|: y = 2/3 eye while y < 2 eye, the only solution.
    net = Network.from_edges([EYE, DIF, HLV], [(0, 1), (2, 1), (1, 2)])
    y = evaluate(net, np.array([[0.375]]))[0]
    assert y[1] == pytest.approx(0.25, abs=1e-9)


def test_the_contraction_factor_bounds_how_far_a_sweep_shrinks_distances():
    rng = np.random.default_rng(7)
    net = Network.from_edges(
        [EYE, SUM, HLV, DIF, HLV, HLV],
        [(0, 1), (1, 2), (2, 1), (2, 3), (3, 4), (4, 5), (5, 3)],
    )
    q = contraction_factor(net)
    assert q is not None and q < 1.0
    w = abs_coupling(net)
    v = np.linalg.solve(np.eye(net.n) - w, np.ones(net.n))
    given = np.zeros((1, net.n))
    for _ in range(200):
        x = rng.uniform(0.0, RATE_MAX, size=(1, net.n))
        y = rng.uniform(0.0, RATE_MAX, size=(1, net.n))
        x[:, 0] = y[:, 0] = 0.0  # the eye is given, not part of the map
        before = np.max(np.abs(x - y) / v)
        after = np.max(np.abs(sweep(net, x, given) - sweep(net, y, given)) / v)
        assert after <= q * before + 1e-12
