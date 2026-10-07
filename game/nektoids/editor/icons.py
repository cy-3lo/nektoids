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

from nektoids.editor.buttons import Button
from nektoids.editor.glyphs import GLYPH, POINTS_TO
from nektoids.editor.layout import (
    Drawer,
    EditButton,
    LevelButton,
    Mode,
    Piece,
    Tool,
    ViewButton,
)
from nektoids.graph.board import Kind

FONT_FILE = Path(__file__).resolve().parent.parent / "assets" / "fontawesome" / "fa-solid-900.ttf"
# Icon heights the font is opened at [px]: from the smallest menu icon to a part at full zoom.
SIZES = (10, 11, 12, 13, 14, 16, 18, 20, 22, 25, 28, 32, 36, 40, 44)

KIND_ICON = {kind: kind.spec.icon for kind in Kind if kind.spec.icon}  # a Source: blank (D-202)
TOOL_ICON = {
    Tool.ADD: "plus",
    Tool.WIRE: "link",
    Tool.TURN_LEFT: "rotate-left",
    Tool.TURN_RIGHT: "rotate-right",
    Tool.MOVE: "up-down-left-right",
    Tool.DELETE: "trash-can",
    Tool.SWAP: "arrow-right-arrow-left",
    Tool.LESS: "minus",  # the Editor's (D-301)
    Tool.MORE: "plus",
}
PIECE_ICON = {
    Piece.LIGHT: "lightbulb",
    Piece.OBSTACLE: "circle",
    Piece.MARK: "circle-plus",  # a + in a circle, as the plane draws a mark (D-306, D-314)
    Piece.START: "location-arrow",
}
# Hooked arrows for undo and redo: the round ones are the turn tools'.
EDIT_ICON = {EditButton.UNDO: "reply", EditButton.REDO: "share"}
MODE_ICON = {Mode.WRITE: "pencil", Mode.DELETE: "eraser", Mode.LOCK: "lock"}  # D-068, D-319
BUTTON_ICON = {  # the Board's buttons (D-401); a part's shows the part itself
    Button.SELECT: "arrow-pointer",
    Button.MOVE: TOOL_ICON[Tool.MOVE],
    Button.LOCK: MODE_ICON[Mode.LOCK],
    Button.UNDO: EDIT_ICON[EditButton.UNDO],
    Button.REDO: EDIT_ICON[EditButton.REDO],
    Button.DELETE: TOOL_ICON[Tool.DELETE],
    Button.TURN_LEFT: TOOL_ICON[Tool.TURN_LEFT],
    Button.TURN_RIGHT: TOOL_ICON[Tool.TURN_RIGHT],
    Button.WIRE: TOOL_ICON[Tool.WIRE],
}
LEVEL_ICON = {LevelButton.RUN: "play", LevelButton.BOARD: "diagram-project"}
DRAWER_ICON = {  # the activity bar's (D-051)
    Drawer.PARTS: "puzzle-piece",
    Drawer.FILES: "floppy-disk",
    Drawer.DIAGNOSTIC: "stethoscope",
    Drawer.INSIDE: "stethoscope",  # the run's Diagnostic, as the Board's (D-089)
    Drawer.SCORE: "trophy",
    Drawer.NAVIGATOR: "compass",
    Drawer.HINTS: "life-ring",
    Drawer.SETTINGS: "gear",
    Drawer.CHAPTERS: "map",
    Drawer.OBJECTS: "shapes",
    Drawer.TEXT: "pen",
    Drawer.GOALS: "list-check",
}
VIEW_ICON = {
    ViewButton.ZOOM_IN: "magnifying-glass-plus",
    ViewButton.ZOOM_OUT: "magnifying-glass-minus",
    ViewButton.PAN: "hand",
    ViewButton.CENTRE: "location-crosshairs",
    ViewButton.RAYS: "lightbulb",
    ViewButton.MOTION: "gauge-high",
    ViewButton.STREAMS: "wind",
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
