import hashlib

import numpy as np
import pytest

from nektoids.graph import dynamics
from nektoids.graph.board import Board, Kind
from nektoids.graph.dynamics import RATE_MAX, SOURCE_RATE, TAU, max_dt, wire_flux
from nektoids.graph.hexgrid import offset_rect
from nektoids.graph.kinds import Hue
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
DT = 1 / 120  # the tick of the simulation [s]
H = DT / TAU  # 1/2: the step of the lag


W, R = Hue.WHITE.channel, Hue.RED.channel


def both(y):
    """White rates (N, n) as the state holds them, (N, n, C): in the white channel, red at 0."""
    y = np.asarray(y, dtype=float)
    return np.stack([y, np.zeros_like(y)], axis=-1)


def one(y):
    """The white rates (N, n) of a state (N, n, C), its red checked at 0 (D-502)."""
    assert not y[..., R].any()
    return y[..., W]


# The tests below run the dynamics in white, as every level is today (D-502): on rates (N, n),
# through the state's white channel, every step checked to leave red at 0.


def initial_state(net, agents=1):
    return one(dynamics.initial_state(net, agents))


def step(net, y, eyes, dt, sources=None):
    return one(dynamics.step(net, both(y), eyes, dt, sources))


def given_rates(net, eyes, sources=None):
    return one(dynamics.given_rates(net, eyes, sources))


def thrust_rates(net, y):
    return one(dynamics.thrust_rates(net, both(y)))


def eyes_row(*values):
    return np.array([values], dtype=float).reshape(1, -1)


def relax(net, eyes, sources=None, ticks=1500, dt=DT, start=None):
    """The state after `ticks` ticks of constant sensors, from rest unless `start` is given."""
    y = initial_state(net, len(eyes)) if start is None else start
    for _ in range(ticks):
        y = step(net, y, eyes, dt, sources)
    return y


def settled(kinds, edges, *eyes, sources=None):
    """Rates of one agent, as a list, once everything has relaxed."""
    return relax(Network.from_edges(kinds, edges), eyes_row(*eyes), sources)[0].tolist()


def reference(kinds, edges, eyes, sources):
    """The value each node relaxes to in a DAG, written recursively and independently."""
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
                total = into[0] - into[1] if kind is DIF and len(into) == 2 else sum(into)
                memo[i] = min(RATE_MAX, GAINS[kind] * abs(total))
        return memo[i]

    return [rate(i) for i in range(n)]


def random_graph(rng, n, loops=False):
    """Random kinds and wires that a board could hold; with `loops`, wires may run backwards."""
    kinds = [KINDS[rng.integers(len(KINDS))] for _ in range(n)]
    edges = []
    for target, kind in enumerate(kinds):
        if not kind.receives:
            continue
        pool = range(n) if loops else range(target)
        emitters = [i for i in pool if kinds[i].emits and i != target]
        wanted = rng.integers(0, (kind.max_inputs or 3) + 1)
        for source in rng.choice(emitters, size=min(wanted, len(emitters)), replace=False):
            edges.append((int(source), target))
    perm = rng.permutation(n)  # the node numbers carry no order
    shuffled = [None] * n
    for old, new in enumerate(perm):
        shuffled[new] = kinds[old]
    return shuffled, [(int(perm[a]), int(perm[b])) for a, b in edges]


def random_inputs(rng, kinds, agents=1):
    eyes = rng.uniform(-3.0, 2.0 * RATE_MAX, size=(agents, kinds.count(EYE)))
    sources = rng.uniform(-1.0, 2.0 * RATE_MAX, size=kinds.count(SRC))
    return eyes, sources


# One node: what it relaxes to


def test_operators_apply_their_gain_to_the_rate_they_receive():
    assert settled([EYE, DBL], [(0, 1)], 0.25)[1] == pytest.approx(0.5)
    assert settled([EYE, HLV], [(0, 1)], 0.25)[1] == pytest.approx(0.125)
    assert settled([EYE, SUM], [(0, 1)], 0.25)[1] == pytest.approx(0.25)  # one input passes
    assert settled([EYE, DIF], [(0, 1)], 0.25)[1] == pytest.approx(0.25)
    assert settled([EYE, THR], [(0, 1)], 0.25)[1] == pytest.approx(0.25)


def test_sum_adds_and_difference_takes_the_gap_in_either_order():
    assert settled([EYE, EYE, SUM], [(0, 2), (1, 2)], 0.375, 0.125)[2] == pytest.approx(0.5)
    assert settled([EYE, EYE, DIF], [(0, 2), (1, 2)], 0.375, 0.125)[2] == pytest.approx(0.25)
    assert settled([EYE, EYE, DIF], [(0, 2), (1, 2)], 0.125, 0.375)[2] == pytest.approx(0.25)


def test_several_wires_into_a_doubler_or_a_thruster_are_added_first():
    assert settled([EYE, EYE, DBL], [(0, 2), (1, 2)], 0.125, 0.0625)[2] == pytest.approx(0.375)
    assert settled([EYE, EYE, THR], [(0, 2), (1, 2)], 0.125, 0.0625)[2] == pytest.approx(0.1875)


def test_a_node_with_nothing_wired_in_stays_at_zero():
    assert settled([SUM, DBL, THR], []) == [0.0, 0.0, 0.0]


def test_a_source_emits_its_rate_unless_the_developer_overrides_it():
    assert settled([SRC, THR], [(0, 1)])[1] == pytest.approx(SOURCE_RATE)
    assert settled([SRC, THR], [(0, 1)], sources=[0.375])[1] == pytest.approx(0.375)


def test_eyes_beyond_their_range_are_clipped():
    assert settled([EYE, THR], [(0, 1)], 100.0)[1] == pytest.approx(RATE_MAX)
    assert settled([EYE, THR], [(0, 1)], -5.0)[1] == 0.0


def test_the_empty_network_has_no_rates():
    net = Network.from_edges([], [])
    assert step(net, initial_state(net, 3), np.zeros((3, 0)), DT).shape == (3, 0)


# Time: one lag, two lags


def test_one_lag_follows_the_exponential_step_by_step():
    net = Network.from_edges([EYE, THR], [(0, 1)])
    y, a = initial_state(net), 1.0 - H
    for k in range(1, 30):
        y = step(net, y, eyes_row(0.8), DT)
        assert y[0, 1] == pytest.approx(0.8 * (1.0 - a**k), abs=1e-12)


def test_two_lags_in_series_follow_their_recurrence():
    net = Network.from_edges([EYE, SUM, THR], [(0, 1), (1, 2)])
    y, a, e = initial_state(net), 1.0 - H, 0.8
    for k in range(1, 30):
        y = step(net, y, eyes_row(e), DT)
        assert y[0, 1] == pytest.approx(e * (1.0 - a**k), abs=1e-12)
        assert y[0, 2] == pytest.approx(e * (1.0 - a**k - k * H * a ** (k - 1)), abs=1e-12)


def test_halving_the_step_halves_the_error_against_the_exact_exponential():
    net = Network.from_edges([EYE, THR], [(0, 1)])
    exact = 0.8 * (1.0 - np.exp(-0.05 / TAU))
    errors = []
    for dt in (TAU / 4, TAU / 8):
        y = relax(net, eyes_row(0.8), ticks=round(0.05 / dt), dt=dt)
        errors.append(abs(y[0, 1] - exact))
    assert 1.6 < errors[0] / errors[1] < 2.4


def test_the_step_is_refused_when_it_is_longer_than_its_laws_allow():
    net = Network.from_edges([EYE, THR], [(0, 1)])
    y = initial_state(net)
    assert max_dt(net) == TAU  # a relaxing law takes dt <= tau (D-202)
    for dt in (0.0, -DT, TAU * 1.01):
        with pytest.raises(ValueError, match="what the laws allow"):
            step(net, y, eyes_row(0.5), dt)


def test_a_step_of_tau_takes_each_node_to_where_its_inputs_ask():
    net = Network.from_edges([EYE, DBL, HLV], [(0, 1), (1, 2)])
    y = initial_state(net)
    y = step(net, y, eyes_row(0.25), TAU)
    assert y[0].tolist() == [0.25, 0.5, 0.0]  # the doubler sees this tick's eye
    y = step(net, y, eyes_row(0.25), TAU)
    assert y[0].tolist() == [0.25, 0.5, 0.25]


def test_the_state_has_one_row_per_agent_and_a_wrong_shape_is_an_error():
    net = Network.from_edges([EYE, THR], [(0, 1)])
    with pytest.raises(ValueError, match="y must have shape"):
        step(net, np.zeros((2, 2)), eyes_row(0.5), DT)


@pytest.mark.parametrize("eyes", [np.zeros(2), np.zeros((1, 3)), np.zeros((2, 1, 2))])
def test_eyes_must_be_one_row_per_agent_and_one_column_per_eye(eyes):
    net = Network.from_edges([EYE, EYE, THR], [(0, 2)])
    with pytest.raises(ValueError, match="eyes must have shape"):
        given_rates(net, eyes)


# Split and cap


def test_a_fork_shares_the_rate_between_its_wires():
    assert settled([EYE, THR, THR], [(0, 1), (0, 2)], 0.75) == pytest.approx([0.75, 0.375, 0.375])
    three = settled([EYE, THR, THR, THR], [(0, 1), (0, 2), (0, 3)], 0.75)
    assert three[1:] == pytest.approx([0.25, 0.25, 0.25])


def test_the_flux_leaving_a_node_adds_up_to_its_rate():
    rng = np.random.default_rng(1)
    for _ in range(50):
        kinds, edges = random_graph(rng, 12)
        net = Network.from_edges(kinds, edges)
        eyes, sources = random_inputs(rng, kinds)
        y = relax(net, eyes, sources, ticks=300)
        flux = wire_flux(net, y)
        for i in range(net.n):
            if net.outdeg[i]:
                leaving = flux[:, net.edges[:, 0] == i].sum(axis=1)
                assert leaving == pytest.approx(y[:, i], rel=1e-12, abs=1e-12)


def test_doublers_in_a_row_saturate_at_the_cap():
    kinds = [EYE] + [DBL] * 5
    edges = [(i, i + 1) for i in range(5)]
    for x in (0.0, 0.01, 0.03, 0.125, 0.5):
        assert settled(kinds, edges, x)[-1] == pytest.approx(min(RATE_MAX, 32 * x), abs=1e-9)


def test_the_order_of_a_sum_and_a_gain_matters_at_the_cap():
    after = settled([EYE, EYE, SUM, HLV], [(0, 2), (1, 2), (2, 3)], 1.0, 1.0)[3]
    before = settled([EYE, EYE, HLV, HLV, SUM], [(0, 2), (1, 3), (2, 4), (3, 4)], 1.0, 1.0)[4]
    assert (after, before) == pytest.approx((0.5, 1.0))
    after = settled([EYE, EYE, DIF, DBL], [(0, 2), (1, 2), (2, 3)], 1.0, 0.75)[3]
    before = settled([EYE, EYE, DBL, DBL, DIF], [(0, 2), (1, 3), (2, 4), (3, 4)], 1.0, 0.75)[4]
    assert (after, before) == pytest.approx((0.5, 0.0))


# Bounds, for every graph, loops included


@pytest.mark.parametrize("dt", [TAU / 12, TAU / 2, TAU])
def test_every_rate_stays_between_zero_and_the_cap_at_every_tick(dt):
    rng = np.random.default_rng(2)
    for _ in range(60):
        kinds, edges = random_graph(rng, 12, loops=True)
        net = Network.from_edges(kinds, edges)
        y = initial_state(net, 3)
        for _ in range(80):
            eyes = rng.uniform(-2.0, 3.0, size=(3, kinds.count(EYE)))
            sources = rng.uniform(-1.0, 2.0, size=kinds.count(SRC))
            y = step(net, y, eyes, dt, sources)
            assert y.min() >= 0.0 and y.max() <= RATE_MAX


# Relaxing to the value the equations give, for DAGs


def test_random_dags_relax_to_what_an_independent_evaluator_gives():
    rng = np.random.default_rng(3)
    for _ in range(120):
        kinds, edges = random_graph(rng, int(rng.integers(1, 14)))
        net = Network.from_edges(kinds, edges)
        eyes, sources = random_inputs(rng, kinds)
        y = relax(net, eyes, sources, ticks=300)  # 13 levels at h = 1/2 are settled long before
        expected = reference(kinds, edges, eyes[0], sources)
        np.testing.assert_allclose(y[0], expected, rtol=1e-9, atol=1e-12)


def test_each_channel_runs_as_a_white_run_of_its_own_sensors_bit_for_bit():
    rng = np.random.default_rng(11)  # D-502: no law of these mixes white and red
    for _ in range(60):
        kinds, edges = random_graph(rng, int(rng.integers(1, 14)), loops=True)
        kinds = [Kind.TANK if k is DBL and rng.random() < 0.3 else k for k in kinds]
        net = Network.from_edges(kinds, edges)
        white, red = (rng.uniform(0.0, RATE_MAX, size=(1, net.n)) for _ in range(2))
        given = np.stack([white, red], axis=-1)  # each sensor's rate in each channel
        y = dynamics.initial_state(net)
        alone = {W: initial_state(net), R: initial_state(net)}
        for _ in range(200):
            y = dynamics.step_given(net, y, given, DT)
            for c, rates in ((W, white), (R, red)):
                alone[c] = one(dynamics.step_given(net, both(alone[c]), both(rates), DT))
        assert np.array_equal(y[..., W], alone[W]) and np.array_equal(y[..., R], alone[R])


def test_a_red_source_leaves_white_dark_and_a_red_eye_sees_no_white_light():
    kinds = [SRC, SUM, Kind.TANK, DIF, DBL, THR, EYE]
    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 1), (4, 5)]
    hues = [Hue.RED, *[Hue.WHITE] * 4, Hue.RED, Hue.RED]
    net = Network.from_edges(kinds, edges, hues=hues)
    y = dynamics.initial_state(net)
    for _ in range(600):
        y = dynamics.step(net, y, eyes_row(0.9), DT)  # white light on the red eye
    assert y[0, :, R].max() > 0.1 and not y[0, :, W].any()
    assert y[0, 6].tolist() == [0.0, 0.0]  # the red eye reads nothing
    assert dynamics.painted(net, y, net.thrusters)[0, 0] == y[0, 5, R]  # it pushes with red


# Braitenberg


def test_crossed_and_uncrossed_wiring_swap_the_thrusters():
    eyes = [EYE, EYE, THR, THR]
    uncrossed = settled(eyes, [(0, 2), (1, 3)], 0.75, 0.25)
    crossed = settled(eyes, [(0, 3), (1, 2)], 0.75, 0.25)
    assert uncrossed[2:] == pytest.approx([0.75, 0.25]) and crossed[2:] == pytest.approx(
        [0.25, 0.75]
    )


def test_a_difference_does_not_care_which_input_is_which_bit_for_bit():
    net = Network.from_edges([EYE, EYE, DIF], [(0, 2), (1, 2)])
    rng = np.random.default_rng(8)
    for a, b in rng.uniform(0.0, RATE_MAX, size=(50, 2)):
        one, two = initial_state(net), initial_state(net)
        for _ in range(5):
            one = step(net, one, eyes_row(a, b), DT)
            two = step(net, two, eyes_row(b, a), DT)
        assert one[0, 2] == two[0, 2]


def test_a_mirrored_board_gives_mirrored_thrusters_bit_for_bit():
    kinds = [EYE, EYE, HLV, HLV, THR, THR]
    net = Network.from_edges(kinds, [(0, 2), (1, 3), (2, 4), (3, 5)])
    a = relax(net, eyes_row(0.53, 0.21), ticks=40)[0]
    b = relax(net, eyes_row(0.21, 0.53), ticks=40)[0]
    assert (a[4], a[5]) == (b[5], b[4])


# Determinism


def trajectory_hash(net, eyes, ticks=60):
    y, digest = initial_state(net, len(eyes)), hashlib.sha256()
    for _ in range(ticks):
        y = step(net, y, eyes, DT)
        digest.update(y.tobytes())
    return digest.hexdigest()


def test_two_runs_give_the_same_bytes_loops_included():
    rng = np.random.default_rng(4)
    kinds, edges = random_graph(rng, 15, loops=True)
    net = Network.from_edges(kinds, edges)
    eyes, _ = random_inputs(rng, kinds, agents=9)
    assert trajectory_hash(net, eyes) == trajectory_hash(net, eyes)


def test_the_order_wires_were_drawn_in_changes_nothing():
    rng = np.random.default_rng(5)
    for _ in range(40):
        kinds, edges = random_graph(rng, 12, loops=True)
        eyes, _ = random_inputs(rng, kinds, agents=3)
        shuffled = [edges[i] for i in rng.permutation(len(edges))]
        one = trajectory_hash(Network.from_edges(kinds, edges), eyes)
        two = trajectory_hash(Network.from_edges(kinds, shuffled), eyes)
        assert one == two


def test_an_agent_follows_the_same_path_alone_or_in_a_crowd():
    rng = np.random.default_rng(6)
    for _ in range(20):
        kinds, edges = random_graph(rng, 14, loops=True)
        net = Network.from_edges(kinds, edges)
        eyes, _ = random_inputs(rng, kinds, agents=7)
        crowd = relax(net, eyes, ticks=80)
        for row in range(7):
            alone = relax(net, eyes[row : row + 1], ticks=80)
            assert np.array_equal(crowd[row], alone[0])


def test_a_board_steps_like_the_network_of_its_wires():
    board = Board(offset_rect(9, 7))
    eye = board.place(EYE, (0, 1))
    half = board.place(HLV, (3, 1))
    thruster = board.place(THR, (6, 1))
    board.connect(eye.id, half.id)
    board.connect(half.id, thruster.id)
    net = Network.from_board(board)
    y = relax(net, eyes_row(0.75))
    assert thrust_rates(net, y)[0].tolist() == pytest.approx([0.375])


# Loops: the lag makes every one of them a trajectory


def halve_ring():
    """A Sum fed by an eye and by its own output, halved: y = min(R, eye + y / 2)."""
    return Network.from_edges([EYE, SUM, HLV], [(0, 1), (1, 2), (2, 1)])


def test_a_contractive_loop_settles_on_one_value_from_any_start():
    net = halve_ring()
    q = contraction_factor(net)
    assert q is not None and 0.0 < q < 1.0
    rng = np.random.default_rng(9)
    for _ in range(5):
        start = rng.uniform(0.0, RATE_MAX, size=(1, net.n))
        y = relax(net, eyes_row(0.375), start=start)[0]
        assert y[1] == pytest.approx(0.75, abs=1e-9) and y[2] == pytest.approx(0.375, abs=1e-9)


def test_a_contractive_loop_saturates_instead_of_running_away():
    y = relax(halve_ring(), eyes_row(RATE_MAX))[0]
    assert y[1] == pytest.approx(RATE_MAX) and y[2] == pytest.approx(RATE_MAX / 2)


def test_an_euler_step_shrinks_distances_as_the_contraction_factor_says():
    rng = np.random.default_rng(7)
    net = Network.from_edges(
        [EYE, SUM, HLV, DIF, HLV, HLV],
        [(0, 1), (1, 2), (2, 1), (2, 3), (3, 4), (4, 5), (5, 3)],
    )
    q = contraction_factor(net)
    assert q is not None and q < 1.0
    v = np.linalg.solve(np.eye(net.n) - abs_coupling(net), np.ones(net.n))
    eyes = eyes_row(0.5)
    for _ in range(200):
        x = rng.uniform(0.0, RATE_MAX, size=(1, net.n))
        z = rng.uniform(0.0, RATE_MAX, size=(1, net.n))
        x[:, 0] = z[:, 0] = 0.5  # the eye is given, not part of the map
        before = np.max(np.abs(x - z) / v)
        after = np.max(np.abs(step(net, x, eyes, DT) - step(net, z, eyes, DT)) / v)
        assert after <= (1.0 - H * (1.0 - q)) * before + 1e-12


def toggle():
    """Two stages that inhibit each other: y = min(1, 4 |source - other / 2|) through a fork."""
    kinds = [SRC, DIF, DBL, DBL, SRC, DIF, DBL, DBL, THR, THR]
    edges = [(0, 1), (1, 2), (2, 3), (4, 5), (5, 6), (6, 7), (3, 5), (7, 1), (3, 8), (7, 9)]
    return Network.from_edges(kinds, edges)


def test_a_toggle_keeps_the_stage_a_nudge_made_the_winner():
    net, none = toggle(), np.zeros((1, 0))
    y = relax(net, none, [0.5, 0.5], ticks=300)
    assert y[0, 3] == y[0, 7] and y[0, 3] == pytest.approx(2 / 3, abs=1e-2)  # the saddle
    y = relax(net, none, [0.5, 0.45], ticks=300, start=y)
    assert y[0, 3] == pytest.approx(1.0) and y[0, 7] < 0.2  # stage a won
    y = relax(net, none, [0.5, 0.5], ticks=600, start=y)
    assert y[0, 3] == pytest.approx(1.0) and y[0, 7] < 0.05  # the nudge is gone, the state stays
    y = relax(net, none, [0.5, 1.0], ticks=300, start=y)  # a stronger source for the loser ...
    y = relax(net, none, [0.5, 0.5], ticks=600, start=y)
    assert y[0, 7] == pytest.approx(1.0) and y[0, 3] < 0.05  # ... flips it


def test_a_loop_of_gain_one_holds_what_an_eye_pulse_left_in_it():
    net = Network.from_edges([EYE, SUM, DBL, DBL, HLV], [(0, 1), (1, 2), (2, 3), (3, 4), (4, 1)])
    y = relax(net, eyes_row(0.1), ticks=240)
    y = relax(net, eyes_row(0.0), ticks=120, start=y)
    held = y[0, 1]
    assert held > 0.0
    y = relax(net, eyes_row(0.0), ticks=600, start=y)
    assert y[0, 1] == pytest.approx(held, abs=1e-9)  # nothing drives it, nothing drains it


def test_a_tank_lags_by_four_seconds_and_on_a_loop_holds_its_level():
    tank = Network.from_edges([EYE, Kind.TANK], [(0, 1)])  # D-500, D-501
    y = relax(tank, eyes_row(0.8), ticks=round(4.0 / DT))
    assert y[0, 1] == pytest.approx(0.8 * (1 - np.exp(-1)), rel=2e-3)  # one lag: 63%
    # eye -> sum -> tank -> double -> (sum, thruster): the Double makes up for the fork
    net = Network.from_edges(
        [EYE, SUM, Kind.TANK, DBL, THR], [(0, 1), (1, 2), (2, 3), (3, 1), (3, 4)]
    )
    y = relax(net, eyes_row(0.5), ticks=round(2.0 / DT))
    y = relax(net, eyes_row(0.0), ticks=round(1.0 / DT), start=y)
    held = y[0, 2]
    assert held > 0.1
    y = relax(net, eyes_row(0.0), ticks=round(20.0 / DT), start=y)
    assert y[0, 2] == pytest.approx(held, rel=1e-6)  # the eye gone dark, the level stays


def ring(stages, doublers):
    """Stages of y = gain * |1 - previous|, closed on themselves; sources emit 1."""
    kinds, edges = [], []
    width = 2 + doublers
    for i in range(stages):
        base = i * width
        kinds += [SRC, DIF] + [DBL] * doublers
        edges += [(base, base + 1)] + [(base + 1 + k, base + 2 + k) for k in range(doublers)]
        edges.append((((i - 1) % stages) * width + 1 + doublers, base + 1))
    outs = [i * width + 1 + doublers for i in range(stages)]
    return Network.from_edges(kinds, edges), outs


def swing(net, outs, dt=DT, ticks=2400):
    y = relax(net, np.zeros((1, 0)), ticks=ticks, dt=dt)
    tail = []
    for _ in range(600):
        y = step(net, y, np.zeros((1, 0)), dt)
        tail.append(y[0, outs])
    tail = np.array(tail)
    return float((tail.max(axis=0) - tail.min(axis=0)).max())


def test_a_ring_of_three_inverting_stages_oscillates_only_when_its_gain_is_high_enough():
    weak, weak_outs = ring(3, 1)  # gain 2 per stage: settles
    strong, strong_outs = ring(3, 2)  # gain 4 per stage: oscillates
    assert swing(weak, weak_outs) < 1e-9
    assert swing(strong, strong_outs) > 0.3


def test_a_step_as_long_as_tau_makes_a_loop_flicker_that_settles_with_half_of_it():
    net, outs = ring(3, 1)
    assert swing(net, outs, dt=TAU / 2) < 1e-9
    assert swing(net, outs, dt=TAU) > 0.5  # y <- F(y): a tick-by-tick flip
