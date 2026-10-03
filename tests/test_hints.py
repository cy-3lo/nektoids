"""A level's hints (D-078): an idea, the parts, the shadow. hints.py imports no pygame."""

import pytest
from test_determinism import play

from nektoids.editor.hints import (
    CHARS,
    IDEA,
    NAMES,
    PARTS,
    SHADOW,
    Hints,
    Taken,
    hint_view,
    parts_line,
)
from nektoids.editor.layout import HINT_ROWS, Drawer, Env, make_layout
from nektoids.graph.network import Network
from nektoids.levels.arenas import arenas
from nektoids.levels.objectives import Outcome

LEVELS = {level.title: level for level in arenas()}


@pytest.mark.parametrize("title", LEVELS)
def test_every_level_has_hints_and_its_shadow_wins_it(title):
    level = LEVELS[title]
    hints = Hints.from_dict(level.hints)
    net = Network.from_board(hints.build(level.new_board()))
    ended, ticks, _ = play(net, title)
    assert ended is Outcome.WON
    assert play(net, title)[1] == ticks  # the same tick, every run


@pytest.mark.parametrize("title", LEVELS)
def test_each_hint_fits_the_drawer_and_the_shadow_says_nothing(title):
    hints = Hints.from_dict(LEVELS[title].hints)
    for index in (IDEA, PARTS):
        assert 1 <= len(hints.says(index)) <= 2
        assert all(len(line) <= CHARS for line in hints.says(index))
    assert hints.says(SHADOW) == ()


@pytest.mark.parametrize("title", LEVELS)
def test_all_taken_in_the_run_they_fit_above_the_objectives_and_the_picture_stays_large(title):
    level = LEVELS[title]
    hints, taken = Hints.from_dict(level.hints), Taken(count=len(NAMES), shown=True)
    view = hint_view(hints, taken, False, hints.build(level.new_board()))
    lines = tuple(map(len, view.lines))
    layout = make_layout(
        Drawer.HINTS, env=Env.RUN, goals=len(level.objectives), hint_lines=lines, shadow=True
    )
    x, y, w, h = layout.shadow_picture
    assert w == h >= 140 and y + h < layout.goal_area[1]
    assert len(NAMES) == HINT_ROWS == len(layout.hint_rows)


def test_the_parts_are_counted_from_the_shadow_in_parts_order():
    love, shadows = (Hints.from_dict(LEVELS[t].hints) for t in ("Love", "Shadows"))
    assert parts_line(love.ghosts) == "One Eye, one Source, one Thruster, one Diff."
    assert parts_line(shadows.ghosts) == "Two Eyes, one Source, two Thrusters."


def test_hints_are_taken_in_turn_and_the_shadow_shows_or_hides():
    taken = Taken()
    assert taken.take(PARTS) == "take Hint 1 first" and taken.count == 0
    assert taken.take(IDEA) is None and taken.count == 1
    assert taken.take(SHADOW) == "take Hint 2 first"
    assert taken.take(IDEA) is None and taken.count == 1  # taken already: it stays
    taken.take(PARTS)
    assert not taken.shown
    taken.take(SHADOW)
    assert taken.count == 3 and taken.shown
    taken.take(SHADOW)
    assert not taken.shown
    taken.take(SHADOW)
    assert taken.shown
