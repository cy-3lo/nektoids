"""Where the screens around the levels put things (D-035), and what is under a given pixel.

The title card, centred over the first level's editor; the map, a list: one row for each level
of the chapter, then the sandbox's apart, and a button back to the open level; the end screen,
its text and a button to the map. Plain numbers, no pygame, so hit-testing is testable headless.
"""

from __future__ import annotations

from nektoids.editor.layout import SCREEN, Rect, contains

CARD: Rect = (SCREEN[0] // 2 - 260, 150, 520, 300)  # the title card, over the first level
ROW_WIDTH, ROW_HEIGHT, ROW_PITCH = 600, 52, 60  # [px]
MAP_TOP = 120  # the first row [px]; the chapter's name sits over it
SANDBOX_GAP = 24  # between the chapter's last row and the sandbox's [px]
BUTTON_SIZE = (200, 40)  # the map's Back and the end screen's Map [px]
BACK_KEY = END_KEY = "Esc"  # leave the map for the open level; leave the end for the map


def map_rows(levels: int) -> tuple[Rect, ...]:
    """The rows of the chapter's `levels` levels, then the sandbox's."""
    left = (SCREEN[0] - ROW_WIDTH) // 2
    rows = [(left, MAP_TOP + k * ROW_PITCH, ROW_WIDTH, ROW_HEIGHT) for k in range(levels)]
    rows.append((left, MAP_TOP + levels * ROW_PITCH + SANDBOX_GAP, ROW_WIDTH, ROW_HEIGHT))
    return tuple(rows)


def map_row_at(levels: int, point: tuple[int, int]) -> int | None:
    """The place under `point`: a level's index, `levels` for the sandbox, None for neither."""
    return next((k for k, rect in enumerate(map_rows(levels)) if contains(rect, point)), None)


def bottom_button() -> Rect:
    """The map's Back and the end screen's Map, at the foot of the screen, centred."""
    w, h = BUTTON_SIZE
    return ((SCREEN[0] - w) // 2, SCREEN[1] - 40 - h, w, h)
