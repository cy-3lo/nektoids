"""Icons from Font Awesome Free 6.7.2 Solid (D-012), bundled unmodified with its licence.

The font is opened at startup, once per size on a fixed ladder (web.md: no file I/O in the
loop); an icon uses the largest size of the ladder that fits. It is opened by path: pygame-ce
under pygbag cannot open a font from bytes in memory. Each glyph is rendered the first time
it is drawn at a given size, colour and turn, then reused.

Icons are centred on their drawn pixels, not on the glyph box, which is uneven. The eye and the
rocket turn with their part, so they point where it does; the operators' chevrons stay upright.
"""

from __future__ import annotations

from bisect import bisect_right
from pathlib import Path

import pygame

from nektoids.editor.layout import EditButton, FileButton, Tool, ViewButton
from nektoids.graph.board import Kind

FONT_FILE = Path(__file__).resolve().parent.parent / "assets" / "fontawesome" / "fa-solid-900.ttf"
# Icon heights the font is opened at [px]: from the smallest menu icon to a part at full zoom.
SIZES = (10, 11, 12, 13, 14, 16, 18, 20, 22, 25, 28, 32, 36, 40, 44)

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
    "minus": 0xF068,
    "magnifying-glass-plus": 0xF00E,
    "magnifying-glass-minus": 0xF010,
    "hand": 0xF256,
    "location-crosshairs": 0xF601,
    "sun": 0xF185,
    "play": 0xF04B,
    "pause": 0xF04C,
    "forward-step": 0xF051,
    "rotate-left": 0xF2EA,
    "backward-step": 0xF048,
    "forward": 0xF04E,
    "lightbulb": 0xF0EB,
    "check": 0xF00C,
    "backward-fast": 0xF049,
    "reply": 0xF3E5,
    "share": 0xF064,
    "floppy-disk": 0xF0C7,
    "folder-open": 0xF07C,
}
# Direction an icon points to as drawn by the font [degrees, counter-clockwise from E]. The eye
# looks up: turned to face E, its long axis runs along the eye's flat side.
POINTS_TO = {"rocket": 45.0, "eye": 90.0}

KIND_ICON = {  # a source is a blank sensor: it senses nothing
    Kind.EYE: "eye",
    Kind.DOUBLE: "angles-up",
    Kind.HALVE: "angles-down",
    Kind.SUM: "plus",
    Kind.DIFFERENCE: "minus",
    Kind.THRUSTER: "rocket",
}
TOOL_ICON = {
    Tool.ADD: "plus",
    Tool.WIRE: "link",
    Tool.TURN_LEFT: "rotate-left",
    Tool.TURN_RIGHT: "rotate-right",
    Tool.MOVE: "up-down-left-right",
    Tool.DELETE: "trash-can",
}
# Hooked arrows for undo and redo: the round ones are the turn tools'.
EDIT_ICON = {EditButton.UNDO: "reply", EditButton.REDO: "share"}
FILE_ICON = {FileButton.SAVE: "floppy-disk", FileButton.LOAD: "folder-open"}
VIEW_ICON = {
    ViewButton.ZOOM_IN: "magnifying-glass-plus",
    ViewButton.ZOOM_OUT: "magnifying-glass-minus",
    ViewButton.PAN: "hand",
    ViewButton.CENTRE: "location-crosshairs",
}


class Icons:
    def __init__(self) -> None:
        """Call once at startup, after pygame.init()."""
        self._fonts = {size: pygame.font.Font(str(FONT_FILE), size) for size in SIZES}
        self._glyphs: dict[tuple[str, int, tuple[int, int, int], float | None], pygame.Surface] = {}

    def draw(self, screen, name: str, centre, size: int, colour, angle: float | None = None):
        """Draw icon `name` centred on `centre`, `size` px tall; if it points somewhere, turned to
        point at `angle` [degrees, counter-clockwise from E on screen]."""
        size = SIZES[max(0, bisect_right(SIZES, size) - 1)]  # the largest that fits
        turn = angle if name in POINTS_TO else None
        key = (name, size, tuple(colour), turn)
        if key not in self._glyphs:
            self._glyphs[key] = self._render(name, size, colour, turn)
        glyph = self._glyphs[key]
        ink = glyph.get_bounding_rect()
        screen.blit(glyph, (round(centre[0]) - ink.centerx, round(centre[1]) - ink.centery))

    def _render(self, name, size, colour, turn):
        glyph = self._fonts[size].render(chr(GLYPH[name]), True, colour)
        if turn is None:
            return glyph
        return pygame.transform.rotozoom(glyph, turn - POINTS_TO[name], 1.0)  # counter-clockwise
