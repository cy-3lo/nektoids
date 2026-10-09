"""A level shared as a few lines of text, the level as one word (D-413). levelword.py imports no
pygame."""

import random
from dataclasses import replace

import pytest

from nektoids.graph import boardtext
from nektoids.graph.board import Kind
from nektoids.graph.spelling import ALPHABET
from nektoids.levels import levelword, making, objectives
from nektoids.levels.arenas import arenas, sandbox
from nektoids.levels.level import Item, ItemKind, Level
from nektoids.levels.levelword import from_word, read_shared, to_shared, to_word

LEVELS = {level.title: level for level in (*arenas(), sandbox())}
DRAGSTER = LEVELS["Dragster"]


def _played(level: Level) -> Level:
    """What the word and the lines hold of a level: neither its board's free parts and wires,
    nor a part it hands out none of, nor its tutorial, passkey or proof."""
    board = dict(level.board)
    board["stock"] = {kind: n for kind, n in board["stock"].items() if n != 0}
    board["parts"], board["wires"] = [p for p in board["parts"] if p["locked"]], []
    return replace(level, board=board, tutorial=None, passkey=None, proof=None)


@pytest.mark.parametrize("level", LEVELS.values(), ids=lambda level: level.title)
def test_every_shipped_level_is_shared_and_read_back_as_it_is_played(level):
    text = to_shared(level)
    assert _played(read_shared(text)) == _played(level)
    assert len(to_word(level)) <= 40  # Orbit's, 35, the longest


@pytest.mark.parametrize(
    "title, word",  # as v1.1 wrote them, before the Tank and the hues (D-501)
    [("Fear", "ba9FDD6LtkJyk40FsuZaZ9m8Fx"), ("Aggression", "1RpbHBm8yv94r6vrUP3CkBu")],
)
def test_a_word_of_version_31_still_reads_as_it_was_written(title, word):
    assert from_word(word)[0] == from_word(to_word(LEVELS[title]))[0]


def test_a_level_placing_painted_parts_reads_back_painted():
    level = LEVELS["Fear"]
    board = dict(level.board)
    board["parts"] = [
        {**part, "hue": "violet"} if part["locked"] else part for part in level.board["parts"]
    ]
    painted = replace(level, board=board)
    parts = from_word(to_word(painted))[0].board["parts"]
    assert parts and all(part["hue"] == "violet" for part in parts)


def test_a_made_level_far_from_the_origin_with_every_kind_of_item_and_goal_reads_back():
    rng = random.Random(4)
    for _ in range(20):
        items = tuple(
            Item(
                kind, (rng.randint(-200, 200) * 3.0, rng.randint(-40, 40) * 3.0), rng.randint(1, 8)
            )
            for kind in rng.choices(list(ItemKind), k=rng.randint(1, 6))
        )
        goals = (
            objectives.Goal(
                objectives.Verb.STAY, objectives.Count.ONE, objectives.Target.MARK, 37.0
            ),
            objectives.Goal(objectives.Verb.REACH, objectives.Count.NONE, objectives.Target.LIGHT),
        )
        stock = {kind.value: rng.choice(making.STOCK) for kind in Kind}
        level = replace(
            LEVELS["Fear"],
            start=(rng.randint(-99, 99), 1000.0, float(rng.randrange(360))),
            items=items,
            board={**LEVELS["Fear"].board, "stock": stock},
            time_limit=float(rng.randint(1, 120)),
            objectives=goals,
        )
        play, corrected = from_word(to_word(level))
        assert (play.start, play.items, play.time_limit, play.objectives) == (
            level.start,
            level.items,
            level.time_limit,
            level.objectives,
        )
        assert play.board == _played(level).board and not corrected


def test_the_lines_are_found_by_their_labels_in_any_order_among_other_words():
    signed = replace(DRAGSTER, author="@Camille")
    lines = to_shared(signed, "rcAmD6PrhXQv").splitlines()
    assert [line.split(":")[0] for line in lines] == list(levelword.LABELS)
    for text in (
        "\n".join(lines),
        "\n".join(reversed(lines)),
        "Hello,\n\n" + "\n".join(lines) + "\n-- \nSent from my phone",
        " ".join(lines),  # a field of one line: its line breaks spaces (`textfield.py`)
    ):
        read = read_shared(text)
        assert (read.title, read.author, read.spec) == (signed.title, "@Camille", signed.spec)
        assert _played(read) == _played(signed) and read.proof["board"] == "rcAmD6PrhXQv"
    alone = read_shared(to_word(DRAGSTER))  # a word alone: a level untitled
    assert (alone.title, alone.author) == (levelword.UNTITLED[0], None)
    assert read_shared(to_shared(DRAGSTER)).proof is None  # Copy level: no board, a draft


def test_one_wrong_character_is_put_right_two_are_refused():
    word = to_word(LEVELS["Orbit"])
    one = word[:5] + ALPHABET[(ALPHABET.index(word[5]) + 1) % 59] + word[6:]
    assert from_word(one) == (from_word(word)[0], True)
    two = one[:9] + ALPHABET[(ALPHABET.index(one[9]) + 1) % 59] + one[10:]
    with pytest.raises(ValueError, match="holds no level"):
        from_word(two)


def test_a_boards_text_is_never_read_as_a_level_nor_a_levels_word_as_a_board():
    board = boardtext.to_text(LEVELS["Love"].new_board())
    with pytest.raises(ValueError, match="a board's text: paste it on the Board"):
        from_word(board)
    with pytest.raises(ValueError, match="holds no board"):
        boardtext.from_text(to_word(LEVELS["Love"]))


def test_a_value_off_the_lattice_is_refused_as_no_word_can_hold_it():
    with pytest.raises(ValueError, match="cannot hold"):
        to_word(replace(DRAGSTER, start=(0.5, 0.0, 0.0)))
    with pytest.raises(ValueError, match="cannot hold"):
        to_word(replace(DRAGSTER, time_limit=121.0))


def test_the_words_ranges_are_the_editors():
    assert levelword.STOCK == making.STOCK
    assert levelword.GOALS == range(making.GOALS_MOST + 1)
    assert (levelword.TIMES[0], levelword.TIMES[-1]) == (making.TIME.lo, making.TIME.hi)
    for scale in making.SETTING.values():
        assert (levelword.SETTINGS[0], levelword.SETTINGS[-1]) == (scale.lo, scale.hi)
    seconds = objectives.SECONDS
    assert (levelword.STAYS[0], levelword.STAYS[-1]) == (seconds.lo, seconds.hi)
