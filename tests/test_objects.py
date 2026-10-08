"""The Editor's objects (D-301, D-410). objects.py imports no pygame."""

from dataclasses import replace

from nektoids.editor.arena_view import ArenaView
from nektoids.editor.layout import Piece
from nektoids.editor.objects import ONE, object_at, reach, where
from nektoids.levels.arenas import sandbox
from nektoids.levels.level import ItemKind
from nektoids.levels.making import adjusted, placed

LEVEL = sandbox()  # lights at (28, 24) and (8, 8); obstacles; the start at (15, 19)
VIEW = ArenaView(10.0, (0.0, 400.0))  # 10 px/u, the plane's (0, 0) at pixel (0, 400)


def px(x: float, y: float) -> tuple[float, float]:
    return VIEW.to_screen(x, y)


def test_a_click_finds_the_swimmer_first_then_the_nearest_item_else_the_open_plane():
    assert object_at(LEVEL, VIEW, px(15.0, 19.0)) is Piece.START
    assert object_at(LEVEL, VIEW, px(27.5, 24.3)) == 0  # the first light
    assert object_at(LEVEL, VIEW, px(21.0, 21.0)) == 2  # an obstacle
    assert object_at(LEVEL, VIEW, px(2.0, 30.0)) is None
    grown = adjusted(LEVEL, 2, 4)  # radius 3: grabbed farther out
    assert (
        object_at(grown, VIEW, px(23.5, 21.0)) == 2
        and object_at(LEVEL, VIEW, px(23.5, 21.0)) is None
    )
    assert object_at(replace(LEVEL, items=()), VIEW, px(2, 2)) is None


def test_an_objects_place_and_reach():
    made = placed(LEVEL, ItemKind.OBSTACLE, (3.0, 3.0))
    assert where(made, 6) == (3.0, 3.0) and where(LEVEL, Piece.START) == (15.0, 19.0)
    assert (
        reach(LEVEL, Piece.START) == reach(LEVEL, 0) == 1.0
        and reach(adjusted(made, 6, 1), 6) == 2.0
    )


def test_a_mark_is_grabbed_by_its_rim_or_its_centre_and_a_click_inside_finds_the_plane():
    zone = placed(replace(LEVEL, items=()), ItemKind.MARK, (5.0, 30.0))  # D-306
    zone = adjusted(zone, 0, 7)  # radius 1 + 7 x 1 = 8 u, the most: 80 px at VIEW's 10 px/u
    assert zone.items[0].value == 8.0 and reach(zone, 0) == 8.0
    assert object_at(zone, VIEW, px(5.0, 30.0)) == 0  # its centre
    assert object_at(zone, VIEW, px(13.0, 30.0)) == 0 and object_at(zone, VIEW, px(5.4, 22.0)) == 0
    assert object_at(zone, VIEW, px(9.0, 30.0)) is None  # inside: the point there
    lit = placed(zone, ItemKind.LIGHT, (5.0, 30.0))  # a light on its centre: the light first
    assert object_at(lit, VIEW, px(5.0, 30.0)) == 1
    assert ONE[Piece.OBSTACLE] == "an obstacle"
