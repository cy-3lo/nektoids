"""Drawing the screens around the levels (D-035): the title card, a level's card, the map, the
end. Reads the router; never changes it. Where things sit is `shell.py`'s.
"""

from __future__ import annotations

import pygame

from nektoids.editor.draw import (
    ACTIVE,
    BACKGROUND,
    BUTTON,
    DIM_TEXT,
    GREYED,
    PANEL,
    RULE,
    TEXT,
    Fonts,
    draw_title,
)
from nektoids.editor.layout import contains
from nektoids.editor.router import CHAPTER, CHAPTER_NAME, Router, level_label
from nektoids.editor.shell import BACK_KEY, CARD, END_KEY, MAP_TOP, bottom_button, map_rows

VEIL = (0, 0, 0, 150)  # over a level's board, under its card
STUDIO = "Cy-3LO"  # always written so (CLAUDE.md)
INVITE = "Wire the eyes to the thrusters, then Run."  # the card's one instruction (D-028)
START = "Click, or press a key, to start."  # how either card goes
CARD_MARGIN = 32  # a card's lines keep this far from its sides [px]
THANKS = "Thank you for playing."
REACH_OUT = (  # the brief's end screen, with the contact chosen for it (D-035)
    "If you liked this and want to support development, reach out:",
    "leave a comment on the itch.io page.",
)


def draw_title_card(screen: pygame.Surface, fonts: Fonts) -> None:
    """Over the first level, veiled: the name, the studio, what to do, how to start."""
    _card(
        screen,
        [
            (fonts.big.render("NEKTOIDS", True, TEXT), 56),
            (fonts.small.render(f"a game by {STUDIO}", True, DIM_TEXT), 136),
            (fonts.text.render(INVITE, True, TEXT), 190),
            (fonts.small.render(START, True, DIM_TEXT), 250),
        ],
    )


def draw_level_card(screen: pygame.Surface, router: Router, fonts: Fonts) -> None:
    """Over a level just opened, veiled: its name, what it asks, its time, how to start."""
    level = router.level
    _card(
        screen,
        [
            (fonts.small.render(router.label, True, DIM_TEXT), 40),
            (fonts.big.render(level.title, True, TEXT), 70),
            (fonts.text.render(level.spec, True, TEXT), 146),
            (fonts.small.render(f"You have {level.time_limit:g} s.", True, DIM_TEXT), 182),
            (fonts.small.render(START, True, DIM_TEXT), 250),
        ],
    )


def _card(screen: pygame.Surface, lines: list[tuple[pygame.Surface, int]]) -> None:
    """The screen veiled, the card over it, and its lines centred, each `dy` below its top; a
    line too wide for the card is shrunk to fit."""
    veil = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    veil.fill(VEIL)
    screen.blit(veil, (0, 0))
    card = pygame.Rect(CARD)
    pygame.draw.rect(screen, PANEL, card, border_radius=10)
    pygame.draw.rect(screen, RULE, card, 2, border_radius=10)
    room = card.width - 2 * CARD_MARGIN
    for shown, dy in lines:
        if shown.get_width() > room:
            height = round(shown.get_height() * room / shown.get_width())
            shown = pygame.transform.smoothscale(shown, (room, height))
        screen.blit(shown, shown.get_rect(midtop=(card.centerx, card.top + dy)))


def draw_map(
    screen: pygame.Surface, router: Router, fonts: Fonts, pointer: tuple[int, int]
) -> None:
    """The chapter's levels, each won, open or locked, then the sandbox; the open one outlined."""
    screen.fill(BACKGROUND)
    rows = map_rows(len(router.levels))
    left = rows[0][0]
    draw_title(screen, fonts, f"Chapter {CHAPTER}: {CHAPTER_NAME}", (left, MAP_TOP - 36))
    for k, rect in enumerate(rows):
        sandbox = k == router.sandbox_index
        level = router.sandbox if sandbox else router.levels[k]
        open_ = router.unlocked(k)
        fill = ACTIVE if open_ and contains(rect, pointer) else BUTTON if open_ else PANEL
        pygame.draw.rect(screen, fill, rect, border_radius=6)
        if k == router.index:
            pygame.draw.rect(screen, DIM_TEXT, rect, 2, border_radius=6)
        x, y, w, h = rect
        ink = TEXT if open_ else GREYED
        name = fonts.text.render("SANDBOX" if sandbox else level_label(k), True, DIM_TEXT)
        screen.blit(name, (x + 16, y + (h - name.get_height()) // 2))
        title = fonts.text.render(level.title, True, ink)
        screen.blit(title, (x + 132, y + (h - title.get_height()) // 2))
        if sandbox:
            state, icon = "no goal", None
        elif k in router.won:
            state, icon = "won", "check"
        elif open_:
            state, icon = "open", None
        else:
            state, icon = "locked", "lock"
        shown = fonts.small.render(state, True, ink)
        right = x + w - 16
        screen.blit(shown, shown.get_rect(midright=(right, y + h // 2)))
        if icon is not None:
            fonts.icons.draw(screen, icon, (right - shown.get_width() - 14, y + h // 2), 14, ink)
    _button(screen, fonts, f"Back to {router.label} ({BACK_KEY})", pointer)


def draw_end(screen: pygame.Surface, fonts: Fonts, pointer: tuple[int, int]) -> None:
    """After the last level: thanks, and where to say so."""
    screen.fill(BACKGROUND)
    middle = screen.get_width() // 2
    shown = fonts.big.render(THANKS, True, TEXT)
    screen.blit(shown, shown.get_rect(midtop=(middle, 190)))
    for k, line in enumerate(REACH_OUT):
        shown = fonts.text.render(line, True, DIM_TEXT)
        screen.blit(shown, shown.get_rect(midtop=(middle, 300 + 30 * k)))
    _button(screen, fonts, f"Map ({END_KEY})", pointer)


def _button(screen: pygame.Surface, fonts: Fonts, text: str, pointer: tuple[int, int]) -> None:
    rect = bottom_button()
    pygame.draw.rect(screen, ACTIVE if contains(rect, pointer) else BUTTON, rect, border_radius=6)
    shown = fonts.text.render(text, True, TEXT)
    screen.blit(shown, shown.get_rect(center=pygame.Rect(rect).center))
