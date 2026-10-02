import numpy as np
import pytest

from nektoids.graph.board import Board
from nektoids.levels.level import Item, ItemKind, Level
from nektoids.levels.objectives import (
    REACH,
    KeepOff,
    LeaveRing,
    Outcome,
    StayNear,
    VisitLights,
    begin,
    follow,
    objective_from_dict,
    objective_to_dict,
    outcome,
    reaching,
)
from nektoids.sim.arena import LIGHT_RADIUS, Arena, Light

ARENA = Arena(lights=(Light(30.0, 20.0, 8.0), Light(5.0, 5.0, 4.0)))
LIGHTS = (Item(ItemKind.LIGHT, (30.0, 20.0), 8.0), Item(ItemKind.LIGHT, (5.0, 5.0), 4.0))
EMPTY = Board(()).to_dict()
LEVEL = Level("Two", "", (10.0, 20.0, 0.0), LIGHTS, EMPTY, 10.0, (VisitLights(),))
DT = 1.0 / 120.0
ONE = np.ones(1)
REACHED = REACH * (LIGHT_RADIUS + 1.0)  # centre to centre, for a body of radius 1


def at(*points):
    return np.array(points, dtype=float).reshape(-1, 2)


def test_a_swimmer_reaches_a_light_at_1_05_times_touching_distance_and_not_before():
    assert REACHED == pytest.approx(2.1)  # 1.05 diameters, for a base body (D-029, D-043)
    near, far = REACHED - 1e-9, REACHED + 1e-9  # either side of the edge
    assert reaching(ARENA, at([30.0 - near, 20.0]), ONE).tolist() == [[True, False]]
    assert reaching(ARENA, at([30.0 - far, 20.0]), ONE).tolist() == [[False, False]]
    assert reaching(ARENA, at([5.0, 5.0 + near]), 1.0 * ONE).tolist() == [[False, True]]
    assert reaching(ARENA, at([5.0, 5.0 + near]), 0.5 * ONE).tolist() == [[False, False]]


def test_every_light_counts_once_and_all_of_them_are_needed():
    visits = VisitLights()
    assert visits.count(np.array([[False, False]])) == (0, 2)
    assert visits.count(np.array([[True, False]])) == (1, 2)
    assert visits.count(np.array([[True, True]])) == (2, 2)
    assert visits.count(np.array([[True, False], [True, True]])) == (3, 4)  # two swimmers


def test_a_run_is_won_when_every_light_is_visited_and_over_when_its_time_is_up():
    one, both = (np.array([[True, False]]),), (np.array([[True, True]]),)  # one objective
    limit = round(LEVEL.time_limit / DT)
    assert outcome(LEVEL, one, limit - 1, DT) is None
    assert outcome(LEVEL, one, limit, DT) is Outcome.TIME_UP
    assert outcome(LEVEL, both, 5, DT) is Outcome.WON
    assert outcome(LEVEL, both, limit, DT) is Outcome.WON  # on the last tick, it still counts


def test_a_level_without_objectives_is_never_won_only_timed_out():
    bare = Level("Bare", "", (10.0, 20.0, 0.0), LIGHTS, EMPTY, time_limit=1.0)
    assert outcome(bare, (), 0, DT) is None
    assert outcome(bare, (), 120, DT) is Outcome.TIME_UP


def test_leaving_the_ring_marks_a_swimmer_once_it_is_farther_than_the_radius_from_every_light():
    ring = LeaveRing(radius=12.0)
    alone = Arena(lights=(Light(20.0, 19.0, 8.0),))
    assert ring.marks(alone, at([25.0, 19.0], [32.5, 19.0]), np.ones(2)).tolist() == [
        [False],
        [True],
    ]
    assert ring.count(np.array([[False], [True]])) == (1, 2)
    two = ring.marks(ARENA, at([18.0, 20.0]), ONE)  # 12 from one light, 19.2 from the other
    assert two.tolist() == [[False]]  # out of a ring means out of all of them


def test_the_run_latches_each_objectives_marks_and_wins_when_all_are_met():
    level = Level(
        "Both", "", (10.0, 20.0, 0.0), LIGHTS, EMPTY, 10.0, (VisitLights(), LeaveRing(radius=2.0))
    )
    near_first = begin(level, at([28.0, 20.0]), ONE)
    assert [m.tolist() for m in near_first] == [[[True, False]], [[False]]]
    later = follow(level, near_first, at([20.0, 20.0]), ONE, DT)  # away again: still visited
    assert [m.tolist() for m in later] == [[[True, False]], [[True]]]
    assert outcome(level, later, 1, DT) is None  # the second light is still to visit
    done = follow(level, later, at([5.0, 7.0]), ONE, DT)
    assert outcome(level, done, 2, DT) is Outcome.WON


def test_staying_by_the_light_counts_the_time_in_a_row_inside_its_ring_and_keeps_it_once_full():
    stay, alone = StayNear(radius=6.0, seconds=0.5), Arena(lights=(Light(20.0, 19.0, 8.0),))
    inside, outside = at([26.0, 19.0]), at([26.0 + 1e-9, 19.0])  # on the ring, and just out
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


def test_touching_the_light_breaks_keep_off_and_loses_the_run_whatever_else_stands():
    keep_off, level = (
        KeepOff(),
        Level("Off", "", (10.0, 20.0, 0.0), LIGHTS, EMPTY, 10.0, (KeepOff(),)),
    )
    clear = begin(level, at([20.0, 20.0]), ONE)
    assert keep_off.count(clear[0]) == (1, 1) and not keep_off.lost(clear[0])
    assert outcome(level, clear, 1, DT) is Outcome.WON  # alone, met from the start
    touched = follow(level, clear, at([30.0 - REACHED + 1e-9, 20.0]), ONE, DT)  # just in
    away = follow(level, touched, at([20.0, 20.0]), ONE, DT)  # gone again: it still touched
    assert keep_off.count(away[0]) == (0, 1) and keep_off.lost(away[0])
    limit = round(level.time_limit / DT)
    assert outcome(level, away, 2, DT) is outcome(level, away, limit, DT) is Outcome.LOST


def test_an_objective_comes_back_from_its_data_with_its_settings():
    assert objective_to_dict(LeaveRing(radius=10.0)) == {"kind": "leave ring", "radius": 10.0}
    assert objective_from_dict({"kind": "leave ring", "radius": 10.0}) == LeaveRing(radius=10.0)
    assert objective_from_dict({"kind": "visit lights"}) == VisitLights()
    stay = StayNear(radius=6.0, seconds=5.0)
    assert objective_to_dict(stay) == {"kind": "stay near", "radius": 6.0, "seconds": 5.0}
    assert objective_from_dict(objective_to_dict(stay)) == stay
    assert objective_from_dict({"kind": "keep off"}) == KeepOff()
