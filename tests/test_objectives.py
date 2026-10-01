import numpy as np
import pytest

from nektoids.levels.objectives import ReachLight
from nektoids.sim.arena import LIGHT_RADIUS, Arena, Light

ARENA = Arena(40.0, 38.0, lights=(Light(30.0, 20.0, 8.0), Light(5.0, 5.0, 4.0)))
START = np.array([[10.0, 20.0]])  # 20 from the first light, 15.8 from the second
ONE = np.ones(1)


def reach(pos) -> float:
    return ReachLight().progress(ARENA, START, np.array(pos, dtype=float).reshape(-1, 2), ONE)


def test_at_the_start_nothing_is_done_and_touching_the_nearest_light_is_all_of_it():
    assert reach([10.0, 20.0]) == 0.0
    touch = LIGHT_RADIUS + 1.0
    assert reach([5.0 + touch, 5.0]) == 1.0
    assert reach([30.0 - touch, 20.0]) == 1.0  # any light will do


def test_the_bar_fills_in_proportion_to_the_way_covered_and_never_goes_below_zero():
    begun = np.hypot(5.0, 15.0) - LIGHT_RADIUS - 1.0  # to touching the nearest light
    halfway = np.array([5.0, 5.0]) + (START[0] - [5.0, 5.0]) * (
        (LIGHT_RADIUS + 1.0 + begun / 2) / np.hypot(5.0, 15.0)
    )
    assert reach(halfway) == pytest.approx(0.5)
    assert reach([1.0, 37.0]) == 0.0  # further than at the start


def test_several_swimmers_average_and_an_arena_without_lights_gives_nothing():
    two = ReachLight().progress(
        ARENA, np.repeat(START, 2, axis=0), np.array([[10.0, 20.0], [7.0, 5.0]]), np.ones(2)
    )
    assert two == pytest.approx(0.5)
    assert ReachLight().progress(Arena(40.0, 38.0), START, START, ONE) == 0.0
