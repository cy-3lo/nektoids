"""The ring of icons round a focused cell (D-068). ring.py imports no pygame."""

import math

from nektoids.editor.layout import Tool
from nektoids.editor.ring import (
    ACTION_FACE,
    ACTIONS,
    FACES,
    ICON,
    angles,
    cycled,
    offer,
    part_key,
    slot_at,
    slots,
)
from nektoids.graph.board import Kind
from nektoids.levels.arenas import arenas, sandbox

AREA = (296, 58, 664, 554)
SIZE = 40.0
FEAR = arenas()[0]


def test_an_empty_cell_offers_the_parts_left_and_a_part_its_actions():
    board = FEAR.new_board()
    kinds = frozenset({Kind.EYE, Kind.THRUSTER})
    assert offer(board, (0, 0), kinds) == (Kind.EYE, Kind.THRUSTER)
    eye = board.place(Kind.EYE, (0, 0))
    assert offer(board, (0, 0), kinds) == (
        Tool.TURN_LEFT,
        Tool.TURN_RIGHT,
        Tool.WIRE,
        Tool.MOVE,
        Tool.DELETE,
    )
    board.place(Kind.EYE, (1, 0))
    assert offer(board, (2, 0), kinds) == (Kind.THRUSTER,)  # no eye left
    assert offer(board, (9, 9), kinds) == ()  # off the zone
    assert eye.id in board.nodes and part_key(Kind.THRUSTER, kinds) == "2"


def test_operators_do_not_turn():
    board = sandbox().new_board()
    board.place(Kind.SUM, (0, 0))
    assert offer(board, (0, 0), frozenset(Kind)) == (Tool.WIRE, Tool.MOVE, Tool.DELETE)


def test_up_to_six_icons_face_the_sides_and_more_spread_over_300_degrees():
    assert angles([Kind.EYE, Kind.THRUSTER]) == list(FACES[:2])
    assert angles([Tool.WIRE, Tool.TURN_LEFT]) == [
        ACTION_FACE[Tool.WIRE],
        ACTION_FACE[Tool.TURN_LEFT],
    ]
    seven = angles(list(Kind)[:7]) if len(Kind) >= 7 else angles([Kind.EYE] * 7)
    assert len(seven) == 7 and 240.0 in seven and 300.0 in seven  # the gap at the foot
    assert not any(240.0 < a < 300.0 for a in seven)


def test_the_icons_sit_round_the_cell_slide_in_at_the_edge_and_are_found_under_a_press():
    kinds = frozenset({Kind.EYE, Kind.THRUSTER})
    ring = slots([Kind.EYE, Kind.THRUSTER], (628.0, 335.0), SIZE, kinds, AREA)
    for slot in ring:
        assert math.dist(slot.at, (628.0, 335.0)) > SIZE  # beyond the cell
        assert slot_at(ring, slot.at, SIZE) is slot
        assert math.dist(slot.key_at, (628.0, 335.0)) > math.dist(slot.at, (628.0, 335.0))
    assert [s.key for s in ring] == ["1", "2"]
    assert slot_at(ring, (628.0, 335.0), SIZE) is None  # the cell itself
    for slot in slots(ACTIONS, (628.0, 335.0), SIZE, kinds, AREA):  # clear of the cell's picture
        assert math.dist(slot.at, (628.0, 335.0)) - ICON * SIZE > SIZE
    edge = slots(ACTIONS, (300.0, 70.0), SIZE, kinds, AREA)
    x, y, w, h = AREA
    assert all(x <= s.at[0] - ICON * SIZE and y <= s.at[1] - ICON * SIZE for s in edge)


def test_the_arrows_go_round_the_ring_and_through_nothing_when_it_is_a_stop():
    ring = slots([Kind.EYE, Kind.THRUSTER], (628.0, 335.0), SIZE, frozenset(Kind), AREA)
    assert cycled(ring, None, 1, blank=True) == 0
    assert cycled(ring, 1, 1, blank=True) is None  # nothing, then round again
    assert cycled(ring, 1, 1, blank=False) == 0
    assert cycled(ring, 0, -1, blank=True) is None
