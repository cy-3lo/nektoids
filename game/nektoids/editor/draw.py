"""Drawing the editor. Reads the scene and the board; never changes them.

Everything is grey: colour is reserved for telling signals apart, later. Red only marks a
refusal.

Shapes carry the category: sensors are half-discs looking out of their round side,
converters are diamonds, thrusters are squares with a nose pointing the way they push.
Oriented shapes are drawn in the agent's frame, forward = E (D-008); the Rotate tool turns
them in place (D-009). An icon inside each shape says its role (D-012).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

from nektoids.editor.geometry import wire_arrows, wire_points
from nektoids.editor.icons import KIND_ICON, TOOL_ICON, VIEW_ICON, Icons
from nektoids.editor.layout import Tool, View, ViewButton, visible_cells
from nektoids.editor.scene import EditorScene
from nektoids.graph.board import Category, Kind, Refused
from nektoids.graph.hexgrid import Cell, to_pixel

BACKGROUND = (18, 20, 28)
PANEL = (26, 29, 40)
GRID_LINE = (60, 64, 78)
ZONE = (26, 29, 40)  # cells of the level's zone
OUTSIDE = (11, 12, 17)  # cells outside it
OUTSIDE_LINE = (28, 30, 38)
HOVER = (44, 50, 68)
FLASH = (150, 50, 55)
BUTTON = (40, 44, 58)
ACTIVE = (78, 84, 100)  # selected tool or menu row
RULE = (52, 56, 70)  # separators between columns and between sets of buttons
SWATCH_OFF = (44, 47, 58)  # colour picker, not active yet
TEXT = (220, 222, 230)
DIM_TEXT = (130, 134, 150)
REFUSED = (240, 110, 110)
DARK = (18, 20, 28)
WIRE = (150, 154, 166)
GHOST = (96, 101, 118)  # where a wire would run
GHOST_OK = (228, 231, 240)  # ... and it may connect there
LOCK_RING = (170, 175, 190)
COMPONENT = (178, 182, 194)
GREYED = (80, 84, 96)

NAME = {
    Kind.EYE: "Eye",
    Kind.DOUBLE: "Double",
    Kind.HALVE: "Halve",
    Kind.THRUSTER: "Thruster",
}
HINT = {
    Tool.ADD: "Drag a component from the menu onto the grid.",
    Tool.WIRE: "Drag from a source to a target, or click one then the other.",
    Tool.ROTATE: "Click an eye or a thruster to turn it clockwise; shift-click turns it back.",
    Tool.MOVE: "Drag a component. Its wires follow as long as they find a path.",
    Tool.DELETE: "Click a component to delete it, or a wire.",
    Tool.PAN: "Drag the grid to move the view. The magnifiers zoom in and out.",
}

# Icon height as a fraction of the hex size.
ICON_SCALE = {Kind.EYE: 0.55}

# Shapes in a local frame: unit = hex size, forward = +x.
_R = 0.68  # half-disc radius
_BACK = 4.0 / (3.0 * math.pi) * _R  # flat side behind the centre, so the centroid is centred
HALF_DISC = (
    [(-_BACK, -_R)]
    + [
        (-_BACK + _R * math.cos(t), _R * math.sin(t))
        for t in (math.radians(a) for a in range(-90, 91, 10))
    ]
    + [(-_BACK, _R)]
)
NOSE = [(-0.5, -0.45), (0.2, -0.45), (0.6, 0.0), (0.2, 0.45), (-0.5, 0.45)]
DIAMOND = [(0.0, -0.6), (0.6, 0.0), (0.0, 0.6), (-0.6, 0.0)]


@dataclass(frozen=True)
class Fonts:
    text: pygame.font.Font
    icons: Icons

    @classmethod
    def load(cls) -> Fonts:
        """Call once at startup, after pygame.init() (web.md: every asset at startup)."""
        return cls(text=pygame.font.Font(None, 22), icons=Icons())


def draw(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    screen.fill(BACKGROUND)
    _draw_menu(screen, scene, fonts)
    _draw_palette(screen, scene, fonts)
    _draw_board(screen, scene, fonts)
    _draw_status(screen, scene, fonts)
    _draw_separators(screen, scene)
    if scene.dragging and scene.picked is not None:
        size = scene.view.size
        facing = scene.picked.default_facing
        _draw_node(screen, fonts, scene.picked, facing, scene.mouse, size, locked=False)


# Board


def _draw_board(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    view, board = scene.view, scene.board
    zone = set(board.cells)
    screen.set_clip(scene.layout.board_area)
    for cell in visible_cells(scene.layout, view):
        hexagon = _hexagon(view, cell)
        if scene.flash_frames > 0 and cell == scene.flash_cell:
            pygame.draw.polygon(screen, FLASH, hexagon)
        elif cell not in zone:
            pygame.draw.polygon(screen, OUTSIDE, hexagon)
        else:
            pygame.draw.polygon(screen, HOVER if cell == scene.hover else ZONE, hexagon)
        pygame.draw.polygon(screen, GRID_LINE if cell in zone else OUTSIDE_LINE, hexagon, 1)

    if isinstance(scene.ghost, tuple):
        colour, width = (GHOST_OK, 3) if scene.ghost_connects else (GHOST, 2)
        _draw_wire(screen, view, scene.ghost, colour, width)
    for wire in board.wires:
        _draw_wire(screen, view, wire.path, WIRE, 3)

    for node in board.nodes.values():
        centre = _centre(view, node.cell)
        _draw_node(screen, fonts, node.kind, node.facing, centre, view.size, node.locked)
        if node.id == scene.source or node.id == scene._wire_start():
            pygame.draw.circle(screen, TEXT, centre, 0.8 * view.size, 2)
    if isinstance(scene.ghost, Refused) and scene.hover is not None:
        pygame.draw.polygon(screen, REFUSED, _hexagon(view, scene.hover), 2)
    screen.set_clip(None)


def _draw_wire(screen, view: View, path: tuple[Cell, ...], colour, width: int) -> None:
    points = wire_points(path, view.size, view.origin)  # arcs where it turns
    pygame.draw.lines(screen, colour, False, points, width)
    for at, angle in wire_arrows(path, view.size, view.origin):
        _draw_arrow(screen, at, angle, 0.14 * view.size, colour)
    # Chevron just outside the target's shape, pointing into it.
    (x0, y0), (x1, y1) = points[-2], points[-1]
    angle = math.atan2(y1 - y0, x1 - x0)
    back = 0.68 * view.size
    tip = (x1 - back * math.cos(angle), y1 - back * math.sin(angle))
    wing = 0.22 * view.size
    wings = [
        (tip[0] - wing * math.cos(angle + s), tip[1] - wing * math.sin(angle + s))
        for s in (0.55, -0.55)
    ]
    pygame.draw.polygon(screen, colour, [tip, *wings])


def _draw_arrow(screen, at, angle: float, half: float, colour) -> None:
    """Small filled arrowhead centred on `at`, pointing along `angle` [rad, screen]."""
    c, s = math.cos(angle), math.sin(angle)
    tip = (at[0] + half * c, at[1] + half * s)
    left = (at[0] - half * c - half * s, at[1] - half * s + half * c)
    right = (at[0] - half * c + half * s, at[1] - half * s - half * c)
    pygame.draw.polygon(screen, colour, [tip, left, right])


def _draw_node(
    screen,
    fonts: Fonts,
    kind: Kind,
    facing: int | None,
    centre,
    size: float,
    locked: bool,
    fill=None,
):
    fill = fill or COMPONENT
    outline = _shape(kind, facing, centre, size)
    pygame.draw.polygon(screen, fill, outline)
    if locked:
        pygame.draw.polygon(screen, LOCK_RING, _shape(kind, facing, centre, 1.25 * size), 2)
    icon_size = max(10, round(ICON_SCALE.get(kind, 0.5) * size))
    fonts.icons.draw(screen, KIND_ICON[kind], centre, icon_size, DARK, facing)


def _shape(kind: Kind, facing: int | None, centre, size: float) -> list[tuple[float, float]]:
    """Polygon for `kind`, turned to `facing` (direction d is at -60° * d, y down)."""
    template = {
        Category.SENSOR: HALF_DISC,
        Category.CONVERTER: DIAMOND,
        Category.ACTUATOR: NOSE,
    }[kind.category]
    phi = math.radians(-60.0 * (facing or 0))
    c, s = math.cos(phi), math.sin(phi)
    return [
        (centre[0] + size * (u * c - v * s), centre[1] + size * (u * s + v * c))
        for u, v in template
    ]


def _hexagon(view: View, cell: Cell) -> list[tuple[float, float]]:
    x, y = _centre(view, cell)
    r = view.size
    return [
        (x + r * math.cos(math.radians(30 + 60 * k)), y + r * math.sin(math.radians(30 + 60 * k)))
        for k in range(6)
    ]


def _centre(view: View, cell: Cell) -> tuple[float, float]:
    return to_pixel(cell, view.size, view.origin)


# Menu, palette, status


def _draw_menu(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    layout, board = scene.layout, scene.board
    pygame.draw.rect(screen, PANEL, layout.menu_area)
    for title, (x, y, _, h) in layout.group_titles:
        caret = "caret-right" if title in scene.folded else "caret-down"
        fonts.icons.draw(screen, caret, (x + 5, y + h // 2), 14, DIM_TEXT)
        text = fonts.text.render(title.upper(), True, DIM_TEXT)
        screen.blit(text, (x + 16, y + (h - text.get_height()) // 2))
    for kind, rect in layout.menu_items:
        left = board.remaining(kind)
        empty = left == 0
        pygame.draw.rect(screen, ACTIVE if kind == scene.picked else BUTTON, rect, border_radius=6)
        x, y, w, h = rect
        icon = (x + 22, y + h / 2)
        fill = GREYED if empty else None
        _draw_node(screen, fonts, kind, kind.default_facing, icon, 26, locked=False, fill=fill)
        name = fonts.text.render(NAME[kind], True, DIM_TEXT if empty else TEXT)
        screen.blit(name, (x + 46, y + (h - name.get_height()) // 2))
        right = x + w - 12  # right edge of the count
        if left is None:
            fonts.icons.draw(screen, "infinity", (right - 8, y + h // 2), 14, TEXT)
        else:
            colour = DIM_TEXT if empty else TEXT
            count = fonts.text.render(f"{left}/{board.total(kind)}", True, colour)
            screen.blit(count, (right - count.get_width(), y + (h - count.get_height()) // 2))


def _draw_palette(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    layout = scene.layout
    pygame.draw.rect(screen, PANEL, layout.palette_area)
    for button, rect in layout.view_buttons:
        active = button is ViewButton.PAN and scene.tool is Tool.PAN
        _draw_button(screen, fonts, rect, VIEW_ICON[button], active)
    for tool, rect in layout.tool_buttons:
        _draw_button(screen, fonts, rect, TOOL_ICON[tool], tool is scene.tool)
    px, _, pw, _ = layout.palette_area
    for y in layout.palette_rules:
        pygame.draw.line(screen, RULE, (px + 20, y), (px + pw - 20, y), 1)
    # The colour picker keeps its place, inactive until colours carry a meaning.
    for rect in layout.swatches:
        pygame.draw.rect(screen, SWATCH_OFF, rect, border_radius=3)


def _draw_button(screen, fonts: Fonts, rect, icon: str, active: bool) -> None:
    pygame.draw.rect(screen, ACTIVE if active else BUTTON, rect, border_radius=6)
    x, y, w, h = rect
    fonts.icons.draw(screen, icon, (x + w // 2, y + h // 2), 20, TEXT)


def _draw_separators(screen: pygame.Surface, scene: EditorScene) -> None:
    for x in (scene.layout.menu_area[2], scene.layout.palette_area[0]):
        pygame.draw.line(screen, RULE, (x, 0), (x, screen.get_height()), 2)


def _draw_status(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    if scene.message:
        text, colour = scene.message, REFUSED
    elif isinstance(scene.ghost, Refused):
        text, colour = scene.ghost.reason, REFUSED
    else:
        text, colour = HINT[scene.tool], DIM_TEXT
    screen.blit(fonts.text.render(text, True, colour), scene.layout.status_at)
