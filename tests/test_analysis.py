import numpy as np
import pytest

from nektoids.graph.analysis import Status, active_branch, loop_report, problems
from nektoids.graph.board import Kind
from nektoids.graph.evaluate import RATE_MAX, AlgebraicLoopError, evaluate, sweep
from nektoids.graph.network import Network

EYE, SRC, DBL, HLV, SUM, DIF, THR = (
    Kind.EYE,
    Kind.SOURCE,
    Kind.DOUBLE,
    Kind.HALVE,
    Kind.SUM,
    Kind.DIFFERENCE,
    Kind.THRUSTER,
)


def halve_ring():
    """y = min(R, eye + y / 2) through a Sum and a Halve."""
    return Network.from_edges([EYE, SUM, HLV], [(0, 1), (1, 2), (2, 1)])


# Loop report


def test_a_dag_has_no_loop_to_report():
    net = Network.from_edges([EYE, DBL, THR], [(0, 1), (1, 2)])
    report = loop_report(net)
    assert report.status is Status.DAG and report.components == () and report.factor == 0.0


def test_a_contractive_loop_reports_its_gain_and_factor():
    report = loop_report(halve_ring())
    assert report.status is Status.CONTRACTIVE
    (part,) = report.components
    assert part.members == (1, 2)
    assert part.rho == pytest.approx(np.sqrt(0.5))  # a two-node cycle with weights 1 and 1/2
    assert part.determinants == pytest.approx((0.5,))  # 1 - 1 * 1/2
    assert part.coherent is True
    assert report.factor == pytest.approx(0.75)  # v = (1, 4, 3), q = 1 - 1/4


def test_a_loop_of_gain_one_is_noncontractive_and_singular():
    net = Network.from_edges([EYE, SUM, DBL, HLV], [(0, 1), (1, 2), (2, 3), (3, 1)])
    report = loop_report(net)
    assert report.status is Status.NONCONTRACTIVE and report.factor is None
    (part,) = report.components
    assert part.rho == pytest.approx(1.0)
    assert part.coherent is False


def test_a_difference_loop_with_two_solutions_has_mixed_determinants():
    # y = |eye - z|, z = 2 y has z = 2/3 eye and z = 2 eye: the two branches disagree in sign.
    net = Network.from_edges([EYE, DIF, DBL], [(0, 1), (2, 1), (1, 2)])
    report = loop_report(net)
    assert report.status is Status.NONCONTRACTIVE
    assert report.components[0].determinants == pytest.approx((3.0, -1.0))
    assert report.components[0].coherent is False


def test_a_difference_loop_of_gain_below_one_is_regular_on_both_branches():
    net = Network.from_edges([EYE, DIF, HLV], [(0, 1), (2, 1), (1, 2)])
    report = loop_report(net)
    assert report.status is Status.CONTRACTIVE
    assert report.components[0].determinants == pytest.approx((1.5, 0.5))


def cancelling_loop():
    """A Difference of two equal paths back from its own output: its input is always 0."""
    return Network.from_edges([DIF, DBL, DBL], [(0, 1), (0, 2), (1, 0), (2, 0)])


def test_cancelling_paths_are_refused_by_the_bound_although_the_solution_is_unique():
    net = cancelling_loop()
    report = loop_report(net)
    assert report.status is Status.NONCONTRACTIVE
    assert report.components[0].rho == pytest.approx(np.sqrt(2.0))
    assert report.components[0].determinants == pytest.approx((1.0, 1.0))
    assert report.components[0].coherent is True
    with pytest.raises(AlgebraicLoopError):
        evaluate(net, np.zeros((1, 0)))
    # What the bound cannot see: from any start the iteration falls onto the rest state.
    y, given = np.array([[1.0, 1.0, 1.0]]), np.zeros((1, 3))
    for _ in range(3):
        y = sweep(net, y, given)
    assert y.tolist() == [[0.0, 0.0, 0.0]]


def test_too_many_differences_in_one_loop_are_left_unchecked():
    n = 12  # a ring of Differences, each with one outside input: 2**12 patterns is too many
    kinds = [EYE] * n + [DIF] * n
    edges = [(i, n + i) for i in range(n)] + [(n + i, n + (i + 1) % n) for i in range(n)]
    report = loop_report(Network.from_edges(kinds, edges))
    assert report.components[0].determinants is None
    assert report.components[0].coherent is None


# The affine branch


def test_the_active_branch_reproduces_the_rates_it_was_taken_at():
    net = halve_ring()
    y = evaluate(net, np.array([[0.375]]))[0]
    branch = active_branch(net, y)
    assert branch.coef[1].tolist() == [1.0, 0.0, 1.0]  # the eye and the halver, in full
    assert branch.const.tolist() == [0.0, 0.0, 0.0]
    np.testing.assert_allclose(branch.solution(net, y), y, atol=1e-9)


def test_the_active_branch_follows_the_sign_of_a_difference_and_the_cap():
    net = Network.from_edges([EYE, DIF, HLV], [(0, 1), (2, 1), (1, 2)])
    y = evaluate(net, np.array([[0.375]]))[0]  # y = 0.25 and z = 0.125: the eye is larger
    np.testing.assert_allclose(active_branch(net, y).solution(net, y), y, atol=1e-9)
    assert active_branch(net, y).coef[1, 2] == -1.0  # a - b with the halver second
    capped = active_branch(halve_ring(), np.array([RATE_MAX, RATE_MAX, RATE_MAX / 2]))
    assert capped.const[1] == RATE_MAX and not capped.coef[1].any()


# Problems


def test_problems_name_what_is_idle_or_unfed():
    net = Network.from_edges(
        [EYE, SUM, SRC, THR, DBL, THR],
        [(0, 1), (1, 3), (2, 3)],  # the doubler and the second thruster are not connected
    )
    assert problems(net) == (
        "P1 has one input and passes it through",
        "D4 is fed by no sensor: its rate is always 0",
        "D4 sends its rate nowhere",
        "T5 is fed by no sensor: its rate is always 0",
    )


def test_a_healthy_graph_has_no_problems_and_a_loop_without_sensor_is_unfed():
    assert problems(Network.from_edges([EYE, EYE, DIF, THR], [(0, 2), (1, 2), (2, 3)])) == ()
    net = Network.from_edges([DBL, HLV], [(0, 1), (1, 0)])
    assert problems(net) == (
        "D0 is fed by no sensor: its rate is always 0",
        "H1 is fed by no sensor: its rate is always 0",
    )
