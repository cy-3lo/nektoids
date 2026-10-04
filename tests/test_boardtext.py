"""A board as text (D-205). boardtext.py imports no pygame."""

import random

import pytest

from nektoids.graph import boardtext
from nektoids.graph.board import Board, Kind, Refused
from nektoids.graph.boardtext import ALPHABET, from_text, to_text
from nektoids.graph.hexgrid import NW, SW, E, hex_disc, offset_rect
from nektoids.levels.arenas import arenas

LEVELS = {level.title: level for level in arenas()}


def parts_and_wires(board):
    """What a text keeps: parts in id order, wires in drawing order by their parts' places."""
    ids = sorted(board.nodes)
    index = {node_id: k for k, node_id in enumerate(ids)}
    parts = [(board.nodes[i].kind, board.nodes[i].cell, board.nodes[i].facing) for i in ids]
    wires = [(index[w.source], index[w.target], w.path) for w in board.wires]
    return sorted(board.cells), parts, wires


def fear():
    """Fear's model board (D-039): eyes at the front looking out, each to its own side."""
    board = LEVELS["Fear"].new_board()
    eyes = [board.place(Kind.EYE, c, facing=f) for c, f in (((2, -1), NW), ((1, 1), SW))]
    thrusters = [board.place(Kind.THRUSTER, cell) for cell in ((1, -2), (-1, 2))]
    for eye, thruster in zip(eyes, thrusters, strict=True):
        board.connect(eye.id, thruster.id)
    return board


def random_board(rng, radius):
    """Parts of every kind placed at random, wires drawn at random; then a few moves, a part
    put on a wire and taken off, so that some wires are left off the router's path."""
    board = Board(hex_disc(radius))
    cells = list(board.cells)
    rng.shuffle(cells)
    for cell in cells[: rng.randint(0, len(cells) // 2)]:
        kind = rng.choice(list(Kind))
        board.place(
            kind, cell, facing=rng.randrange(6) if kind.default_facing is not None else None
        )
    ids = sorted(board.nodes)
    for _ in range(rng.randint(0, 2 * len(ids))):
        if len(ids) > 1:
            board.connect(*rng.sample(ids, 2))
    for _ in range(3):
        free = [c for c in board.cells if board.node_at(c) is None]
        if ids and free:
            board.move_node(rng.choice(ids), rng.choice(free))
        crossed = [c for w in board.wires for c in w.path[1:-1]]
        if crossed:
            block = board.place(Kind.SUM, rng.choice(crossed))  # the wire goes round it...
            if not isinstance(block, Refused):
                board.remove_node(block.id)  # ... and stays round when it goes
    return board


def test_fears_board_is_a_short_line_and_comes_back_the_same():
    board = fear()
    text = to_text(board)
    assert text == "2Svbskor23U3aec"  # a change here is a new format: raise VERSION (D-205)
    assert set(text) <= set(ALPHABET) and to_text(board) == text
    assert parts_and_wires(from_text(text)) == parts_and_wires(board)


@pytest.mark.parametrize("seed", range(40))
def test_every_board_comes_back_the_same_routes_and_all(seed):
    rng = random.Random(seed)
    board = random_board(rng, rng.choice((1, 2, 3)))
    assert parts_and_wires(from_text(to_text(board))) == parts_and_wires(board)


def test_a_board_too_long_for_a_block_takes_several():
    rng = random.Random(7)
    board = Board(hex_disc(3))
    for cell in board.cells:  # all 37 cells
        kind = rng.choice(list(Kind))
        board.place(
            kind, cell, facing=rng.randrange(6) if kind.default_facing is not None else None
        )
    text = to_text(board)
    assert len(text) > boardtext.BLOCK + boardtext.CHECKS
    assert parts_and_wires(from_text(text)) == parts_and_wires(board)
    second = boardtext.BLOCK + boardtext.CHECKS + 3  # a typo in the second block
    typo = text[:second] + ("Z" if text[second] != "Z" else "Y") + text[second + 1 :]
    assert parts_and_wires(from_text(typo)) == parts_and_wires(board)


def test_one_wrong_character_is_put_right_and_two_are_refused():
    text, rng = to_text(fear()), random.Random(3)
    board = parts_and_wires(fear())
    for i in range(len(text)):
        for char in ALPHABET:
            if char != text[i]:
                assert parts_and_wires(from_text(text[:i] + char + text[i + 1 :])) == board
    for i in range(len(text) - 1):  # two neighbours swapped
        if text[i] != text[i + 1]:
            with pytest.raises(ValueError, match="mistyped"):
                from_text(text[:i] + text[i + 1] + text[i] + text[i + 2 :])
    for _ in range(500):  # any two wrong
        wrong = list(text)
        for i in rng.sample(range(len(text)), 2):
            wrong[i] = rng.choice([c for c in ALPHABET if c != text[i]])
        with pytest.raises(ValueError, match="mistyped"):
            from_text("".join(wrong))


def test_a_text_of_another_version_is_refused(monkeypatch):
    monkeypatch.setattr(boardtext, "VERSION", 2)
    text = to_text(fear())
    monkeypatch.setattr(boardtext, "VERSION", 1)
    with pytest.raises(ValueError, match="another version"):
        from_text(text)


def test_a_person_may_space_it_dash_it_and_mistake_I_l_O_for_1_and_0():
    text = to_text(fear())
    spaced = "-".join(text[i : i + 4] for i in range(0, len(text), 4))
    assert parts_and_wires(from_text(f"  {spaced} ")) == parts_and_wires(fear())
    assert boardtext.READ["I"] == boardtext.READ["l"] == boardtext.READ["1"]
    assert boardtext.READ["O"] == boardtext.READ["0"]
    with pytest.raises(ValueError, match="character '#'"):
        from_text(text + "#")


def test_a_body_that_is_not_a_disc_and_a_part_not_yet_made_have_no_text():
    with pytest.raises(ValueError, match="disc"):
        to_text(Board(offset_rect(9, 7)))

    def picks(tag, options):
        return options[2] if tag == "zone" else (1 if tag == "parts" else options[-1])

    with pytest.raises(ValueError, match="does not have"):
        boardtext._replay(picks)  # the last kind code, kept for a part to come


def test_kinds_keep_their_codes_as_new_ones_come_after_them():
    first = ["eye", "source", "double", "halve", "sum", "difference", "thruster"]
    assert [kind.value for kind in Kind][: len(first)] == first  # D-205: append only
    assert len(Kind) <= boardtext.CAPACITY


def test_a_board_read_from_text_goes_on_a_level_as_a_win_does_or_says_why_not():
    greed = LEVELS["Greed"].new_board()
    eyes = [greed.place(Kind.EYE, c, facing=E) for c in ((-1, -1), (-2, 1))]
    thrusters = [greed.place(Kind.THRUSTER, c) for c in ((2, -1), (1, 1))]
    doubles = [greed.place(Kind.DOUBLE, c) for c in ((0, -1), (0, 1))]
    for a, b in ((eyes[0], doubles[0]), (doubles[0], thrusters[1])):
        greed.connect(a.id, b.id)
    read = from_text(to_text(greed))
    assert (
        LEVELS["Fear"].new_board().adopt(read.snapshot()).reason
        == "this level hands out no doubles"
    )
    assert LEVELS["Greed"].new_board().adopt(from_text(to_text(fear())).snapshot()) is None
