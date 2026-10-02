"""Drawing the editor. Reads the scene and the board; never changes them.

The frame (D-051): the activity bar down the left edge, its open drawer's icon lit with an
accent bar, Chapters and the accented switch to the Run at its foot; the open drawer, its rows
all alike (icon, name, info disc, then a count, a key or a lock), an arrow on its edge to fold
it; the tabs over the board, the level's caption after them; the status line at the board's
foot. Colours come from the palette (D-047); the accent marks what the player works with.

Shapes carry the category, all inside one circle: eyes are discs cut flat in front, the flat
face being the photosensor, which looks where the eye faces (D-020); sources are whole discs;
operators are diamonds; thrusters are squares whose front is cut to a 150° point, the way they
push.
Oriented shapes are drawn in the agent's frame, forward = E (D-008); the turn tools turn
them in place (D-009, D-025), and the selected part's cell is lit. An icon inside each shape
says its role (D-012). The board is the body (D-018): the swimmer's symbol lies faintly behind
it, a circle round a wedge, tip forward.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

from nektoids.editor.devdrive import DT
from nektoids.editor.geometry import body_circle, symbol_corners, wire_arrows, wire_points
from nektoids.editor.icons import (
    DRAWER_ICON,
    EDIT_ICON,
    FILE_ICON,
    KIND_ICON,
    LEVEL_ICON,
    TOOL_ICON,
    VIEW_ICON,
    Icons,
)
from nektoids.editor.layout import (
    BAR_WIDTH,
    DRAWER_KEYS,
    EDIT_KEYS,
    INFO_AT,
    LEVEL_KEYS,
    PALETTE_TITLE,
    SCREEN,
    STATUS_HEIGHT,
    TABS_HEIGHT,
    TOOL_KEYS,
    VIEW_KEYS,
    Drawer,
    EditButton,
    FileButton,
    LevelButton,
    Setting,
    Tool,
    View,
    ViewButton,
    visible_cells,
)
from nektoids.editor.palette import (
    ACTIVE,
    BACKGROUND,
    BAR,
    BODY_OUTLINE,
    BUTTON,
    COMPONENT,
    DARK,
    DIM_TEXT,
    DOOMED,
    EYE_FACE,
    FLASH,
    GHOST,
    GHOST_FILL,
    GHOST_OK,
    GREYED,
    GRID_LINE,
    HOVER,
    LIT,
    LOCK_RING,
    OUTSIDE,
    OUTSIDE_LINE,
    PANEL,
    REFUSED,
    RULE,
    TEXT,
    THRUSTER_BACK,
    TOOLTIP_BG,
    WIRE,
    ZONE,
)
from nektoids.editor.parts import NAME, info
from nektoids.editor.scene import EditorScene
from nektoids.graph.board import Category, Kind, Refused
from nektoids.graph.hexgrid import Cell, to_pixel

TIP = {
    Tool.ADD: "Add a part",
    Tool.WIRE: "Wire",
    Tool.TURN_LEFT: "Turn left",
    Tool.TURN_RIGHT: "Turn right",
    Tool.MOVE: "Move a part",
    Tool.DELETE: "Delete",
    ViewButton.ZOOM_IN: "Zoom in",
    ViewButton.ZOOM_OUT: "Zoom out",
    ViewButton.PAN: "Move the view",
    ViewButton.CENTRE: "Centre the view",
    EditButton.UNDO: "Undo",
    EditButton.REDO: "Redo",
    FileButton.SAVE: "Save: not yet",
    FileButton.LOAD: "Load: not yet",
    LevelButton.RUN: "Run",
    Drawer.PARTS: "Parts",
    Drawer.TOOLS: "Tools",
    Drawer.NAVIGATOR: "Navigator",
    Drawer.SETTINGS: "Settings",
    Drawer.CHAPTERS: "Chapters",
}
SETTING = {  # Settings' rows: their name, icon and what their info box says (D-054)
    Setting.FAST: ("Fast forward", "forward", "How fast the run goes when fast forward is on."),
    Setting.HINTS: ("Key hints", "keyboard", "Show each row's key, and the bar's in its tooltip."),
    Setting.TOOLTIPS: (
        "Tooltips",
        "clock",
        "How long the mouse rests on an icon before its name shows.",
    ),
    Setting.TUTORIAL: (
        "Tutorial",
        "graduation-cap",
        "Fear again, from its first step, on a fresh board.",
    ),
    Setting.SOUND: ("Sound", "volume-high", "There is no sound yet."),
    Setting.MUSIC: ("Music", "music", "There is no music yet."),
}
ROW_NAME = {  # a drawer's row, by what it does; a part's row takes the part's name
    Tool.ADD: "Add",
    Tool.WIRE: "Wire",
    Tool.MOVE: "Move",
    Tool.DELETE: "Delete",
    Tool.TURN_LEFT: "Turn left",
    Tool.TURN_RIGHT: "Turn right",
    EditButton.UNDO: "Undo",
    EditButton.REDO: "Redo",
    FileButton.SAVE: "Save",
    FileButton.LOAD: "Load",
    ViewButton.ZOOM_IN: "Zoom in",
    ViewButton.ZOOM_OUT: "Zoom out",
    ViewButton.PAN: "Hand",
    ViewButton.CENTRE: "Centre",
}
TAB_NAME = {"editor": "Editor", "run": "Run"}
HINT = {
    Tool.ADD: "Drag a part from Parts onto the board (or its number, arrows, Enter).",
    Tool.WIRE: "Drag from one part to another, or click one then the other.",
    Tool.TURN_LEFT: "Click a part to select it, again to turn it left. L turns the selected one.",
    Tool.TURN_RIGHT: "Click a part to select it, again to turn it right. R turns the selected one.",
    Tool.MOVE: "Drag a part. Its wires follow as long as they find a path.",
    Tool.DELETE: "Click a part to delete it, or a wire.",
    Tool.PAN: "Drag the grid to move the view. The magnifiers zoom in and out.",
}

# How parts sit in the menu: eyes looking up (flat side up), thrusters pointing up
# [degrees, counter-clockwise from E]. On the grid they point along their facing.
MENU_ANGLE = {Kind.EYE: 90.0, Kind.THRUSTER: 90.0}

ARROW_HALF = 0.14  # half-length of every arrowhead on a wire [hex sizes]
FACE = {Kind.EYE: EYE_FACE, Kind.THRUSTER: THRUSTER_BACK}  # the side that reads, that pushes
FACE_WIDTH = 0.1  # [hex sizes]
INFO_ICON = 12  # a menu row's info disc [px]
INFO_PAD = 12  # inside the info box [px]

# Icon height as a fraction of the hex size.
ICON_SCALE = {Kind.EYE: 0.68, Kind.THRUSTER: 0.62}  # the rest: 0.5

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
# The eye's and the thruster's outlines end where their face begins: the edge from the last
# point back to the first is the face, drawn in its accent (D-047).
# Eye: a disc with its front cut off by a chord at half the radius. The flat face is the
# photosensor, and it looks forward (D-019, D-020).
EYE_DISC = _to_area(_arc(60, 301))
# Source: a whole disc; it has no direction.
DISC = _to_area(_arc(0, 360))
DIAMOND = _to_area([(0.0, -1.0), (1.0, 0.0), (0.0, 1.0), (-1.0, 0.0)])
# Thruster: a square, its front corners cut so the front is a point of 150° that ends on the
# square's front edge: the outline stays square, 1:1. Its face is its back, where it pushes from.
SQUARE_POINT = _to_area([(-_S, -_S), (_SHOULDER, -_S), (_S, 0.0), (_SHOULDER, _S), (-_S, _S)])
# Icon shift along the facing [hex sizes]: the eye's shape runs from its rim, a radius R behind
# the centre, to its flat face, half a radius ahead, so its middle lies R/4 behind the centre.
ICON_AHEAD = {Kind.EYE: -0.25 * max(math.hypot(u, v) for u, v in EYE_DISC)}


@dataclass(frozen=True)
class Fonts:
    text: pygame.font.Font
    small: pygame.font.Font  # the developer view's panel
    big: pygame.font.Font  # the title card's name, the end's thanks
    icons: Icons

    @classmethod
    def load(cls) -> Fonts:
        """Call once at startup, after pygame.init() (web.md: every asset at startup)."""
        return cls(
            text=pygame.font.Font(None, 22),
            small=pygame.font.Font(None, 18),
            big=pygame.font.Font(None, 64),
            icons=Icons(),
        )


def draw(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    screen.fill(BACKGROUND)
    _draw_board(screen, scene, fonts)
    _draw_tabs(screen, scene, fonts)
    _draw_status(screen, scene, fonts)
    _draw_bar(screen, scene, fonts)
    _draw_drawer(screen, scene, fonts)
    _draw_tooltip(screen, scene, fonts)
    _draw_info(screen, scene, fonts)
    if scene.dragging and scene.picked is not None:
        size = scene.view.size
        angle = placed_angle(scene.picked, scene.picked.default_facing)  # as it will land
        draw_part(screen, fonts, scene.picked, angle, scene.mouse, size, locked=False)


# Board


def _draw_board(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    view, board = scene.view, scene.board
    zone = set(board.cells)
    selected = board.nodes[scene.selected].cell if scene.selected in board.nodes else None
    screen.set_clip(scene.layout.board_area)
    for cell in visible_cells(scene.layout, view):
        hexagon = _hexagon(view, cell)
        if scene.flash_frames > 0 and cell == scene.flash_cell:
            pygame.draw.polygon(screen, FLASH, hexagon)
        elif cell not in zone:
            pygame.draw.polygon(screen, OUTSIDE, hexagon)
        elif cell == selected:
            pygame.draw.polygon(screen, ACTIVE, hexagon)  # as lit as the tool in hand
        else:
            pygame.draw.polygon(screen, HOVER if cell == scene.hover else ZONE, hexagon)
        pygame.draw.polygon(screen, GRID_LINE if cell in zone else OUTSIDE_LINE, hexagon, 1)
    if board.cells:
        draw_body(screen, board.cells, view.size, view.origin)

    if isinstance(scene.ghost, tuple):
        colour, width = (GHOST_OK, 3) if scene.ghost_connects else (GHOST, 2)
        target = board.node_at(scene.ghost[-1])
        reach = extent(target.kind) if target is not None else 0.3
        _draw_wire(screen, view, scene.ghost, colour, width, reach)
    doomed_node, doomed_wires = scene.doomed()  # what a Delete click would take, darkened
    for wire in board.wires:
        colour = DOOMED if wire in doomed_wires else WIRE
        _draw_wire(screen, view, wire.path, colour, 3, extent(board.nodes[wire.target].kind))

    for ghost in scene.ghosts:  # where a part goes, facing the way it should (D-039)
        centre, angle = _centre(view, ghost.cell), placed_angle(ghost.kind, ghost.facing)
        pygame.draw.polygon(screen, GHOST_FILL, _shape(ghost.kind, angle, centre, view.size))
        pygame.draw.polygon(screen, GHOST, _shape(ghost.kind, angle, centre, view.size), 2)
    for node in board.nodes.values():
        centre = _centre(view, node.cell)
        angle = placed_angle(node.kind, node.facing)
        fill = DOOMED if node.id == doomed_node else None
        draw_part(screen, fonts, node.kind, angle, centre, view.size, node.locked, fill)
        if node.id == scene.source or node.id == scene._wire_start():
            pygame.draw.circle(screen, TEXT, centre, 0.8 * view.size, 2)
    for ghost in scene.ghosts:  # over a part that does not face its way yet: where to turn it
        node = board.node_at(ghost.cell)
        if node is not None and node.kind is ghost.kind and node.facing != ghost.facing:
            angle = placed_angle(ghost.kind, ghost.facing)
            outline = _shape(ghost.kind, angle, _centre(view, ghost.cell), view.size)
            pygame.draw.polygon(screen, GHOST_OK, outline, 2)
    if scene.cursor is not None:
        pygame.draw.polygon(screen, TEXT, _hexagon(view, scene.cursor), 3)
    if isinstance(scene.ghost, Refused) and scene.hover is not None:
        pygame.draw.polygon(screen, REFUSED, _hexagon(view, scene.hover), 2)
    screen.set_clip(None)


def _draw_wire(
    screen, view: View, path: tuple[Cell, ...], colour, width: int, reach: float = 0.3
) -> None:
    """One arrow in each free cell crossed; between neighbours, which have none, one just outside
    the target's shape instead. reach: how far that shape extends [hex sizes]."""
    points = wire_points(path, view.size, view.origin)  # arcs where it turns
    pygame.draw.lines(screen, colour, False, points, width)
    arrows = wire_arrows(path, view.size, view.origin)
    for at, angle in arrows:
        _draw_arrow(screen, at, angle, ARROW_HALF * view.size, colour)
    if arrows:
        return
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


def draw_body(screen, zone: list[Cell], size: float, origin) -> None:
    """The swimmer's symbol behind a board, a corner forward (E): the body is the board (D-018)."""
    centre, radius = body_circle(zone, size, origin)
    draw_symbol(screen, BODY_OUTLINE, centre, radius, 0.0, 3)


def draw_symbol(screen, colour, centre, radius: float, heading: float, width: int) -> None:
    """The swimmer's symbol: a circle of `radius` [px] round a wedge, the two sides of an
    equilateral triangle that meet at its tip, at `heading` [rad, counter-clockwise on screen];
    the back is open, so the tip shows the way. Both lines `width` px wide, anti-aliased. A
    circle's line grows inwards from its radius, so the corners sit on the middle of that line."""
    pygame.draw.aacircle(screen, colour, centre, radius, width)
    tip, left, right = symbol_corners(centre, radius - width / 2, heading)
    pygame.draw.aaline(screen, colour, left, tip, width)
    pygame.draw.aaline(screen, colour, tip, right, width)


def draw_part(
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
    if kind in FACE:  # the closing edge, astride the outline
        width = max(2, round(FACE_WIDTH * size))
        pygame.draw.line(screen, FACE[kind], outline[-1], outline[0], width)
    if locked:
        pygame.draw.polygon(screen, LOCK_RING, _shape(kind, angle, centre, 1.25 * size), 2)
    icon_size = max(10, round(ICON_SCALE.get(kind, 0.5) * size))
    if kind in KIND_ICON:
        ahead = ICON_AHEAD.get(kind, 0.0) * size
        phi = math.radians(angle or 0.0)  # counter-clockwise on screen, y down
        at = (centre[0] + ahead * math.cos(phi), centre[1] - ahead * math.sin(phi))
        fonts.icons.draw(screen, KIND_ICON[kind], at, icon_size, DARK, angle)


def placed_angle(kind: Kind, facing: int | None) -> float | None:
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


def extent(kind: Kind) -> float:
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


def _draw_bar(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """The activity bar: the drawers' icons, the open one lit, an accent bar on its edge; at the
    foot, Chapters and the accented switch to the Run."""
    layout = scene.layout
    pygame.draw.rect(screen, BAR, layout.bar_area)
    for drawer, rect in layout.drawer_buttons:
        on = drawer is layout.drawer
        box = pygame.Rect(rect)
        if on:
            pygame.draw.rect(screen, LIT, (0, box.top + 2, 3, box.height - 4))
        fonts.icons.draw(screen, DRAWER_ICON[drawer], box.center, 22, TEXT if on else DIM_TEXT)
    for button, rect in layout.level_buttons:
        box = pygame.Rect(rect)
        if button is LevelButton.RUN:
            pygame.draw.rect(screen, ACTIVE, box, border_radius=8)
            fonts.icons.draw(screen, LEVEL_ICON[button], box.center, 18, TEXT)
        else:
            fonts.icons.draw(screen, LEVEL_ICON[button], box.center, 22, DIM_TEXT)


def _draw_drawer(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """The open drawer: its title, its sections or groups, its rows, the arrow that folds it."""
    layout = scene.layout
    if layout.drawer is None:
        return
    area = pygame.Rect(layout.drawer_area)
    pygame.draw.rect(screen, PANEL, area)
    pygame.draw.line(screen, RULE, (area.right - 1, 0), (area.right - 1, area.bottom), 2)
    lit = layout.drawer.value in scene.lit  # a tutorial step explains it (D-050)
    ink = LIT if lit else DIM_TEXT
    draw_title(screen, fonts, TIP[layout.drawer], layout.drawer_title_at, lit=lit)
    for title, (x, y, _, h) in layout.section_titles:
        shown = fonts.small.render(title.upper(), True, ink)
        screen.blit(shown, (x, y + (h - shown.get_height()) // 2))
    for title, (x, y, _, h) in layout.group_titles:
        caret = "caret-right" if title in scene.folded else "caret-down"
        fonts.icons.draw(screen, caret, (x + 5, y + h // 2), 14, ink)
        shown = fonts.small.render(title.upper(), True, ink)
        screen.blit(shown, (x + 16, y + (h - shown.get_height()) // 2))
    board = scene.board
    for kind, rect in layout.menu_items:
        left = board.remaining(kind)
        status = ("infinity", "") if left is None else ("count", f"{left}/{board.total(kind)}")
        picked = kind == scene.picked
        _draw_row(
            screen, scene, fonts, rect, kind, NAME[kind], status, picked, left == 0, part=kind
        )
    for tool, rect in layout.tool_buttons:
        key = ("key", TOOL_KEYS[tool])
        _draw_row(
            screen,
            scene,
            fonts,
            rect,
            tool,
            ROW_NAME[tool],
            key,
            tool is scene.tool,
            icon=TOOL_ICON[tool],
        )
    can = {EditButton.UNDO: scene.history.can_undo, EditButton.REDO: scene.history.can_redo}
    for button, rect in layout.edit_buttons:
        key = ("key", EDIT_KEYS[button].replace("+", " "))
        _draw_row(
            screen,
            scene,
            fonts,
            rect,
            button,
            ROW_NAME[button],
            key,
            False,
            not can[button],
            icon=EDIT_ICON[button],
        )
    for button, rect in layout.file_buttons:  # in their place, inactive until saving exists
        _draw_row(
            screen,
            scene,
            fonts,
            rect,
            button,
            ROW_NAME[button],
            ("lock", ""),
            False,
            True,
            icon=FILE_ICON[button],
        )
    for button, rect in layout.view_buttons:
        active = button is ViewButton.PAN and scene.tool is Tool.PAN
        key = ("key", VIEW_KEYS[button])
        _draw_row(
            screen,
            scene,
            fonts,
            rect,
            button,
            ROW_NAME[button],
            key,
            active,
            icon=VIEW_ICON[button],
        )
    settings = scene.settings
    shown = {
        Setting.FAST: ("count", f"{settings.fast}x"),
        Setting.HINTS: ("tick", "on") if settings.key_hints else ("count", "off"),
        Setting.TOOLTIPS: ("count", f"{settings.tooltip_seconds:.1f} s"),
        Setting.TUTORIAL: ("none", ""),
    }
    for setting, rect in layout.setting_rows:
        name, icon, _ = SETTING[setting]
        status = shown.get(setting, ("lock", ""))
        greyed = setting not in shown  # Sound and Music: no sound yet
        _draw_row(screen, scene, fonts, rect, setting, name, status, False, greyed, icon=icon)
    places = {row.index: row for row in scene.chapters}
    for index, rect in layout.chapter_rows:
        row = places.get(index)
        if row is None:
            continue
        if row.state == "won":
            status = ("tick", "")  # the fastest win is in the row's info box
        else:
            status = ("lock", "") if row.state == "locked" else ("none", "")
        badge = row.label or None
        icon = None if badge else "border-all"  # the sandbox
        locked = row.state == "locked"
        _draw_row(
            screen,
            scene,
            fonts,
            rect,
            index,
            "Sandbox" if row.state == "sandbox" else row.title,
            status,
            row.current,
            locked,
            icon=icon,
            badge=badge,
        )
    handle = pygame.Rect(layout.fold_handle)
    corners = {"border_top_right_radius": 6, "border_bottom_right_radius": 6}
    pygame.draw.rect(screen, PANEL, handle, **corners)
    pygame.draw.rect(screen, RULE, handle, 1, **corners)
    fonts.icons.draw(screen, "chevron-left", handle.center, 11, DIM_TEXT)


def _draw_row(
    screen: pygame.Surface,
    scene: EditorScene,
    fonts: Fonts,
    rect,
    what: object,
    name: str,
    status: tuple[str, str],
    active: bool = False,
    greyed: bool = False,
    icon: str | None = None,
    part: Kind | None = None,
    badge: str | None = None,
) -> None:
    """A drawer's row, as every drawer draws them (D-051): an icon (or the part itself, or a
    level's number), the name, an info disc, then a count, the infinity sign, a key, a tick or a
    lock, right-aligned; nothing for "none". Keys show while the key hints are on (D-054)."""
    box = pygame.Rect(rect)
    pygame.draw.rect(screen, ACTIVE if active else BUTTON, box, border_radius=6)
    ink = GREYED if greyed else TEXT
    slot = (box.left + 20, box.centery)
    if part is not None:
        fill = GREYED if greyed else None
        draw_part(screen, fonts, part, MENU_ANGLE.get(part), slot, 24, False, fill)
    elif badge is not None:
        label = fonts.small.render(badge, True, DIM_TEXT if greyed else TEXT)
        screen.blit(label, label.get_rect(center=slot))
    elif icon is not None:
        fonts.icons.draw(screen, icon, slot, 16, ink)
    shown = fonts.text.render(name, True, DIM_TEXT if greyed else TEXT)
    screen.blit(shown, (box.left + 42, box.centery - shown.get_height() // 2))
    disc = TEXT if what == scene.info else DIM_TEXT
    fonts.icons.draw(screen, "circle-info", (box.left + INFO_AT, box.centery), INFO_ICON, disc)
    kind, text = status
    right = box.right - 10
    if kind == "infinity":
        fonts.icons.draw(screen, "infinity", (right - 8, box.centery), 14, ink)
    elif kind == "lock":
        fonts.icons.draw(screen, "lock", (right - 6, box.centery), 12, GREYED)
    elif kind == "tick":
        shown = fonts.small.render(text, True, DIM_TEXT)
        screen.blit(shown, shown.get_rect(midright=(right, box.centery)))
        x = right - shown.get_width() - 12 if text else right - 6
        fonts.icons.draw(screen, "check", (x, box.centery), 12, LIT)
    elif kind == "none":
        pass
    elif kind == "key":
        if not scene.settings.key_hints:
            return
        cap = fonts.small.render(text, True, GREYED if greyed else DIM_TEXT)
        cap_box = cap.get_rect(midright=(right, box.centery)).inflate(10, 4)
        pygame.draw.rect(screen, RULE, cap_box, 1, border_radius=4)
        screen.blit(cap, cap.get_rect(center=cap_box.center))
    else:
        count = fonts.text.render(text, True, DIM_TEXT if greyed else TEXT)
        screen.blit(count, count.get_rect(midright=(right, box.centery)))


def _draw_tabs(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """The tabs over the board, Editor lit, then the level's title and what it asks."""
    layout = scene.layout
    left = layout.board_area[0]
    pygame.draw.rect(screen, BAR, (left, 0, SCREEN[0] - left, TABS_HEIGHT))
    for name, rect in layout.tabs:
        box = pygame.Rect(rect)
        on = name == "editor"
        if on:
            pygame.draw.rect(screen, BACKGROUND, box)
            pygame.draw.rect(screen, LIT, (box.left, 0, box.width, 2))
        label = fonts.small.render(TAB_NAME[name], True, TEXT if on else DIM_TEXT)
        screen.blit(label, label.get_rect(center=box.center))
        pygame.draw.line(screen, RULE, (box.right, 6), (box.right, TABS_HEIGHT - 6))
    title, spec = scene.caption
    if title:
        x, y = layout.caption_at
        shown = fonts.small.render(title, True, TEXT)
        screen.blit(shown, (x, y))
        screen.blit(fonts.small.render(spec, True, DIM_TEXT), (x + shown.get_width() + 10, y))


def draw_title(
    screen, fonts: Fonts, title: str, topleft, height: int = PALETTE_TITLE, lit: bool = False
) -> None:
    """A section's title, as every view writes them: upper case, dimmed, centred in `height`;
    `lit`, in the accent, while a tutorial step explains its panel (D-050)."""
    text = fonts.text.render(title.upper(), True, LIT if lit else DIM_TEXT)
    screen.blit(text, (topleft[0], topleft[1] + (height - text.get_height()) // 2))


def draw_button(screen, fonts: Fonts, rect, icon: str, active: bool, enabled: bool = True) -> None:
    """A palette button: lit while `active`, its icon greyed when it would do nothing."""
    pygame.draw.rect(screen, ACTIVE if active else BUTTON, rect, border_radius=6)
    x, y, w, h = rect
    fonts.icons.draw(screen, icon, (x + w // 2, y + h // 2), 20, TEXT if enabled else GREYED)


def draw_tip(screen: pygame.Surface, fonts: Fonts, text: str, **where) -> None:
    """A tooltip: `text` placed by keywords of `Rect.get_rect` (e.g. midright=(x, y)), in a box
    8 px wider on each side."""
    shown = fonts.text.render(text, True, TEXT)
    box = shown.get_rect(**where).inflate(16, 10)
    pygame.draw.rect(screen, TOOLTIP_BG, box, border_radius=5)
    pygame.draw.rect(screen, RULE, box, 1, border_radius=5)
    screen.blit(shown, shown.get_rect(center=box.center))


def _draw_tooltip(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """The name of the bar's icon under the mouse, and its key if it has one, beside the bar."""
    target = scene.tooltip
    if target is None:
        return
    rects = dict(scene.layout.drawer_buttons) | dict(scene.layout.level_buttons)
    _, y, _, h = rects[target]
    key = (LEVEL_KEYS | DRAWER_KEYS).get(target) if scene.settings.key_hints else None
    text = TIP[target] + (f" ({key})" if key else "")
    draw_tip(screen, fonts, text, midleft=(BAR_WIDTH + 10, y + h // 2))


def _draw_info(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """The open info box, beside the drawer at its row: the name, then what it does."""
    if scene.info is None:
        return
    what = scene.info
    places = {row.index: row for row in scene.chapters}
    if isinstance(what, Kind):
        name, lines = NAME[what], info(what)
    elif isinstance(what, Setting):
        name, _, line = SETTING[what]
        lines = (line,)
    elif isinstance(what, int) and what in places:
        place = places[what]
        name, lines = place.title, (place.spec,)
        if place.best is not None:
            lines += (f"Fastest win: {place.best.ticks * DT:.2f} s, {place.best.parts} parts.",)
    else:
        name, lines = ROW_NAME[what], (HINT.get(what) or TIP[what],)
    rows = [fonts.text.render(name, True, TEXT)]
    rows += [fonts.small.render(line, True, TEXT) for line in lines]
    width = max(row.get_width() for row in rows) + 2 * INFO_PAD
    height = sum(row.get_height() + 4 for row in rows) + 2 * INFO_PAD
    _, top, _, _ = dict(scene.layout.info_buttons)[what]
    top = min(top, screen.get_height() - height - 8)  # kept on screen
    area = scene.layout.drawer_area or scene.layout.bar_area
    box = pygame.Rect(area[0] + area[2] + 8, top, width, height)
    pygame.draw.rect(screen, TOOLTIP_BG, box, border_radius=6)
    pygame.draw.rect(screen, RULE, box, 1, border_radius=6)
    y = box.top + INFO_PAD
    for row in rows:
        screen.blit(row, (box.left + INFO_PAD, y))
        y += row.get_height() + 4


def _draw_status(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    if scene.message:
        text, colour = scene.message, REFUSED
    elif isinstance(scene.ghost, Refused):
        text, colour = scene.ghost.reason, REFUSED
    else:
        text, colour = HINT[scene.tool], DIM_TEXT
    left = scene.layout.board_area[0]
    strip = (left, SCREEN[1] - STATUS_HEIGHT, SCREEN[0] - left, STATUS_HEIGHT)
    pygame.draw.rect(screen, BAR, strip)
    screen.blit(fonts.small.render(text, True, colour), scene.layout.status_at)
