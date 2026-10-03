"""Drawing a tutorial's step over the screen (D-039): while the step shows a target, the rest is
dimmed, with no outline: a disc round a cell, a rounded hole round anything else (D-048); then
the box, its lines, the step's place, Skip and Next. A hint dims nothing. Reads the tutorial;
never changes it. Where things sit is `tutorial.py`'s.
"""

from __future__ import annotations

import pygame

from nektoids.editor.draw import Fonts
from nektoids.editor.layout import Rect, contains
from nektoids.editor.palette import (
    ACTIVE,
    BUTTON,
    DIM_TEXT,
    LIT,
    RULE,
    TEXT,
    TOOLTIP_BG,
)
from nektoids.editor.tutorial import (
    LINE,
    PAD,
    Docked,
    Page,
    Tutorial,
    next_rect,
    outline_kept,
    skip_rect,
)

HALO = 6  # the lit margin round the target [px]
HOLE_RADIUS = 10  # the corners of a hole round an area or a button [px]
OUTLINE = 2  # round a panel a step explains (D-050) [px]


def draw_tutorial(
    screen: pygame.Surface,
    fonts: Fonts,
    tutorial: Tutorial,
    spots: list[tuple[Rect, str]],
    box: Rect,
    pointer: tuple[int, int],
) -> None:
    step = tutorial.step
    if step is None:
        return
    for rect, shape in spots:  # nothing dimmed (D-063, D-071): what it shows outlined in the
        if tutorial.explains or shape in ("spot", "icon"):  # accent; the cells a step asks
            _outline(screen, LIT, rect, shape)  # for are lit by the board instead
    frame = pygame.Rect(box)
    pygame.draw.rect(screen, TOOLTIP_BG, frame, border_radius=8)
    pygame.draw.rect(screen, LIT if spots else RULE, frame, 2, border_radius=8)
    y = frame.top + PAD
    for line in step.say:
        screen.blit(fonts.small.render(line, True, TEXT), (frame.left + PAD, y))
        y += LINE
    count = fonts.small.render(f"{tutorial.index + 1} / {len(tutorial.steps)}", True, DIM_TEXT)
    button = next_rect(box)
    screen.blit(count, count.get_rect(midleft=(frame.left + PAD, pygame.Rect(button).centery)))
    last = tutorial.index == len(tutorial.steps) - 1
    if tutorial.waits_for_next:  # a step that waits for an action has no Next
        _button(screen, fonts, button, "Close" if last else "Next", pointer)
    if not last:  # on the last step, Close does what Skip would
        _button(screen, fonts, skip_rect(box), "Skip", pointer)


def _outline(surface: pygame.Surface, colour, rect: Rect, shape) -> None:
    """A target's outline, OUTLINE px wide, kept EDGE px inside the screen (D-071): a disc round
    a cell or a Wheel's icon, HALO px out; a panel, a page and its tab, a drawer and its icon on
    their own edges, the line inside them; a rounded rectangle HALO px round anything else, a
    button, a row, the swimmer."""
    if shape == "none":  # a place the box keeps clear of, not drawn
        return
    if shape in ("disc", "icon"):  # a cell, a Wheel's icon (D-070)
        hole = pygame.Rect(rect)
        pygame.draw.circle(surface, colour, hole.center, hole.height // 2 + HALO, OUTLINE)
        return
    if shape == "panel":
        pygame.draw.rect(surface, colour, outline_kept(rect), OUTLINE)
        return
    if not isinstance(shape, (Page, Docked)):
        x, y, w, h = rect
        lit = outline_kept((x - HALO, y - HALO, w + 2 * HALO, h + 2 * HALO))
        pygame.draw.rect(surface, colour, lit, OUTLINE, border_radius=HOLE_RADIUS)
        return
    inset = OUTLINE // 2
    x, y, w, h = outline_kept(rect)
    left, right, top, bottom = x + inset, x + w - 1 - inset, y + inset, y + h - 1 - inset
    if isinstance(shape, Docked):  # the drawer and its icon beside it, in the bar (D-071)
        ix, iy, _, ih = shape.icon
        points = [(ix, iy), (left, iy), (left, top), (right, top), (right, bottom)]
        points += [(left, bottom), (left, iy + ih), (ix, iy + ih)]
    else:  # a page: its tab on top, the level's line and the main screen under it (D-062)
        tx, _, tw, th = shape.tab
        tx = max(tx, left)  # a tab at the page's own left edge
        points = [(tx, top), (tx + tw, top), (tx + tw, th), (right, th), (right, bottom)]
        points += [(left, bottom), (left, th), (tx, th)]
    pygame.draw.lines(surface, colour, True, points, OUTLINE)


def _button(screen: pygame.Surface, fonts: Fonts, rect: Rect, text: str, pointer) -> None:
    pygame.draw.rect(screen, ACTIVE if contains(rect, pointer) else BUTTON, rect, border_radius=6)
    label = fonts.label.render(text, True, TEXT)
    screen.blit(label, label.get_rect(center=pygame.Rect(rect).center))
