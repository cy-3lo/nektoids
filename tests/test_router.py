"""Where the player is, and how they move about (D-030, D-035). router.py imports no pygame."""

import pytest

from nektoids.editor.router import Router, Screen, level_label
from nektoids.graph.board import Kind
from nektoids.levels.arenas import arenas, sandbox


def a_router():
    return Router(arenas(), sandbox())


def test_the_game_opens_on_the_first_level_under_its_title_card():
    router = a_router()
    assert router.screen is Screen.TITLE and router.index == 0
    router.begin()
    assert router.screen is Screen.EDIT and router.label == "LEVEL 1.1"
    assert router.board.nodes == {} and router.board.remaining(Kind.EYE) == 2  # the free board


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
    router.open_map()
    router.open(1)
    assert (router.index, router.screen, router.label) == (1, Screen.EDIT, "LEVEL 1.2")


def test_next_goes_on_with_its_own_board_and_after_the_last_level_comes_the_end():
    router = a_router()
    first = router.board
    first.place(Kind.EYE, (0, 0))
    router.next()
    assert (router.index, router.screen) == (1, Screen.EDIT) and 0 in router.won
    assert router.board is not first and router.board.nodes == {}
    assert not router.has_next and router.is_last
    with pytest.raises(ValueError, match="last level"):
        router.next()
    router.finish()
    assert router.screen is Screen.END and router.won == {0, 1}


def test_the_sandbox_has_no_next_and_is_never_won():
    router = a_router()
    router.open(router.sandbox_index)
    assert router.label == "SANDBOX" and router.level.objectives == ()
    assert not router.has_next and not router.is_last
    router.mark_won()
    assert router.won == set()


def test_levels_are_named_by_chapter_and_place():
    assert level_label(0) == "LEVEL 1.1" and level_label(1) == "LEVEL 1.2"
