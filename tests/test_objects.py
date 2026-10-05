"""The Maker's objects and its Wheel (D-301). objects.py imports no pygame."""

from dataclasses import replace

import pytest

from nektoids.editor.arena_view import ArenaView
from nektoids.editor.layout import Piece, Tool
from nektoids.editor.objects import (
    KEYS,
    ONE,
    Point,
    chosen,
    name,
    object_at,
    offer,
    piece_of,
    reach,
    says,
    turned_to,
    where,
)
from nektoids.editor.wheel import angles, slots
from nektoids.levels.arenas import sandbox
from nektoids.levels.level import ItemKind
from nektoids.levels.making import adjusted, placed

LEVEL = sandbox()  # lights at (28, 24) and (8, 8); obstacles; the start at (15, 19)
VIEW = ArenaView(10.0, (0.0, 400.0))  # 10 px/u, the plane's (0, 0) at pixel (0, 400)


def px(x: float, y: float) -> tuple[float, float]:
    return VIEW.to_screen(x, y)


def test_the_wheel_offers_what_may_go_on_a_point_and_what_may_be_done_to_an_object():
    assert offer(None) == ()
    assert offer(Point((3.0, 4.0))) == (Piece.LIGHT, Piece.OBSTACLE, Piece.MARK)  # a cell's
    assert offer(0) == (Tool.LESS, Tool.MOVE, Tool.MORE, Tool.DELETE)  # More at the top, D-314
    assert offer(Piece.START) == (Tool.TURN_LEFT, Tool.MOVE, Tool.TURN_RIGHT)  # it stays
    pieces = (Piece.LIGHT, Piece.OBSTACLE, Piece.MARK, Tool.LESS, Tool.MORE)
    assert [KEYS[w] for w in pieces] == list("123<>")


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
    assert says(LEVEL, 0) == "A light, power 8" and says(LEVEL, 2) == "An obstacle, radius 1"
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
    assert says(zone, 0) == "A mark, radius 8" and name(zone, 0, Tool.MORE) == "Bigger"


def test_the_wheel_lights_move_on_an_object_more_on_a_new_one_and_the_arrows_go_round():
    light, point = 0, Point((3.0, 3.0))  # D-314, as the Editor's Wheel (D-084)
    assert chosen(light, Tool.MOVE) == 1 and chosen(light, Tool.MORE) == 2
    assert chosen(Piece.START, Tool.MOVE) == 1 and chosen(Piece.START, Tool.MORE) is None
    assert chosen(point, Piece.MARK) == 2 and chosen(None, Tool.MOVE) is None
    assert turned_to(light, None, 1) == 0 and turned_to(light, None, -1) == 3  # from none
    assert turned_to(light, 1, 1) == 2 and turned_to(light, 3, 1) == 3  # it stops at the end
    assert turned_to(light, 0, -1) == 0 and turned_to(None, None, 1) is None
    assert piece_of(LEVEL, light) is Piece.LIGHT and piece_of(LEVEL, 2) is Piece.OBSTACLE
    assert piece_of(LEVEL, Piece.START) is Piece.START and piece_of(LEVEL, point) is None


def test_the_makers_wheel_sits_side_by_side_over_the_top_more_at_its_top():
    assert angles(4) == [210.0, 150.0, 90.0, 30.0]  # D-314, D-316: no corner left empty
    on_item = slots(offer(0), (0.0, 0.0), 10.0, frozenset(), keys=KEYS)
    top = min(on_item, key=lambda slot: slot.at[1])  # the screen's y runs down
    assert top.what is Tool.MORE and top.at[0] == pytest.approx(0.0)
