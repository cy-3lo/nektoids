"""The example boards of the developer view build and do what their titles say."""

import numpy as np
import pytest

from nektoids.graph.analysis import Status, loop_report
from nektoids.graph.board import Refused
from nektoids.graph.evaluate import RATE_MAX, AlgebraicLoopError, evaluate
from nektoids.graph.network import Network, topological_order
from nektoids.levels.scenarios import scenarios

ALL = scenarios()
BY_TITLE = {s.title: s for s in ALL}


def rates(title, *eyes, sources=None):
    net = Network.from_board(BY_TITLE[title].board)
    given = np.array([eyes]) if eyes else np.full((1, len(net.eyes)), RATE_MAX / 2)
    return evaluate(net, given, sources)[0].tolist()


def test_titles_are_unique_and_every_board_compiles():
    assert len(BY_TITLE) == len(ALL) == 10
    for scenario in ALL:
        assert Network.from_board(scenario.board).n > 0


def test_boards_are_built_the_same_way_every_time():
    again = scenarios()
    for one, two in zip(ALL, again, strict=True):
        assert one.board.wires == two.board.wires
        assert one.board.nodes == two.board.nodes


@pytest.mark.parametrize("scenario", ALL, ids=lambda s: s.title)
def test_a_board_is_refused_by_the_evaluator_exactly_when_it_is_marked(scenario):
    net = Network.from_board(scenario.board)
    eyes = np.full((1, len(net.eyes)), RATE_MAX / 2)
    if scenario.refused:
        with pytest.raises(AlgebraicLoopError):
            evaluate(net, eyes)
    else:
        assert evaluate(net, eyes).max() <= RATE_MAX


def test_only_the_loop_boards_have_loops_and_the_board_would_have_refused_them():
    for scenario in ALL:
        net = Network.from_board(scenario.board)
        assert (topological_order(net) is None) == scenario.title.startswith("Loop")


def test_braitenberg_wiring_straight_and_crossed():
    straight = rates("Braitenberg, uncrossed", 0.75, 0.25)
    crossed = rates("Braitenberg, crossed", 0.75, 0.25)
    assert straight[2:] == [0.75, 0.25] and crossed[2:] == [0.25, 0.75]


def test_a_halver_on_one_side_halves_that_thruster_only():
    assert rates("Halve on one side: asymmetry", 0.75, 0.75) == [0.75, 0.375, 0.75, 0.375, 0.75]


def test_a_fork_gives_each_thruster_a_third():
    assert rates("A fork splits the rate", 0.75)[1:] == pytest.approx([0.25, 0.25, 0.25])


def test_three_doublers_saturate_above_one_eighth_of_the_cap():
    assert rates("Doublers saturate at R", 0.125)[-1] == 1.0  # 0.125 * 2**3
    assert rates("Doublers saturate at R", 0.0625)[-1] == 0.5
    assert rates("Doublers saturate at R", 0.75)[-1] == RATE_MAX


def test_a_source_and_a_difference_give_the_gap_to_the_source_rate():
    title = "Source and Difference: |x - c|"
    xs = (0.0, 0.25, 0.5, 0.75, 1.0)
    # The source at its default rate 1 is the cap: the gap is the complement of the eye.
    assert [rates(title, x)[3] for x in xs] == [1.0, 0.75, 0.5, 0.25, 0.0]
    # Lower the source (a slider in the developer view) and the gap is a V.
    half = [rates(title, x, sources=[0.5])[3] for x in xs]
    assert half == [0.5, 0.25, 0.0, 0.25, 0.5]


def test_the_settling_loop_matches_its_hand_solution():
    # y_sum = eye + y_half / 2 and y_half = y_sum / 2, so y_sum = 4/3 eye and the thruster
    # gets y_half / 2.
    y = rates("Loop that settles (gain 1/4)", 0.375)
    assert y[1] == pytest.approx(0.5, abs=1e-9)
    assert y[3] == pytest.approx(0.125, abs=1e-9)
    report = loop_report(Network.from_board(BY_TITLE["Loop that settles (gain 1/4)"].board))
    assert report.status is Status.CONTRACTIVE and report.components[0].rho == pytest.approx(0.5)


def test_the_refused_loops_show_why_in_the_report():
    one = loop_report(Network.from_board(BY_TITLE["Loop of gain 1: refused"].board))
    assert one.status is Status.NONCONTRACTIVE
    assert one.components[0].rho == pytest.approx(1.0) and one.components[0].coherent is False
    two = loop_report(Network.from_board(BY_TITLE["Loop with two solutions: refused"].board))
    assert two.components[0].rho == pytest.approx(2 ** (1 / 3))
    assert two.components[0].determinants == pytest.approx((3.0, -1.0))


def test_the_editor_would_not_have_drawn_the_closing_wire():
    for scenario in scenarios():  # fresh boards: this test takes a wire off
        if not scenario.title.startswith("Loop"):
            continue
        board = scenario.board
        closing = board.wires[-1]
        board.remove_wire(closing)
        assert board.connect(closing.source, closing.target) == Refused("would close a loop")
