"""Where the player is, and how they move about (D-030, D-035). router.py imports no pygame."""

from dataclasses import replace

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
    assert router.screen is Screen.RUN and router.label == "LEVEL 1.1"  # D-069
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
    assert router.board is not first and router.board.nodes == router.level.new_board().nodes
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
    assert router.screen is Screen.RUN  # a level opens on its run (D-069)
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
    assert router.board is not first and router.board.nodes == router.level.new_board().nodes
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


def test_files_lists_the_wins_with_their_boards_the_unbeaten_first_each_score_once():
    router = a_router()
    router.begin()
    first = router.board.snapshot()
    router.record(Score(ticks=900, parts=4), first)
    router.board.place(Kind.EYE, (0, 0))
    later = router.board.snapshot()
    router.record(Score(ticks=600, parts=5), later)
    router.record(Score(ticks=700, parts=6), later)  # beaten by the 600-tick win
    router.record(Score(ticks=900, parts=4), later)  # the same score: its first board stays
    wins = router.wins(0)
    assert [(w.score.ticks, w.best) for w in wins] == [(600, True), (900, True), (700, False)]
    assert wins[1].board == first and wins[0].board == later
    assert router.wins(1) == ()


def test_files_lists_every_levels_wins_the_open_ones_first_then_the_chapters_order():
    router = a_router()  # D-092
    assert router.files() == ()
    for k, ticks in ((0, 900), (2, 800), (2, 700)):
        router.index = k
        router.record(Score(ticks=ticks, parts=4), router.board.snapshot())
    router.index = 2
    files = router.files()
    assert [(group.index, group.title) for group in files] == [(2, "1.3 Love"), (0, "1.1 Fear")]
    assert files[0].wins == router.wins(2) and len(files[1].wins) == 1
    router.index = router.sandbox_index  # no wins of its own: the levels', in order
    assert [group.index for group in router.files()] == [0, 2]


def test_a_passkey_opens_the_level_after_the_one_whose_win_gives_it_and_those_before():
    router = a_router()  # D-075: LOVE is Fear's word, SWORD Aggression's, HEART Love's
    assert router.state(2) == "locked" and router.unlock("nothing") is None
    assert router.unlock("  sword ") == 2  # any case, spaces round it
    assert [router.state(k) for k in range(4)] == ["open", "open", "open", "locked"]
    assert not router.won  # opened, not won: no score
    router.open(2)  # Love opens
    assert router.unlock(router.levels[-1].passkey) is None  # the last's opens nothing yet
    assert router.unlock("heart") == 3 and router.state(3) == "open"


def test_a_win_card_names_the_word_for_the_next_level_and_chapters_once_it_is_won():
    router = a_router()
    router.begin()  # Fear
    assert router.next_passkey() == ("LOVE", "LEVEL 1.2")
    assert router.rows()[0].passkey == ""  # not won yet: not given away
    router.mark_won()
    assert router.rows()[0].passkey == "LOVE" and router.rows()[1].passkey == ""
    router.unlock(router.levels[-2].passkey)  # the word before the last opens it
    router.open(len(router.levels) - 1)  # the last: there is no next level to open
    assert router.next_passkey() is None
    router.open(router.sandbox_index)
    assert router.next_passkey() is None


def test_the_maker_opens_on_the_sandbox_alone_and_the_editor_and_the_run_go_on_from_it():
    router = a_router()  # D-301
    with pytest.raises(ValueError, match="only the sandbox"):
        router.make()
    router.open(router.sandbox_index)
    router.begin()
    router.make()
    assert router.screen is Screen.MAKE and router.label == "SANDBOX"
    router.run()
    assert router.screen is Screen.RUN
    router.make()
    router.edit()
    assert router.screen is Screen.EDIT


def test_the_maker_revises_the_sandboxs_level_alone_and_its_board_stays():
    router = a_router()  # D-301
    with pytest.raises(ValueError, match="only the sandbox"):
        router.revise(router.level)
    router.open(router.sandbox_index)
    board = router.board
    eye = board.place(Kind.EYE, (0, 0))
    made = replace(router.level, start=(3.0, 4.0, 90.0))
    router.revise(made)
    assert router.level is made and router.sandbox is made
    assert router.board is board and eye.id in board.nodes  # the plane changed round it
