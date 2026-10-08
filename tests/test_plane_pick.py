"""What is picked on the Editor's plane (D-410). plane_pick.py imports no pygame."""

from nektoids.editor.layout import Piece
from nektoids.editor.plane_pick import (
    NOTHING,
    after_removal,
    boxed,
    clicked,
    items,
)


def test_a_click_picks_one_object_the_add_key_adds_or_drops_one():
    pick = clicked(NOTHING, 2)
    assert pick == (2,) and clicked(pick, 3) == (3,) and clicked(pick, 2) == NOTHING
    assert clicked(pick, None) == NOTHING  # the open plane
    both = clicked(clicked(pick, Piece.START, add=True), 4, add=True)
    assert both == (2, Piece.START, 4) and clicked(both, 2, add=True) == (Piece.START, 4)
    assert clicked(both, None, add=True) == both
    assert items(both) == [2, 4]


def test_a_rectangle_picks_the_objects_whose_centres_lie_inside_it():
    centres = {0: (10.0, 10.0), 1: (50.0, 60.0), 2: (90.0, 20.0), Piece.START: (40.0, 30.0)}
    assert boxed(NOTHING, centres, (0, 0), (60, 61)) == (0, 1, Piece.START)
    assert boxed(NOTHING, centres, (60, 61), (0, 0)) == (0, 1, Piece.START)  # either way
    assert boxed((2,), centres, (45, 55), (55, 65)) == (1,)  # a new pick
    assert boxed((2,), centres, (45, 55), (55, 65), add=True) == (2, 1)  # Shift: added


def test_the_pick_follows_the_items_when_some_go():
    assert after_removal((0, 2, Piece.START, 5), [2, 3]) == (0, Piece.START, 3)
