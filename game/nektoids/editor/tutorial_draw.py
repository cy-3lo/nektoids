"""Drawing a tutorial's step over the screen (D-039): while the step shows a target, the rest
is dimmed and the target outlined; then the box, its lines, the step's place, and Next. A hint
dims nothing. Reads the tutorial; never changes it. Where things sit is `tutorial.py`'s.
"""

from __future__ import annotations

import pygame

from nektoids.editor.draw import ACTIVE, BUTTON, DIM_TEXT, RULE, TEXT, TOOLTIP_BG, Fonts
from nektoids.editor.layout import Rect, contains
from nektoids.editor.tutorial import LINE, PAD, Tutorial, next_rect

DIM = (0, 0, 0, 150)  # over everything but the target
LIT = (228, 231, 240)  # the target's outline, and the box's while it leads
HALO = 6  # the lit margin round the target [px]


def draw_tutorial(
    screen: pygame.Surface,
    fonts: Fonts,
    tutorial: Tutorial,
    targets: list[Rect],
    box: Rect,
    pointer: tuple[int, int],
) -> None:
    step = tutorial.step
    if step is None:
        return
    if targets:
        lit = [pygame.Rect(target).inflate(2 * HALO, 2 * HALO) for target in targets]
        veil = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        veil.fill(DIM)
        for hole in lit:
            veil.fill((0, 0, 0, 0), hole)
        screen.blit(veil, (0, 0))
        for hole in lit:
            pygame.draw.rect(screen, LIT, hole, 2, border_radius=6)
    frame = pygame.Rect(box)
    pygame.draw.rect(screen, TOOLTIP_BG, frame, border_radius=8)
    pygame.draw.rect(screen, LIT if targets else RULE, frame, 2, border_radius=8)
    y = frame.top + PAD
    for line in step.say:
        screen.blit(fonts.small.render(line, True, TEXT), (frame.left + PAD, y))
        y += LINE
    count = fonts.small.render(f"{tutorial.index + 1} / {len(tutorial.steps)}", True, DIM_TEXT)
    button = next_rect(box)
    screen.blit(count, count.get_rect(midleft=(frame.left + PAD, pygame.Rect(button).centery)))
    last = tutorial.index == len(tutorial.steps) - 1
    pygame.draw.rect(
        screen, ACTIVE if contains(button, pointer) else BUTTON, button, border_radius=6
    )
    label = fonts.small.render("Close" if last else "Next", True, TEXT)
    screen.blit(label, label.get_rect(center=pygame.Rect(button).center))
