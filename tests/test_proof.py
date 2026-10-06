"""A level's proof (D-320): its board's text and score, run again headless. proof.py imports no
pygame."""

import json
from dataclasses import replace

import pytest

from nektoids.editor.boardfield import load
from nektoids.editor.hints import Hints
from nektoids.graph import boardtext
from nektoids.graph.board import complexity
from nektoids.levels.arenas import arenas
from nektoids.levels.level import Level, to_json
from nektoids.levels.making import read_level
from nektoids.levels.objectives import Outcome
from nektoids.levels.proof import Proof, Replay

DT = 1.0 / 120.0
ORBIT = next(level for level in arenas() if level.title == "Orbit")
ORBITER = Hints.from_dict(ORBIT.hints).build(ORBIT.blank_board())  # its hint's board, which wins


def test_a_proof_is_its_boards_text_and_its_score_and_refuses_what_it_does_not_know():
    proof = Proof(boardtext.to_text(ORBITER), 1093, 4)
    assert Proof.from_dict(json.loads(json.dumps(proof.to_dict()))) == proof
    with pytest.raises(ValueError, match="takes no 'time'"):
        Proof.from_dict({**proof.to_dict(), "time": 9.1})
    with pytest.raises(ValueError, match="needs its 'parts'"):
        Proof.from_dict({"board": proof.board, "ticks": 1})


def test_a_winning_board_run_again_wins_at_the_tick_it_won_at_a_few_ticks_a_frame():
    replay = Replay(ORBIT, ORBITER, DT)
    while replay.advance(120) is None:  # a second of the run a frame
        assert 0.0 < replay.progress < 1.0
    assert replay.outcome is Outcome.WON and replay.tick == 1093  # as the pinned run (D-312)
    assert replay.advance(120) is Outcome.WON and replay.tick == 1093  # over: no further
    empty = Replay(ORBIT, ORBIT.blank_board(), DT)  # no part: it stays where it starts
    assert empty.advance(10_000) is Outcome.TIME_UP and empty.progress == 1.0


def test_a_level_shared_carries_its_proof_through_its_text():
    proof = Proof(boardtext.to_text(ORBITER), 1093, 4)
    shared = replace(ORBIT, proof=proof.to_dict())
    again = read_level(to_json(shared))
    assert again == shared and Proof.from_dict(again.proof) == proof
    assert "proof" not in json.loads(to_json(replace(ORBIT, proof=None)))  # none, none written
    with pytest.raises(ValueError, match="a proof takes no 'seed'"):
        Level.from_dict({**json.loads(to_json(shared)), "proof": {**proof.to_dict(), "seed": 1}})


@pytest.mark.parametrize("level", arenas(), ids=lambda level: level.title)
def test_every_shipped_level_carries_its_proof_and_its_board_wins_it_again(level):
    proof = Proof.from_dict(level.proof)  # D-328: the level's clear check, as a pasted one's
    board = level.new_board()
    fits, why = load(board, proof.board)
    assert fits, why
    assert complexity(board) == proof.parts
    replay = Replay(level, board, DT)
    assert replay.advance(replay.last) is Outcome.WON  # the win, not its tick (D-004)
