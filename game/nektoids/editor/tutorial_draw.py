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
    CLEAR,
    DIM_TEXT,
    LIT,
    RULE,
    TEXT,
    TOOLTIP_BG,
    VEIL,
)
from nektoids.editor.tutorial import LINE, PAD, Tutorial, next_rect, skip_rect

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
    if spots:  # pygame.draw writes CLEAR as it is, alpha and all: holes in the veil
        veil = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        veil.fill(VEIL)
        for rect, shape in spots:
            _hole(veil, CLEAR, rect, shape, 0)
        screen.blit(veil, (0, 0))
        if tutorial.explains:  # it explains a panel: outlined, besides dimming the rest
            for rect, shape in spots:
                _hole(screen, LIT, rect, shape, OUTLINE)
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


def _hole(surface: pygame.Surface, colour, rect: Rect, shape: str, width: int) -> None:
    """A target's shape, filled (`width` 0) or outlined: a disc round a cell, round its corners and
    the margin; a panel on its own edges, square, the outline inside them, so that one at the
    screen's edge stays on it; a rounded rectangle round anything else."""
    hole = pygame.Rect(rect)
    if shape == "disc":
        pygame.draw.circle(surface, colour, hole.center, hole.height // 2 + HALO, width)
    elif shape == "panel":
        pygame.draw.rect(surface, colour, hole, width)
    else:
        lit = hole.inflate(2 * HALO, 2 * HALO)
        pygame.draw.rect(surface, colour, lit, width, border_radius=HOLE_RADIUS)


def _button(screen: pygame.Surface, fonts: Fonts, rect: Rect, text: str, pointer) -> None:
    pygame.draw.rect(screen, ACTIVE if contains(rect, pointer) else BUTTON, rect, border_radius=6)
    label = fonts.label.render(text, True, TEXT)
    screen.blit(label, label.get_rect(center=pygame.Rect(rect).center))
