"""Where the player is, and how they move about (D-030, D-035). router.py imports no pygame."""

from dataclasses import replace

import pytest

from nektoids.editor.router import (
    SANDBOX_LABEL,
    ChapterRow,
    Router,
    Screen,
    captioned,
    level_label,
)
from nektoids.graph.board import Kind
from nektoids.levels.arenas import EVERY_LEVEL, arenas, sandbox
from nektoids.levels.score import Score


def a_router():
    return Router(arenas(), sandbox())


AT = {level.title: k for k, level in enumerate(arenas())}  # each level's place on the route
FIRSTS = {
    AT[t] for t in ("Wiring", "Fear", "Shadows", "Greed", "Violet", "Latch", "Dragster")
}  # D-325


def test_the_game_opens_on_the_first_level_under_its_title_card():
    router = a_router()
    assert router.screen is Screen.TITLE and router.index == 0
    router.begin()
    assert router.screen is Screen.RUN and router.label == "LEVEL 0.1"  # D-069, D-335
    assert all(n.locked for n in router.board.nodes.values()) and len(router.board.nodes) == 2
    assert router.board.remaining(Kind.EYE) == 0  # its own stock: none


def test_run_and_back_to_edit_keeps_the_board_as_it_was_left():
    router = a_router()
    router.index = AT["Fear"]  # a level that hands out eyes
    board = router.board
    eye = board.place(Kind.EYE, (0, 0))
    router.run()
    assert router.screen is Screen.RUN
    router.open_board()
    assert router.screen is Screen.BOARD and router.board is board and eye.id in board.nodes


def test_a_level_opens_once_the_one_before_it_is_won_and_the_sandbox_always():
    router = a_router()
    fear, aggression = AT["Fear"], AT["Aggression"]
    assert router.unlocked(fear) and not router.unlocked(aggression)
    assert router.unlocked(router.sandbox_index) and all(router.unlocked(k) for k in range(6))
    with pytest.raises(ValueError, match="once the level before it is won"):
        router.open(aggression)
    router.index = fear
    router.mark_won()
    assert router.unlocked(aggression)
    router.open(aggression)
    assert (router.index, router.screen, router.label) == (aggression, Screen.SPEC, "LEVEL 1.2")


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
    router.open_board()  # Edit after a run
    assert router.screen is Screen.BOARD
    router.open(router.sandbox_index)
    assert router.screen is Screen.EDITOR  # Open Editor: straight on the Editor, no card (D-341)


def test_the_sandbox_has_no_next_and_is_never_won():
    router = a_router()
    router.open(router.sandbox_index)
    assert router.label == "YOUR LEVEL" and router.level.objectives == ()  # D-341
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
    assert level_label(0) == "LEVEL 0.1" and level_label(AT["Fear"]) == "LEVEL 1.1"
    assert (
        level_label(AT["Shadows"]) == "LEVEL 2.1" and level_label(AT["Two lights"]) == "LEVEL 3.3"
    )
    labels = [row.label for row in a_router().rows()]  # D-325, D-335
    tutorials = [f"0.{k}" for k in range(1, 7)]
    assert labels == [
        *tutorials,
        "1.1",
        "1.2",
        "1.3",
        "1.4",
        "2.1",
        "3.1",
        "3.2",
        "3.3",
        "4.1",
        "4.2",
        "4.3",
        "5.1",
        "",  # made by users: unnumbered (D-510)
        "",
        "",  # the sandbox
    ]


def test_each_chapters_first_level_is_open_and_a_chapters_last_gives_no_word():
    router = a_router()  # D-325: the next chapter's first level is open from the start
    states = [router.state(k) for k in range(len(router.levels))]
    opened = FIRSTS | set(range(6)) | {AT["Dragster II"]}  # tutorials, made by users (D-348)
    assert states == ["open" if k in opened else "locked" for k in range(len(router.levels))]
    assert router.state(router.sandbox_index) == "sandbox"
    router.index = AT["Orbit"]
    assert router.next_passkey() is None
    router.mark_won()
    assert router.rows()[AT["Orbit"]].passkey == ""
    router.index = AT["Greed"]  # its word opens Patience
    assert router.next_passkey() == ("GOLD", "LEVEL 3.2")


def test_chapters_shows_the_chapter_being_played_and_folds_the_others_until_asked():
    router = a_router()  # D-326
    zero, one = "0. Tutorials", "1. Braitenberg"
    two, three = "2. Obstacles", "3. Many lights"
    assert zero not in router.folded and {one, two, three} <= router.folded
    router.fold(three)  # the player shows chapter 3 too
    router.next()  # 0.2: the same chapter, the folds kept
    assert router.folded & {zero, three} == set()
    router.index = AT["Orbit"]  # then Next level: Shadows, in chapter 2, which was folded
    router.next()
    assert router.label == "LEVEL 2.1" and two not in router.folded and one in router.folded
    router.open(router.sandbox_index)  # Free play keeps them
    assert two not in router.folded and one in router.folded
    router.fold(one)
    router.open(AT["Fear"])  # chapter 1 shows: nothing else folds
    assert router.folded & {one, two} == set()


def test_a_passkey_shows_the_chapter_of_the_level_it_opens():
    router = a_router()  # D-326
    assert "3. Many lights" in router.folded
    assert router.unlock("gold") == AT["Patience"]  # Greed's word opens Patience, 3.2
    assert "3. Many lights" not in router.folded


def test_chapters_rows_show_each_place_its_state_and_its_fastest_win():
    router = a_router()
    rows = router.rows()
    assert len(rows) == len(router.levels) + 1 and rows[-1].index == router.sandbox_index
    assert [row.state for row in rows[:3]] == ["open", "open", "open"]  # tutorials (D-335)
    fear = AT["Fear"]
    assert [row.state for row in rows[fear : fear + 3]] == ["open", "locked", "locked"]
    assert (rows[0].label, rows[0].current, rows[-1].label, rows[-1].state) == (
        "0.1",
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
    router.index = AT["Fear"]  # a level that hands out eyes
    router.begin()
    first = router.board.snapshot()
    router.record(Score(ticks=900, parts=4), first)
    router.board.place(Kind.EYE, (0, 0))
    later = router.board.snapshot()
    router.record(Score(ticks=600, parts=5), later)
    router.record(Score(ticks=700, parts=6), later)  # beaten by the 600-tick win
    router.record(Score(ticks=900, parts=4), later)  # the same score: its first board stays
    wins = router.wins(AT["Fear"])
    assert [(w.score.ticks, w.best) for w in wins] == [(600, True), (900, True), (700, False)]
    assert wins[1].board == first and wins[0].board == later and first != later
    assert router.wins(AT["Aggression"]) == ()


def test_files_lists_every_levels_wins_the_open_ones_first_then_the_chapters_order():
    router = a_router()  # D-092
    assert router.files() == ()
    fear, love = AT["Fear"], AT["Love"]
    for k, ticks in ((fear, 900), (love, 800), (love, 700)):
        router.index = k
        router.record(Score(ticks=ticks, parts=4), router.board.snapshot())
    router.index = love
    files = router.files()
    assert [(group.index, group.title) for group in files] == [
        (love, "1.3 Love"),
        (fear, "1.1 Fear"),
    ]
    assert files[0].wins == router.wins(love) and len(files[1].wins) == 1
    router.index = router.sandbox_index  # no wins of its own: the levels', in order
    assert [group.index for group in router.files()] == [fear, love]


def test_a_passkey_opens_the_level_after_the_one_whose_win_gives_it_and_those_before():
    router = a_router()  # D-075: LOVE is Fear's word, SWORD Aggression's, HEART Love's
    fear, love, orbit = AT["Fear"], AT["Love"], AT["Orbit"]
    assert router.state(love) == "locked" and router.unlock("nothing") is None
    assert router.unlock("  sword ") == love  # any case, spaces round it
    states = [router.state(k) for k in range(fear, orbit + 1)]
    assert states == ["open", "open", "open", "locked"]
    assert not router.won  # every level before it in its chapter, none won
    router.open(love)  # Love opens
    assert router.levels[-1].passkey is None  # the last gives no word (D-332)
    assert router.unlock("heart") == orbit and router.state(orbit) == "open"


def test_a_passkey_opens_levels_of_its_own_chapter_and_leaves_the_others_as_they_are():
    router = a_router()  # D-355: SNAIL, Patience's word, opens Two lights, 3.3
    assert router.unlock("snail") == AT["Two lights"]
    assert [router.state(AT[t]) for t in ("Greed", "Patience", "Two lights")] == ["open"] * 3
    assert [router.state(AT[t]) for t in ("Aggression", "Love", "Orbit")] == ["locked"] * 3
    assert router.unlock("moon") is None  # a chapter's last gives no word, and has none


def test_the_word_for_every_level_is_given_once_all_are_won_and_opens_them_all():
    router = a_router()  # D-355
    assert not router.unlock_every("snail") and router.state(AT["Orbit"]) == "locked"
    for k in range(len(router.levels) - 1):  # all won but the last
        router.index = k
        router.mark_won()
    assert not router.all_won and router.rows()[0].every_level == ""
    router.index = len(router.levels) - 1  # its win completes the set: the card says so
    assert router.next_passkey() is None
    router.mark_won()
    assert router.all_won and router.next_passkey() == (EVERY_LEVEL, "every level")
    assert router.rows()[AT["Fear"]].every_level == EVERY_LEVEL
    router.open(router.sandbox_index)
    assert router.next_passkey() is None  # the sandbox gives none
    fresh = a_router()  # another session: typed, it opens every level, none of them won
    assert fresh.unlock_every(" vehicles ")
    assert {fresh.state(k) for k in range(len(fresh.levels))} == {"open"} and not fresh.won


def test_a_win_card_names_the_word_for_the_next_level_and_chapters_once_it_is_won():
    router = a_router()
    router.begin()  # Wiring: the tutorials give no word, every one being open (D-335)
    assert router.next_passkey() is None
    fear = router.index = AT["Fear"]
    assert router.next_passkey() == ("LOVE", "LEVEL 1.2")
    assert router.rows()[fear].passkey == ""  # not won yet: not given away
    router.mark_won()
    assert router.rows()[fear].passkey == "LOVE" and router.rows()[fear + 1].passkey == ""
    router.open(len(router.levels) - 1)  # the last, open as chapter 4's are: no next (D-348)
    assert router.next_passkey() is None
    router.open(router.sandbox_index)
    assert router.next_passkey() is None


def test_the_editor_opens_on_the_sandbox_alone_and_the_board_and_the_run_go_on_from_it():
    router = a_router()  # D-301
    with pytest.raises(ValueError, match="only the sandbox"):
        router.open_editor()
    router.open(router.sandbox_index)
    router.begin()
    router.open_editor()
    assert router.screen is Screen.EDITOR and router.label == "YOUR LEVEL"
    router.run()
    assert router.screen is Screen.RUN
    router.open_editor()
    router.open_board()
    assert router.screen is Screen.BOARD


def test_the_editor_revises_the_sandboxs_level_alone_and_its_board_stays():
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


def test_the_sandbox_is_captioned_by_its_title_or_your_level_while_it_has_none():
    assert captioned(SANDBOX_LABEL, "") == "YOUR LEVEL"  # D-419
    assert captioned(SANDBOX_LABEL, "Dragster") == "Dragster"
    assert captioned("LEVEL 1.2", "Fear") == "LEVEL 1.2. Fear"  # D-034
