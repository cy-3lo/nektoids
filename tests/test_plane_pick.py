"""What is picked on the Editor's plane (D-410). plane_pick.py imports no pygame."""

from nektoids.editor.layout import Piece
from nektoids.editor.plane_pick import (
    NOTHING,
    after_removal,
    begun,
    clicked,
    crossed,
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


def test_a_drag_picks_what_it_crosses_and_going_back_cuts_its_path_back():
    sweep = begun(NOTHING)
    for target in (None, 0, None, 1, 2, 3):
        sweep = crossed(sweep, target)
    assert sweep.pick == (0, 1, 2, 3)
    assert crossed(sweep, 1).pick == (0, 1)  # two back at once
    kept = begun((5,), add=True)
    assert crossed(crossed(kept, 0), 5).pick == (5, 0)  # picked before: kept, not doubled


def test_the_pick_follows_the_items_when_some_go():
    assert after_removal((0, 2, Piece.START, 5), [2, 3]) == (0, Piece.START, 3)
