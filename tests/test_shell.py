"""The screens around the levels (D-035, D-054). shell.py imports no pygame."""

from nektoids.editor.layout import SCREEN
from nektoids.editor.shell import CARD, bottom_button


def test_the_card_and_the_bottom_button_sit_on_screen():
    for x, y, w, h in (CARD, bottom_button()):
        assert 0 <= x and x + w <= SCREEN[0] and 0 <= y and y + h <= SCREEN[1]
