"""The loop between editing a level and running it. router.py imports no pygame."""

import pytest

from nektoids.editor.router import Router, Screen, level_label
from nektoids.graph.board import Kind
from nektoids.levels.arenas import arenas


def test_a_level_opens_in_the_editor_on_its_own_board():
    router = Router(arenas())
    assert router.screen is Screen.EDIT and router.index == 0
    assert router.board.nodes == {} and router.board.remaining(Kind.EYE) == 2  # the free board


def test_run_and_back_to_edit_keeps_the_board_as_it_was_left():
    router = Router(arenas())
    board = router.board
    eye = board.place(Kind.EYE, (0, 0))
    router.run()
    assert router.screen is Screen.RUN
    router.edit()
    assert router.screen is Screen.EDIT and router.board is board and eye.id in board.nodes


def test_the_next_level_has_its_own_board_and_there_is_none_after_the_last():
    router = Router(arenas())
    first = router.board
    first.place(Kind.EYE, (0, 0))
    router.run()
    router.next()
    assert (router.index, router.screen) == (1, Screen.EDIT)
    assert router.board is not first and router.board.nodes == {}
    assert not router.has_next
    with pytest.raises(ValueError, match="last level"):
        router.next()


def test_levels_are_named_by_route_and_place():
    router = Router(arenas())
    assert router.label == "LEVEL 1.1" and level_label(1) == "LEVEL 1.2"
    router.next()
    assert router.label == "LEVEL 1.2"
