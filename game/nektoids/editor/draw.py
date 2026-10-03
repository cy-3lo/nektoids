"""Drawing the editor. Reads the scene and the board; never changes them.

The frame (D-051): the activity bar down the left edge, its open drawer's icon lit with an
accent bar, Chapters and the accented switch to the Run at its foot; the open drawer, its rows
all alike (icon, name, info disc, then a count, a key or a lock), an arrow on its edge to fold
it; the tabs over the board, the level's caption under them; the status line at the board's
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
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pygame

from nektoids.editor.devdrive import DT
from nektoids.editor.frame import Frame
from nektoids.editor.geometry import body_circle, symbol_corners, wire_arrows, wire_points
from nektoids.editor.icons import (
    DRAWER_ICON,
    EDIT_ICON,
    FILE_ICON,
    KIND_ICON,
    LEVEL_ICON,
    MODE_ICON,
    TOOL_ICON,
    VIEW_ICON,
    Icons,
)
from nektoids.editor.layout import (
    BAR_WIDTH,
    CAPTION_HEIGHT,
    CELL_TITLE,
    DIAGNOSTIC_MAP,
    DRAWER_KEYS,
    EDIT_KEYS,
    INFO_AT,
    LEVEL_KEYS,
    MARGIN,
    MAX_HEX,
    MODE_KEY,
    PALETTE_TITLE,
    SCREEN,
    STATUS_HEIGHT,
    SWITCH_TO,
    TABS_HEIGHT,
    VIEW_KEYS,
    Drawer,
    EditButton,
    FileButton,
    LevelButton,
    Mode,
    Setting,
    Tool,
    View,
    ViewButton,
    WinRow,
    level_of,
    overview_view,
    scroll_thumb,
    shown_frame,
    visible_cells,
)
from nektoids.editor.palette import (
    ACTIVE,
    BACKGROUND,
    BAR,
    BODY,
    BODY_OUTLINE,
    BUTTON,
    COMPONENT,
    DARK,
    DIM_TEXT,
    DOOMED,
    EYE_FACE,
    FLASH,
    FOCUS_CELL,
    FULL,
    GHOST,
    GHOST_FILL,
    GHOST_OK,
    GREYED,
    GRID_LINE,
    HOVER,
    ICON_EDGE,
    LIGHT,
    LIT,
    LOCK_RING,
    OBSTACLE,
    OUTSIDE,
    OUTSIDE_LINE,
    PANEL,
    REFUSED,
    RING,
    RULE,
    SCROLL_THUMB,
    SHADOW,
    TEXT,
    THRUSTER_BACK,
    TOOLTIP_BG,
    WIRE,
    ZONE,
)
from nektoids.editor.parts import NAME, info
from nektoids.editor.probe import level_view, ring_radii
from nektoids.editor.ring import ICON, LINE_BELOW, RING_HEX
from nektoids.editor.scene import EditorScene
from nektoids.graph.board import Category, Kind, Refused
from nektoids.graph.hexgrid import Cell, to_pixel
from nektoids.sim.arena import BASE_RADIUS, LIGHT_RADIUS

TIP = {
    Tool.ADD: "Add a part",
    Tool.WIRE: "Wire",
    Tool.TURN_LEFT: "Turn left",
    Tool.TURN_RIGHT: "Turn right",
    Tool.MOVE: "Move a part",
    Tool.DELETE: "Delete",
    Tool.SWAP: "Swap for another part",
    ViewButton.ZOOM_IN: "Zoom in",
    ViewButton.ZOOM_OUT: "Zoom out",
    ViewButton.PAN: "Move the view",
    ViewButton.CENTRE: "Centre the view",
    ViewButton.RAYS: "Show or hide the light's rays",
    EditButton.UNDO: "Undo",
    EditButton.REDO: "Redo",
    Mode.WRITE: "Click a cell: Tools and Parts show its ring. Click two parts to wire them; drag"
    " one to move it.",
    Mode.DELETE: "A click removes the part under it, with its wires, or the wire under it.",
    FileButton.SAVE: "Save: not yet",
    FileButton.LOAD: "Load: not yet",
    LevelButton.RUN: "Run",
    LevelButton.EDIT: "Back to the editor",
    Drawer.TOOLS: "Tools",
    Drawer.PARTS: "Parts",
    Drawer.FILES: "Files",
    Drawer.DIAGNOSTIC: "Diagnostic",
    Drawer.INSIDE: "Inside",
    Drawer.SCORE: "Score",
    Drawer.NAVIGATOR: "Navigator",
    Drawer.SETTINGS: "Settings",
    Drawer.CHAPTERS: "Chapters",
}
SETTING = {  # Settings' rows: their name, icon and what their info box says (D-054)
    Setting.FAST: ("Fast forward", "forward", "How fast the run goes when fast forward is on."),
    Setting.HINTS: ("Key hints", "keyboard", "Show each row's key, and the bar's in its tooltip."),
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
    Tool.SWAP: "Swap",
    EditButton.UNDO: "Undo",
    EditButton.REDO: "Redo",
    Mode.WRITE: "Write",
    Mode.DELETE: "Delete",
    FileButton.SAVE: "Save",
    FileButton.LOAD: "Load",
    ViewButton.ZOOM_IN: "Zoom in",
    ViewButton.ZOOM_OUT: "Zoom out",
    ViewButton.PAN: "Hand",
    ViewButton.CENTRE: "Centre",
    ViewButton.RAYS: "Rays",
}
TAB_NAME = {"editor": "Editor", "run": "Run"}

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


# IBM Plex Mono, Medium (SIL OFL 1.1, with its licence beside it): every letter as wide as the
# next, so the gaps within a word are even at any size (D-055). Opened by path: pygbag cannot
# open a font from memory.
ASSETS = Path(__file__).resolve().parent.parent / "assets"
TEXT_FONT_FILE = ASSETS / "plexmono" / "IBMPlexMono-Medium.ttf"


@dataclass(frozen=True)
class Fonts:
    """The fonts by their job (D-055): FreeSans Bold, pygame's own, names things; Plex Mono
    explains them."""

    text: pygame.font.Font  # what explains: info lines, counts, values, tooltips, card lines
    small: pygame.font.Font  # the same, smaller: the tutorial, the status line, the panels
    name: pygame.font.Font  # what names: titles, rows, objectives, info headings, buttons
    label: pygame.font.Font  # the same, smaller: section labels, tabs, keys, the box's buttons
    big: pygame.font.Font  # the cards' titles, the end's thanks
    icons: Icons

    @classmethod
    def load(cls) -> Fonts:
        """Call once at startup, after pygame.init() (web.md: every asset at startup)."""
        return cls(
            text=pygame.font.Font(TEXT_FONT_FILE, 17),
            small=pygame.font.Font(TEXT_FONT_FILE, 15),
            name=pygame.font.Font(None, 22),
            label=pygame.font.Font(None, 18),
            big=pygame.font.Font(None, 64),
            icons=Icons(),
        )


def draw(
    screen: pygame.Surface, scene: EditorScene, fonts: Fonts, main: Callable | None = None
) -> None:
    """The editor: its main screen, the board on its grid, or what `main(screen, scene, fonts)`
    draws there instead (the Run preview, D-058); then the frame round it."""
    screen.fill(BACKGROUND)
    (main or _draw_board)(screen, scene, fonts)
    if scene.layout.action_at is not None:  # while Tools is folded (D-068)
        _draw_action(screen, scene, fonts)
    draw_tabs(screen, scene, fonts)
    _draw_status(screen, scene, fonts)
    draw_bar(screen, scene, fonts)
    draw_drawer(screen, scene, fonts, _draw_rows)
    draw_tooltip(screen, scene, fonts)
    draw_info(screen, scene, fonts, _about)
    if scene.dragging and scene.picked is not None:
        size = scene.view.size
        angle = placed_angle(scene.picked, scene.picked.default_facing)  # as it will land
        draw_part(screen, fonts, scene.picked, angle, scene.mouse, size, locked=False)


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
        elif cell == scene.focused:  # the ring's cell, the keyboard's (D-068)
            pygame.draw.polygon(screen, ACTIVE, hexagon)
        elif cell in scene.guide_cells:  # a cell a tutorial's step acts on (D-063)
            pygame.draw.polygon(screen, FOCUS_CELL, hexagon)
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

    for ghost in scene.ghosts:  # where a part goes, facing the way it should (D-039, D-060)
        centre, angle = _centre(view, ghost.cell), placed_angle(ghost.kind, ghost.facing)
        pygame.draw.polygon(screen, GHOST_FILL, _shape(ghost.kind, angle, centre, view.size))
    for node in board.nodes.values():
        centre = _centre(view, node.cell)
        angle = placed_angle(node.kind, node.facing)
        fill = DOOMED if node.id == doomed_node else None
        draw_part(screen, fonts, node.kind, angle, centre, view.size, node.locked, fill)
    for ghost in scene.ghosts:  # over a part that does not face its way yet: where to turn it
        node = board.node_at(ghost.cell)
        if node is not None and node.kind is ghost.kind and node.facing != ghost.facing:
            angle = placed_angle(ghost.kind, ghost.facing)
            outline = _shape(ghost.kind, angle, _centre(view, ghost.cell), view.size)
            pygame.draw.polygon(screen, GHOST_OK, outline, 2)
    if isinstance(scene.ghost, Refused) and scene.hover is not None:
        pygame.draw.polygon(screen, REFUSED, _hexagon(view, scene.hover), 2)
    if scene.focused is not None:  # the cell Tools and Parts show (D-068, D-069)
        pygame.draw.polygon(screen, LIT, _hexagon(view, scene.focused), 2)
    screen.set_clip(None)


def _draw_action(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """Atop the main screen: what the next click or Enter does (D-068), as a lit button with its
    key beside it while key hints are on, and a line under it saying what it is. A click on it
    opens Tools."""
    box = pygame.Rect(scene.layout.action_at)
    what, key = scene.action()
    _draw_disc(screen, fonts, box.center, what, ACTIVE, LIT)  # as the ring draws its icons
    if scene.settings.key_hints:
        shown = fonts.text.render(key, True, DIM_TEXT)
        screen.blit(shown, shown.get_rect(midleft=(box.right + 8, box.centery)))
    says = fonts.small.render(_action_says(scene, what), True, TEXT)
    at = says.get_rect(midtop=(box.centerx, box.bottom + 8))  # its patch clear of the disc
    pygame.draw.rect(screen, BAR, at.inflate(14, 6), border_radius=5)  # legible over the grid
    screen.blit(says, at)


ACTION_SAYS = {  # under the action atop the main screen: what it is (D-068)
    Mode.WRITE: "Write: a click on a cell shows what can be done there",
    Mode.DELETE: "Delete: a click removes the part or the wire under it",
    Tool.WIRE: "Wire: the next part clicked is wired to this one",
    Tool.MOVE: "Move: the part goes to the next empty cell clicked, or with the arrows",
    Tool.TURN_LEFT: "Turn left: the part turns 60° counter-clockwise",
    Tool.TURN_RIGHT: "Turn right: the part turns 60° clockwise",
    Tool.DELETE: "Delete: the part goes, and its wires with it",
    Tool.SWAP: "Swap: the part becomes another of its group",
    Tool.PAN: "Hand: a drag on the board moves the view",
}


def _action_says(scene: EditorScene, what: Kind | Tool | Mode) -> str:
    if not isinstance(what, Kind):
        return ACTION_SAYS[what]
    if scene.swapping:
        return f"{NAME[what]}: Enter swaps the part for one"
    if scene.picked is what:
        return f"{NAME[what]}: a click on a cell places one there"
    return f"{NAME[what]}: Enter places one on the cell"


def _draw_disc(screen, fonts: Fonts, at, what: Kind | Tool | Mode | None, fill, edge) -> None:
    """One of the ring's icons, or the action atop the main screen, alike (D-068): a disc, the
    part on it just smaller than Tools' cell's, or the action's glyph; empty for None."""
    radius = ICON * RING_HEX
    pygame.draw.circle(screen, fill, at, radius)
    pygame.draw.circle(screen, edge, at, radius, 2)
    if isinstance(what, Kind):  # its tips well inside the disc, a diamond's too
        draw_part(screen, fonts, what, MENU_ANGLE.get(what), at, 1.15 * radius, False)
    elif what is not None:
        fonts.icons.draw(screen, _action_icon(what), at, round(1.05 * radius), TEXT)


def _action_icon(what: Tool | Mode) -> str:
    if isinstance(what, Mode):
        return MODE_ICON[what]
    return VIEW_ICON[ViewButton.PAN] if what is Tool.PAN else TOOL_ICON[what]


def _draw_cell(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """At the foot of Tools and of Parts (D-068, D-069): a rule, The cell's title, which folds;
    unless folded, the focused cell, large, as the board has it, its ring round it, a line under
    it saying what it holds."""
    layout = scene.layout
    fx, fy, fw, fh = layout.cell_fold
    pygame.draw.line(screen, RULE, (fx, fy - 3), (fx + fw, fy - 3), 2)  # the bar that divides
    draw_fold_title(screen, fonts, CELL_TITLE, layout.cell_fold, scene.cell_folded, DIM_TEXT)
    if layout.cell_view is None:
        return
    x, y, w, h = layout.cell_view
    centre = scene.cell_centre()
    corners = _small_hexagon(centre, RING_HEX)
    focused = scene.focused is not None
    if focused:
        pygame.draw.polygon(screen, ACTIVE, corners)
        pygame.draw.polygon(screen, LIT, corners, 2)
        node = scene.board.node_at(scene.focused)
        if node is not None:
            fill = DOOMED if node.id == scene.doomed()[0] else None
            angle = placed_angle(node.kind, node.facing)
            draw_part(screen, fonts, node.kind, angle, centre, RING_HEX, node.locked, fill)
    else:
        pygame.draw.polygon(screen, RULE, corners, 1)
    ring = scene.ring()
    k = scene.choice if scene.going_round() and scene.choice is not None else len(ring)
    chosen = ring[k] if k < len(ring) else None
    in_hand = scene.tool if scene.tool in (Tool.WIRE, Tool.MOVE) else None
    radius = ICON * RING_HEX
    for slot in sorted(ring, key=lambda s: -s.depth):  # down a pile, the further first, under
        if slot.depth:  # piled: an empty disc, its edge showing past the one over it
            turning = (slot.at[0] > centre[0]) == (scene.piling > 0) and scene.piling != 0
            _draw_disc(screen, fonts, slot.at, None, BUTTON, LIT if turning else ICON_EDGE)
            continue
        lit = slot == chosen or slot.what is in_hand
        fill = ACTIVE if lit else HOVER if slot == scene.ring_hover else BUTTON
        _draw_disc(screen, fonts, slot.at, slot.what, fill, LIT if lit else ICON_EDGE)
        if scene.settings.key_hints:
            key = fonts.small.render(slot.key, True, LIT if lit else DIM_TEXT)
            screen.blit(key, key.get_rect(center=(round(slot.key_at[0]), round(slot.key_at[1]))))
    lowest = max([centre[1] + RING_HEX] + [slot.at[1] + radius for slot in ring])
    line = fonts.small.render(_fitted(fonts.small, _cell_says(scene), w), True, DIM_TEXT)
    screen.blit(line, line.get_rect(midtop=(round(centre[0]), round(lowest) + LINE_BELOW)))


def _draw_tools(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """Tools' rows (D-068): Write and Delete, undo and redo."""
    layout = scene.layout
    for mode, rect in layout.mode_buttons:
        status = ("key", MODE_KEY)
        icon = MODE_ICON[mode]
        draw_row(
            screen, scene, fonts, rect, mode, ROW_NAME[mode], status, mode is scene.mode, icon=icon
        )
    can = {EditButton.UNDO: scene.history.can_undo, EditButton.REDO: scene.history.can_redo}
    for button, rect in layout.edit_buttons:
        status = ("key", EDIT_KEYS[button].replace("+", " "))
        icon = EDIT_ICON[button]
        draw_row(
            screen,
            scene,
            fonts,
            rect,
            button,
            ROW_NAME[button],
            status,
            False,
            not can[button],
            icon=icon,
        )


def _cell_says(scene: EditorScene) -> str:
    """The line under the drawer's picture of the cell."""
    if scene.mode is Mode.DELETE:
        return "Click what goes"
    if scene.focused is None:
        return "Click a cell"
    node = scene.board.node_at(scene.focused)
    if node is None:
        return "An empty cell" if scene.offered() else "Empty: no part left"
    if scene.swapping:
        return f"Swap the {NAME[node.kind].lower()} for:"
    return NAME[node.kind] + (", the level's" if node.locked else "")


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


# The frame, the editor's and the run's (D-051): `scene` is a `frame.Frame`


def draw_bar(screen: pygame.Surface, scene: Frame, fonts: Fonts) -> None:
    """The activity bar: the drawers' icons, the open one lit, an accent bar on its edge; at the
    foot, Settings, Chapters and the accented switch to the other environment."""
    layout = scene.layout
    pygame.draw.rect(screen, BAR, layout.bar_area)
    for drawer, rect in layout.drawer_buttons:
        on = drawer is layout.drawer
        box = pygame.Rect(rect)
        if on:
            pygame.draw.rect(screen, LIT, (0, box.top + 2, 3, box.height - 4))
        fonts.icons.draw(screen, DRAWER_ICON[drawer], box.center, 22, TEXT if on else DIM_TEXT)
    for button, rect in layout.level_buttons:  # the switch
        box = pygame.Rect(rect)
        pygame.draw.rect(screen, ACTIVE, box, border_radius=8)
        fonts.icons.draw(screen, LEVEL_ICON[button], box.center, 18, TEXT)


def draw_drawer(screen: pygame.Surface, scene: Frame, fonts: Fonts, rows: Callable) -> None:
    """The open drawer: its title, its sections or groups, its rows, the arrow that folds it.
    `rows(screen, scene, fonts)` draws the environment's own rows; Settings' and Chapters' are
    drawn here."""
    layout = scene.layout
    if layout.drawer is None:
        return
    area = pygame.Rect(layout.drawer_area)
    pygame.draw.rect(screen, PANEL, area)
    pygame.draw.line(screen, RULE, (area.right - 1, 0), (area.right - 1, area.bottom), 2)
    lit = layout.drawer.value in scene.lit  # a tutorial step explains it (D-050)
    ink = LIT if lit else DIM_TEXT
    draw_title(screen, fonts, TIP[layout.drawer], layout.drawer_title_at, lit=lit)
    for title, (x, y, _, h) in layout.section_titles:  # lit with its drawer, or by its name
        shown = fonts.label.render(title.upper(), True, LIT if title.lower() in scene.lit else ink)
        screen.blit(shown, (x, y + (h - shown.get_height()) // 2))
    screen.set_clip(layout.list_area)  # Parts' list scrolls within it (D-069); None: no clip
    for title, rect in layout.group_titles:
        draw_fold_title(screen, fonts, title, rect, title in scene.folded, ink)
    screen.set_clip(None)
    rows(screen, scene, fonts)
    _draw_settings(screen, scene, fonts)
    _draw_chapters(screen, scene, fonts)
    handle = pygame.Rect(layout.fold_handle)
    corners = {"border_top_right_radius": 6, "border_bottom_right_radius": 6}
    pygame.draw.rect(screen, PANEL, handle, **corners)
    pygame.draw.rect(screen, RULE, handle, 1, **corners)
    fonts.icons.draw(screen, "chevron-left", handle.center, 11, DIM_TEXT)


def draw_fold_title(screen, fonts: Fonts, title: str, rect, folded: bool, ink) -> None:
    """A title that folds what is under it, as Parts' groups and The cell (D-069): a caret, right
    while folded, down while open, then the title in upper case."""
    x, y, _, h = rect
    caret = "caret-right" if folded else "caret-down"
    fonts.icons.draw(screen, caret, (x + 5, y + h // 2), 14, ink)
    shown = fonts.label.render(title.upper(), True, ink)
    screen.blit(shown, (x + 16, y + (h - shown.get_height()) // 2))


def _draw_files(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """Files (D-059): this session's wins of the level, the best first, a tick on those no other
    beats, the one on the board now lit; a click puts its board back."""
    now = scene.board.snapshot()
    for row, rect in scene.layout.win_rows:
        won = scene.wins[row.index]
        status = ("tick", "") if won.best else ("none", "")
        active = won.board == now
        draw_row(screen, scene, fonts, rect, row, _win_name(won), status, active, icon="trophy")
    rows = scene.layout.win_rows
    top = rows[-1][1][1] + rows[-1][1][3] + 12 if rows else DIAGNOSTIC_MAP[1]
    note = (
        "Each win of this level is kept here for the session. A click puts its board back;"
        " Undo brings yours back."
        if rows
        else "No win yet. Each win of this level will be kept here for the session."
    )
    draw_note(screen, fonts, note, (DIAGNOSTIC_MAP[0], top), DIAGNOSTIC_MAP[2])


def _win_name(won) -> str:
    return f"{won.score.ticks * DT:.2f} s, {won.score.parts} parts"


def draw_level_map(
    screen: pygame.Surface,
    level,
    area: pygame.Rect,
    pose: tuple[float, float, float],
    frame: pygame.Rect | None = None,
    view=None,
) -> None:
    """The level seen whole and small in `area`: its obstacles, its lights and their rings, and
    the swimmer at `pose` (x, y [u], heading [rad]); `frame`, what the main screen shows of it,
    outlined (Diagnostic's map, the run's overview, D-058, D-060); `view`, how it is seen, else the
    level seen whole."""
    view, arena = view or level_view(level, tuple(area)), level.arena
    pygame.draw.rect(screen, SHADOW, area, border_radius=6)
    screen.set_clip(area)
    for disc in arena.obstacles:
        pygame.draw.circle(
            screen, OBSTACLE, view.to_screen(disc.x, disc.y), disc.radius * view.scale
        )
    for radius in ring_radii(level):
        for x, y in arena.light_xy:
            pygame.draw.circle(screen, RING, view.to_screen(x, y), radius * view.scale, 1)
    for light in arena.lights:
        pygame.draw.circle(
            screen, LIGHT, view.to_screen(light.x, light.y), LIGHT_RADIUS * view.scale
        )
    x, y, heading = pose
    draw_symbol(screen, BODY, view.to_screen(x, y), BASE_RADIUS * view.scale, heading, 2)
    if frame is not None:
        pygame.draw.rect(screen, LIT, frame, 1)
    screen.set_clip(None)
    pygame.draw.rect(screen, RULE, area, 1, border_radius=6)


def draw_zoom(screen: pygame.Surface, scene: Frame, fonts: Fonts, level: float) -> None:
    """Navigator's zoom (D-065): out and in either end of a bar filled to `level`, 0 the
    farthest, 1 the nearest, a knob where it stands; the bar is pressed or dragged too."""
    icons = {
        ViewButton.ZOOM_OUT: "magnifying-glass-minus",
        ViewButton.ZOOM_IN: "magnifying-glass-plus",
    }
    for button, rect in scene.layout.zoom_buttons:
        draw_button(screen, fonts, rect, icons[button], False)
    x, y, w, h = scene.layout.zoom_bar
    track = pygame.Rect(x, y + h // 2 - 3, w, 6)
    pygame.draw.rect(screen, RULE, track, border_radius=3)
    filled = track.copy()
    filled.width = round(w * level)
    if filled.width > 0:
        pygame.draw.rect(screen, FULL, filled, border_radius=3)
    knob = (x + round(w * level), track.centery)
    pygame.draw.circle(screen, FULL, knob, 6)
    pygame.draw.circle(screen, DARK, knob, 6, 1)


def _draw_overview(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """Navigator's overview (D-060): the whole board small, its parts as dots, and a frame round
    what the main screen shows; a press or a drag there moves the view."""
    area = pygame.Rect(scene.layout.overview)
    pygame.draw.rect(screen, SHADOW, area, border_radius=6)
    small = overview_view(scene.layout, sorted(scene.board.cells))
    screen.set_clip(area)
    for cell in scene.board.cells:
        pygame.draw.polygon(screen, ZONE, _hexagon(small, cell))
    for node in scene.board.nodes.values():
        pygame.draw.circle(screen, COMPONENT, _centre(small, node.cell), 0.45 * small.size)
    pygame.draw.rect(screen, LIT, shown_frame(scene.layout, scene.view, small), 1)
    screen.set_clip(None)
    pygame.draw.rect(screen, RULE, area, 1, border_radius=6)


def _draw_diagnostic(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """Diagnostic (D-058, D-069): the level small, its obstacles, its lights and their rings,
    and the probe, the swimmer the Run preview runs at, to drag and turn."""
    area = pygame.Rect(DIAGNOSTIC_MAP)
    if scene.level is not None and scene.probe is not None:
        draw_level_map(screen, scene.level, area, scene.probe.pose)
    else:
        pygame.draw.rect(screen, SHADOW, area, border_radius=6)
        pygame.draw.rect(screen, RULE, area, 1, border_radius=6)
    note = (
        "Drag the swimmer anywhere; the wheel, or L and R, turn it. The main screen runs your"
        " board there."
    )
    draw_note(screen, fonts, note, (area.left, area.bottom + 10), area.width)


def draw_note(
    screen: pygame.Surface, fonts: Fonts, text: str, at: tuple[int, int], width: int
) -> None:
    """A dim note, broken into lines no wider than `width` [px], from `at` down."""
    line, lines = "", []
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and fonts.small.size(trial)[0] > width:
            lines.append(line)
            line = word
        else:
            line = trial
    for k, part in enumerate([*lines, line]):
        screen.blit(fonts.small.render(part, True, DIM_TEXT), (at[0], at[1] + 20 * k))


def _small_hexagon(centre: tuple[float, float], radius: float) -> list[tuple[float, float]]:
    """A hex cell's corners for an icon, pointy side up, as the board draws them."""
    angles = (math.radians(30 + 60 * k) for k in range(6))
    return [(centre[0] + radius * math.cos(a), centre[1] + radius * math.sin(a)) for a in angles]


def _draw_rows(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """The editor's own drawers' rows: Tools, Parts, Files, Navigator; the cell at the foot of
    Tools and Parts; Diagnostic's map."""
    layout, board = scene.layout, scene.board
    if layout.cell_fold is not None:  # Tools, Parts
        _draw_cell(screen, scene, fonts)
    if layout.drawer is Drawer.TOOLS:
        _draw_tools(screen, scene, fonts)
    if layout.drawer is Drawer.DIAGNOSTIC:
        _draw_diagnostic(screen, scene, fonts)
    if layout.drawer is Drawer.FILES:
        _draw_files(screen, scene, fonts)
    if layout.overview is not None:
        _draw_overview(screen, scene, fonts)
        draw_zoom(screen, scene, fonts, level_of(scene.view.size, scene.least_zoom(), MAX_HEX))
    screen.set_clip(layout.list_area)  # Parts' list, scrolled within its area (D-069)
    for kind, rect in layout.menu_items:
        left = board.remaining(kind)
        status = ("infinity", "") if left is None else ("count", f"{left}/{board.total(kind)}")
        picked = kind == scene.picked
        draw_row(screen, scene, fonts, rect, kind, NAME[kind], status, picked, left == 0, part=kind)
    screen.set_clip(None)
    if layout.scroll_bar is not None:  # while the list does not fit
        pygame.draw.rect(screen, RULE, layout.scroll_bar, border_radius=2)
        pygame.draw.rect(screen, SCROLL_THUMB, scroll_thumb(layout), border_radius=2)
    for button, rect in layout.file_buttons:  # in their place, inactive until saving exists
        draw_row(
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
        draw_row(
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


def _draw_settings(screen: pygame.Surface, scene: Frame, fonts: Fonts) -> None:
    settings = scene.settings
    shown = {
        Setting.FAST: ("count", f"{settings.fast}x"),
        Setting.HINTS: ("tick", "on") if settings.key_hints else ("count", "off"),
        Setting.TUTORIAL: ("none", ""),
    }
    for setting, rect in scene.layout.setting_rows:
        name, icon, _ = SETTING[setting]
        status = shown.get(setting, ("lock", ""))
        greyed = setting not in shown  # Sound and Music: no sound yet
        draw_row(screen, scene, fonts, rect, setting, name, status, False, greyed, icon=icon)


def _draw_chapters(screen: pygame.Surface, scene: Frame, fonts: Fonts) -> None:
    places = {row.index: row for row in scene.chapters}
    for index, rect in scene.layout.chapter_rows:
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
        draw_row(
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


def draw_row(
    screen: pygame.Surface,
    scene: Frame,
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
    alarm: bool = False,
) -> None:
    """A drawer's row, as every drawer draws them (D-051): an icon (or the part itself, or a
    level's number), the name, an info disc, then a count, the infinity sign, a key, a tick or a
    lock, right-aligned; nothing for "none". Keys show while the key hints are on (D-054).
    `alarm`: the name and the count in the refusals' colour, for an objective that lost."""
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
    shown = fonts.name.render(name, True, REFUSED if alarm else DIM_TEXT if greyed else TEXT)
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
        cap = fonts.label.render(text, True, GREYED if greyed else DIM_TEXT)
        cap_box = cap.get_rect(midright=(right, box.centery)).inflate(10, 4)
        pygame.draw.rect(screen, RULE, cap_box, 1, border_radius=4)
        screen.blit(cap, cap.get_rect(center=cap_box.center))
    else:
        count = fonts.small.render(text, True, REFUSED if alarm else DIM_TEXT if greyed else TEXT)
        screen.blit(count, count.get_rect(midright=(right, box.centery)))


def draw_tabs(screen: pygame.Surface, scene: Frame, fonts: Fonts) -> None:
    """The tabs over the main screen, the open one lit; under them, inside it, the level's title
    and what it asks, on one baseline, a rule under them (D-056)."""
    layout = scene.layout
    left = layout.board_area[0]
    pygame.draw.rect(screen, BAR, (left, 0, SCREEN[0] - left, TABS_HEIGHT))
    for name, rect in layout.tabs:
        box = pygame.Rect(rect)
        on = name == layout.env.value
        if on:
            pygame.draw.rect(screen, BACKGROUND, box)
            pygame.draw.rect(screen, LIT, (box.left, 0, box.width, 2))
        label = fonts.label.render(TAB_NAME[name], True, TEXT if on else DIM_TEXT)
        screen.blit(label, label.get_rect(center=box.center))
        pygame.draw.line(screen, RULE, (box.right, 6), (box.right, TABS_HEIGHT - 6))
    strip = pygame.Rect(left, TABS_HEIGHT, SCREEN[0] - left, CAPTION_HEIGHT)
    pygame.draw.rect(screen, BACKGROUND, strip)
    pygame.draw.line(screen, RULE, (left, strip.bottom - 1), (SCREEN[0], strip.bottom - 1))
    title, spec = scene.caption
    if title:
        x, y = layout.caption_at
        shown = fonts.name.render(title, True, TEXT)  # as big as the Plex beside it looks
        screen.blit(shown, (x, y))
        base = y + fonts.name.get_ascent() - fonts.small.get_ascent()  # on one baseline
        left = x + shown.get_width() + 10
        spec = _fitted(fonts.small, spec, SCREEN[0] - MARGIN - left)
        screen.blit(fonts.small.render(spec, True, DIM_TEXT), (left, base))


def _fitted(font: pygame.font.Font, text: str, width: int) -> str:
    """`text`, or as many of its words as fit in `width` [px] with an ellipsis after them."""
    if font.size(text)[0] <= width:
        return text
    words = text.split()
    while words and font.size(" ".join(words) + "…")[0] > width:
        words.pop()
    return " ".join(words) + "…"


def draw_title(
    screen, fonts: Fonts, title: str, topleft, height: int = PALETTE_TITLE, lit: bool = False
) -> None:
    """A section's title, as every view writes them: upper case, dimmed, centred in `height`;
    `lit`, in the accent, while a tutorial step explains its panel (D-050)."""
    text = fonts.name.render(title.upper(), True, LIT if lit else DIM_TEXT)
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


def draw_tooltip(screen: pygame.Surface, scene: Frame, fonts: Fonts) -> None:
    """The name of the bar's icon under the mouse, and its key if it has one, beside the bar;
    the other tab's, under it."""
    target = scene.tooltip
    if target is None:
        return
    if isinstance(target, str):  # the other tab: what the switch to it says
        x, y, _, h = dict(scene.layout.tabs)[target]
        button = SWITCH_TO[scene.layout.env]
        key = LEVEL_KEYS[button] if scene.settings.key_hints else None
        text = TIP[button] + (f" ({key})" if key else "")
        draw_tip(screen, fonts, text, topleft=(x + 8, y + h + 8))
        return
    rects = dict(scene.layout.drawer_buttons) | dict(scene.layout.level_buttons)
    _, y, _, h = rects[target]
    key = (LEVEL_KEYS | DRAWER_KEYS).get(target) if scene.settings.key_hints else None
    text = TIP[target] + (f" ({key})" if key else "")
    draw_tip(screen, fonts, text, midleft=(BAR_WIDTH + 10, y + h // 2))


def draw_info(screen: pygame.Surface, scene: Frame, fonts: Fonts, about: Callable) -> None:
    """The open info box, beside the drawer at its row: the name, then what it does. A setting's
    and a place's are told here; `about(scene, what)` tells the environment's own, as a name
    and its lines."""
    if scene.info is None:
        return
    what = scene.info
    places = {row.index: row for row in scene.chapters}
    if isinstance(what, Setting):
        name, _, line = SETTING[what]
        lines = (line,)
    elif isinstance(what, int) and what in places:
        place = places[what]
        name, lines = place.title, (place.spec,)
        if place.best is not None:
            lines += (f"Fastest win: {place.best.ticks * DT:.2f} s, {place.best.parts} parts.",)
    else:
        name, lines = about(scene, what)
    rows = [fonts.name.render(name, True, TEXT)]
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


def _about(scene: EditorScene, what: object) -> tuple[str, tuple[str, ...]]:
    """What the editor's info boxes say: a part's entry, a win, or what a row does."""
    if isinstance(what, Kind):
        return NAME[what], tuple(info(what))
    if isinstance(what, WinRow):
        won = scene.wins[what.index]
        beaten = "No other win beats it." if won.best else "Another win beats it."
        return "A win", (f"This board won in {_win_name(won)}. {beaten}",)
    return ROW_NAME[what], (TIP[what],)


def _draw_status(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    if scene.message:
        text, colour = scene.message, REFUSED
    elif isinstance(scene.ghost, Refused):
        text, colour = scene.ghost.reason, REFUSED
    else:
        text, colour = scene.hint(), DIM_TEXT
    draw_status_line(screen, scene, fonts, text, colour)


def draw_status_line(screen: pygame.Surface, scene: Frame, fonts: Fonts, text: str, colour) -> None:
    """The status line under the main screen: a hint, the keys, or why something was refused."""
    left = scene.layout.board_area[0]
    strip = (left, SCREEN[1] - STATUS_HEIGHT, SCREEN[0] - left, STATUS_HEIGHT)
    pygame.draw.rect(screen, BAR, strip)
    room = SCREEN[0] - scene.layout.status_at[0] - 8
    screen.blit(
        fonts.small.render(_fitted(fonts.small, text, room), True, colour), scene.layout.status_at
    )
