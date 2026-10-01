"""The screens around the levels (D-035). shell.py imports no pygame."""

from nektoids.editor.layout import SCREEN, contains
from nektoids.editor.shell import CARD, bottom_button, map_row_at, map_rows


def centre(rect):
    x, y, w, h = rect
    return (x + w // 2, y + h // 2)


def test_the_map_lists_the_route_then_the_sandbox_apart_all_on_screen():
    rows = map_rows(2)
    assert len(rows) == 3
    (_, y0, _, h0), (_, y1, _, h1), (_, ys, _, _) = rows
    assert y0 + h0 < y1 and ys - (y1 + h1) > y1 - (y0 + h0)  # the sandbox stands apart
    for k, rect in enumerate(rows):
        assert contains((0, 0, *SCREEN), rect[:2]) and map_row_at(2, centre(rect)) == k
    assert rows[-1][1] + rows[-1][3] < bottom_button()[1]
    assert map_row_at(2, (5, 5)) is None


def test_the_card_and_the_bottom_button_sit_on_screen():
    for x, y, w, h in (CARD, bottom_button()):
        assert 0 <= x and x + w <= SCREEN[0] and 0 <= y and y + h <= SCREEN[1]
