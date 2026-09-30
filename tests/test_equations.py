import numpy as np

from nektoids.graph.analysis import loop_report
from nektoids.graph.board import Kind
from nektoids.graph.equations import (
    LIMIT,
    branch_equations,
    composed,
    node_equations,
    report_lines,
)
from nektoids.graph.evaluate import evaluate
from nektoids.graph.network import Network, label

EYE, SRC, DBL, HLV, SUM, DIF, THR = (
    Kind.EYE,
    Kind.SOURCE,
    Kind.DOUBLE,
    Kind.HALVE,
    Kind.SUM,
    Kind.DIFFERENCE,
    Kind.THRUSTER,
)


def sample():
    """Two eyes: E0 feeds a halver and thruster T4; the halver and E1 feed a difference; T5."""
    kinds = [EYE, EYE, HLV, DIF, THR, THR]
    edges = [(0, 2), (2, 3), (1, 3), (0, 4), (3, 5)]
    return Network.from_edges(kinds, edges)


def test_labels_name_the_kind_and_the_index():
    net = Network.from_edges([EYE, SRC, DBL, HLV, SUM, DIF, THR], [])
    assert [label(net, i) for i in range(net.n)] == ["E0", "S1", "D2", "H3", "P4", "M5", "T6"]


def test_each_node_has_one_line_in_terms_of_its_inputs():
    assert node_equations(sample()) == (
        "R = 1",
        "E0 = eye",
        "E1 = eye",
        "H2 = min(R, E0/2/2)",  # E0 forks in two, then the halver
        "M3 = min(R, |E1 - H2|)",
        "T4 = min(R, E0/2)",
        "T5 = min(R, M3)",
    )


def test_gains_wrap_a_sum_and_leave_a_difference_alone():
    net = Network.from_edges(
        [EYE, SRC, SUM, DBL, EYE, DIF, HLV, DIF, THR],
        [(0, 2), (1, 2), (2, 3), (4, 5), (3, 5), (5, 6), (6, 7), (3, 7), (7, 8)],
    )
    lines = dict(line.split(" = ", 1) for line in node_equations(net)[1:])
    assert lines["S1"] == "1"
    assert lines["P2"] == "min(R, E0 + S1)"
    assert lines["D3"] == "min(R, 2*P2)"
    assert lines["M5"] == "min(R, |D3/2 - E4|)"  # D3 forks to M5 and M7
    assert lines["H6"] == "min(R, M5/2)"
    assert lines["M7"] == "min(R, |D3/2 - H6|)"
    net = Network.from_edges([EYE, EYE, SUM, DBL, HLV], [(0, 2), (1, 2), (2, 3), (2, 4)])
    lines = dict(line.split(" = ", 1) for line in node_equations(net)[1:])
    assert lines["D3"] == "min(R, 2*P2/2)" and lines["H4"] == "min(R, P2/2/2)"


def test_an_operator_with_nothing_wired_in_is_zero():
    assert node_equations(Network.from_edges([SUM], []))[1] == "P0 = 0"


def test_composition_gives_each_thruster_from_the_sensors():
    assert composed(sample()) == {
        4: "T4 = min(R, E0/2)",
        5: "T5 = min(R, min(R, |E1 - min(R, E0/2/2)|))",
    }


def test_composition_of_a_sum_under_a_gain_is_wrapped():
    net = Network.from_edges([EYE, EYE, SUM, DBL, THR], [(0, 2), (1, 2), (2, 3), (3, 4)])
    assert composed(net) == {4: "T4 = min(R, min(R, 2*min(R, E0 + E1)))"}


def test_a_deep_chain_falls_back_on_names_instead_of_growing_without_limit():
    n = 30
    net = Network.from_edges([EYE] + [DBL] * (n - 1) + [THR], [(i, i + 1) for i in range(n)])
    (line,) = composed(net).values()
    assert len(line) <= LIMIT + 40
    assert "D" in line.split(" = ", 1)[1]  # an earlier node stands in for the rest


def test_there_is_no_composition_for_a_loop():
    assert composed(Network.from_edges([DBL, HLV], [(0, 1), (1, 0)])) is None


def test_a_loop_is_written_as_the_affine_equations_of_its_active_branch():
    ring = Network.from_edges([EYE, SUM, HLV], [(0, 1), (1, 2), (2, 1)])
    y = evaluate(ring, np.array([[0.375]]))[0]
    assert branch_equations(ring, y) == ("P1 = E0 + H2", "H2 = 0.5*P1")
    # The eye is the larger input of the Difference, so its second input enters with a minus.
    gap = Network.from_edges([EYE, DIF, HLV], [(0, 1), (2, 1), (1, 2)])
    y = evaluate(gap, np.array([[0.375]]))[0]
    assert branch_equations(gap, y) == ("M1 = E0 - H2", "H2 = 0.5*M1")


def test_a_capped_node_of_a_loop_is_written_as_the_cap():
    ring = Network.from_edges([EYE, SUM, HLV], [(0, 1), (1, 2), (2, 1)])
    y = evaluate(ring, np.array([[1.0]]))[0]
    assert branch_equations(ring, y) == ("P1 = R", "H2 = 0.5*P1")


def test_the_report_is_put_in_words():
    ring = Network.from_edges([EYE, SUM, HLV], [(0, 1), (1, 2), (2, 1)])
    assert report_lines(ring, loop_report(ring)) == (
        "loop P1 H2: rho = 0.707",
        "  det(I - W_s) per sign pattern: 0.5",
        "contractive (q = 0.75): the solution is unique",
    )
    dag = sample()
    assert report_lines(dag, loop_report(dag)) == ("no loop: one pass in topological order",)
    flat = Network.from_edges([EYE, SUM, DBL, HLV], [(0, 1), (1, 2), (2, 3), (3, 1)])
    assert report_lines(flat, loop_report(flat))[-2:] == (
        "rho >= 1: evaluation refuses this loop",
        "  a branch is singular or reversed: the solution may not be unique",
    )
