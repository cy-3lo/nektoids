import numpy as np
import pytest

from nektoids.graph.analysis import Status, loop_report, problems
from nektoids.graph.board import Kind
from nektoids.graph.dynamics import CHANNELS, RATE_MAX, TAU, initial_state, step
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
DT = 1 / 120


def halve_ring():
    """y = min(R, eye + y / 2) through a Sum and a Halve."""
    return Network.from_edges([EYE, SUM, HLV], [(0, 1), (1, 2), (2, 1)])


def relax(net, start, eyes, ticks=1500):
    """From amber rates `start` (1, n), the state (1, n, C) after `ticks` ticks (D-503)."""
    y = np.stack([start, np.zeros_like(start)], axis=-1)
    for _ in range(ticks):
        y = step(net, y, eyes, DT)
    return y


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
    assert report.factor == pytest.approx(0.75)  # v = (1, 4, 3), q = 1 - 1/4


def test_a_loop_of_gain_one_is_noncontractive():
    net = Network.from_edges([EYE, SUM, DBL, HLV], [(0, 1), (1, 2), (2, 3), (3, 1)])
    report = loop_report(net)
    assert report.status is Status.NONCONTRACTIVE and report.factor is None
    assert report.components[0].rho == pytest.approx(1.0)


def test_a_difference_loop_of_gain_two_is_noncontractive_and_below_one_is_contractive():
    strong = Network.from_edges([EYE, DIF, DBL], [(0, 1), (2, 1), (1, 2)])
    weak = Network.from_edges([EYE, DIF, HLV], [(0, 1), (2, 1), (1, 2)])
    assert loop_report(strong).status is Status.NONCONTRACTIVE
    assert loop_report(weak).status is Status.CONTRACTIVE


def test_the_bound_is_not_a_verdict_cancelling_paths_are_noncontractive_yet_settle():
    # A Difference of two equal paths back from its own output: its input is always 0.
    net = Network.from_edges([DIF, DBL, DBL], [(0, 1), (0, 2), (1, 0), (2, 0)])
    report = loop_report(net)
    assert report.status is Status.NONCONTRACTIVE
    assert report.components[0].rho == pytest.approx(np.sqrt(2.0))
    rng = np.random.default_rng(11)
    for _ in range(5):
        start = rng.uniform(0.0, RATE_MAX, size=(1, net.n))
        assert relax(net, start, np.zeros((1, 0)), ticks=400).max() < 1e-9


def test_a_contractive_loop_forgets_its_start_and_a_noncontractive_one_may_not():
    eyes = np.array([[0.375]])
    ring = halve_ring()
    ends = [relax(ring, np.full((1, ring.n), v), eyes) for v in (0.0, 0.5, 1.0)]
    assert np.allclose(ends[0], ends[1]) and np.allclose(ends[1], ends[2])
    hold = Network.from_edges([EYE, SUM, DBL, DBL, HLV], [(0, 1), (1, 2), (2, 3), (3, 4), (4, 1)])
    low, high = (relax(hold, np.full((1, hold.n), v), np.zeros((1, 1))) for v in (0.0, 0.3))
    assert abs(low[0, 1, 0] - high[0, 1, 0]) > 0.05  # the start is remembered


def test_the_time_constant_is_a_sixtieth_of_a_second():
    assert TAU == pytest.approx(1 / 60)
    assert initial_state(halve_ring()).shape == (1, 3, CHANNELS)


# Problems


def test_problems_name_what_is_idle_or_unfed():
    net = Network.from_edges(
        [EYE, SUM, SRC, THR, DBL, THR],
        [(0, 1), (1, 3), (2, 3)],  # the doubler and the second thruster are not connected
    )
    assert problems(net) == (
        "P1 has one input and passes it through",
        "D4 is fed by no sensor: its rate stays 0",
        "D4 sends its rate nowhere",
        "T5 is fed by no sensor: its rate stays 0",
    )


def test_a_healthy_graph_has_no_problems_and_a_loop_without_sensor_is_unfed():
    assert problems(Network.from_edges([EYE, EYE, DIF, THR], [(0, 2), (1, 2), (2, 3)])) == ()
    net = Network.from_edges([DBL, HLV], [(0, 1), (1, 0)])
    assert problems(net) == (
        "D0 is fed by no sensor: its rate stays 0",
        "H1 is fed by no sensor: its rate stays 0",
    )
