"""A field's keys and clicks, as every scene with a field takes them (D-418).

Natively a key held repeats while a field is open, and only then: the game's own keys act once
a press. Ctrl or Cmd with C copies the selection, with X cuts it, with V pastes; with Shift the
arrows, Home and End select (`TextField.type`). A click in the open field places its caret and a
drag selects: the character under the mouse is found as the field draws it, IBM Plex Mono's
characters all one width (`fieldfont.py`). On the web the page's field takes the keys, so
`select` hands it the selection a click made.
"""

from __future__ import annotations

import pygame

from nektoids.editor import clipboard, fieldfont
from nektoids.editor.layout import FIELD_PAD, HINT_LINE, SPEC_LINES, Rect
from nektoids.editor.textfield import (
    TextField,
    caret_at,
    index_at,
    index_in_lines,
    shown_from,
    wrapped,
)

REPEAT = (400, 35)  # a key held repeats after this long, then this often [ms]
COMMAND = pygame.KMOD_CTRL | pygame.KMOD_META


def opened() -> None:
    """A field has opened: keys held repeat."""
    pygame.key.set_repeat(*REPEAT)


def closed() -> None:
    """No field is open: each press of a key acts once."""
    pygame.key.set_repeat()


def key(field: TextField, event: pygame.event.Event) -> str | None:
    """A key natively, as `TextField.type` answers it: "enter" or "escape" when it ends the field;
    Ctrl/Cmd+C, X and V go through the clipboard."""
    command = bool(event.mod & COMMAND)
    if command and event.key == pygame.K_c:
        if field.selected():
            clipboard.copy(field.selected())
        return None
    if command and event.key == pygame.K_x:
        if field.selected():
            clipboard.copy(field.cut())
        return None
    if command and event.key == pygame.K_v:
        field.paste(clipboard.paste())
        return None
    shift = bool(event.mod & pygame.KMOD_SHIFT)
    return field.type(pygame.key.name(event.key), event.unicode, shift, command)


def index_in_line(field: TextField, rect: Rect, x: int, icon: bool = False) -> int:
    """The place in a field of one line nearest the pixel column `x`, as `draw_field` lays its
    text out: after its icon, if it has one, slid left as far as the caret needs."""
    left = rect[0] + (42 if icon else 12)
    room = rect[0] + rect[2] - 10 - left
    advance = fieldfont.ADVANCE["text"]
    start = shown_from(field.text, field.caret, lambda part: len(part) * advance <= room)
    return index_at(field.text, start, advance, x - left)


def index_in_box(field: TextField, rect: Rect, pos: tuple[int, int]) -> int:
    """The same in Text's spec, its lines wrapped, the lines round the caret shown."""
    advance = fieldfont.ADVANCE["small"]
    room = rect[2] - 24
    lines = wrapped(field.text, lambda line: len(line.rstrip()) * advance <= room)
    line, _ = caret_at(lines, field.caret)
    first = max(0, line - SPEC_LINES + 1)
    row = first + (pos[1] - rect[1] - FIELD_PAD) // HINT_LINE
    return index_in_lines(lines, row, advance, pos[0] - rect[0] - 12)


def select(field: TextField) -> None:
    """On the web, the page's field takes the selection a click made, and the keys again."""
    clipboard.select_field(field.caret, field.caret if field.anchor is None else field.anchor)
