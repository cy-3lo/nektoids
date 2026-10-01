"""The parts' names and info boxes (D-036). parts.py imports no pygame."""

from nektoids.editor.parts import NAME, info, ports
from nektoids.graph.board import Kind


def test_every_part_has_a_name_and_an_info_box():
    for kind in Kind:
        assert NAME[kind] and info(kind)
    assert NAME[Kind.DIFFERENCE] == "Diff"


def test_the_info_box_says_what_the_board_allows_in_and_out():
    assert ports(Kind.EYE) == ("In: nothing.", "Out: any number of wires, sharing what it sends.")
    assert ports(Kind.SUM) == (
        "In: two wires at most; with one, it passes it on.",
        "Out: one wire.",
    )
    assert ports(Kind.THRUSTER) == ("In: any number of wires, added.", "Out: nothing.")
    assert info(Kind.HALVE)[-2:] == ports(Kind.HALVE)


def test_the_lines_are_short_enough_for_the_box():
    for kind in Kind:
        assert all(len(line) <= 52 for line in info(kind)), kind
