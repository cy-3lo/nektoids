"""The Maker's objects and its Wheel (D-301). objects.py imports no pygame."""

from dataclasses import replace

from nektoids.editor.arena_view import ArenaView
from nektoids.editor.layout import Piece, Tool
from nektoids.editor.objects import (
    KEYS,
    ONE,
    Point,
    name,
    object_at,
    offer,
    reach,
    says,
    where,
)
from nektoids.levels.arenas import sandbox
from nektoids.levels.level import ItemKind
from nektoids.levels.making import adjusted, placed

LEVEL = sandbox()  # lights at (27.5, 24) and (7.5, 7.5); obstacles; the start at (15, 19)
VIEW = ArenaView(10.0, (0.0, 400.0))  # 10 px/u, the plane's (0, 0) at pixel (0, 400)


def px(x: float, y: float) -> tuple[float, float]:
    return VIEW.to_screen(x, y)


def test_the_wheel_offers_what_may_go_on_a_point_and_what_may_be_done_to_an_object():
    assert offer(None) == ()
    assert offer(Point((3.0, 4.0))) == (Piece.LIGHT, Piece.OBSTACLE)  # as an empty cell
    assert offer(0) == (Tool.LESS, Tool.MOVE, Tool.DELETE, Tool.MORE)  # less, more by the gap
    assert offer(Piece.START) == (Tool.TURN_LEFT, Tool.MOVE, Tool.TURN_RIGHT)  # it stays
    assert [KEYS[w] for w in (Piece.LIGHT, Piece.OBSTACLE, Tool.LESS, Tool.MORE)] == list("12<>")


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


def test_what_the_wheels_line_and_its_tooltips_say():
    assert says(LEVEL, None) == "Click the plane"
    assert says(LEVEL, Point((10.0, 14.5))) == "(10, 14.5): empty"
    assert says(LEVEL, Piece.START) == "Swimmer, heading 20°"
    assert says(LEVEL, 0) == "A light, power 8" and says(LEVEL, 2) == "An obstacle, radius 1 u"
    assert (name(LEVEL, 0, Tool.LESS), name(LEVEL, 0, Tool.MORE)) == ("Dimmer", "Brighter")
    assert (name(LEVEL, 2, Tool.LESS), name(LEVEL, 2, Tool.MORE)) == ("Smaller", "Bigger")
    assert name(LEVEL, Piece.START, Tool.TURN_LEFT) == "Turn left"
    assert name(LEVEL, None, Piece.OBSTACLE) == "Obstacle" and ONE[Piece.OBSTACLE] == "an obstacle"


def test_an_objects_place_and_reach():
    made = placed(LEVEL, ItemKind.OBSTACLE, (3.0, 3.0))
    assert where(made, 6) == (3.0, 3.0) and where(LEVEL, Piece.START) == (15.0, 19.0)
    assert where(LEVEL, Point((1.0, 2.0))) == (1.0, 2.0)
    assert (
        reach(LEVEL, Piece.START) == reach(LEVEL, 0) == 1.0
        and reach(adjusted(made, 6, 2), 6) == 2.0
    )
