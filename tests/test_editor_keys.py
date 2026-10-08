"""The Editor's buttons (D-410). editor_keys.py imports no pygame."""

from dataclasses import replace

from nektoids.editor.buttons import State
from nektoids.editor.editor_keys import (
    LEFT,
    RIGHT,
    SIZE,
    Key,
    key_at,
    places,
    states,
    tip,
)
from nektoids.editor.layout import Drawer, Env, Piece, contains, make_layout
from nektoids.levels.arenas import sandbox


def test_the_keys_sit_inside_the_plane_at_its_edges_whatever_the_drawer():
    for drawer in (Drawer.OBJECTS, None):
        area = make_layout(drawer, env=Env.EDITOR, editor=True).board_area
        x, y, w, h = area
        found = places(area)
        assert set(found) == {*[k for pair in LEFT for k in pair], *RIGHT}
        for rect in found.values():
            assert contains(area, rect[:2]) and contains(area, (rect[0] + SIZE, rect[1] + SIZE))
        assert all(found[k][0] < x + 3 * SIZE for pair in LEFT for k in pair)  # at the left
        assert all(found[p][0] > x + w - 2 * SIZE for p in RIGHT)  # at the right
        cx, cy = found[Key.CUT][0] + 5, found[Key.CUT][1] + 5
        assert key_at(area, (cx, cy)) is Key.CUT and key_at(area, (x + w // 2, y + h // 2)) is None
    pairs = [(found[a][1], found[b][1]) for a, b in LEFT]
    assert all(ya == yb for ya, yb in pairs)  # side by side
    assert found[Key.COPY][1] < found[Key.CUT][1]  # Copy and Paste over Cut and Erase all


def test_a_key_lights_on_what_it_acts_on_and_greys_when_it_cannot():
    level = sandbox()
    nothing = states(level, Key.SELECT, (), False, False, False)
    assert nothing[Key.SELECT] is State.CHOSEN
    assert nothing[Key.CUT] is nothing[Key.PASTE] is nothing[Key.UNDO] is State.GREYED
    assert nothing[Key.ERASE] is nothing[Piece.LIGHT] is State.PLAIN
    picked = states(level, Piece.MARK, (0, Piece.START), True, False, True)
    assert picked[Key.BIGGER] is picked[Key.COPY] is State.LIT
    assert picked[Piece.MARK] is State.CHOSEN and picked[Key.PASTE] is State.PLAIN
    start = states(level, Key.SELECT, (Piece.START,), False, False, False)
    assert start[Key.BIGGER] is State.GREYED  # the start has no size
    assert start[Key.CUT] is State.LIT and start[Piece.START] is State.GREYED  # one swimmer
    off = states(level, Key.SELECT, (), False, False, False, start_off=True)
    assert off[Piece.START] is State.PLAIN  # cut: its key places it again (D-410)
    empty = states(replace(level, items=()), Key.SELECT, (), False, False, False)
    assert empty[Key.ERASE] is State.GREYED


def test_a_tooltip_names_the_key_and_says_its_key():
    assert tip(Key.ERASE) == "Erase all" and tip(Key.CUT) == "Cut (Del)"
    assert tip(Piece.START) == "Swimmer (0)" and tip(Piece.LIGHT) == "Light (1)"
    assert tip(Key.HAND, key_hints=False) == "Hand"
