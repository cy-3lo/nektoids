"""The ring of icons round a focused cell (D-068). ring.py imports no pygame."""

import math

import pytest

from nektoids.editor.layout import ACTION_WIDTH, Drawer, Tool, make_layout
from nektoids.editor.ring import (
    ACTIONS,
    ICON,
    IN_RING,
    KEY_OUT,
    LINE_BELOW,
    PILE,
    RADIUS,
    RING_HEX,
    angles,
    centre_in,
    cycled,
    offer,
    part_key,
    pile_at,
    slot_at,
    slots,
    swaps,
    turned,
)
from nektoids.graph.board import Kind
from nektoids.levels.arenas import arenas, sandbox

SIZE = 40.0
CENTRE = (628.0, 335.0)
FEAR = arenas()[0]


def test_an_empty_cell_offers_the_parts_left_and_a_part_its_actions():
    board = FEAR.new_board()
    kinds = frozenset({Kind.EYE, Kind.THRUSTER})
    assert offer(board, (0, 0), kinds) == (Kind.EYE, Kind.THRUSTER)
    eye = board.place(Kind.EYE, (0, 0))
    assert offer(board, (0, 0), kinds) == (  # no swap: no source in Fear
        Tool.TURN_LEFT,
        Tool.MOVE,
        Tool.WIRE,
        Tool.TURN_RIGHT,
        Tool.DELETE,
    )
    board.place(Kind.EYE, (1, 0))
    assert offer(board, (2, 0), kinds) == (Kind.THRUSTER,)  # no eye left
    assert offer(board, (9, 9), kinds) == ()  # off the zone
    assert eye.id in board.nodes and part_key(Kind.THRUSTER, kinds) == "2"


def test_operators_do_not_turn():
    board = sandbox().new_board()
    board.place(Kind.SUM, (0, 0))
    assert offer(board, (0, 0), frozenset(Kind)) == (Tool.MOVE, Tool.WIRE, Tool.SWAP, Tool.DELETE)


def test_a_part_may_be_swapped_for_another_of_its_group_left_in_parts_order():
    board = sandbox().new_board()
    total, eye, thruster = (
        board.place(k, c)
        for k, c in ((Kind.SUM, (0, 0)), (Kind.EYE, (1, 0)), (Kind.THRUSTER, (2, 0)))
    )
    assert swaps(board, total.cell, frozenset(Kind)) == (Kind.DOUBLE, Kind.HALVE, Kind.DIFFERENCE)
    assert swaps(board, eye.cell, frozenset({Kind.EYE, Kind.THRUSTER})) == ()  # no source here
    assert swaps(board, thruster.cell, frozenset(Kind)) == ()  # alone in its group
    assert Tool.SWAP not in offer(board, thruster.cell, frozenset(Kind))


def test_up_to_five_icons_sit_beyond_the_cells_corners_the_gap_at_the_foot():
    assert angles(1) == [90.0] and angles(2) == [150.0, 30.0]  # the top, or each side of it
    assert angles(4) == [210.0, 150.0, 30.0, -30.0]
    assert angles(IN_RING) == [210.0, 150.0, 90.0, 30.0, -30.0]  # the corners but the lowest
    for n in range(IN_RING + 1):
        assert len(angles(n)) == n and all(a % 60.0 == 30.0 for a in angles(n))  # corners
        assert all(a % 360.0 != 270.0 for a in angles(n))  # the foot stays clear
    ring = slots([Kind.EYE, Kind.THRUSTER], CENTRE, SIZE, frozenset({Kind.EYE, Kind.THRUSTER}))
    for slot in ring:
        assert math.dist(slot.at, CENTRE) == pytest.approx(RADIUS * SIZE) and slot.depth == 0
        assert slot_at(ring, slot.at, SIZE) is slot
        assert math.dist(slot.key_at, CENTRE) > math.dist(slot.at, CENTRE)  # outside it
    assert [s.key for s in ring] == ["1", "2"]
    assert slot_at(ring, CENTRE, SIZE) is None  # the cell itself
    for slot in slots(ACTIONS, CENTRE, SIZE, frozenset(Kind)):  # clear of the cell's picture
        assert slot.depth or math.dist(slot.at, CENTRE) - ICON * SIZE > SIZE


def test_more_than_five_turn_on_a_wheel_the_others_piled_under_its_ends():
    seven = list(Kind)  # the sandbox's seven parts
    ring = slots(seven, CENTRE, SIZE, frozenset(Kind))
    assert [s.depth for s in ring] == [0, 0, 0, 0, 0, 1, 2]  # piled under the last end
    last, first_pile, second = ring[4], ring[5], ring[6]
    step = PILE * ICON * SIZE  # a fifth of a radius, along the circle, towards the gap
    for near, far in ((last, first_pile), (first_pile, second)):
        assert math.dist(far.at, CENTRE) == pytest.approx(RADIUS * SIZE)
        assert math.dist(near.at, far.at) == pytest.approx(step, rel=1e-3)
        assert far.at[1] > near.at[1]  # the last end is low on the right: on towards the gap
    turned_two = slots(seven, CENTRE, SIZE, frozenset(Kind), turn=2)
    assert [s.depth for s in turned_two] == [2, 1, 0, 0, 0, 0, 0]  # under the first end now
    # A pile lies under its end: a press there takes the icon on the ring.
    assert slot_at(ring, first_pile.at, SIZE) is last and slot_at(ring, second.at, SIZE) is last


def test_the_mouse_resting_past_an_end_on_its_pile_turns_the_wheel_that_way():
    def at(angle, r=RADIUS * SIZE):
        a = math.radians(angle)
        return CENTRE[0] + r * math.cos(a), CENTRE[1] - r * math.sin(a)

    past = math.degrees(1.5 * ICON / RADIUS)  # half a radius past the end icon, along the circle
    first, last = angles(IN_RING)[0], angles(IN_RING)[-1]
    assert pile_at(7, 0, CENTRE, SIZE, at(last - past)) == 1  # the pile under the last end
    assert pile_at(7, 0, CENTRE, SIZE, at(last)) == 0  # the end icon: a click takes it
    assert pile_at(7, 0, CENTRE, SIZE, at(first + past)) == 0  # nothing piled there yet
    assert pile_at(7, 2, CENTRE, SIZE, at(first + past)) == -1  # turned: piled under the first
    assert pile_at(7, 2, CENTRE, SIZE, at(last - past)) == 0  # and none left under the last
    assert pile_at(5, 0, CENTRE, SIZE, at(last - past)) == 0  # five: no pile at all


def test_the_action_atop_the_main_screen_is_as_wide_as_a_ring_icon():
    assert ACTION_WIDTH == round(2 * ICON * RING_HEX)


def test_the_wheel_turns_just_enough_for_the_choice_to_be_on_the_ring():
    assert turned(0, 4, 7) == 0 and turned(0, 5, 7) == 1 and turned(0, 6, 7) == 2
    assert turned(2, 0, 7) == 0 and turned(2, 3, 7) == 2  # back, or already there
    assert turned(9, None, 7) == 2 and turned(3, None, 4) == 0  # never past the last


def test_the_arrows_go_round_the_ring_and_through_nothing_when_it_is_a_stop():
    ring = slots([Kind.EYE, Kind.THRUSTER], CENTRE, SIZE, frozenset(Kind))
    assert cycled(ring, None, 1, blank=True) == 0
    assert cycled(ring, 1, 1, blank=True) is None  # nothing, then round again
    assert cycled(ring, 1, 1, blank=False) == 0
    assert cycled(ring, 0, -1, blank=True) is None


def test_the_sandboxs_seven_parts_fit_in_tools_wheel_and_piles_included():
    x, y, w, h = make_layout(Drawer.TOOLS).cell_view
    centre = (x + w / 2, y + 14 + (RADIUS + KEY_OUT) * RING_HEX)  # as the scene puts it
    for turn in (0, 2):
        for slot in slots(list(Kind), centre, RING_HEX, frozenset(Kind), turn):
            sx, sy = slot.at
            r = ICON * RING_HEX
            assert x <= sx - r and sx + r <= x + w and y <= sy - r and sy + r <= y + h - 24
            assert x <= slot.key_at[0] <= x + w and y <= slot.key_at[1] <= y + h


def test_the_ring_fits_the_drawers_picture_of_the_cell_with_its_line_under_it():
    view = make_layout(Drawer.PARTS).cell_view  # Tools' is the same (D-069)
    assert make_layout(Drawer.TOOLS).cell_view == view
    x, y, w, h = view
    centre, line = centre_in(view), 20  # the line under it: Plex Mono at 15 px
    items = list(Kind)  # the most a ring offers: every part, piled under its ends
    for n in range(1, len(items) + 1):
        for turn in range(max(1, n - IN_RING + 1)):
            ring = slots(items[:n], centre, RING_HEX, frozenset(Kind), turn)
            r = ICON * RING_HEX
            for slot in ring:
                assert x <= slot.at[0] - r and slot.at[0] + r <= x + w
                assert y <= slot.key_at[1] - 10 and slot.at[1] - r >= y
            lowest = max([centre[1] + RING_HEX] + [slot.at[1] + r for slot in ring])
            assert lowest + LINE_BELOW + line <= y + h
