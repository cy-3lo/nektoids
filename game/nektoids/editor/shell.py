"""Where the screens around the levels put things (D-035), and what is under a given pixel.

The card, centred over a level's Board: the title card over the first, then each level's own as
it opens; the end screen, its text and a button back to the Board, Chapters open (D-054). The
full-screen map is gone: Chapters, a drawer, lists the levels. Plain numbers, no pygame, so
hit-testing is testable headless.
"""

from __future__ import annotations

from nektoids.editor.layout import SCREEN, Rect

CARD: Rect = (SCREEN[0] // 2 - 300, 150, 600, 300)  # the title card, or a level's
BUTTON_SIZE = (200, 40)  # the end screen's Chapters [px]
END_KEY = "Esc"  # leave the end for the Board, Chapters open


def bottom_button() -> Rect:
    """The end screen's Chapters, at the foot of the screen, centred."""
    w, h = BUTTON_SIZE
    return ((SCREEN[0] - w) // 2, SCREEN[1] - 40 - h, w, h)
