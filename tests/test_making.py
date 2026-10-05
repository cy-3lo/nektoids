"""A level made by hand (D-301). making.py imports no pygame."""

import json
from dataclasses import replace

import pytest

from nektoids.levels.arenas import arenas, sandbox
from nektoids.levels.level import Item, ItemKind, Level, to_json
from nektoids.levels.making import (
    BLANK_TIME,
    GOALS_MOST,
    NEW,
    SETTING,
    SPEC_LONGEST,
    TIME,
    TITLE_LONGEST,
    Unmade,
    adjusted,
    blank,
    goal_added,
    goal_removed,
    goal_set,
    goal_worded,
    lacks,
    moved,
    number,
    pasted,
    placed,
    removed,
    specified,
    start_moved,
    taken,
    timed,
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
    assert moved(LEVEL, light, (12.74, 3.1)).items[light].at == (13.0, 3.0)  # whole u, D-311
    assert adjusted(LEVEL, light, 3).items[light].value == 11.0
    assert adjusted(LEVEL, light, 99).items[light].value == SETTING[ItemKind.LIGHT].hi
    obstacle = 2  # radius 1
    assert adjusted(LEVEL, obstacle, -1).items[obstacle].value == 1.0  # no smaller
    assert adjusted(LEVEL, obstacle, 2).items[obstacle].value == 3.0
    assert adjusted(LEVEL, obstacle, 9).items[obstacle].value == 5.0  # no bigger


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
    assert start_moved(LEVEL, (4.3, 4.8)).start == (4.0, 5.0, 20.0)
    assert turned(LEVEL, 1).start[2] == 30.0  # 35, onto the lattice: touched, it snaps
    assert turned(turned(LEVEL, 1), 1).start[2] == 45.0
    assert turned(turned(LEVEL, -1), -1).start[2] == 345.0  # 5, then -10: within [0, 360)
    assert turned(replace(LEVEL, start=(0.0, 0.0, 345.0)), 1).start[2] == 0.0


def test_a_made_level_reads_back_as_written_by_to_json():
    made = turned(placed(start_moved(LEVEL, (3.0, 4.5)), ItemKind.OBSTACLE, (12.0, 4.0)), -2)
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


def test_a_mark_goes_anywhere_its_radius_from_one_unit_to_thirty():
    on_light = placed(LEVEL, ItemKind.MARK, LEVEL.items[0].at)  # D-306: no light refuses it
    assert on_light.items[-1].value == NEW[ItemKind.MARK] == 1.0  # the least (D-314)
    over = placed(LEVEL, ItemKind.MARK, (15.0, 19.0))  # on the swimmer, on obstacles: a zone
    assert adjusted(over, 6, 99).items[6].value == SETTING[ItemKind.MARK].hi == 30.0
    assert adjusted(over, 6, -99).items[6].value == 1.0
    assert (over.arena.lights, over.arena.obstacles) == (LEVEL.arena.lights, LEVEL.arena.obstacles)


def test_the_last_of_a_kind_a_goal_aims_at_stays():
    goal = Goal(Verb.LEAVE, Count.ALL, Target.MARK)  # D-307
    ringed = replace(placed(LEVEL, ItemKind.MARK, (3.0, 3.0)), objectives=(goal,))
    with pytest.raises(Unmade, match="Leave every ring needs a ring: take the goal out first"):
        removed(ringed, 6)
    two = placed(ringed, ItemKind.MARK, (9.0, 9.0))
    assert len(removed(two, 6).marks) == 1  # one of two may go


def test_the_time_allowed_sits_on_five_second_steps_from_five_seconds_to_two_minutes():
    assert LEVEL.time_limit == 120.0 and timed(LEVEL, 42.0).time_limit == 40.0
    assert timed(LEVEL, 0.0).time_limit == TIME.lo == 5.0
    assert timed(LEVEL, 999.0).time_limit == TIME.hi == 120.0  # D-311


def test_a_goal_added_is_the_first_sentence_the_level_can_hold_and_does_not_ask_two_at_most():
    one = goal_added(LEVEL)  # the sandbox asks nothing; it has lights and obstacles, no mark
    assert one.objectives == (Goal(Verb.REACH, Count.ALL, Target.LIGHT),) and not LEVEL.objectives
    two = goal_added(one)
    assert two.objectives[1] == Goal(Verb.REACH, Count.ALL, Target.OBSTACLE)
    assert len(two.objectives) == GOALS_MOST
    with pytest.raises(Unmade, match="2 goals at most"):
        goal_added(two)
    assert goal_removed(two, 0).objectives == two.objectives[1:]
    marks_only = replace(LEVEL, items=(Item(ItemKind.MARK, (3.0, 3.0), 3.0),))
    assert goal_added(marks_only).objectives[0] == Goal(Verb.REACH, Count.ALL, Target.MARK)
    with pytest.raises(Unmade, match="place a light, an obstacle or a mark first"):
        goal_added(replace(LEVEL, items=()))


def test_a_word_chosen_rewords_the_goal_unless_it_would_aim_at_nothing_or_ask_twice():
    two = goal_added(goal_added(LEVEL))  # reach every light, reach every obstacle
    assert goal_worded(two, 0, Count.NONE).objectives[0] == Goal(
        Verb.REACH, Count.NONE, Target.LIGHT
    )
    assert lacks(two, 0, Count.NONE) is None and lacks(two, 0, Target.MARK) is not None
    for word in (Target.MARK, Verb.LEAVE, Verb.STAY):  # each would aim at marks: there are none
        assert lacks(two, 0, word) == "the level has no mark: place one in Objects"
        with pytest.raises(Unmade, match="no mark"):
            goal_worded(two, 0, word)
    with pytest.raises(Unmade, match="asks that already"):
        goal_worded(two, 1, Target.LIGHT)
    assert goal_worded(two, 1, Target.OBSTACLE) == two  # the word it has: nothing changes
    ringed = placed(two, ItemKind.MARK, (3.0, 3.0))
    assert goal_worded(ringed, 0, Verb.STAY).objectives[0] == Goal(
        Verb.STAY, Count.ALL, Target.MARK
    )


def test_a_stays_seconds_sit_on_their_range_and_a_verb_without_a_setting_has_none():
    ringed = placed(LEVEL, ItemKind.MARK, (3.0, 3.0))
    stay = replace(ringed, objectives=(Goal(Verb.STAY, Count.ONE, Target.MARK),))
    assert goal_set(stay, 0, 12.4).objectives[0].seconds == 12.0
    assert goal_set(stay, 0, 99.0).objectives[0].seconds == 60.0
    assert goal_set(stay, 0, 0.0).objectives[0].seconds == 1.0 and stay.objectives[0].seconds == 5
    with pytest.raises(ValueError, match="no setting"):
        goal_set(goal_added(LEVEL), 0, 3.0)


def test_a_level_with_goals_made_reads_back_as_written_by_to_json():
    ringed = placed(goal_added(LEVEL), ItemKind.MARK, (3.0, 3.0))
    made = goal_set(goal_worded(timed(ringed, 35.0), 0, Verb.STAY), 0, 8.0)
    text = to_json(made)
    again = Level.from_dict(json.loads(text))
    assert again == made and again.objectives[0].seconds == 8.0 and again.time_limit == 35.0


def test_a_sliders_box_takes_a_number_typed_and_refuses_anything_else():
    assert number("35") == 35.0 and number("12.5") == 12.5 and number("007") == 7.0
    for text in ("", ".", "1.2.3", "inf"):
        with pytest.raises(Unmade, match="type a number"):
            number(text)
    assert timed(LEVEL, number("42")).time_limit == 40.0  # then onto the slider's steps


def test_a_level_copied_as_text_is_pasted_back_as_it_was():
    made = goal_set(
        goal_worded(placed(goal_added(LEVEL), ItemKind.MARK, (3.0, 3.0)), 0, Verb.STAY), 0, 8
    )
    made = titled(timed(turned(made, 2), 45.0), "Made")
    assert pasted(LEVEL, to_json(made)) == made  # D-310
    assert pasted(made, to_json(LEVEL)) == LEVEL  # and back: one step for undo each way


def test_a_shipped_level_pasted_brings_its_plane_goals_and_time_but_not_its_board():
    fear = arenas()[0]  # its tutorial, its passkey, its hints, a board of its own
    made = pasted(LEVEL, to_json(fear))
    assert (made.title, made.spec, made.start) == (fear.title, fear.spec, fear.start)
    assert (made.items, made.objectives, made.time_limit) == (
        fear.items,
        fear.objectives,
        fear.time_limit,
    )
    assert made.board == LEVEL.board and made.board != fear.board  # the Maker sets no board yet
    assert made.tutorial is None and made.passkey is None and made.hints is None
    assert fear.tutorial is not None and fear.passkey is not None


def test_a_text_no_level_could_hold_is_refused_with_its_reason():
    text = json.loads(to_json(LEVEL))
    for given, why in (
        ("  ", "paste a level's text into the field first"),
        ("{", "not JSON"),
        ("[1, 2]", "without its version"),
        ("12", "not a level's text"),
        (json.dumps({**text, "version": 9}), "version 9"),
        (json.dumps({**text, "colour": "red"}), "takes no 'colour'"),
        (json.dumps({k: v for k, v in text.items() if k != "title"}), "no 'title'"),
        (json.dumps({**text, "title": "   "}), "needs a title"),
        (json.dumps({**text, "start": {"at": [21.0, 21.0], "heading": 0}}), "inside an obstacle"),
    ):
        with pytest.raises(Unmade, match=why):
            pasted(LEVEL, given)


def test_a_blank_plane_has_no_item_no_goal_and_the_swimmer_at_the_origin_on_the_same_board():
    made = blank(goal_added(LEVEL))  # D-310
    assert (made.items, made.objectives, made.start) == ((), (), (0.0, 0.0, 0.0))
    assert made.time_limit == BLANK_TIME and made.title == "New level" and made.spec
    assert made.board == LEVEL.board and pasted(LEVEL, to_json(made)) == made


def test_every_shipped_level_may_be_started_from_its_plane_goals_and_time_on_the_same_board():
    for level in (*arenas(), sandbox()):
        made = taken(blank(LEVEL), level)
        assert (made.title, made.items, made.objectives) == (
            level.title,
            level.items,
            level.objectives,
        )
        assert made.board == LEVEL.board and made.tutorial is None
