"""Where the arena view puts things on the 960 x 640 screen, and what is under a given pixel.

Left, the arena, with a status line at its foot, and once a run is over a banner at its top with
Next level and Edit. Right, one column: at the top the title and two palettes, one row each: the
player (back to the editor, start again, one frame back, play or pause, one frame, fast forward)
and the view (zoom in, zoom out, move the view, centre, rays on or off); in the
middle the objectives, each with its bar; at the bottom the swimmer's wiring on its body. The
polar plot of the light at the eyes, a developer's tool, is an inset over the arena's top left
corner. Plain numbers, no pygame, so hit-testing is testable headless.
"""

from __future__ import annotations

from enum import Enum

from nektoids.editor.layout import (
    BUTTON,
    SCREEN,
    TOOL_KEYS,
    VIEW_KEYS,
    Rect,
    Tool,
    ViewButton,
    contains,
)

PANEL_WIDTH = 320  # the right column [px]
STATUS_HEIGHT = 32  # [px]
MARGIN = 16  # [px]
PANEL_LEFT = SCREEN[0] - PANEL_WIDTH
ARENA_AREA: Rect = (0, 0, PANEL_LEFT, SCREEN[1] - STATUS_HEIGHT)
TITLE_AT = (PANEL_LEFT + MARGIN, 12)
BUTTONS_TOP = 40  # the player's row; the view's is one pitch lower [px]
BUTTON_PITCH = 48  # [px], across and down
SCORE_AREA: Rect = (PANEL_LEFT, 146, PANEL_WIDTH, 156)
CIRCUIT_AREA: Rect = (PANEL_LEFT, 316, PANEL_WIDTH, SCREEN[1] - 316)
RULES = (140, 308)  # y of the separators between the three parts of the column
POLAR_BOX: Rect = (8, 8, 236, 252)  # over the arena's top left corner
POLAR_CENTRE = (POLAR_BOX[0] + POLAR_BOX[2] // 2, POLAR_BOX[1] + 128)
POLAR_RADIUS = 80  # of the plot's circle [px]


class ArenaButton(Enum):
    EDIT = "edit"  # back to the editor, the board as it was
    NEXT = "next"  # on to the next level, once this one is won: in the banner
    RESTART = "restart"
    BACK = "back"  # one frame back
    PLAY = "play"  # play or pause, the one button
    STEP = "step"  # one frame on
    FAST = "fast"  # fast forward, on or off
    ZOOM_IN = "zoom in"
    ZOOM_OUT = "zoom out"
    HAND = "hand"  # dragging moves the view, on or off
    CENTRE = "centre"  # on the swimmers and the lights, all in view
    LIGHT = "light"  # the light's rays, shown or not


PLAYER = (
    ArenaButton.EDIT,
    ArenaButton.RESTART,
    ArenaButton.BACK,
    ArenaButton.PLAY,
    ArenaButton.STEP,
    ArenaButton.FAST,
)
VIEW = (
    ArenaButton.ZOOM_IN,
    ArenaButton.ZOOM_OUT,
    ArenaButton.HAND,
    ArenaButton.CENTRE,
    ArenaButton.LIGHT,
)
# One key, one meaning, in the editor and here: the view's keys are the editor's own, and no key
# the editor uses means anything else here (R rotates there, so starting again is 0: t = 0).
BUTTON_KEYS = {
    ArenaButton.EDIT: "Esc",  # leave the run, as Escape leaves a gesture in the editor
    ArenaButton.NEXT: "Enter",
    ArenaButton.RESTART: "0",
    ArenaButton.BACK: ",",
    ArenaButton.PLAY: "Space",
    ArenaButton.STEP: ".",
    ArenaButton.FAST: "F",
    ArenaButton.ZOOM_IN: VIEW_KEYS[ViewButton.ZOOM_IN],
    ArenaButton.ZOOM_OUT: VIEW_KEYS[ViewButton.ZOOM_OUT],
    ArenaButton.HAND: VIEW_KEYS[ViewButton.PAN],
    ArenaButton.CENTRE: VIEW_KEYS[ViewButton.CENTRE],
    ArenaButton.LIGHT: "X",  # the rays, as in x-rays: L turns left (D-025)
}
# Keys with no button, for developers: turn the swimmer, the light map, the polar plot.
TURN_KEYS = (TOOL_KEYS[Tool.TURN_LEFT], TOOL_KEYS[Tool.TURN_RIGHT])  # the editor's: L, R
MAP_KEY, POLAR_KEY = "I", "P"
# Typed characters that press a button; Space, 0, Esc and Enter are matched on the physical key.
KEY_BUTTONS = {key: b for b, key in BUTTON_KEYS.items() if len(key) == 1 and not key.isdigit()}


def button_rects() -> tuple[tuple[ArenaButton, Rect], ...]:
    """The player's palette on one row, the view's on the next, both centred in the column."""
    rects = []
    for row, palette in enumerate((PLAYER, VIEW)):
        width = BUTTON + (len(palette) - 1) * BUTTON_PITCH
        left = PANEL_LEFT + (PANEL_WIDTH - width) // 2
        top = BUTTONS_TOP + row * BUTTON_PITCH
        rects += [
            (b, (left + k * BUTTON_PITCH, top, BUTTON, BUTTON)) for k, b in enumerate(palette)
        ]
    return tuple(rects)


def button_at(point: tuple[int, int]) -> ArenaButton | None:
    return next((button for button, rect in button_rects() if contains(rect, point)), None)


BANNER: Rect = (ARENA_AREA[0] + (ARENA_AREA[2] - 320) // 2, 16, 320, 132)  # over the arena's top
BANNER_BUTTON = (132, 32)  # [px]


def banner_rects(
    buttons: tuple[ArenaButton, ...],
) -> tuple[tuple[ArenaButton, Rect], ...]:
    """The banner's buttons, side by side along its foot, centred."""
    x, y, w, h = BANNER
    bw, bh = BANNER_BUTTON
    gap = 16
    width = len(buttons) * bw + (len(buttons) - 1) * gap
    left, top = x + (w - width) // 2, y + h - bh - 12
    return tuple((b, (left + k * (bw + gap), top, bw, bh)) for k, b in enumerate(buttons))


def banner_button_at(
    buttons: tuple[ArenaButton, ...], point: tuple[int, int]
) -> ArenaButton | None:
    return next((b for b, rect in banner_rects(buttons) if contains(rect, point)), None)
