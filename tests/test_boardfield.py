"""Load's field and loading a board's text (D-206). boardfield.py imports no pygame."""

from nektoids.editor.boardfield import LONGEST, BoardField, load
from nektoids.graph.board import Kind
from nektoids.graph.boardtext import to_text
from nektoids.graph.hexgrid import NW, SW
from nektoids.levels.arenas import arenas
from nektoids.levels.sandbox import tutorial_board

LEVELS = {level.title: level for level in arenas()}


def fear():
    board = LEVELS["Fear"].new_board()
    eyes = [board.place(Kind.EYE, c, facing=f) for c, f in (((2, -1), NW), ((1, 1), SW))]
    thrusters = [board.place(Kind.THRUSTER, cell) for cell in ((1, -2), (-1, 2))]
    for eye, thruster in zip(eyes, thrusters, strict=True):
        board.connect(eye.id, thruster.id)
    return board


def built(board):
    return sorted((n.kind.value, n.cell, n.facing or 0) for n in board.nodes.values()), [
        w.path for w in board.wires
    ]


def test_the_field_takes_a_boards_characters_and_ends_on_enter_or_escape():
    field = BoardField()
    for char in "2Sv#b k":
        assert field.type(char, char) is None
    assert field.text == "2Svb k"  # no board has '#'; a space may be typed, and is read past
    assert field.type("backspace", "") is None and field.text == "2Svb "
    assert field.type("return", "\r") == "enter" and field.type("escape", "\x1b") == "escape"
    field.paste("x" * 1000)
    assert len(field.text) == LONGEST


def test_a_boards_text_goes_on_the_level_and_says_so():
    board = LEVELS["Fear"].new_board()
    loaded, said = load(board, to_text(fear()))
    assert loaded and said == "Loaded: 4 parts, 2 wires."
    assert built(board) == built(fear())
    text = to_text(fear())
    typo = ("Z" if text[5] != "Z" else "Y").join((text[:5], text[6:]))
    assert load(LEVELS["Fear"].new_board(), typo) == (
        True,
        "Loaded: 4 parts, 2 wires, one mistyped character put right.",
    )


def test_a_text_the_level_cannot_hold_or_no_board_at_all_leaves_the_board_and_says_why():
    greed = LEVELS["Greed"].new_board()
    eye, double, thruster = (
        greed.place(Kind.EYE, (-1, -1)),
        greed.place(Kind.DOUBLE, (0, -1)),
        greed.place(Kind.THRUSTER, (2, -1)),
    )
    greed.connect(eye.id, double.id)
    greed.connect(double.id, thruster.id)
    board = fear()
    before = built(board)
    for text, why in (
        (to_text(greed), "this level hands out no doubles"),
        ("", "paste a board's text into the field first"),
        ("hello world", "this text holds no board: mistyped, or of another version"),
    ):
        assert load(board, text) == (False, why)
        assert built(board) == before


def test_the_levels_locked_parts_are_the_texts_parts_on_their_cells():
    crossed = tutorial_board()  # its eyes and thrusters are placed by the level, locked
    eyes = sorted(n.id for n in crossed.nodes.values() if n.kind is Kind.EYE)
    thrusters = sorted(n.id for n in crossed.nodes.values() if n.kind is Kind.THRUSTER)
    crossed.connect(eyes[0], thrusters[1])
    crossed.connect(eyes[1], thrusters[0])
    board = tutorial_board()
    assert load(board, to_text(crossed))[0]
    assert sorted(n.locked for n in board.nodes.values()) == [True] * 4
    assert built(board) == built(crossed)
    assert load(tutorial_board(), to_text(fear())) == (False, "this level places other parts")
