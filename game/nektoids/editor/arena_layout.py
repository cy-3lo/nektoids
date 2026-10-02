"""Where the run puts its own things in the frame it shares with the editor (D-051, D-057), and
what is under a given pixel.

The frame (`layout.make_layout(env=Env.RUN)`) gives the bar, the drawers, the tabs, the level's
line under them, the arena as the main screen and a strip under it for the controls. In that
strip, from the left: start again, play or pause, a step of 0.1 s, fast forward; the timeline;
how many of the objectives are met (D-060). Once a run is over, a banner at the arena's top
offers Next level and Edit. Inside and Score draw in the drawer's body, under its title. The
polar plot of the light at the eyes, a developer's tool, is an inset over the arena's top left
corner. Plain numbers, no pygame, so hit-testing is testable headless.
"""

from __future__ import annotations

from enum import Enum

from nektoids.editor.layout import (
    BAR_WIDTH,
    DRAWER_TOP,
    DRAWER_WIDTH,
    MARGIN,
    TITLE_HEIGHT,
    TOOL_KEYS,
    VIEW_KEYS,
    Layout,
    Rect,
    Tool,
    ViewButton,
    contains,
)

CONTROL = 32  # a control's square button [px]
CONTROL_PITCH = 38  # from one to the next [px]
SUMMARY_WIDTH = 132  # right of the timeline: so many objectives met of so many [px]
TIMELINE_HEIGHT = 20  # what a press on it catches [px]
TIMELINE_BAR = 8  # the bar's height, centred in it [px]
DRAWER_BODY: Rect = (BAR_WIDTH, DRAWER_TOP + TITLE_HEIGHT, DRAWER_WIDTH, 300)  # Inside, Score
BANNER_SIZE = (352, 132)  # [px]
BANNER_BUTTON = (160, 32)  # [px]
POLAR_SIZE = (300, 252)  # the developer's inset [px]
POLAR_RADIUS = 80  # of the plot's circle [px]


class ArenaButton(Enum):
    EDIT = "edit"  # back to the editor, the board as it was
    NEXT = "next"  # on to the next level, once this one is won: in the banner
    RESTART = "restart"
    PLAY = "play"  # play or pause, the one button
    STEP = "step"  # a step on: STEP_FRAMES frames, 0.1 s
    FAST = "fast"  # fast forward, on or off
    ZOOM_IN = "zoom in"
    ZOOM_OUT = "zoom out"
    HAND = "hand"  # dragging moves the view, on or off
    CENTRE = "centre"  # on the swimmers and the lights, all in view
    LIGHT = "light"  # the light's rays, shown or not


CONTROLS = (ArenaButton.RESTART, ArenaButton.PLAY, ArenaButton.STEP, ArenaButton.FAST)
VIEW_BUTTON = {  # Navigator's rows, as the run's buttons
    ViewButton.ZOOM_IN: ArenaButton.ZOOM_IN,
    ViewButton.ZOOM_OUT: ArenaButton.ZOOM_OUT,
    ViewButton.PAN: ArenaButton.HAND,
    ViewButton.CENTRE: ArenaButton.CENTRE,
    ViewButton.RAYS: ArenaButton.LIGHT,
}
# One key, one meaning, in the editor and here: the view's keys are the editor's own, and no key
# the editor uses means anything else here (R rotates there, so starting again is 0: t = 0).
BUTTON_KEYS = {
    ArenaButton.EDIT: "Esc",  # leave the run, as Escape leaves a gesture in the editor
    ArenaButton.NEXT: "Enter",
    ArenaButton.RESTART: "0",
    ArenaButton.PLAY: "Space",
    ArenaButton.STEP: ".",
    ArenaButton.FAST: "F",
    **{button: VIEW_KEYS[view] for view, button in VIEW_BUTTON.items()},
}
# Keys with no button, for developers: turn the swimmer, the light map, the polar plot.
TURN_KEYS = (TOOL_KEYS[Tool.TURN_LEFT], TOOL_KEYS[Tool.TURN_RIGHT])  # the editor's: L, R
MAP_KEY, POLAR_KEY = "I", "P"
# Typed characters that press a button; Space, 0, Esc and Enter are matched on the physical key.
KEY_BUTTONS = {key: b for b, key in BUTTON_KEYS.items() if len(key) == 1 and not key.isdigit()}


def control_rects(layout: Layout) -> tuple[tuple[ArenaButton, Rect], ...]:
    """The controls, side by side at the left of the strip under the arena."""
    x, y, _, h = layout.controls_area
    top = y + (h - CONTROL) // 2
    return tuple(
        (b, (x + MARGIN + k * CONTROL_PITCH, top, CONTROL, CONTROL)) for k, b in enumerate(CONTROLS)
    )


def control_at(layout: Layout, point: tuple[int, int]) -> ArenaButton | None:
    return next((b for b, rect in control_rects(layout) if contains(rect, point)), None)


def timeline_rect(layout: Layout) -> Rect:
    """The timeline: after the controls, before the time."""
    x, y, w, h = layout.controls_area
    left = x + MARGIN + len(CONTROLS) * CONTROL_PITCH + MARGIN
    right = x + w - MARGIN - SUMMARY_WIDTH
    return (left, y + (h - TIMELINE_HEIGHT) // 2, right - left, TIMELINE_HEIGHT)


def summary_at(layout: Layout) -> tuple[int, int]:
    """The right end of the objectives' summary, centred on the strip's height (D-060)."""
    x, y, w, h = layout.controls_area
    return (x + w - MARGIN, y + h // 2)


def timeline_x(layout: Layout, seconds: float, limit: float) -> float:
    """Where a time [s] of a run lasting at most `limit` [s] sits along the timeline [px]."""
    x, _, w, _ = timeline_rect(layout)
    return x + w * min(1.0, max(0.0, seconds / limit))


def timeline_time(layout: Layout, px: float, limit: float) -> float:
    """The time [s], from 0 to `limit`, at the screen x `px` along the timeline."""
    x, _, w, _ = timeline_rect(layout)
    return limit * min(1.0, max(0.0, (px - x) / w))


def timeline_at(layout: Layout, point: tuple[int, int], limit: float) -> float | None:
    """The time [s] a press at `point` asks for; None off the timeline."""
    on = contains(timeline_rect(layout), point)
    return timeline_time(layout, point[0], limit) if on else None


def banner_rect(layout: Layout) -> Rect:
    """At the arena's top, in its middle."""
    x, y, w, _ = layout.board_area
    bw, bh = BANNER_SIZE
    return (x + (w - bw) // 2, y + 12, bw, bh)


def banner_rects(
    layout: Layout, buttons: tuple[ArenaButton, ...]
) -> tuple[tuple[ArenaButton, Rect], ...]:
    """The banner's buttons, side by side along its foot, centred."""
    x, y, w, h = banner_rect(layout)
    bw, bh = BANNER_BUTTON
    gap = 16
    width = len(buttons) * bw + (len(buttons) - 1) * gap
    left, top = x + (w - width) // 2, y + h - bh - 12
    return tuple((b, (left + k * (bw + gap), top, bw, bh)) for k, b in enumerate(buttons))


def banner_button_at(
    layout: Layout, buttons: tuple[ArenaButton, ...], point: tuple[int, int]
) -> ArenaButton | None:
    return next((b for b, rect in banner_rects(layout, buttons) if contains(rect, point)), None)


def polar_box(layout: Layout) -> Rect:
    """The developer's polar plot, over the arena's top left corner."""
    x, y, _, _ = layout.board_area
    return (x + 8, y + 8, *POLAR_SIZE)
