"""The Wheel, the icons round a focused cell (D-068, D-069). wheel.py imports no pygame."""

import math
from itertools import pairwise

import pytest

from nektoids.editor.layout import BAR_WIDTH, DRAWER_WIDTH, Drawer, Tool, make_layout
from nektoids.editor.wheel import (
    ACTIONS,
    ICON,
    LINE_BELOW,
    ON_RIM,
    PILE,
    RADIUS,
    SLIDE,
    WHEEL_HEX,
    angles,
    centre_in,
    cycled,
    offer,
    part_key,
    pile_at,
    slid,
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
    for slot in slots(ACTIONS, CENTRE, SIZE, frozenset(Kind)):  # clear of the cell's picture
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


def test_the_mouse_resting_past_an_end_on_its_pile_turns_the_wheel_that_way():
    def at(angle, r=RADIUS * SIZE):
        a = math.radians(angle)
        return CENTRE[0] + r * math.cos(a), CENTRE[1] - r * math.sin(a)

    past = math.degrees(1.5 * ICON / RADIUS)  # half a radius past the end icon, along the circle
    first, last = angles(ON_RIM)[0], angles(ON_RIM)[-1]
    assert pile_at(7, 0, CENTRE, SIZE, at(last - past)) == 1  # the pile under the last end
    assert pile_at(7, 0, CENTRE, SIZE, at(last)) == 0  # the end icon: a click takes it
    assert pile_at(7, 0, CENTRE, SIZE, at(first + past)) == 0  # nothing piled there yet
    assert pile_at(7, 2, CENTRE, SIZE, at(first + past)) == -1  # turned: piled under the first
    assert pile_at(7, 2, CENTRE, SIZE, at(last - past)) == 0  # and none left under the last
    assert pile_at(5, 0, CENTRE, SIZE, at(last - past)) == 0  # five: no pile at all


def test_the_wheel_turns_just_enough_for_the_choice_to_be_on_the_rim():
    assert turned(0, 4, 7) == 0 and turned(0, 5, 7) == 1 and turned(0, 6, 7) == 2
    assert turned(2, 0, 7) == 0 and turned(2, 3, 7) == 2  # back, or already there
    assert turned(9, None, 7) == 2 and turned(3, None, 4) == 0  # never past the last


def test_a_step_slides_in_six_frames_eased_and_a_new_one_goes_straight_on():
    assert SLIDE == 6  # 0.1 s at 60 frames a second (D-083)
    shown = [slid(0.0, 1, left) for left in range(SLIDE, -1, -1)]  # frame by frame
    assert shown[0] == 0.0 and shown[-1] == 1.0
    assert all(a < b for a, b in pairwise(shown))  # one way only
    assert shown[SLIDE // 2] > 0.5  # eased out: past half way at half time
    midway = slid(0.0, 1, SLIDE - 2)  # a second step, two frames in
    assert slid(midway, 2, SLIDE) == midway and slid(midway, 2, 0) == 2.0  # on from there


def test_while_the_wheel_slides_its_icons_run_along_the_circle_between_their_places():
    def angle(slot):  # counter-clockwise from the right, the gap at the foot [degrees]
        a = math.degrees(math.atan2(CENTRE[1] - slot.at[1], slot.at[0] - CENTRE[0]))
        return a + 360.0 if a < -90.0 else a

    seven = list(Kind)
    for start in (0, 1):
        before = slots(seven, CENTRE, SIZE, frozenset(Kind), start)
        after = slots(seven, CENTRE, SIZE, frozenset(Kind), start + 1)
        for frame in range(1, SLIDE):
            now = slots(seven, CENTRE, SIZE, frozenset(Kind), start + frame / SLIDE)
            for b, n, a in zip(before, now, after, strict=True):
                assert math.dist(n.at, CENTRE) == pytest.approx(RADIUS * SIZE)
                low, high = sorted((angle(b), angle(a)))
                assert low < angle(n) < high or angle(b) == pytest.approx(angle(a))
    # The icon going under a pile is drawn under the one sliding over its place: either way round.
    half = slots(seven, CENTRE, SIZE, frozenset(Kind), 0.5)
    assert 0 < half[0].depth < 1 and half[1].depth == 0  # 0 tucks under the first end, 1 over
    assert 0 < half[5].depth < 1 and half[4].depth == 0  # back: 5 under the last end, 4 over


def test_the_arrows_go_along_the_arc_and_stop_at_its_ends():
    wheel = slots([Kind.EYE, Kind.THRUSTER, Kind.SUM], CENTRE, SIZE, frozenset(Kind))
    assert cycled(wheel, None, 1) == 0 and cycled(wheel, None, -1) == 2  # from nothing: an end
    assert cycled(wheel, 0, 1) == 1 and cycled(wheel, 2, -1) == 1
    assert cycled(wheel, 2, 1) == 2 and cycled(wheel, 0, -1) == 0  # never round past an end
    assert cycled([], None, 1) is None


def test_the_wheel_fits_its_room_at_the_drawers_foot_with_its_line_under_it():
    view = make_layout(Drawer.PARTS).wheel_view  # Tools' is the same (D-069)
    assert make_layout(Drawer.TOOLS).wheel_view == view
    x, y, w, h = view
    centre, line = centre_in(view), 20  # the line under it: Plex Mono at 15 px
    items = list(Kind)  # the most a Wheel offers: every part, piled under its ends
    for n in range(1, len(items) + 1):
        for frame in range(SLIDE * max(0, n - ON_RIM) + 1):  # in sixths: half way, the furthest
            wheel = slots(items[:n], centre, WHEEL_HEX, frozenset(Kind), frame / SLIDE)
            r = ICON * WHEEL_HEX
            # At rest in the room; sliding, an icon swings round past a corner, out of the room
            # into the drawer's margin, never out of the drawer (D-083).
            left, right = (
                (x, x + w) if frame % SLIDE == 0 else (BAR_WIDTH, BAR_WIDTH + DRAWER_WIDTH)
            )
            for slot in wheel:
                assert left <= slot.at[0] - r and slot.at[0] + r <= right
                assert slot.at[1] - r >= y
            lowest = max([centre[1] + WHEEL_HEX] + [slot.at[1] + r for slot in wheel])
            assert lowest + LINE_BELOW + line <= y + h
