"""Icons from Font Awesome Free 6.7.2 Solid (D-012), bundled unmodified with its licence.

The font is opened once at startup (web.md); each glyph is rendered the first time it is drawn at
a given size, colour and turn, then reused. Icons are centred on their drawn pixels, not on the
glyph box, which is uneven. The eye and the rocket turn with their part, so they point where it
does; the converters' chevrons stay upright.
"""

from __future__ import annotations

from pathlib import Path

import pygame

from nektoids.editor.layout import Tool
from nektoids.graph.board import Kind

FONT_FILE = Path(__file__).resolve().parent.parent / "assets" / "fontawesome" / "fa-solid-900.ttf"

# Codepoints from the font's own metadata (icons.yml, Font Awesome Free 6.7.2).
GLYPH = {
    "eye": 0xF06E,
    "angles-up": 0xF102,
    "angles-down": 0xF103,
    "rocket": 0xF135,
    "plus": 0x2B,
    "link": 0xF0C1,
    "rotate-right": 0xF2F9,
    "up-down-left-right": 0xF0B2,
    "trash-can": 0xF2ED,
    "caret-down": 0xF0D7,
    "caret-right": 0xF0DA,
    "infinity": 0xF534,
}
# Direction an icon points to as drawn by the font [degrees, counter-clockwise from E]. The eye
# looks up: turned to face E, its long axis runs along the half-disc's flat side.
POINTS_TO = {"rocket": 45.0, "eye": 90.0}

KIND_ICON = {
    Kind.EYE: "eye",
    Kind.DOUBLE: "angles-up",
    Kind.HALVE: "angles-down",
    Kind.THRUSTER: "rocket",
}
TOOL_ICON = {
    Tool.ADD: "plus",
    Tool.WIRE: "link",
    Tool.ROTATE: "rotate-right",
    Tool.MOVE: "up-down-left-right",
    Tool.DELETE: "trash-can",
}


class Icons:
    def __init__(self) -> None:
        """Call once at startup, after pygame.init()."""
        self._fonts: dict[int, pygame.font.Font] = {}
        self._glyphs: dict[tuple[str, int, tuple[int, int, int], int | None], pygame.Surface] = {}

    def draw(self, screen, name: str, centre, size: int, colour, facing: int | None = None):
        """Draw icon `name` centred on `centre`, `size` px tall, turned to `facing` if it points."""
        turn = facing if name in POINTS_TO else None
        key = (name, size, tuple(colour), turn)
        if key not in self._glyphs:
            self._glyphs[key] = self._render(name, size, colour, turn)
        glyph = self._glyphs[key]
        ink = glyph.get_bounding_rect()
        screen.blit(glyph, (round(centre[0]) - ink.centerx, round(centre[1]) - ink.centery))

    def _render(self, name, size, colour, turn):
        if size not in self._fonts:
            self._fonts[size] = pygame.font.Font(str(FONT_FILE), size)
        glyph = self._fonts[size].render(chr(GLYPH[name]), True, colour)
        if turn is None:
            return glyph
        # Direction d lies at 60° * d counter-clockwise from E; pygame turns counter-clockwise.
        return pygame.transform.rotozoom(glyph, 60.0 * turn - POINTS_TO[name], 1.0)
