"""A level made by hand (D-301). making.py imports no pygame."""

import json
from dataclasses import replace

import pytest

from nektoids.levels.arenas import sandbox
from nektoids.levels.level import ItemKind, Level, to_json
from nektoids.levels.making import (
    NEW,
    SETTING,
    SPEC_LONGEST,
    TITLE_LONGEST,
    Unmade,
    adjusted,
    moved,
    placed,
    removed,
    specified,
    start_moved,
    titled,
    turned,
)
from nektoids.levels.objectives import Count, Goal, Target, Verb

LEVEL = sandbox()  # two lights, four obstacles; the start at (15, 19), heading 20°


def test_an_item_placed_lands_on_the_lattice_last_in_order_set_as_new_and_the_old_level_stays():
    made = placed(LEVEL, ItemKind.LIGHT, (10.2, 13.9))
    assert made.items[:-1] == LEVEL.items and len(LEVEL.items) == 6
    last = made.items[-1]
    assert (last.kind, last.at, last.value) == (ItemKind.LIGHT, (10.0, 14.0), NEW[ItemKind.LIGHT])
    assert len(made.arena.lights) == 3  # the simulation reads it
    assert placed(LEVEL, ItemKind.OBSTACLE, (3.0, 3.0)).items[-1].value == 1.0


def test_an_item_moved_or_set_stays_on_the_lattice_and_within_its_range():
    light = len(LEVEL.items) - 6  # the first light, power 8
    assert moved(LEVEL, light, (12.74, 3.1)).items[light].at == (12.5, 3.0)
    assert adjusted(LEVEL, light, 3).items[light].value == 11.0
    assert adjusted(LEVEL, light, 99).items[light].value == SETTING[ItemKind.LIGHT].hi
    obstacle = 2  # radius 1
    assert adjusted(LEVEL, obstacle, -1).items[obstacle].value == 0.5
    assert adjusted(LEVEL, obstacle, -5).items[obstacle].value == 0.5  # no smaller
    assert adjusted(LEVEL, obstacle, 2).items[obstacle].value == 2.0


def test_a_light_on_an_obstacle_and_a_start_inside_one_are_refused_with_their_reason():
    obstacle = LEVEL.items[2].at  # (21, 21), radius 1
    with pytest.raises(Unmade, match="touches an obstacle"):
        moved(LEVEL, 0, obstacle)
    with pytest.raises(Unmade, match="touches an obstacle"):
        placed(LEVEL, ItemKind.LIGHT, (obstacle[0] + 1.5, obstacle[1]))  # rims 0.5 u apart
    placed(LEVEL, ItemKind.LIGHT, (obstacle[0] + 2.5, obstacle[1]))  # clear of it
    with pytest.raises(Unmade, match="start inside an obstacle"):
        start_moved(LEVEL, (obstacle[0] + 1.5, obstacle[1]))
    with pytest.raises(Unmade, match="start inside an obstacle"):
        placed(LEVEL, ItemKind.OBSTACLE, (15.0, 20.5))  # on the swimmer
    with pytest.raises(Unmade, match="start inside an obstacle"):
        adjusted(placed(LEVEL, ItemKind.OBSTACLE, (15.0, 21.5)), 6, 2)  # grown onto it


def test_an_item_removed_takes_its_place_out_and_the_others_move_up():
    made = removed(LEVEL, 1)
    assert made.items == LEVEL.items[:1] + LEVEL.items[2:]
    assert len(made.arena.lights) == 1


def test_the_start_moves_on_the_lattice_and_turns_by_fifteen_degrees_within_a_turn():
    assert start_moved(LEVEL, (4.3, 4.8)).start == (4.5, 5.0, 20.0)
    assert turned(LEVEL, 1).start[2] == 30.0  # 35, onto the lattice: touched, it snaps
    assert turned(turned(LEVEL, 1), 1).start[2] == 45.0
    assert turned(turned(LEVEL, -1), -1).start[2] == 345.0  # 5, then -10: within [0, 360)
    assert turned(replace(LEVEL, start=(0.0, 0.0, 345.0)), 1).start[2] == 0.0


def test_a_made_level_reads_back_as_written_by_to_json():
    made = turned(placed(start_moved(LEVEL, (3.0, 4.5)), ItemKind.OBSTACLE, (9.0, 9.0)), -2)
    text = to_json(made)
    again = Level.from_dict(json.loads(text))
    assert again == made and to_json(again) == text


def test_a_title_and_a_spec_are_written_their_spaces_squeezed_and_never_left_empty():
    made = specified(titled(LEVEL, "  Two   lights "), "Touch\nboth lights.")
    assert (made.title, made.spec) == ("Two lights", "Touch both lights.")
    assert made.items == LEVEL.items and len(titled(LEVEL, "x" * 99).title) == TITLE_LONGEST
    assert len(specified(LEVEL, "y" * 999).spec) == SPEC_LONGEST
    with pytest.raises(Unmade, match="needs a title"):
        titled(LEVEL, "   ")
    with pytest.raises(Unmade, match="what the level asks"):
        specified(LEVEL, "")


def test_a_mark_goes_anywhere_its_radius_from_half_a_unit_to_thirty():
    on_light = placed(LEVEL, ItemKind.MARK, LEVEL.items[0].at)  # D-306: no light refuses it
    assert on_light.items[-1].value == NEW[ItemKind.MARK] == 3.0
    over = placed(LEVEL, ItemKind.MARK, (15.0, 19.0))  # on the swimmer, on obstacles: a zone
    assert adjusted(over, 6, 99).items[6].value == SETTING[ItemKind.MARK].hi == 30.0
    assert adjusted(over, 6, -99).items[6].value == 0.5
    assert (over.arena.lights, over.arena.obstacles) == (LEVEL.arena.lights, LEVEL.arena.obstacles)


def test_the_last_of_a_kind_a_goal_aims_at_stays():
    goal = Goal(Verb.LEAVE, Count.ALL, Target.MARK)  # D-307
    ringed = replace(placed(LEVEL, ItemKind.MARK, (3.0, 3.0)), objectives=(goal,))
    with pytest.raises(Unmade, match="Leave the ring needs a ring: take the goal out first"):
        removed(ringed, 6)
    two = placed(ringed, ItemKind.MARK, (9.0, 9.0))
    assert len(removed(two, 6).marks) == 1  # one of two may go
