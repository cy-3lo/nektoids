import math

import pytest

from nektoids.levels.arenas import CHAPTERS, arenas, locate
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


def test_the_route_runs_through_the_chapters_in_order_each_level_in_one():
    assert [chapter.heading for chapter in CHAPTERS] == [
        "Chapter 0: Tutorials",
        "Chapter 1: Braitenberg",
        "Chapter 2: Obstacles",
        "Chapter 3: Many lights",
        "Chapter 4: Your levels",
    ]  # D-325
    assert [len(chapter.names) for chapter in CHAPTERS] == [0, 4, 1, 3, 1]  # D-332: Dragster
    assert [(locate(k)[0].number, locate(k)[1]) for k in (0, 3, 4, 5, 7)] == [
        (1, 0),
        (1, 3),
        (2, 0),
        (3, 0),
        (3, 2),
    ]
    assert locate(4)[0].names[0] == "shadows"
    with pytest.raises(IndexError):
        locate(len(arenas()))
    with pytest.raises(IndexError):
        locate(-1)
