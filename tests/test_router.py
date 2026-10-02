"""Where the player is, and how they move about (D-030, D-035). router.py imports no pygame."""

import pytest

from nektoids.editor.router import ChapterRow, Router, Screen, level_label
from nektoids.graph.board import Kind
from nektoids.levels.arenas import arenas, sandbox
from nektoids.levels.score import Score


def a_router():
    return Router(arenas(), sandbox())


def test_the_game_opens_on_the_first_level_under_its_title_card():
    router = a_router()
    assert router.screen is Screen.TITLE and router.index == 0
    router.begin()
    assert router.screen is Screen.EDIT and router.label == "LEVEL 1.1"
    assert router.board.nodes == {} and router.board.remaining(Kind.EYE) == 2  # its own stock


def test_run_and_back_to_edit_keeps_the_board_as_it_was_left():
    router = a_router()
    board = router.board
    eye = board.place(Kind.EYE, (0, 0))
    router.run()
    assert router.screen is Screen.RUN
    router.edit()
    assert router.screen is Screen.EDIT and router.board is board and eye.id in board.nodes


def test_a_level_opens_once_the_one_before_it_is_won_and_the_sandbox_always():
    router = a_router()
    assert router.unlocked(0) and not router.unlocked(1) and router.unlocked(router.sandbox_index)
    with pytest.raises(ValueError, match="once the level before it is won"):
        router.open(1)
    router.mark_won()
    assert router.unlocked(1)
    router.open(1)
    assert (router.index, router.screen, router.label) == (1, Screen.SPEC, "LEVEL 1.2")


def test_next_goes_on_with_its_own_board_and_after_the_last_level_comes_the_end():
    router = a_router()
    first = router.board
    first.place(Kind.EYE, (0, 0))
    router.next()
    assert (router.index, router.screen) == (1, Screen.SPEC) and 0 in router.won
    assert router.board is not first and router.board.nodes == {}
    while router.has_next:
        router.next()
    assert router.is_last and router.index == len(router.levels) - 1
    with pytest.raises(ValueError, match="last level"):
        router.next()
    router.finish()
    assert router.screen is Screen.END and router.won == set(range(len(router.levels)))


def test_a_level_opened_comes_up_under_its_card_and_one_returned_to_does_not():
    router = a_router()
    router.mark_won()
    router.open(1)
    assert router.screen is Screen.SPEC
    router.begin()
    assert router.screen is Screen.EDIT
    router.run()
    router.edit()  # Edit after a run
    assert router.screen is Screen.EDIT
    router.open(router.sandbox_index)
    assert router.screen is Screen.SPEC


def test_the_sandbox_has_no_next_and_is_never_won():
    router = a_router()
    router.open(router.sandbox_index)
    assert router.label == "SANDBOX" and router.level.objectives == ()
    assert not router.has_next and not router.is_last
    router.mark_won()
    assert router.won == set()


def test_each_level_keeps_the_scores_of_its_wins_once_each_and_the_sandbox_none():
    router = a_router()
    router.record(Score(4, 900))
    router.record(Score(4, 900))  # recorded every frame the run shows won
    router.record(Score(8, 700))
    assert router.scores == {Score(4, 900), Score(8, 700)}
    router.next()
    assert router.scores == frozenset()  # the next level has its own
    router.open(0)
    assert len(router.scores) == 2
    router.open(router.sandbox_index)
    router.record(Score(4, 900))
    assert router.scores == frozenset()


def test_a_level_reset_opens_on_a_fresh_board_and_the_others_keep_theirs():
    router = a_router()
    router.begin()
    first = router.board
    first.place(Kind.EYE, (0, 0))
    router.mark_won()
    router.open(1)
    second = router.board
    second.place(Kind.EYE, (0, 0))
    router.reset(0)
    router.open(0)
    assert router.board is not first and router.board.nodes == {}
    router.open(1)
    assert router.board is second and second.nodes


def test_levels_are_named_by_chapter_and_place():
    assert level_label(0) == "LEVEL 1.1" and level_label(1) == "LEVEL 1.2"


def test_chapters_rows_show_each_place_its_state_and_its_fastest_win():
    router = a_router()
    rows = router.rows()
    assert len(rows) == len(router.levels) + 1 and rows[-1].index == router.sandbox_index
    assert [row.state for row in rows[:3]] == ["open", "locked", "locked"]
    assert (rows[0].label, rows[0].current, rows[-1].label, rows[-1].state) == (
        "1.1",
        True,
        "",
        "sandbox",
    )
    router.record(Score(ticks=900, parts=5))
    router.record(Score(ticks=600, parts=7))
    router.mark_won()
    first, second = router.rows()[:2]
    assert (first.state, first.best, second.state) == ("won", Score(ticks=600, parts=7), "open")
    assert isinstance(first, ChapterRow) and first.title == router.levels[0].title
