"""Drawing a tutorial's step over the screen (D-039): nothing dimmed and nothing outlined; the
target is drawn by what draws it in the accent, pulsing (`tutorial.panels`, `palette.pulse`), the
only highlight, sparks gone (D-336, D-337); then the box, its lines, a game's word in them in the
accent, the step's place, Skip and Next, Next in the accent: what a key does. Reads the tutorial;
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
    HOVER,
    LIT,
    RULE,
    TEXT,
    TOOLTIP_BG,
)
from nektoids.editor.tutorial import LINE, MARK, PAD, Tutorial, next_rect, runs, skip_rect


def draw_tutorial(
    screen: pygame.Surface,
    fonts: Fonts,
    tutorial: Tutorial,
    box: Rect,
    pointer: tuple[int, int],
) -> None:
    step = tutorial.step
    if step is None:
        return
    card = pygame.Rect(box)
    pygame.draw.rect(screen, TOOLTIP_BG, card, border_radius=8)
    pygame.draw.rect(screen, RULE, card, 1, border_radius=8)  # as an info box's (D-080)
    y, marked = card.top + PAD, False
    for line in step.lines:  # a game's word, marked, in the accent (D-337)
        x = card.left + PAD
        for text, lit in runs(line, marked):
            shown = fonts.small.render(text, True, LIT if lit else TEXT)
            screen.blit(shown, (x, y))
            x += shown.get_width()
        marked = marked != (line.count(MARK) % 2 == 1)  # a marked phrase run on to the next
        y += LINE
    count = fonts.small.render(f"{tutorial.index + 1} / {len(tutorial.steps)}", True, DIM_TEXT)
    button = next_rect(box)
    screen.blit(count, count.get_rect(midleft=(card.left + PAD, pygame.Rect(button).centery)))
    last = tutorial.index == len(tutorial.steps) - 1
    if tutorial.waits_for_next:  # a step that waits for an action has no Next
        _button(screen, fonts, button, "Close" if last else "Next", pointer, default=True)
    if not last:  # on the last step, Close does what Skip would
        _button(screen, fonts, skip_rect(box), "Skip", pointer)


def _button(
    screen: pygame.Surface, fonts: Fonts, rect: Rect, text: str, pointer, default: bool = False
) -> None:
    """A button of the box. The `default`, Next or Close, what Enter or any key does, is filled
    in the accent, and outlined in it while the mouse is on it; Skip is not (D-080)."""
    over = contains(rect, pointer)
    fill = ACTIVE if default else HOVER if over else BUTTON
    pygame.draw.rect(screen, fill, rect, border_radius=6)
    if default and over:
        pygame.draw.rect(screen, LIT, rect, 2, border_radius=6)
    label = fonts.label.render(text, True, TEXT)
    screen.blit(label, label.get_rect(center=pygame.Rect(rect).center))
