"""The Wheel, the icons round a focused cell (D-068, D-069). wheel.py imports no pygame."""

import math

import pytest

from nektoids.editor.layout import Piece, Tool
from nektoids.editor.objects import KEYS
from nektoids.editor.wheel import (
    ICON,
    ON_RIM,
    PILE,
    RADIUS,
    WHEEL_HEX,
    angles,
    slot_at,
    slots,
)
from nektoids.graph.board import Kind

SIZE = 40.0
CENTRE = (628.0, 335.0)
FEAR = {"zone": 19, "stock": {"eye": 2, "thruster": 2}, "parts": [], "wires": []}
# Fear's board before its thrusters were locked (D-354): two eyes and two thrusters to place


def test_up_to_five_icons_sit_beyond_the_cells_corners_the_gap_at_the_foot():
    assert angles(1) == [90.0] and angles(2) == [150.0, 90.0]  # side by side, no gap (D-316)
    assert angles(4) == [210.0, 150.0, 90.0, 30.0]  # a Source's actions: none left empty
    for n in range(1, ON_RIM + 1):
        assert all(b - a == -60.0 for a, b in zip(angles(n), angles(n)[1:], strict=False))
    assert angles(ON_RIM) == [210.0, 150.0, 90.0, 30.0, -30.0]  # the corners but the lowest
    for n in range(ON_RIM + 1):
        assert len(angles(n)) == n and all(a % 60.0 == 30.0 for a in angles(n))  # corners
        assert all(a % 360.0 != 270.0 for a in angles(n))  # the foot stays clear
    wheel = slots([Kind.EYE, Kind.THRUSTER], CENTRE, SIZE, frozenset({Kind.EYE, Kind.THRUSTER}))
    for slot in wheel:
        assert math.dist(slot.at, CENTRE) == pytest.approx(RADIUS * SIZE) and slot.depth == 0
        assert slot_at(wheel, slot.at, SIZE) is slot
    assert [s.key for s in wheel] == ["1", "2"]
    assert slot_at(wheel, CENTRE, SIZE) is None  # the cell itself
    actions = [Tool.TURN_LEFT, Tool.MOVE, Tool.WIRE, Tool.TURN_RIGHT, Tool.DELETE]
    for slot in slots(actions, CENTRE, SIZE, frozenset(Kind)):  # clear of the cell's picture
        assert slot.depth or math.dist(slot.at, CENTRE) - ICON * SIZE > SIZE


def test_more_than_five_turn_on_a_wheel_the_others_piled_under_its_ends():
    seven = list(Kind)[:7]  # the sandbox's seven parts: more kinds must not change the test
    wheel = slots(seven, CENTRE, SIZE, frozenset(Kind))
    assert [s.depth for s in wheel] == [0, 0, 0, 0, 0, 1, 2]  # piled under the last end
    last, first_pile, second = wheel[4], wheel[5], wheel[6]
    step = PILE * ICON * SIZE  # a fifth of a radius, along the circle, towards the gap
    for near, far in ((last, first_pile), (first_pile, second)):
        assert math.dist(far.at, CENTRE) == pytest.approx(RADIUS * SIZE)
        assert math.dist(near.at, far.at) == pytest.approx(step, rel=1e-3)
        assert far.at[1] > near.at[1]  # the last end is low on the right: on towards the gap
    turned_two = slots(seven, CENTRE, SIZE, frozenset(Kind), turn=2)
    assert [s.depth for s in turned_two] == [2, 1, 0, 0, 0, 0, 0]  # under the first end now
    # A pile lies under its end: a press there takes the icon on the Wheel.
    assert slot_at(wheel, first_pile.at, SIZE) is last and slot_at(wheel, second.at, SIZE) is last


def test_the_wheel_takes_the_editors_keys_for_its_own_icons():
    items = (Piece.LIGHT, Piece.OBSTACLE)  # an empty point of the plane (D-301)
    shown = slots(items, (100.0, 100.0), WHEEL_HEX, frozenset(), keys=KEYS)
    assert [(s.what, s.key) for s in shown] == [(Piece.LIGHT, "1"), (Piece.OBSTACLE, "2")]
    assert [s.at for s in shown] == [
        s.at for s in slots(list(Kind)[:2], (100.0, 100.0), WHEEL_HEX, frozenset(Kind))
    ]
