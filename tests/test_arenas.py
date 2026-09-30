import math

import pytest

from nektoids.levels.arenas import arenas
from nektoids.sim.arena import BASE_RADIUS


@pytest.mark.parametrize("level", arenas(), ids=lambda level: level.title)
def test_the_swimmer_starts_whole_inside_the_arena_clear_of_obstacles_and_lights(level):
    x, y, _ = level.start
    arena, r = level.arena, BASE_RADIUS
    assert r <= x <= arena.width - r and r <= y <= arena.height - r
    for disc in arena.obstacles:
        assert math.hypot(x - disc.x, y - disc.y) > disc.radius + r
    for light in arena.lights:
        assert math.hypot(x - light.x, y - light.y) > r


def test_arena_titles_tell_them_apart():
    titles = [level.title for level in arenas()]
    assert len(set(titles)) == len(titles)
