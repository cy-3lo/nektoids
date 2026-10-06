"""Levels as data (D-028). level.py imports no pygame."""

import json

import pytest

from nektoids.graph.board import Board, Kind
from nektoids.graph.hexgrid import NE, hex_disc
from nektoids.levels.arenas import DATA, ORDER, SANDBOX, arenas, sandbox
from nektoids.levels.level import FORMAT, Item, ItemKind, Level, is_passkey, load, to_json
from nektoids.levels.objectives import Count, Goal, Target, Verb
from nektoids.levels.sandbox import tutorial_board
from nektoids.sim.arena import OBSTACLE_RADIUS


def a_level(**changes):
    """A small level as data, with `changes` to its top-level keys."""
    data = {
        "version": 1,
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
    names = (path.relative_to(DATA).with_suffix("").as_posix() for path in DATA.rglob("*.json"))
    assert sorted(names) == sorted((*ORDER, SANDBOX))  # each in its chapter's folder (D-325)
    for name in (*ORDER, SANDBOX):
        path = DATA / f"{name}.json"
        assert to_json(load(path)) == path.read_text(encoding="utf-8")
    titles = ["Fear", "Aggression", "Love", "Orbit", "Shadows", "Greed", "Patience"]  # D-097
    titles.append("Two lights")  # D-324
    assert [level.title for level in arenas()] == titles


def test_a_level_comes_back_from_its_data_as_it_was_even_through_json():
    level = Level.from_dict(a_level())
    assert Level.from_dict(json.loads(json.dumps(level.to_dict()))) == level
    assert level.start == (5.0, 5.0, 90.0) and level.time_limit == 30.0
    assert level.objectives == (Goal(Verb.REACH, Count.ALL, Target.LIGHT),)  # D-307


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
        ({"extra": 1}, "a level takes no 'extra'"),  # D-201: refused, not ignored
        ({"start": {"at": [5.0, 5.0], "heading": 90.0, "speed": 1.0}}, "start takes no 'speed'"),
        ({"items": [{"kind": "light", "at": [0.0, 0.0], "power": 6.0, "colour": "red"}]}, "colour"),
        ({"objectives": [{"kind": "leave ring", "radus": 10.0}]}, "'leave ring' takes no 'radus'"),
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


def test_the_sandbox_hands_out_every_part_without_limit_on_a_zone_a_ring_wider():
    board = sandbox().new_board()  # D-102
    assert all(board.total(kind) is None for kind in Kind)
    assert sorted(board.cells) == sorted(hex_disc(3))


def test_a_level_without_its_version_or_of_another_is_refused():
    data = a_level()
    del data["version"]
    with pytest.raises(ValueError, match="without its version: this game reads version 4"):
        Level.from_dict(data)
    with pytest.raises(ValueError, match="of version 5: this game reads version 4 and those"):
        Level.from_dict(a_level(version=5))  # D-201
    assert Level.from_dict(a_level()).to_dict()["version"] == FORMAT == 4  # 1 upgraded (D-313)


def test_every_level_but_the_last_gives_a_passkey_and_no_two_alike():
    words = [level.passkey for level in arenas()]  # D-075
    assert words == ["LOVE", "SWORD", "HEART", "MOON", "DARK", "GOLD", "SNAIL", "GEMINI"]
    assert len(set(words)) == len(words)
    assert all(is_passkey(word) for word in words) and sandbox().passkey is None
    assert not is_passkey("sword") and not is_passkey("SWÖRD") and not is_passkey("A" * 11)
    data = a_level(passkey="lower")
    with pytest.raises(ValueError):
        Level.from_dict(data)


def test_a_mark_is_an_item_the_arena_never_has_so_the_run_is_what_it_was():
    marked = a_level(
        version=2, items=[*a_level()["items"], {"kind": "mark", "at": [20.0, 5.0], "radius": 6.0}]
    )
    level, plain = Level.from_dict(marked), Level.from_dict(a_level())  # D-306
    assert level.marks == (Item(ItemKind.MARK, (20.0, 5.0), 6.0),) and plain.marks == ()
    seen = (level.arena.lights, level.arena.obstacles)  # on a light, of any size, unread
    assert seen == (plain.arena.lights, plain.arena.obstacles)
    assert ItemKind.MARK.setting == "radius" and ItemKind.MARK.default is None
    assert Level.from_dict(json.loads(to_json(level))) == level
    with pytest.raises(ValueError, match="a mark needs its radius"):
        Level.from_dict(a_level(items=[{"kind": "mark", "at": [1.0, 1.0]}]))
    with pytest.raises(ValueError, match="'zone' is not a valid ItemKind"):
        Level.from_dict(a_level(items=[{"kind": "zone", "at": [1.0, 1.0]}]))


def test_version_2s_rings_become_marks_on_its_lights_and_its_objectives_sentences():
    data = a_level(version=2, objectives=[{"kind": "leave ring", "radius": 12.0}])  # D-307
    level = Level.from_dict(data)
    assert level.marks == (Item(ItemKind.MARK, (20.0, 5.0), 12.0),)  # on its one light
    assert level.objectives == (Goal(Verb.LEAVE, Count.ALL, Target.MARK),)
    assert level.items[:3] == Level.from_dict(a_level()).items  # the rest as it was
    marked = [*a_level()["items"], {"kind": "mark", "at": [1.0, 1.0], "radius": 2.0}]
    with pytest.raises(ValueError, match="would count its marks"):
        Level.from_dict(a_level(version=2, items=marked, objectives=data["objectives"]))


def test_a_goal_must_aim_at_something_the_level_has():
    goal = {"verb": "leave", "count": "all", "target": "mark"}  # D-307: no mark to leave
    with pytest.raises(ValueError, match="'Leave every ring': the level has no rings"):
        Level.from_dict(a_level(version=3, objectives=[goal]))


def test_version_4_writes_a_hexagons_zone_as_its_size_and_whole_numbers_as_integers():
    old = a_level(version=3, objectives=[{"verb": "reach", "count": "all", "target": "light"}])
    old["board"] = {**old["board"], "zone": [list(c) for c in hex_disc(2)]}  # its cells
    data = Level.from_dict(old).to_dict()  # D-313
    assert data["board"]["zone"] == 19 and data["start"] == {"at": [5, 5], "heading": 90}
    assert data["items"][1] == {"kind": "light", "at": [20, 5], "power": 6}
    assert data["time_limit"] == 30 and isinstance(data["time_limit"], int)
    again = Level.from_dict(json.loads(json.dumps(data)))
    assert again.start == (5.0, 5.0, 90.0) and isinstance(again.start[0], float)
    assert again.new_board().cells == Level.from_dict(old).new_board().cells
    halves = Level.from_dict({**data, "start": {"at": [5.5, 5], "heading": 90}}).to_dict()
    assert halves["start"]["at"] == [5.5, 5]  # not whole: written as it is
    bare = {**old["board"], "zone": [[0, 0], [1, 0]], "parts": [], "wires": []}
    odd = Level.from_dict({**old, "board": bare})
    assert odd.to_dict()["board"]["zone"] == [[0, 0], [1, 0]]  # no hexagon: its cells


def test_a_blank_board_keeps_the_levels_locked_parts_and_none_of_its_free_ones():
    board = Board(hex_disc(1), {Kind.EYE: 1})  # a level that places a Source and a thruster
    source = board.place(Kind.SOURCE, (0, 0), locked=True)
    thruster = board.place(Kind.THRUSTER, (-1, 0), locked=True)
    eye = board.place(Kind.EYE, (1, 0))  # a free part, as Aggression's (D-103)
    board.connect(source.id, thruster.id)
    board.connect(eye.id, thruster.id)
    level = Level.from_dict(a_level(board=board.to_dict()))
    blank = level.blank_board()  # D-328: what a hint's shadow goes on
    assert {(n.kind, n.cell, n.locked) for n in blank.nodes.values()} == {
        (Kind.SOURCE, (0, 0), True),
        (Kind.THRUSTER, (-1, 0), True),
    }
    assert blank.wires == [] and blank.remaining(Kind.EYE) == 1


def test_every_shipped_levels_positions_are_whole_units_and_its_zone_a_size():
    for path in sorted(DATA.rglob("*.json")):  # D-313
        data = json.loads(path.read_text())
        points = [data["start"]["at"], *(item["at"] for item in data["items"])]
        assert all(isinstance(v, int) for point in points for v in point), path.stem
        assert data["version"] == 4 and data["board"]["zone"] in (19, 37), path.stem
