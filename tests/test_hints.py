"""A level's hints (D-078): an idea, the parts, the shadow. hints.py imports no pygame."""

import pytest
from test_determinism import play

from nektoids.editor.hints import CHARS, IDEA, PARTS, SHADOW, Hints, Taken, parts_line
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


def test_the_parts_are_counted_from_the_shadow_in_parts_order():
    love, shadows = (Hints.from_dict(LEVELS[t].hints) for t in ("Love", "Shadows"))
    assert parts_line(love.ghosts) == "One Eye, one Source, one Thruster, one Diff."
    assert parts_line(shadows.ghosts) == "Two Eyes, one Source, two Thrusters."


def test_hints_are_taken_in_turn_and_the_shadow_shows_or_hides():
    taken = Taken()
    assert taken.take(PARTS) == "take Idea first" and taken.count == 0
    assert taken.take(IDEA) is None and taken.count == 1
    assert taken.take(SHADOW) == "take Parts first"
    assert taken.take(IDEA) is None and taken.count == 1  # taken already: it stays
    taken.take(PARTS)
    assert not taken.shown
    taken.take(SHADOW)
    assert taken.count == 3 and taken.shown
    taken.take(SHADOW)
    assert not taken.shown
    taken.take(SHADOW)
    assert taken.shown
