"""Drawing the editor. Reads the scene and the board; never changes them.

Shapes carry the category: sensors are half-discs looking out of their round side,
converters are diamonds, thrusters are squares with a nose pointing the way they push.
Oriented shapes are drawn in the agent's frame, forward = E (D-008); the Rotate tool turns
them in place (D-009).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

from nektoids.editor.layout import Layout, Tool
from nektoids.editor.scene import EditorScene
from nektoids.graph.board import Category, Kind, Refused
from nektoids.graph.hexgrid import Cell, to_pixel

BACKGROUND = (18, 20, 28)
PANEL = (26, 29, 40)
GRID_LINE = (60, 64, 78)
HOVER = (40, 46, 62)
FLASH = (150, 50, 55)
BUTTON = (40, 44, 58)
ACTIVE = (70, 90, 150)
TEXT = (220, 222, 230)
DIM_TEXT = (130, 134, 150)
REFUSED = (240, 110, 110)
DARK = (18, 20, 28)
WIRE = (200, 205, 220)
GHOST = (110, 115, 135)
LOCK_RING = (170, 175, 190)
FILL = {
    Category.SENSOR: (240, 200, 90),
    Category.CONVERTER: (120, 200, 240),
    Category.ACTUATOR: (230, 120, 90),
}
GREYED = (80, 84, 96)

LABEL = {
    Kind.SENSOR_L: "L",
    Kind.SENSOR_R: "R",
    Kind.DOUBLE: "×2",
    Kind.HALVE: "÷2",
    Kind.THRUSTER_L: "L",
    Kind.THRUSTER_R: "R",
}
NAME = {
    Kind.SENSOR_L: "Left eye",
    Kind.SENSOR_R: "Right eye",
    Kind.DOUBLE: "Double",
    Kind.HALVE: "Halve",
    Kind.THRUSTER_L: "Left thruster",
    Kind.THRUSTER_R: "Right thruster",
}
HINT = {
    Tool.ADD: "Drag a component from the palette onto the grid.",
    Tool.WIRE: "Click a source, then a target. Right click cancels.",
    Tool.ROTATE: "Click an eye or a thruster to turn it clockwise; shift-click turns it back.",
    Tool.DELETE: "Click a component, or a wire where it crosses a cell.",
}

# Shapes in a local frame: unit = hex size, forward = +x.
_R = 0.62  # half-disc radius
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
    label: pygame.font.Font
    text: pygame.font.Font

    @classmethod
    def load(cls) -> Fonts:
        """Call once at startup, after pygame.init() (web.md: every asset at startup)."""
        return cls(label=pygame.font.Font(None, 24), text=pygame.font.Font(None, 22))


def draw(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    screen.fill(BACKGROUND)
    _draw_palette(screen, scene, fonts)
    _draw_toolbar(screen, scene)
    _draw_board(screen, scene, fonts)
    _draw_status(screen, scene, fonts)
    if scene.dragging and scene.picked is not None:
        size = scene.layout.hex_size
        facing = scene.picked.default_facing
        _draw_node(screen, fonts, scene.picked, facing, scene.mouse, size, locked=False)


# Board


def _draw_board(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    layout, board = scene.layout, scene.board
    for cell in board.cells:
        if scene.flash_frames > 0 and cell == scene.flash_cell:
            pygame.draw.polygon(screen, FLASH, _hexagon(layout, cell))
        elif cell == scene.hover:
            pygame.draw.polygon(screen, HOVER, _hexagon(layout, cell))
        pygame.draw.polygon(screen, GRID_LINE, _hexagon(layout, cell), 1)

    if isinstance(scene.ghost, tuple):
        _draw_wire(screen, layout, scene.ghost, GHOST, 2)
    for wire in board.wires:
        _draw_wire(screen, layout, wire.path, WIRE, 3)

    for node in board.nodes.values():
        centre = _centre(layout, node.cell)
        _draw_node(screen, fonts, node.kind, node.facing, centre, layout.hex_size, node.locked)
        if node.id == scene.source:
            pygame.draw.circle(screen, TEXT, centre, 0.8 * layout.hex_size, 2)
    if isinstance(scene.ghost, Refused) and scene.hover is not None:
        pygame.draw.polygon(screen, REFUSED, _hexagon(layout, scene.hover), 2)


def _draw_wire(screen, layout: Layout, path: tuple[Cell, ...], colour, width: int) -> None:
    points = [_centre(layout, cell) for cell in path]
    pygame.draw.lines(screen, colour, False, points, width)
    # Chevron just outside the target's shape, pointing into it.
    (x0, y0), (x1, y1) = points[-2], points[-1]
    angle = math.atan2(y1 - y0, x1 - x0)
    back = 0.68 * layout.hex_size
    tip = (x1 - back * math.cos(angle), y1 - back * math.sin(angle))
    wing = 0.22 * layout.hex_size
    wings = [
        (tip[0] - wing * math.cos(angle + s), tip[1] - wing * math.sin(angle + s))
        for s in (0.55, -0.55)
    ]
    pygame.draw.polygon(screen, colour, [tip, *wings])


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
    fill = fill or FILL[kind.category]
    outline = _shape(kind, facing, centre, size)
    pygame.draw.polygon(screen, fill, outline)
    if locked:
        pygame.draw.polygon(screen, LOCK_RING, _shape(kind, facing, centre, 1.25 * size), 2)
    text = fonts.label.render(LABEL[kind], True, DARK)
    screen.blit(text, text.get_rect(center=(round(centre[0]), round(centre[1]))))


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


def _hexagon(layout: Layout, cell: Cell) -> list[tuple[float, float]]:
    x, y = _centre(layout, cell)
    r = layout.hex_size
    return [
        (x + r * math.cos(math.radians(30 + 60 * k)), y + r * math.sin(math.radians(30 + 60 * k)))
        for k in range(6)
    ]


def _centre(layout: Layout, cell: Cell) -> tuple[float, float]:
    return to_pixel(cell, layout.hex_size, layout.origin)


# Palette, toolbar, status


def _draw_palette(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    layout, board = scene.layout, scene.board
    pygame.draw.rect(screen, PANEL, (0, 0, layout.board_area[0], screen.get_height()))
    for title, at in layout.group_titles:
        screen.blit(fonts.text.render(title.upper(), True, DIM_TEXT), at)
    for kind, rect in layout.palette_items:
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
            _draw_infinity(screen, (right - 6, y + h // 2), TEXT)
        else:
            count = fonts.text.render(str(left), True, DIM_TEXT if empty else TEXT)
            screen.blit(count, (right - count.get_width(), y + (h - count.get_height()) // 2))


def _draw_infinity(screen, centre, colour) -> None:
    # The default font has no ∞ glyph (D-008: icon font is post-jam).
    x, y = centre
    pygame.draw.circle(screen, colour, (x - 4, y), 4, 2)
    pygame.draw.circle(screen, colour, (x + 4, y), 4, 2)


def _draw_rotate(screen, centre, r: float, colour) -> None:
    """Clockwise circular arrow of radius r (the default font has no ↻)."""
    cx, cy = centre
    # pygame arcs run counter-clockwise on screen: this one leaves a gap on the right.
    arc_box = (cx - r, cy - r, 2 * r, 2 * r)
    pygame.draw.arc(screen, colour, arc_box, math.radians(30), math.radians(330), 2)
    end = math.radians(30)  # the arrow ends up-right, heading clockwise (down-right)
    px, py = cx + r * math.cos(end), cy - r * math.sin(end)
    tx, ty = math.sin(end), math.cos(end)  # clockwise tangent, y down
    nx, ny = math.cos(end), -math.sin(end)  # outward normal, y down
    head = [
        (px + 0.7 * r * tx, py + 0.7 * r * ty),
        (px + 0.55 * r * nx - 0.15 * r * tx, py + 0.55 * r * ny - 0.15 * r * ty),
        (px - 0.55 * r * nx - 0.15 * r * tx, py - 0.55 * r * ny - 0.15 * r * ty),
    ]
    pygame.draw.polygon(screen, colour, head)


def _draw_toolbar(screen: pygame.Surface, scene: EditorScene) -> None:
    for tool, rect in scene.layout.tool_buttons:
        pygame.draw.rect(screen, ACTIVE if tool is scene.tool else BUTTON, rect, border_radius=6)
        x, y, w, h = rect
        cx, cy = x + w // 2, y + h // 2
        if tool is Tool.ADD:
            pygame.draw.line(screen, TEXT, (cx - 10, cy), (cx + 10, cy), 3)
            pygame.draw.line(screen, TEXT, (cx, cy - 10), (cx, cy + 10), 3)
        elif tool is Tool.WIRE:
            points = [(cx - 12, cy + 6), (cx - 4, cy + 6), (cx + 4, cy - 6), (cx + 12, cy - 6)]
            pygame.draw.lines(screen, TEXT, False, points, 3)
            pygame.draw.circle(screen, TEXT, points[0], 3)
            pygame.draw.circle(screen, TEXT, points[-1], 3)
        elif tool is Tool.ROTATE:
            _draw_rotate(screen, (cx, cy), 10, TEXT)
        else:
            pygame.draw.polygon(
                screen,
                TEXT,
                [(cx - 8, cy - 6), (cx + 8, cy - 6), (cx + 6, cy + 11), (cx - 6, cy + 11)],
                2,
            )
            pygame.draw.line(screen, TEXT, (cx - 11, cy - 9), (cx + 11, cy - 9), 3)
            pygame.draw.line(screen, TEXT, (cx - 3, cy - 12), (cx + 3, cy - 12), 3)


def _draw_status(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    if scene.message:
        text, colour = scene.message, REFUSED
    elif isinstance(scene.ghost, Refused):
        text, colour = scene.ghost.reason, REFUSED
    else:
        text, colour = HINT[scene.tool], DIM_TEXT
    screen.blit(fonts.text.render(text, True, colour), scene.layout.status_at)
