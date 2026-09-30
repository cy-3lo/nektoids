"""Drawing the editor. Reads the scene and the board; never changes them.

Everything is grey: colour is reserved for telling signals apart, later. Red only marks a
refusal; what the Delete tool would remove on a click turns a darker grey.

Shapes carry the category, all inside one circle: eyes are discs cut flat at the back, looking
out of their round side; sources are whole discs; operators are diamonds; thrusters are squares
whose front is cut to a 150° point, the way they push.
Oriented shapes are drawn in the agent's frame, forward = E (D-008); the Rotate tool turns
them in place (D-009). An icon inside each shape says its role (D-012).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

from nektoids.editor.geometry import wire_arrows, wire_points
from nektoids.editor.icons import KIND_ICON, TOOL_ICON, VIEW_ICON, Icons
from nektoids.editor.layout import TOOL_KEYS, VIEW_KEYS, Tool, View, ViewButton, visible_cells
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
TOOLTIP_BG = (34, 37, 50)
TEXT = (220, 222, 230)
DIM_TEXT = (130, 134, 150)
REFUSED = (240, 110, 110)
DOOMED = (86, 90, 104)  # darker grey: what a Delete click would remove
DARK = (18, 20, 28)
WIRE = (150, 154, 166)
GHOST = (96, 101, 118)  # where a wire would run
GHOST_OK = (228, 231, 240)  # ... and it may connect there
LOCK_RING = (170, 175, 190)
COMPONENT = (178, 182, 194)
GREYED = (80, 84, 96)

NAME = {
    Kind.EYE: "Eye",
    Kind.SOURCE: "Source",
    Kind.DOUBLE: "Double",
    Kind.HALVE: "Halve",
    Kind.SUM: "Sum",
    Kind.DIFFERENCE: "Difference",
    Kind.THRUSTER: "Thruster",
}
TIP = {
    Tool.ADD: "Add a component",
    Tool.WIRE: "Wire",
    Tool.ROTATE: "Rotate",
    Tool.MOVE: "Move a component",
    Tool.DELETE: "Delete",
    ViewButton.ZOOM_IN: "Zoom in",
    ViewButton.ZOOM_OUT: "Zoom out",
    ViewButton.PAN: "Move the view",
    ViewButton.CENTRE: "Centre the view",
    "colours": "Colours: not yet",
}
HINT = {
    Tool.ADD: "Drag a component from the menu onto the grid (or its number, arrows, Enter).",
    Tool.WIRE: "Drag from a source to a target, or click one then the other.",
    Tool.ROTATE: "Click an eye or a thruster to turn it clockwise; shift-click turns it back.",
    Tool.MOVE: "Drag a component. Its wires follow as long as they find a path.",
    Tool.DELETE: "Click a component to delete it, or a wire.",
    Tool.PAN: "Drag the grid to move the view. The magnifiers zoom in and out.",
}

# How parts sit in the menu: eyes flat side up, thrusters pointing up
# [degrees, counter-clockwise from E]. On the grid they point along their facing.
MENU_ANGLE = {Kind.EYE: 270.0, Kind.THRUSTER: 90.0}

ARROW_HALF = 0.14  # half-length of every arrowhead on a wire [hex sizes]

# Icon height as a fraction of the hex size.
ICON_SCALE = {Kind.EYE: 0.55}

# Shapes in a local frame: unit = hex size, forward = +x. Each outline is scaled to the same
# area, SHAPE_AREA, so that no part looks bigger than another: fitted to one circle, the disc
# covered 1.7 times the thruster's area.
SHAPE_AREA = 0.8


def _to_area(outline: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """The outline scaled about the cell centre until it encloses SHAPE_AREA (shoelace formula)."""
    closed = zip(outline, outline[1:] + outline[:1], strict=True)
    area = 0.5 * abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in closed))
    k = math.sqrt(SHAPE_AREA / area)
    return [(k * x, k * y) for x, y in outline]


def _arc(start: int, stop: int) -> list[tuple[float, float]]:
    """Points on the unit circle every 10°, from `start` to `stop` degrees."""
    return [(math.cos(math.radians(a)), math.sin(math.radians(a))) for a in range(start, stop, 10)]


_S = 1.0 / math.sqrt(2.0)  # half-side of the square inscribed in the unit circle
_SHOULDER = _S * (1.0 - math.tan(math.radians(15.0)))
# Eye: a disc with its back cut off by a chord at half the radius, flat side behind.
EYE_DISC = _to_area(_arc(-120, 121))
# Source: a whole disc; it has no direction.
DISC = _to_area(_arc(0, 360))
DIAMOND = _to_area([(0.0, -1.0), (1.0, 0.0), (0.0, 1.0), (-1.0, 0.0)])
# Thruster: a square, its front corners cut so the front is a point of 150° that ends on the
# square's front edge: the outline stays square, 1:1.
SQUARE_POINT = _to_area([(-_S, -_S), (_SHOULDER, -_S), (_S, 0.0), (_SHOULDER, _S), (-_S, _S)])
# Icon shift along the facing [hex sizes]: the eye's shape runs from its cut, half a radius R
# behind the centre, to its rim, so its middle lies R/4 ahead of the centre.
ICON_AHEAD = {Kind.EYE: 0.25 * max(math.hypot(u, v) for u, v in EYE_DISC)}


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
    _draw_tooltip(screen, scene, fonts)
    if scene.dragging and scene.picked is not None:
        size = scene.view.size
        angle = _placed_angle(scene.picked, scene.picked.default_facing)  # as it will land
        _draw_node(screen, fonts, scene.picked, angle, scene.mouse, size, locked=False)


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
        target = board.node_at(scene.ghost[-1])
        reach = _extent(target.kind) if target is not None else 0.3
        _draw_wire(screen, view, scene.ghost, colour, width, reach)
    doomed_node, doomed_wires = scene.doomed()  # what a Delete click would take, darkened
    for wire in board.wires:
        colour = DOOMED if wire in doomed_wires else WIRE
        _draw_wire(screen, view, wire.path, colour, 3, _extent(board.nodes[wire.target].kind))

    for node in board.nodes.values():
        centre = _centre(view, node.cell)
        angle = _placed_angle(node.kind, node.facing)
        fill = DOOMED if node.id == doomed_node else None
        _draw_node(screen, fonts, node.kind, angle, centre, view.size, node.locked, fill)
        if node.id == scene.source or node.id == scene._wire_start():
            pygame.draw.circle(screen, TEXT, centre, 0.8 * view.size, 2)
    if scene.cursor is not None:
        pygame.draw.polygon(screen, TEXT, _hexagon(view, scene.cursor), 3)
    if isinstance(scene.ghost, Refused) and scene.hover is not None:
        pygame.draw.polygon(screen, REFUSED, _hexagon(view, scene.hover), 2)
    screen.set_clip(None)


def _draw_wire(
    screen, view: View, path: tuple[Cell, ...], colour, width: int, reach: float = 0.3
) -> None:
    """reach: how far the target's shape extends [hex sizes]; the last arrow sits just outside."""
    points = wire_points(path, view.size, view.origin)  # arcs where it turns
    pygame.draw.lines(screen, colour, False, points, width)
    for at, angle in wire_arrows(path, view.size, view.origin):
        _draw_arrow(screen, at, angle, ARROW_HALF * view.size, colour)
    # And one more, the same size, just outside the target's circle, pointing into it.
    (x0, y0), (x1, y1) = points[-2], points[-1]
    angle = math.atan2(y1 - y0, x1 - x0)
    back = (reach + ARROW_HALF + 0.04) * view.size
    at = (x1 - back * math.cos(angle), y1 - back * math.sin(angle))
    _draw_arrow(screen, at, angle, ARROW_HALF * view.size, colour)


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
    angle: float | None,
    centre,
    size: float,
    locked: bool,
    fill=None,
):
    fill = fill or COMPONENT
    outline = _shape(kind, angle, centre, size)
    pygame.draw.polygon(screen, fill, outline)
    if locked:
        pygame.draw.polygon(screen, LOCK_RING, _shape(kind, angle, centre, 1.25 * size), 2)
    icon_size = max(10, round(ICON_SCALE.get(kind, 0.5) * size))
    if kind in KIND_ICON:
        ahead = ICON_AHEAD.get(kind, 0.0) * size
        phi = math.radians(angle or 0.0)  # counter-clockwise on screen, y down
        at = (centre[0] + ahead * math.cos(phi), centre[1] - ahead * math.sin(phi))
        fonts.icons.draw(screen, KIND_ICON[kind], at, icon_size, DARK, angle)


def _placed_angle(kind: Kind, facing: int | None) -> float | None:
    """Screen angle a part is drawn at on the grid [degrees, counter-clockwise from E]."""
    if facing is not None:
        return 60.0 * facing  # direction d lies at 60° * d
    return None


def _template(kind: Kind) -> list[tuple[float, float]]:
    if kind is Kind.SOURCE:
        return DISC
    return {
        Category.SENSOR: EYE_DISC,
        Category.OPERATOR: DIAMOND,
        Category.ACTUATOR: SQUARE_POINT,
    }[kind.category]


def _extent(kind: Kind) -> float:
    """How far the shape of `kind` reaches from its cell centre [hex sizes]."""
    return max(math.hypot(u, v) for u, v in _template(kind))


def _shape(kind: Kind, angle: float | None, centre, size: float) -> list[tuple[float, float]]:
    """Polygon for `kind`, turned to point at `angle` [degrees, counter-clockwise on screen]."""
    template = _template(kind)
    phi = math.radians(-(angle or 0.0))  # y points down
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
        angle = MENU_ANGLE.get(kind)
        _draw_node(screen, fonts, kind, angle, icon, 26, locked=False, fill=fill)
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


def _draw_tooltip(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """Name and shortcut of the palette button under the mouse, to its left."""
    target = scene.tooltip
    if target is None:
        return
    layout = scene.layout
    rects = dict(layout.tool_buttons) | dict(layout.view_buttons)
    x, y, _, h = rects[target] if target in rects else layout.swatches[0]
    key = TOOL_KEYS.get(target) or VIEW_KEYS.get(target)
    text = fonts.text.render(TIP[target] + (f" ({key})" if key else ""), True, TEXT)
    box = text.get_rect(midright=(x - 10, y + h // 2)).inflate(16, 10)
    pygame.draw.rect(screen, TOOLTIP_BG, box, border_radius=5)
    pygame.draw.rect(screen, RULE, box, 1, border_radius=5)
    screen.blit(text, text.get_rect(center=box.center))


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
