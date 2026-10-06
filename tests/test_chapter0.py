"""Chapter 0's levels, each teaching one thing (D-335): the board that does not do that thing
fails, and the proof, which does, wins (`test_proof.py`). proof.py imports no pygame."""

import pytest

from nektoids.graph.board import Kind
from nektoids.graph.hexgrid import E, W
from nektoids.levels.arenas import arenas
from nektoids.levels.objectives import Outcome
from nektoids.levels.proof import Replay

DT = 1.0 / 120.0
LEVELS = {level.title: level for level in arenas()}


def ended(title, parts=(), wires=(), board=None):
    """How `title` ends with `parts` (kind, cell, facing) placed on its board as it opens, then
    `wires` drawn cell to cell."""
    level = LEVELS[title]
    board = level.new_board() if board is None else board
    for kind, cell, facing in parts:
        board.place(kind, cell, facing=facing)
    for a, b in wires:
        board.connect(board.node_at(a).id, board.node_at(b).id)
    replay = Replay(level, board, DT)
    return replay.advance(replay.last)


def test_wiring_stays_put_until_the_wire_is_drawn():
    assert ended("Wiring") is Outcome.TIME_UP


def test_turning_pushed_through_the_centre_slides_away_without_turning():
    assert ended("Turning") is Outcome.TIME_UP  # its thruster as it comes, pointing SE (D-336)


@pytest.mark.parametrize("facing", [E, W])
def test_eyes_an_eye_on_its_thruster_must_look_at_the_light(facing):
    parts = [(Kind.EYE, (1, 0), facing), (Kind.THRUSTER, (-1, 0), E)]
    outcome = ended("Eyes", parts, [((1, 0), (-1, 0))])
    assert outcome is (Outcome.WON if facing == E else Outcome.TIME_UP)


@pytest.mark.parametrize("operator", [None, Kind.DOUBLE])
def test_half_a_full_push_crosses_the_ring_too_fast_and_a_double_adds_nothing(operator):
    parts = [(Kind.SOURCE, (0, 0), None), (Kind.THRUSTER, (-1, 0), E)]
    wires = [((0, 0), (-1, 0))]
    if operator is not None:  # no wire carries more than a Source sends (D-335)
        parts.append((operator, (1, 0), None))
        wires = [((0, 0), (1, 0)), ((1, 0), (-1, 0))]
    assert ended("Half", parts, wires) is Outcome.TIME_UP


def test_minus_an_eye_alone_or_a_source_alone_touches_the_light():
    eye = [(Kind.EYE, (1, 0), E), (Kind.THRUSTER, (-1, 0), E)]
    assert ended("Minus", eye, [((1, 0), (-1, 0))]) is Outcome.LOST
    source = [(Kind.SOURCE, (0, 0), None), (Kind.THRUSTER, (-1, 0), E)]
    assert ended("Minus", source, [((0, 0), (-1, 0))]) is Outcome.LOST


def test_diagnostic_comes_with_an_eye_looking_back_and_never_moves():
    board = LEVELS["Diagnostic"].new_board()
    assert board.node_at((1, 0)).facing == W
    assert ended("Diagnostic", board=board) is Outcome.TIME_UP


def test_turning_pointed_ahead_off_the_centre_goes_round_the_obstacle_into_the_ring():
    board = LEVELS["Turning"].new_board()
    board.rotate(board.node_at((0, 1)).id, 1)  # one turn left: E (D-009, D-336)
    assert board.node_at((0, 1)).facing == E
    assert ended("Turning", board=board) is Outcome.WON
