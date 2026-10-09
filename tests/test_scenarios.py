"""The example boards of the developer view build and do what their titles say."""

import numpy as np
import pytest

from nektoids.graph.analysis import Status, loop_report
from nektoids.graph.dynamics import RATE_MAX, initial_state, step
from nektoids.graph.network import Network, topological_order
from nektoids.levels.scenarios import scenarios

ALL = scenarios()
BY_TITLE = {s.title: s for s in ALL}
DT = 1 / 120
SETTLE = 1500  # ticks: 12 s, long after every lag here has settled


def run(title, eyes, ticks=SETTLE, sources=None, start=None):
    """The rates (1, n) of the board `title` after `ticks` ticks of constant sensors (one agent),
    white: the state's white channel, its red checked at 0 (D-502); `start` white too."""
    scenario = BY_TITLE[title]
    net = Network.from_board(scenario.board)
    if sources is None:
        sources = np.full(len(net.sources), scenario.source_level)
    eyes = np.array([eyes], dtype=float).reshape(1, -1)
    y = initial_state(net) if start is None else np.stack([start, np.zeros_like(start)], axis=-1)
    for _ in range(ticks):
        y = step(net, y, eyes, DT, sources)
    assert not y[..., 1].any()
    return y[..., 0]


def rates(title, *eyes, sources=None):
    return run(title, eyes, sources=sources)[0].tolist()


def test_titles_are_unique_and_every_board_compiles():
    assert len(BY_TITLE) == len(ALL) == 11
    for scenario in ALL:
        assert Network.from_board(scenario.board).n > 0


def test_boards_are_built_the_same_way_every_time():
    again = scenarios()
    for one, two in zip(ALL, again, strict=True):
        assert one.board.wires == two.board.wires
        assert one.board.nodes == two.board.nodes
        assert one.source_level == two.source_level


@pytest.mark.parametrize("scenario", ALL, ids=lambda s: s.title)
def test_every_board_runs_and_stays_inside_the_cap(scenario):
    net = Network.from_board(scenario.board)
    sources = np.full(len(net.sources), scenario.source_level)
    y = initial_state(net)
    for _ in range(600):
        y = step(net, y, np.full((1, len(net.eyes)), RATE_MAX / 2), DT, sources)
        assert 0.0 <= y.min() and y.max() <= RATE_MAX


def test_only_the_loop_boards_have_loops():
    for scenario in ALL:
        net = Network.from_board(scenario.board)
        assert (topological_order(net) is None) == scenario.title.startswith(("Loop", "Toggle"))


def test_the_board_draws_the_closing_wire_again_the_same_way():
    for scenario in scenarios():  # fresh boards: this test takes a wire off
        if not scenario.title.startswith(("Loop", "Toggle")):
            continue
        board = scenario.board
        closing = board.wires[-1]
        board.remove_wire(closing)
        assert board.connect(closing.source, closing.target) == closing  # D-428


# Without loops


def test_braitenberg_wiring_straight_and_crossed():
    straight = rates("Braitenberg, uncrossed", 0.75, 0.25)
    crossed = rates("Braitenberg, crossed", 0.75, 0.25)
    assert straight[2:] == pytest.approx([0.75, 0.25])
    assert crossed[2:] == pytest.approx([0.25, 0.75])


def test_a_halver_on_one_side_halves_that_thruster_only():
    y = rates("Halve on one side: asymmetry", 0.75, 0.75)
    assert y == pytest.approx([0.75, 0.375, 0.75, 0.375, 0.75])


def test_a_fork_gives_each_thruster_a_third():
    assert rates("A fork splits the rate", 0.75)[1:] == pytest.approx([0.25, 0.25, 0.25])


def test_three_doublers_saturate_above_one_eighth_of_the_cap():
    assert rates("Doublers saturate at R", 0.125)[-1] == pytest.approx(1.0)  # 0.125 * 2**3
    assert rates("Doublers saturate at R", 0.0625)[-1] == pytest.approx(0.5)
    assert rates("Doublers saturate at R", 0.75)[-1] == pytest.approx(RATE_MAX)


def test_a_source_and_a_difference_give_the_gap_to_the_source_rate():
    title = "Source and Difference: |x - c|"
    xs = (0.0, 0.25, 0.5, 0.75, 1.0)
    # The board starts its source at 0.5: the gap is a V.
    assert [rates(title, x)[3] for x in xs] == pytest.approx([0.5, 0.25, 0.0, 0.25, 0.5])
    # A source at the cap makes it the complement of the eye.
    full = [rates(title, x, sources=[1.0])[3] for x in xs]
    assert full == pytest.approx([1.0, 0.75, 0.5, 0.25, 0.0])


# Loops


def test_the_settling_loop_matches_its_hand_solution():
    # y_sum = eye + y_half / 2 and y_half = y_sum / 2, so y_sum = 4/3 eye and the thruster
    # gets y_half / 2.
    title = "Loop that settles (gain 1/4)"
    y = rates(title, 0.375)
    assert y[1] == pytest.approx(0.5, abs=1e-9)
    assert y[3] == pytest.approx(0.125, abs=1e-9)
    report = loop_report(Network.from_board(BY_TITLE[title].board))
    assert report.status is Status.CONTRACTIVE and report.components[0].rho == pytest.approx(0.5)


def test_the_loop_of_gain_one_holds_what_an_eye_pulse_left_in_it():
    title = "Loop of gain 1: holds a value"
    y = run(title, [0.5], ticks=600)
    y = run(title, [0.0], ticks=300, start=y)
    held = y[0, 1]
    assert held > 0.0
    y = run(title, [0.0], ticks=900, start=y)
    assert y[0, 1] == pytest.approx(held, abs=1e-9)
    report = loop_report(Network.from_board(BY_TITLE[title].board))
    assert report.status is Status.NONCONTRACTIVE and report.components[0].rho == pytest.approx(1.0)


def test_the_loop_through_a_difference_settles_on_a_third_of_the_eye():
    # gap = |eye - y_second / 2| with y_second = 4 gap: gap = eye / 3, thruster = 2 gap.
    y = rates("Loop through a Difference (gain 2)", 0.375)
    assert y[1] == pytest.approx(0.125, abs=1e-9)
    assert y[4] == pytest.approx(0.25, abs=1e-9)


def test_the_toggle_keeps_its_winner_and_a_stronger_source_flips_it():
    title = "Toggle: two stages inhibiting each other"
    thrusters = [4, 9]  # half of each stage's last doubler
    y = run(title, [], ticks=400)  # both sources at 0.5: the unstable middle
    assert y[0, thrusters[0]] == y[0, thrusters[1]]
    y = run(title, [], ticks=300, sources=[0.5, 0.45], start=y)
    assert y[0, thrusters[0]] > 4 * y[0, thrusters[1]]  # stage a won, b is held down by 0.05
    y = run(title, [], ticks=600, start=y)  # both back to 0.5
    assert y[0, thrusters[0]] > 10 * y[0, thrusters[1]]  # and it stays so
    y = run(title, [], ticks=300, sources=[0.5, 1.0], start=y)  # the loser's source up ...
    y = run(title, [], ticks=600, start=y)
    assert y[0, thrusters[1]] > 10 * y[0, thrusters[0]]  # ... flips it


def test_a_loop_runs_bit_identical_twice():  # invariant 1
    title = "Toggle: two stages inhibiting each other"
    sources = [0.5, 0.45]
    assert np.array_equal(run(title, [], sources=sources), run(title, [], sources=sources))
