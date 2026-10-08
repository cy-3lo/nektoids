"""A field of text, and its text in lines (D-206, D-305). textfield.py imports no pygame."""

from nektoids.editor.textfield import LONGEST, TextField, caret_at, wrapped


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
