import re

from nektoids.graph.analysis import loop_report
from nektoids.graph.board import Kind
from nektoids.graph.equations import node_equations, report_lines
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


def targets(net):
    """What each operator asks for, by label, from its line 'tau dX/dt = -X + target'."""
    found = {}
    for line in node_equations(net)[1:]:
        match = re.fullmatch(r"tau d(\w+)/dt = -\1 \+ (.*)", line)
        if match:
            found[match.group(1)] = match.group(2)
    return found


def test_labels_name_the_kind_and_the_index():
    net = Network.from_edges([EYE, SRC, DBL, HLV, SUM, DIF, THR], [])
    assert [label(net, i) for i in range(net.n)] == ["E0", "S1", "D2", "H3", "P4", "M5", "T6"]


def test_each_node_has_one_line_and_the_operators_relax_with_the_lag():
    assert node_equations(sample()) == (
        "R = 1, tau = 16.7 ms",
        "E0 = eye",
        "E1 = eye",
        "tau dH2/dt = -H2 + min(R, E0/2/2)",  # E0 forks in two, then the halver
        "tau dM3/dt = -M3 + min(R, |E1 - H2|)",
        "tau dT4/dt = -T4 + min(R, E0/2)",
        "tau dT5/dt = -T5 + min(R, M3)",
    )


def test_eyes_and_sources_are_given():
    lines = node_equations(Network.from_edges([EYE, SRC, THR], [(0, 2), (1, 2)]))
    assert lines[1:3] == ("E0 = eye", "S1 = source")


def test_gains_wrap_a_sum_and_leave_a_difference_alone():
    net = Network.from_edges(
        [EYE, SRC, SUM, DBL, EYE, DIF, HLV, DIF, THR],
        [(0, 2), (1, 2), (2, 3), (4, 5), (3, 5), (5, 6), (6, 7), (3, 7), (7, 8)],
    )
    found = targets(net)
    assert found["P2"] == "min(R, E0 + S1)"
    assert found["D3"] == "min(R, 2*P2)"
    assert found["M5"] == "min(R, |D3/2 - E4|)"  # D3 forks to M5 and M7
    assert found["H6"] == "min(R, M5/2)"
    assert found["M7"] == "min(R, |D3/2 - H6|)"
    net = Network.from_edges([EYE, EYE, SUM, DBL, HLV], [(0, 2), (1, 2), (2, 3), (2, 4)])
    found = targets(net)
    assert found["D3"] == "min(R, 2*P2/2)" and found["H4"] == "min(R, P2/2/2)"
    net = Network.from_edges([EYE, EYE, DBL], [(0, 2), (1, 2)])
    assert targets(net)["D2"] == "min(R, 2*(E0 + E1))"


def test_an_operator_with_nothing_wired_in_asks_for_zero():
    assert targets(Network.from_edges([SUM], []))["P0"] == "0"


def test_the_report_is_put_in_words():
    ring = Network.from_edges([EYE, SUM, HLV], [(0, 1), (1, 2), (2, 1)])
    assert report_lines(ring, loop_report(ring)) == (
        "loop P1 H2: rho = 0.707",
        "rho < 1 (q = 0.75): it settles to one value",
    )
    dag = sample()
    assert report_lines(dag, loop_report(dag)) == ("no loop",)
    flat = Network.from_edges([EYE, SUM, DBL, HLV], [(0, 1), (1, 2), (2, 3), (3, 1)])
    assert report_lines(flat, loop_report(flat))[-1] == (
        "rho >= 1: it may hold a value, latch, oscillate or saturate"
    )
