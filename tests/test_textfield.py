"""A field of text, and its text in lines (D-206, D-305). textfield.py imports no pygame."""

from nektoids.editor.textfield import (
    LONGEST,
    TextField,
    caret_at,
    index_at,
    index_in_lines,
    shown_from,
    wrapped,
)


def keys(field: TextField, *typed: str) -> None:
    for key in typed:
        field.type(key, key if len(key) == 1 else "")


def test_a_field_types_at_its_caret_which_the_arrows_home_and_end_move():
    field = TextField("Fear")
    assert field.caret == 4 and field.longest == LONGEST
    keys(field, "left", "left", "x")
    assert (field.text, field.caret) == ("Fexar", 3)
    keys(field, "backspace", "delete")
    assert (field.text, field.caret) == ("Fer", 2)
    keys(field, "home", "backspace", "A", "end", "!")
    assert (field.text, field.caret) == ("AFer!", 5)
    keys(field, "right", "right")
    assert field.caret == 5  # no farther than the text
    assert field.type("return", "\r") == "enter" and field.type("escape", "\x1b") == "escape"


def test_a_field_takes_what_it_says_as_far_as_it_may_grow_pasted_at_the_caret():
    free = TextField(longest=11)
    free.paste("Two\nlight")  # a pasted line break, which it does not take, a space (D-413)
    assert (free.text, free.caret) == ("Two light", 9)
    free.type("tab", "\t")
    free.paste("sxyz")
    assert free.text == "Two lightsx" and free.caret == 11
    board = TextField(taken=frozenset("abc"), longest=5)
    board.paste("a#b c")
    assert board.text == "abc"
    assert TextField("x" * 99, longest=5).text == "xxxxx"


def test_what_the_pages_field_holds_comes_in_its_caret_moved_back_past_what_is_left_out():
    field = TextField(taken=frozenset("ab"))
    field.take("a#b#a", 4)  # the caret after "a#b#": two kept before it
    assert (field.text, field.caret) == ("aba", 2)


def test_text_wraps_after_a_space_where_one_fits_else_anywhere_and_each_line_knows_its_start():
    fits = lambda line: len(line.rstrip()) <= 8  # noqa: E731 - eight characters a line
    lines = wrapped("Touch all three lights.", fits)
    assert lines == [(0, "Touch "), (6, "all "), (10, "three "), (16, "lights.")]
    assert wrapped("Avoidtheshadows", fits) == [(0, "Avoidthe"), (8, "shadows")]
    assert wrapped("", fits) == [(0, "")]
    assert caret_at(lines, 0) == (0, 0) and caret_at(lines, 8) == (1, 2)
    assert caret_at(lines, 23) == (3, 7)  # after the last character


def test_shift_and_the_arrows_select_and_what_is_typed_replaces_the_selection():
    field = TextField("Two lights")  # D-418
    for _ in range(6):
        field.type("left", "", shift=True)
    assert field.selection == (4, 10) and field.selected() == "lights"
    field.type("x", "x")
    assert (field.text, field.caret, field.selection) == ("Two x", 5, None)
    field.type("home", "", shift=True)
    field.type("backspace", "")
    assert (field.text, field.caret) == ("", 0)


def test_an_arrow_without_shift_drops_the_selection_at_its_end_that_way():
    field = TextField("Fear")
    field.type("a", "a", command=True)  # Ctrl/Cmd+A: it all
    assert field.selection == (0, 4) and field.text == "Fear"
    field.type("left", "")
    assert (field.caret, field.selection) == (0, None)
    field.type("end", "", shift=True)
    field.type("right", "")
    assert (field.caret, field.selection) == (4, None)


def test_delete_cut_and_paste_act_on_the_selection():
    field = TextField("Love and Fear", longest=14)
    field.place(5)
    field.place(9, extend=True)  # a drag from 5 to 9: "and "
    assert field.selected() == "and "
    assert field.cut() == "and " and (field.text, field.caret) == ("Love Fear", 5)
    field.place(0)
    field.place(4, extend=True)
    field.paste("Hope and all")  # in place of "Love", as far as the field may grow: 9 more
    assert (field.text, field.caret, field.selection) == ("Hope and  Fear", 9, None)
    field.place(0)
    field.place(5, extend=True)
    field.type("delete", "")
    assert (field.text, field.caret) == ("and  Fear", 0)


def test_the_page_field_brings_its_selection_web():
    field = TextField()
    field.take("Orbit\nring", caret=2, anchor=7)  # the line break a space
    assert (field.text, field.caret, field.anchor) == ("Orbit ring", 2, 7)
    field.take("Orbit", caret=3, anchor=3)
    assert field.selection is None


def test_a_click_finds_the_place_between_two_characters_as_the_field_draws_them():
    text, advance = "Two lights, four obstacles", 10.0
    assert index_at(text, 0, advance, 34) == 3 and index_at(text, 0, advance, 36) == 4
    assert index_at(text, 0, advance, -20) == 0 and index_at(text, 0, advance, 999) == len(text)
    start = shown_from(text, len(text), lambda part: len(part) * advance <= 100)
    assert start == len(text) - 10  # slid left to show the caret, ten characters fit
    assert index_at(text, start, advance, 0) == start
    lines = wrapped(text, lambda line: len(line.rstrip()) * advance <= 120)
    assert [words for _, words in lines] == ["Two lights, ", "four ", "obstacles"]
    assert index_in_lines(lines, 0, advance, 999) == 11  # before the space that breaks it
    assert index_in_lines(lines, 9, advance, 15) == lines[2][0] + 2  # past the last line
