"""Levels as data (D-028). level.py imports no pygame."""

import json

import pytest

from nektoids.graph.board import Kind
from nektoids.graph.hexgrid import NE
from nektoids.levels.arenas import DATA, ORDER, SANDBOX, arenas
from nektoids.levels.level import Item, ItemKind, Level, load, to_json
from nektoids.levels.objectives import VisitLights
from nektoids.levels.sandbox import tutorial_board
from nektoids.sim.arena import OBSTACLE_RADIUS


def a_level(**changes):
    """A small level as data, with `changes` to its top-level keys."""
    data = {
        "title": "Test",
        "spec": "Touch the light.",
        "start": {"at": [5.0, 5.0], "heading": 90.0},
        "items": [
            {"kind": "obstacle", "at": [10.0, 3.0], "radius": 2.0},
            {"kind": "light", "at": [20.0, 5.0], "power": 6.0},
            {"kind": "obstacle", "at": [12.0, 9.0]},
        ],
        "board": tutorial_board().to_dict(),
        "time_limit": 30.0,
        "objectives": [{"kind": "visit lights"}],
    }
    return data | changes


def test_every_shipped_level_is_in_the_order_and_its_file_is_what_the_code_writes():
    assert sorted(path.stem for path in DATA.glob("*.json")) == sorted((*ORDER, SANDBOX))
    for name in (*ORDER, SANDBOX):
        path = DATA / f"{name}.json"
        assert to_json(load(path)) == path.read_text(encoding="utf-8")
    assert [level.title for level in arenas()] == ["Fear", "Aggression", "Love", "In the shadow"]


def test_a_level_comes_back_from_its_data_as_it_was_even_through_json():
    level = Level.from_dict(a_level())
    assert Level.from_dict(json.loads(json.dumps(level.to_dict()))) == level
    assert level.start == (5.0, 5.0, 90.0) and level.time_limit == 30.0
    assert level.objectives == (VisitLights(),)


def test_items_are_placed_as_parts_are_a_kind_a_point_and_their_kinds_setting():
    level = Level.from_dict(a_level())
    first, light, last = level.items
    assert first == Item(ItemKind.OBSTACLE, (10.0, 3.0), 2.0)
    assert light == Item(ItemKind.LIGHT, (20.0, 5.0), 6.0)
    assert last.value == OBSTACLE_RADIUS  # an obstacle's radius has a default, a light's power not
    assert (ItemKind.LIGHT.setting, ItemKind.OBSTACLE.setting) == ("power", "radius")
    assert light.to_dict() == {"kind": "light", "at": [20.0, 5.0], "power": 6.0}


def test_the_arena_takes_the_lights_and_the_obstacles_each_in_item_order():
    arena = Level.from_dict(a_level()).arena
    assert arena.light_xy.tolist() == [[20.0, 5.0]] and arena.light_power.tolist() == [6.0]
    assert arena.disc_xy.tolist() == [[10.0, 3.0], [12.0, 9.0]]
    assert arena.disc_radius.tolist() == [2.0, OBSTACLE_RADIUS]


def test_each_new_board_is_the_levels_own_fresh_from_its_data():
    level = Level.from_dict(a_level())
    board = level.new_board()
    assert [n.kind for n in board.nodes.values()] == [Kind.EYE] * 2 + [Kind.THRUSTER] * 2
    assert all(n.locked for n in board.nodes.values()) and board.nodes[0].facing == NE
    board.connect(0, 3)
    assert level.new_board().wires == []  # the level's data is not changed by playing


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"items": [{"kind": "wall", "at": [0.0, 0.0]}]}, "wall"),
        ({"items": [{"kind": "light", "at": [0.0, 0.0]}]}, "needs its power"),
        ({"objectives": [{"kind": "survive"}]}, "survive"),
        (
            {
                "items": [
                    {"kind": "light", "at": [10.0, 10.0], "power": 4.0},
                    {"kind": "obstacle", "at": [10.5, 10.0]},
                ]
            },
            "touches an obstacle",
        ),
    ],
)
def test_data_no_level_could_hold_fails_when_it_is_loaded(changes, message):
    with pytest.raises(ValueError, match=message):
        Level.from_dict(a_level(**changes))
