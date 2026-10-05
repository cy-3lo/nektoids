"""Objectives as sentences (D-023, D-038, D-040, D-097, D-307). objectives.py imports no pygame."""

import numpy as np
import pytest

from nektoids.editor.glyphs import GLYPH
from nektoids.graph.board import Board
from nektoids.levels.level import Item, ItemKind, Level
from nektoids.levels.objectives import (
    REACH,
    Count,
    Goal,
    Outcome,
    Target,
    Verb,
    begin,
    follow,
    objective_from_dict,
    objective_to_dict,
    outcome,
    reaching,
    reworded,
    sensible,
    settings,
    upgraded,
)
from nektoids.sim.arena import LIGHT_RADIUS

LIGHTS = (Item(ItemKind.LIGHT, (30.0, 20.0), 8.0), Item(ItemKind.LIGHT, (5.0, 5.0), 4.0))
EMPTY = Board(()).to_dict()
DT = 1.0 / 120.0
ONE = np.ones(1)
REACHED = REACH * (LIGHT_RADIUS + 1.0)  # centre to centre, for a body of radius 1
VISIT = Goal(Verb.REACH, Count.ALL, Target.LIGHT)  # version 1's "visit lights"
KEEP_OFF = Goal(Verb.REACH, Count.NONE, Target.LIGHT)  # ... "keep off"


def level(*goals, items=LIGHTS, time=10.0):
    return Level("Test", "", (10.0, 20.0, 0.0), tuple(items), EMPTY, time, goals)


def mark(x, y, r):
    return Item(ItemKind.MARK, (x, y), r)


def at(*points):
    return np.array(points, dtype=float).reshape(-1, 2)


LEVEL = level(VISIT)


def test_a_swimmer_reaches_a_light_at_1_05_times_touching_distance_and_not_before():
    assert REACHED == pytest.approx(2.1)  # 1.05 diameters, for a base body (D-029, D-043)
    near, far = REACHED - 1e-9, REACHED + 1e-9  # either side of the edge
    assert reaching(LEVEL, at([30.0 - near, 20.0]), ONE).tolist() == [[True, False]]
    assert reaching(LEVEL, at([30.0 - far, 20.0]), ONE).tolist() == [[False, False]]
    assert reaching(LEVEL, at([5.0, 5.0 + near]), 1.0 * ONE).tolist() == [[False, True]]
    assert reaching(LEVEL, at([5.0, 5.0 + near]), 0.5 * ONE).tolist() == [[False, False]]


def test_every_light_counts_once_and_all_of_them_are_needed():
    assert VISIT.count(np.array([[False, False]])) == (0, 2)
    assert VISIT.count(np.array([[True, False]])) == (1, 2)
    assert VISIT.count(np.array([[True, True]])) == (2, 2)
    assert VISIT.count(np.array([[True, False], [True, True]])) == (3, 4)  # two swimmers


def test_one_light_is_any_of_them_once():
    one = Goal(Verb.REACH, Count.ONE, Target.LIGHT)
    assert one.marks(LEVEL, at([5.0, 6.0], [20.0, 20.0]), np.ones(2)).tolist() == [[True], [False]]
    assert one.count(np.array([[True], [False]])) == (1, 2) and one.name(LEVEL) == "Reach a light"


def test_a_run_is_won_when_every_light_is_visited_and_over_when_its_time_is_up():
    one, both = (np.array([[True, False]]),), (np.array([[True, True]]),)  # one objective
    limit = round(LEVEL.time_limit / DT)
    assert outcome(LEVEL, one, limit - 1, DT) is None
    assert outcome(LEVEL, one, limit, DT) is Outcome.TIME_UP
    assert outcome(LEVEL, both, 5, DT) is Outcome.WON
    assert outcome(LEVEL, both, limit, DT) is Outcome.WON  # on the last tick, it still counts


def test_a_level_without_objectives_is_never_won_only_timed_out():
    bare = level(time=1.0)
    assert outcome(bare, (), 0, DT) is None
    assert outcome(bare, (), 120, DT) is Outcome.TIME_UP


def test_leaving_every_mark_marks_a_swimmer_once_it_is_out_of_all_of_them_at_once():
    leave = Goal(Verb.LEAVE, Count.ALL, Target.MARK)  # version 1's "leave ring", round a light
    alone = level(leave, items=(*LIGHTS[:1], mark(20.0, 19.0, 12.0)))
    assert leave.marks(alone, at([25.0, 19.0], [32.5, 19.0]), np.ones(2)).tolist() == [
        [False],
        [True],
    ]
    assert leave.count(np.array([[False], [True]])) == (1, 2)
    two = level(leave, items=(*LIGHTS, mark(30.0, 20.0, 12.0), mark(5.0, 5.0, 12.0)))
    assert leave.marks(two, at([18.0, 20.0]), ONE).tolist() == [[False]]  # out of one only
    assert Goal(Verb.LEAVE, Count.ONE, Target.MARK).marks(two, at([18.0, 20.0]), ONE).tolist() == [
        [True]
    ]


def test_the_run_latches_each_objectives_marks_and_wins_when_all_are_met():
    leave = Goal(Verb.LEAVE, Count.ALL, Target.MARK)
    both = level(VISIT, leave, items=(*LIGHTS, mark(30.0, 20.0, 2.0)))
    near_first = begin(both, at([28.0, 20.0]), ONE)
    assert [m.tolist() for m in near_first] == [[[True, False]], [[False]]]
    later = follow(both, near_first, at([20.0, 20.0]), ONE, DT)  # away again: still visited
    assert [m.tolist() for m in later] == [[[True, False]], [[True]]]
    assert outcome(both, later, 1, DT) is None  # the second light is still to visit
    done = follow(both, later, at([5.0, 7.0]), ONE, DT)
    assert outcome(both, done, 2, DT) is Outcome.WON


def test_staying_in_a_mark_counts_the_time_in_a_row_inside_it_and_keeps_it_once_full():
    stay = Goal(Verb.STAY, Count.ONE, Target.MARK, seconds=0.5)  # version 1's "stay near"
    alone = level(stay, items=(*LIGHTS[:1], mark(20.0, 19.0, 6.0)))
    inside, outside = at([26.0, 19.0]), at([26.0 + 1e-9, 19.0])  # on the rim, and just out
    assert stay.marks(alone, inside, ONE).tolist() == [[True]]
    assert stay.marks(alone, outside, ONE).tolist() == [[False]]
    kept = stay.start(stay.marks(alone, inside, ONE))
    assert kept.tolist() == [[0.0]]  # nothing yet at t = 0
    for _ in range(30):
        kept = stay.keep(kept, stay.marks(alone, inside, ONE), DT)
    assert stay.count(kept) == (0, 1) and stay.progress(kept) == pytest.approx(0.5)
    kept = stay.keep(kept, stay.marks(alone, outside, ONE), DT)  # out: back to nothing
    assert kept.tolist() == [[0.0]] and stay.progress(kept) == 0.0
    for _ in range(60):
        kept = stay.keep(kept, stay.marks(alone, inside, ONE), DT)
    assert stay.count(kept) == (1, 1) and stay.progress(kept) == 1.0  # 60 ticks of 1/120 s
    kept = stay.keep(kept, stay.marks(alone, outside, ONE), DT)
    assert stay.count(kept) == (1, 1) and not stay.lost(kept)  # once met, it stays met


def test_touching_a_light_breaks_the_ban_and_loses_the_run_whatever_else_stands():
    off = level(KEEP_OFF)
    clear = begin(off, at([20.0, 20.0]), ONE)
    assert KEEP_OFF.count(clear[0]) == (1, 1) and not KEEP_OFF.lost(clear[0])
    assert outcome(off, clear, 1, DT) is Outcome.WON  # alone, met from the start
    touched = follow(off, clear, at([30.0 - REACHED + 1e-9, 20.0]), ONE, DT)  # just in
    away = follow(off, touched, at([20.0, 20.0]), ONE, DT)  # gone again: it still touched
    assert KEEP_OFF.count(away[0]) == (0, 1) and KEEP_OFF.lost(away[0])
    limit = round(off.time_limit / DT)
    assert outcome(off, away, 2, DT) is outcome(off, away, limit, DT) is Outcome.LOST


def test_obstacles_are_touched_as_lights_are_and_marks_entered_by_the_swimmers_centre():
    rock = Item(ItemKind.OBSTACLE, (20.0, 10.0), 2.0)
    rocks = level(items=(*LIGHTS, rock, mark(20.0, 30.0, 4.0)))
    touch = Goal(Verb.REACH, Count.ALL, Target.OBSTACLE)
    edge = REACH * (2.0 + 1.0)  # an obstacle's radius and the swimmer's, a little short
    assert touch.marks(rocks, at([20.0, 10.0 + edge - 1e-9]), ONE).tolist() == [[True]]
    assert touch.marks(rocks, at([20.0, 10.0 + edge + 1e-9]), ONE).tolist() == [[False]]
    enter = Goal(Verb.REACH, Count.ALL, Target.MARK)
    assert enter.marks(rocks, at([20.0, 34.0]), ONE).tolist() == [[True]]  # its centre on it
    assert enter.marks(rocks, at([20.0, 34.0 + 1e-9]), ONE).tolist() == [[False]]
    out = Goal(Verb.REACH, Count.NONE, Target.MARK)  # keep out of the rings: a ban
    kept = out.start(out.marks(rocks, at([20.0, 40.0]), ONE))
    assert not out.lost(kept) and out.lost(
        out.keep(kept, out.marks(rocks, at([20.0, 31.0]), ONE), DT)
    )
    inside = Goal(Verb.LEAVE, Count.NONE, Target.MARK)  # never get out
    kept = inside.start(inside.marks(rocks, at([20.0, 31.0]), ONE))
    assert not inside.lost(kept) and inside.lost(
        inside.keep(kept, inside.marks(rocks, at([20.0, 40.0]), ONE), DT)
    )


def test_a_sentence_must_say_something_a_run_can_count():
    assert sensible(Verb.REACH, Count.NONE, Target.OBSTACLE) is None
    assert "ring" in sensible(Verb.LEAVE, Count.ALL, Target.LIGHT)  # leave and stay: marks
    assert "ring" in sensible(Verb.STAY, Count.ONE, Target.OBSTACLE)
    assert "none" in sensible(Verb.STAY, Count.NONE, Target.MARK)  # a ban on staying: no
    assert "none" in sensible(Verb.CIRCLE, Count.NONE, Target.LIGHT)
    with pytest.raises(ValueError, match="a ring, not a light"):
        Goal(Verb.LEAVE, Count.ALL, Target.LIGHT)
    with pytest.raises(ValueError, match="takes no turns"):
        Goal(Verb.STAY, Count.ONE, Target.MARK, turns=2)
    assert Goal(Verb.STAY, Count.ONE, Target.MARK).seconds == 5.0  # its setting's default
    assert Goal(Verb.CIRCLE, Count.ONE, Target.LIGHT).turns == 2 and VISIT.seconds is None
    assert [n for n, _ in settings(Goal(Verb.CIRCLE, Count.ALL, Target.MARK))] == ["turns"]


def test_a_word_chosen_moves_the_others_as_little_as_makes_the_sentence_say_something():
    stay = Goal(Verb.STAY, Count.ONE, Target.MARK, seconds=12.0)
    assert reworded(VISIT, Verb.LEAVE) == Goal(Verb.LEAVE, Count.ALL, Target.MARK)  # onto marks
    assert reworded(KEEP_OFF, Verb.STAY) == Goal(Verb.STAY, Count.ONE, Target.MARK)  # not none
    assert reworded(KEEP_OFF, Verb.CIRCLE) == Goal(Verb.CIRCLE, Count.ONE, Target.LIGHT)
    assert reworded(stay, Count.NONE) == Goal(Verb.REACH, Count.NONE, Target.MARK)  # to reach
    assert reworded(stay, Target.LIGHT) == Goal(Verb.REACH, Count.ONE, Target.LIGHT)
    assert reworded(stay, Count.ALL) == Goal(Verb.STAY, Count.ALL, Target.MARK, seconds=12.0)
    assert reworded(stay, Verb.CIRCLE).turns == 2 and reworded(stay, Verb.STAY) == stay
    assert reworded(VISIT, Target.OBSTACLE) == Goal(Verb.REACH, Count.ALL, Target.OBSTACLE)
    for word in (*Verb, *Count, *Target):  # whatever the sentence, whatever the word
        for goal in (VISIT, KEEP_OFF, stay, Goal(Verb.CIRCLE, Count.ALL, Target.OBSTACLE)):
            again = reworded(goal, word)
            assert word in (again.verb, again.many, again.target)


def test_version_1s_five_objectives_keep_their_names_but_the_stay_whose_ring_is_any_mark():
    alone = level(items=(LIGHTS[0], mark(30.0, 20.0, 12.0)))  # one light, one ring: as shipped
    names = [g.name(alone) for g in (VISIT, KEEP_OFF)]
    assert names == ["Visit every light", "Don't touch the light"]
    assert Goal(Verb.LEAVE, Count.ALL, Target.MARK).name(alone) == "Leave the ring"
    assert Goal(Verb.CIRCLE, Count.ONE, Target.LIGHT).name(alone) == "Circle the light"
    assert Goal(Verb.STAY, Count.ONE, Target.MARK).name(alone) == "Stay in a ring"
    assert KEEP_OFF.broken(alone) == "It touched the light" and VISIT.broken(alone) == "Lost"
    assert Goal(Verb.CIRCLE, Count.ONE, Target.LIGHT, turns=3).about(alone) == (
        "Go round the light 3 times, either way."
    )


def test_a_name_says_the_light_only_where_the_level_has_one():
    two = level(items=(*LIGHTS, mark(30.0, 20.0, 12.0), mark(5.0, 5.0, 6.0)))  # two of each
    assert KEEP_OFF.name(two) == "Touch no light" and VISIT.name(two) == "Visit every light"
    assert Goal(Verb.LEAVE, Count.ALL, Target.MARK).name(two) == "Leave every ring"
    assert Goal(Verb.CIRCLE, Count.ONE, Target.LIGHT).name(two) == "Circle a light"
    assert Goal(Verb.LEAVE, Count.NONE, Target.MARK).name(two) == "Stay inside the rings"
    assert KEEP_OFF.broken(two) == "It touched a light"
    assert Goal(Verb.CIRCLE, Count.ONE, Target.LIGHT, turns=1).about(two) == (
        "Go round a light 1 time, either way."
    )
    one_ring = level(items=(*LIGHTS, mark(30.0, 20.0, 12.0)))
    assert Goal(Verb.LEAVE, Count.NONE, Target.MARK).name(one_ring) == "Stay inside the ring"
    assert Goal(Verb.REACH, Count.NONE, Target.MARK).broken(one_ring) == "It went into a ring"
    assert Goal(Verb.LEAVE, Count.NONE, Target.MARK).about(one_ring) == (
        "Getting out of the ring loses the run at once."
    )


def test_every_sentence_has_a_name_an_icon_the_font_has_and_an_info_text():
    for verb in Verb:
        for many in Count:
            for target in Target:
                if sensible(verb, many, target) is None:
                    goal = Goal(verb, many, target)
                    for where in (LEVEL, level(items=(*LIGHTS, mark(0.0, 0.0, 3.0)))):
                        assert goal.name(where) and goal.about(where), goal
                        assert goal.broken(where), goal
                    assert goal.icon in GLYPH, goal


def test_an_objective_comes_back_from_its_data_with_its_setting():
    stay = Goal(Verb.STAY, Count.ONE, Target.MARK, seconds=5.0)
    assert objective_to_dict(stay) == {
        "verb": "stay",
        "count": "one",
        "target": "mark",
        "seconds": 5.0,
    }
    assert objective_to_dict(VISIT) == {"verb": "reach", "count": "all", "target": "light"}
    for goal in (stay, VISIT, KEEP_OFF, Goal(Verb.CIRCLE, Count.ALL, Target.OBSTACLE, turns=3)):
        assert objective_from_dict(objective_to_dict(goal)) == goal
    with pytest.raises(ValueError, match="takes no 'kind'"):
        objective_from_dict({"kind": "visit lights"})  # version 2's: upgraded, never read
    with pytest.raises(ValueError, match="needs its target"):
        objective_from_dict({"verb": "reach", "count": "all"})


def test_version_2s_objectives_become_sentences_and_their_rings_marks_on_every_light():
    lights = [[20.0, 19.0], [5.0, 5.0]]
    goals, marks = upgraded([{"kind": "leave ring", "radius": 12.0}, {"kind": "keep off"}], lights)
    assert goals == [
        {"verb": "leave", "count": "all", "target": "mark"},
        {"verb": "reach", "count": "none", "target": "light"},
    ]
    assert marks == [{"kind": "mark", "at": at_, "radius": 12.0} for at_ in lights]
    goals, marks = upgraded(
        [{"kind": "stay near"}, {"kind": "circle light", "turns": 3}], lights[:1]
    )
    assert goals == [
        {"verb": "stay", "count": "one", "target": "mark", "seconds": 5.0},
        {"verb": "circle", "count": "one", "target": "light", "turns": 3},
    ]
    assert marks == [{"kind": "mark", "at": [20.0, 19.0], "radius": 6.0}]  # its default ring
    with pytest.raises(ValueError, match="two sizes"):
        upgraded([{"kind": "leave ring"}, {"kind": "stay near"}], lights)
    with pytest.raises(ValueError, match="takes no 'seconds'"):
        upgraded([{"kind": "visit lights", "seconds": 1.0}], lights)


def going_round(goal, angles, where, centre=(30.0, 20.0), radius=5.0):
    """What `goal` keeps for a swimmer taken round `centre` through `angles` [rad] in `where`."""
    points = [at([centre[0] + radius * np.cos(a), centre[1] + radius * np.sin(a)]) for a in angles]
    kept = goal.start(goal.marks(where, points[0], ONE))
    for point in points[1:]:
        kept = goal.keep(kept, goal.marks(where, point, ONE), DT)
    return kept


def test_circling_the_light_counts_whole_turns_either_way_and_going_back_unwinds_them():
    circle = Goal(Verb.CIRCLE, Count.ONE, Target.LIGHT, turns=2)  # D-097
    step = 0.05  # [rad] a tick's turn, far less than half a turn
    once = going_round(circle, np.arange(0.0, 2 * np.pi + step, step), LEVEL)
    assert circle.count(once) == (1, 2) and 0.5 <= circle.progress(once) < 0.55
    twice = going_round(circle, -np.arange(0.0, 4 * np.pi + step, step), LEVEL)  # clockwise
    assert circle.count(twice) == (2, 2) and circle.progress(twice) == 1.0
    there_and_back = np.concatenate((np.arange(0.0, 6.0, step), np.arange(6.0, 0.0, -step)))
    back = going_round(circle, there_and_back, LEVEL)
    assert circle.count(back) == (0, 2) and circle.progress(back) < 0.01
    full = np.arange(0.0, 4 * np.pi + step, step)
    then_back = going_round(
        circle, np.concatenate((full, full[-1] - np.arange(0.0, 3.0, step))), LEVEL
    )
    assert circle.count(then_back) == (2, 2)  # once the turns are made, going back keeps them
    beside = going_round(circle, np.arange(0.0, 4 * np.pi, step), LEVEL, (15.0, 20.0), 3.0)
    assert circle.count(beside) == (0, 2)  # round a point beside the lights: no turn of theirs
    assert not circle.lost(twice)
    every = Goal(Verb.CIRCLE, Count.ALL, Target.LIGHT, turns=2)
    assert every.count(going_round(every, full, LEVEL)) == (2, 4)  # one light gone round of two


def test_circling_the_light_twice_wins_a_level_unless_it_touches_the_light():
    orbit = level(Goal(Verb.CIRCLE, Count.ONE, Target.LIGHT), KEEP_OFF, time=30.0)
    path = [(30.0 + 5.0 * np.cos(a), 20.0 + 5.0 * np.sin(a)) for a in np.arange(0.0, 13.0, 0.05)]
    kept = begin(orbit, at(path[0]), ONE)
    for tick, point in enumerate(path[1:], start=1):
        kept = follow(orbit, kept, at(point), ONE, DT)
        if outcome(orbit, kept, tick, DT) is not None:
            break
    assert outcome(orbit, kept, tick, DT) is Outcome.WON and tick * 0.05 >= 4 * np.pi
    touched = follow(orbit, kept, at([30.0, 20.0]), ONE, DT)
    assert outcome(orbit, touched, tick + 1, DT) is Outcome.LOST  # touching still loses
