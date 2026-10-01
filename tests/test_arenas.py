import math

import pytest

from nektoids.levels.arenas import arenas
from nektoids.levels.objectives import REACH
from nektoids.sim.arena import BASE_RADIUS, LIGHT_RADIUS


@pytest.mark.parametrize("level", arenas(), ids=lambda level: level.title)
def test_the_swimmer_starts_clear_of_obstacles_and_lights(level):
    x, y, _ = level.start
    arena, r = level.arena, BASE_RADIUS
    for disc in arena.obstacles:
        assert math.hypot(x - disc.x, y - disc.y) > disc.radius + r
    for light in arena.lights:  # not within reach of one, or it would be visited at t = 0
        assert math.hypot(x - light.x, y - light.y) > REACH * (LIGHT_RADIUS + r)


def test_arena_titles_tell_them_apart():
    titles = [level.title for level in arenas()]
    assert len(set(titles)) == len(titles)
