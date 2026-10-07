"""A level's hints (D-078, D-353): the parts, then the shadow, without its wires. hints.py imports
no pygame."""

from dataclasses import replace

import pytest
from test_determinism import play

from nektoids.editor.hints import (
    CHARS,
    NAMES,
    PARTS,
    SHADOW,
    Hints,
    Taken,
    hint_view,
    parts_line,
)
from nektoids.editor.layout import HINT_ROWS, Drawer, Env, make_layout
from nektoids.graph import boardtext
from nektoids.graph.board import Board, Kind
from nektoids.graph.hexgrid import hex_disc
from nektoids.graph.network import Network
from nektoids.levels.arenas import arenas, locate
from nektoids.levels.objectives import Outcome
from nektoids.levels.proof import Proof

LEVELS = {level.title: level for level in arenas()}
HINTED = [title for k, title in enumerate(LEVELS) if locate(k)[0].hints]


def test_the_levels_of_chapters_0_to_3_have_hints_and_those_made_by_users_none():
    chapters = [locate(k)[0].number for k in range(len(LEVELS))]  # D-353
    assert HINTED == [title for title, n in zip(LEVELS, chapters, strict=True) if n <= 3]
    assert "Shadows" in HINTED and "Two lights" in HINTED
    assert "Dragster" not in HINTED and "Dragster II" not in HINTED  # D-348


@pytest.mark.parametrize("title", HINTED)
def test_every_level_has_hints_and_its_shadow_wins_it(title):
    level = LEVELS[title]
    hints = Hints.of(level)  # the shadow: its proof's board (D-329)
    net = Network.from_board(hints.board)
    ended, ticks, _ = play(net, title)
    assert ended is Outcome.WON
    assert play(net, title)[1] == ticks  # the same tick, every run


@pytest.mark.parametrize("title", HINTED)
def test_each_hint_fits_the_drawer_and_the_shadow_says_nothing(title):
    hints = Hints.of(LEVELS[title])
    assert 1 <= len(hints.says(PARTS)) <= 3  # Patience's, the longest: five kinds
    assert all(len(line) <= CHARS for line in hints.says(PARTS))
    assert hints.says(SHADOW) == ()


@pytest.mark.parametrize("title", HINTED)
def test_all_taken_in_the_run_they_fit_above_the_objectives_and_the_picture_stays_large(title):
    level = LEVELS[title]
    hints, taken = Hints.of(level), Taken(count=len(NAMES), shown=True)
    view = hint_view(hints, taken, False, hints.board)
    lines = tuple(map(len, view.lines))
    layout = make_layout(
        Drawer.HINTS, env=Env.RUN, goals=len(level.objectives), hint_lines=lines, shadow=True
    )
    x, y, w, h = layout.shadow_picture
    assert w == h >= 140 and y + h < layout.shadow_line[1]
    assert layout.shadow_line[1] + layout.shadow_line[3] < layout.goal_area[1]  # D-088
    assert len(NAMES) == HINT_ROWS == len(layout.hint_rows)


def test_the_parts_are_counted_from_the_shadow_in_parts_order():
    love, aggression = (Hints.of(LEVELS[t]) for t in ("Love", "Aggression"))
    assert parts_line(love.ghosts) == "One Eye, one Source, one Thruster, one Diff."
    assert parts_line(aggression.ghosts) == "Two Eyes, two Thrusters."
    assert parts_line(()) == "No part to add: only wires."


def test_the_shadow_goes_over_the_parts_the_level_places_and_adds_only_the_rest():
    board = Board(hex_disc(1), {})  # D-329: as 0.1 will be, a Source and a thruster locked
    source = board.place(Kind.SOURCE, (0, 0), locked=True)
    thruster = board.place(Kind.THRUSTER, (-1, 0), locked=True)
    level = replace(LEVELS["Fear"], board=board.to_dict())
    board.connect(source.id, thruster.id)
    level = replace(level, proof=Proof(boardtext.to_text(board), 600, 2).to_dict())
    hints = Hints.of(level)
    assert hints.ghosts == () and hints.ghost_wires == ()  # the shadow draws no wire (D-353)
    assert len(hints.board.wires) == 1 and all(n.locked for n in hints.board.nodes.values())
    assert " ".join(hints.says(PARTS)) == "No part to add: only wires."


def test_hints_are_taken_in_turn_and_the_shadow_shows_or_hides():
    taken = Taken()
    assert taken.take(SHADOW) == "take Hint 1 first" and taken.count == 0
    assert taken.take(PARTS) is None and taken.count == 1
    assert taken.take(PARTS) is None and taken.count == 1  # taken already: it stays
    assert not taken.shown
    taken.take(SHADOW)
    assert taken.count == 2 and taken.shown
    taken.take(SHADOW)
    assert not taken.shown
    taken.take(SHADOW)
    assert taken.shown
