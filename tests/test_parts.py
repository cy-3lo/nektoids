"""The parts' names and info boxes (D-036). parts.py imports no pygame."""

from nektoids.editor.parts import NAME, PAINTED, WHAT, info, ports
from nektoids.graph.board import Kind


def test_every_part_has_a_name_and_an_info_box():
    for kind in Kind:
        assert NAME[kind] and info(kind)
    assert NAME[Kind.DIFFERENCE] == "Diff"


def test_the_info_box_says_what_the_board_allows_in_and_out():
    assert ports(Kind.EYE) == ("In: nothing.", "Out: any number of wires.")
    assert ports(Kind.SUM) == ("In: two wires at most.", "Out: one wire.")
    assert ports(Kind.THRUSTER) == ("In: any number of wires.", "Out: nothing.")
    assert info(Kind.HALVE)[-2:] == ports(Kind.HALVE)


def test_the_info_box_holds_paragraphs_what_it_does_its_paint_then_in_and_out():
    for kind in Kind:  # each a paragraph the box wraps (D-094)
        painted = (PAINTED[kind],) if kind.paintable else ()  # D-502
        assert info(kind) == (WHAT[kind], *painted, *ports(kind)), kind
        assert isinstance(WHAT[kind], str), kind
    assert set(PAINTED) == {kind for kind in Kind if kind.paintable}
