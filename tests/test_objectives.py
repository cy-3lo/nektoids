import numpy as np

from nektoids.graph.board import Board
from nektoids.levels.level import Item, ItemKind, Level
from nektoids.levels.objectives import Outcome, VisitLights, outcome, touching
from nektoids.sim.arena import LIGHT_RADIUS, Arena, Light

ARENA = Arena(lights=(Light(30.0, 20.0, 8.0), Light(5.0, 5.0, 4.0)))
LIGHTS = (Item(ItemKind.LIGHT, (30.0, 20.0), 8.0), Item(ItemKind.LIGHT, (5.0, 5.0), 4.0))
EMPTY = Board(()).to_dict()
LEVEL = Level("Two", "", (10.0, 20.0, 0.0), LIGHTS, EMPTY, 10.0, (VisitLights(),))
DT = 1.0 / 120.0
ONE = np.ones(1)
TOUCH = LIGHT_RADIUS + 1.0  # centre to centre, for a body of radius 1


def at(*points):
    return np.array(points, dtype=float).reshape(-1, 2)


def test_a_swimmer_touches_a_light_when_their_discs_meet_and_not_before():
    assert touching(ARENA, at([30.0 - TOUCH, 20.0]), ONE).tolist() == [[True, False]]
    assert touching(ARENA, at([30.0 - TOUCH - 1e-9, 20.0]), ONE).tolist() == [[False, False]]
    assert touching(ARENA, at([5.0, 5.0 + TOUCH]), 1.0 * ONE).tolist() == [[False, True]]
    assert touching(ARENA, at([5.0, 5.0 + TOUCH]), 0.5 * ONE).tolist() == [[False, False]]


def test_every_light_counts_once_and_all_of_them_are_needed():
    visits = VisitLights()
    assert visits.count(np.array([[False, False]])) == (0, 2)
    assert visits.count(np.array([[True, False]])) == (1, 2)
    assert visits.count(np.array([[True, True]])) == (2, 2)
    assert visits.count(np.array([[True, False], [True, True]])) == (3, 4)  # two swimmers


def test_a_run_is_won_when_every_light_is_visited_and_over_when_its_time_is_up():
    one, both = np.array([[True, False]]), np.array([[True, True]])
    limit = round(LEVEL.time_limit / DT)
    assert outcome(LEVEL, one, limit - 1, DT) is None
    assert outcome(LEVEL, one, limit, DT) is Outcome.TIME_UP
    assert outcome(LEVEL, both, 5, DT) is Outcome.WON
    assert outcome(LEVEL, both, limit, DT) is Outcome.WON  # on the last tick, it still counts


def test_a_level_without_objectives_is_never_won_only_timed_out():
    bare = Level("Bare", "", (10.0, 20.0, 0.0), LIGHTS, EMPTY, time_limit=1.0)
    assert outcome(bare, np.array([[True, True]]), 0, DT) is None
    assert outcome(bare, np.array([[True, True]]), 120, DT) is Outcome.TIME_UP
