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
import textwrap
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pygame

from nektoids.editor.beads import BEAD_RATE_AT_FULL
from nektoids.editor.circuit import BEAD_RADIUS, METER_AT, METER_HEIGHT, Circuit
from nektoids.editor.devdrive import DT, TICKS_PER_FRAME
from nektoids.editor.entry import ENTRY_AREA
from nektoids.editor.frame import Frame
from nektoids.editor.geometry import (
    EYE_DISC,
    SHAPES,
    body_circle,
    cumulative_lengths,
    point_at,
    symbol_corners,
    wire_arrows,
    wire_points,
)
from nektoids.editor.hints import NAMES
from nektoids.editor.hints import SHADOW as SHADOW_HINT
from nektoids.editor.icons import (
    DRAWER_ICON,
    EDIT_ICON,
    KIND_ICON,
    LEVEL_ICON,
    MODE_ICON,
    PIECE_ICON,
    TOOL_ICON,
    VIEW_ICON,
    Icons,
)
from nektoids.editor.layout import (
    ACTION_WIDTH,
    BAR_WIDTH,
    CAPTION_HEIGHT,
    DIAGNOSTIC_MAP,
    DRAWER_KEYS,
    EDIT_KEYS,
    HINT_LINE,
    INFO_AT,
    LEVEL_KEYS,
    LOCK_KEY,
    MARGIN,
    MAX_HEX,
    MODE_KEY,
    PALETTE_TITLE,
    PASSKEY_KEY,
    SCREEN,
    STATUS_HEIGHT,
    TABS_HEIGHT,
    VIEW_KEYS,
    WHEEL_TITLE,
    Drawer,
    EditButton,
    FileButton,
    GoalButton,
    HintRow,
    LevelButton,
    MainView,
    Mode,
    Piece,
    Setting,
    Tool,
    View,
    ViewButton,
    WinRow,
    fitted_view,
    level_of,
    overview_view,
    scroll_thumb,
    shown_frame,
    tab_key_to,
    visible_cells,
)
from nektoids.editor.marks import AtWork, at_work
from nektoids.editor.marks_draw import SPECK, draw_over, draw_under
from nektoids.editor.palette import (
    ACTIVE,
    BACKGROUND,
    BAR,
    BEAD,
    BODY,
    BODY_OUTLINE,
    BUTTON,
    COMPONENT,
    DARK,
    DIM_TEXT,
    DOOMED,
    EYE_FACE,
    FLAME,
    FLASH,
    FOCUS_CELL,
    FULL,
    GHOST_FILL,
    GHOST_OK,
    GREYED,
    GRID_LINE,
    HOVER,
    ICON_EDGE,
    INTAKE,
    LIGHT,
    LIT,
    LOCK_RING,
    MARK,
    METER,
    OBSTACLE,
    OUTSIDE,
    OUTSIDE_LINE,
    PANEL,
    REFUSED,
    RULE,
    SCROLL_THUMB,
    SHADOW,
    TEXT,
    THRUSTER_BACK,
    TOOLTIP_BG,
    WIRE,
    WIRING,
    WIRING_OK,
    ZONE,
)
from nektoids.editor.parts import NAME, info, ports
from nektoids.editor.probe import level_view
from nektoids.editor.router import level_label
from nektoids.editor.scene import EditorScene
from nektoids.editor.wheel import ICON, LINE_BELOW, WHEEL_HEX
from nektoids.graph.board import Board, Kind, Refused
from nektoids.graph.dynamics import RATE_MAX
from nektoids.graph.hexgrid import Cell, to_pixel
from nektoids.graph.network import label
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
    ViewButton.MOTION: "Show or hide the swimmer's velocity and spin",
    ViewButton.STREAMS: "Show or hide the swimmer's flames and the light its eyes draw in",
    EditButton.UNDO: "Undo",
    EditButton.REDO: "Redo",
    Mode.WRITE: "Click a cell: Tools and Parts show its Wheel. Click two parts to wire them, or"
    " drag one to move it.",
    Mode.DELETE: "A click removes the part under it, with its wires, or the wire under it.",
    Mode.LOCK: "A click on a part makes it the level's: the player can neither move nor take it"
    " off, and it uses no stock. A click on one of the level's parts frees it.",
    FileButton.SAVE: "Copies the board as a line of text, to paste anywhere and keep. Paste it"
    " into Paste a board, under this row, to bring it back, on this level or another.",
    FileButton.LEVEL: "Copies the level as text, its JSON, as the game's own level files hold it:"
    " to keep, or to paste into Paste a level, under this row, to make it again.",
    FileButton.SHARE: "Copies the level as text with its proof, the board that won it and its"
    " score, the one to beat. Offered once the level, as it stands, has been won in the Run;"
    " pasted, the proof is run again, and the level is cleared if it wins.",
    LevelButton.RUN: "Run",
    LevelButton.EDIT: "Back to the editor",
    Drawer.TOOLS: "Tools",
    Drawer.PARTS: "Parts",
    Drawer.FILES: "Files",
    Drawer.DIAGNOSTIC: "Diagnostic",
    Drawer.INSIDE: "Diagnostic",  # the run's, as the editor's (D-089)
    Drawer.SCORE: "Score",
    Drawer.NAVIGATOR: "Navigator",
    Drawer.HINTS: "Hints",
    Drawer.SETTINGS: "Settings",
    Drawer.CHAPTERS: "Chapters",
    Drawer.OBJECTS: "Objects",
    Drawer.TEXT: "Text",  # once Brief (D-318)
    Drawer.GOALS: "Goals",
    GoalButton.ADD: "One goal more, two at most: reach every light, on most levels. Its words"
    " change under its name, and the bin at its right takes it out.",
}
SETTING = {  # Settings' rows: their name, icon and what their info box says (D-054)
    Setting.FAST: ("Fast forward", "forward", "How fast the run goes when fast forward is on."),
    Setting.HINTS: ("Key hints", "keyboard", "Keys on each row and in the bar's tooltips."),
    Setting.TUTORIAL: (
        "Tutorial",
        "graduation-cap",
        "Fear's tutorial again, from its first step.",
    ),
    Setting.SOUND: ("Sound", "volume-high", "There is no sound yet."),
    Setting.MUSIC: ("Music", "music", "There is no music yet."),
}
HINT = (  # Hints' rows, in NAMES' order: their icon, a speech bubble, and what their info box
    ("comment", "An idea to start from, a bit cryptic."),  # says (D-078, D-088)
    ("comment", "The parts one way to win takes."),
    ("comment", "One way to win, faint: here and on the board."),
)
BUILD_IT = ("Go to", Drawer.TOOLS, "Tools or", Drawer.PARTS, "Parts")  # under the shadow (D-088)
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
    Mode.LOCK: "Lock",
    FileButton.SAVE: "Copy a board",
    FileButton.LEVEL: "Copy level",
    FileButton.SHARE: "Share level",
    GoalButton.ADD: "Add a goal",
    ViewButton.ZOOM_IN: "Zoom in",
    ViewButton.ZOOM_OUT: "Zoom out",
    ViewButton.PAN: "Hand",
    ViewButton.CENTRE: "Centre",
    ViewButton.RAYS: "Rays",
    ViewButton.MOTION: "Motion",
    ViewButton.STREAMS: "Streams",
}
TAB_NAME = {"editor": "Editor", "run": "Run", "maker": "Maker"}
TAB_TIP = {"run": "Run", "editor": "Back to the editor", "maker": "Make the level"}  # D-301

# How parts sit in the menu: eyes looking up (flat side up), thrusters pointing up
# [degrees, counter-clockwise from E]. On the grid they point along their facing.
MENU_ANGLE = {kind: 90.0 for kind in Kind if kind.default_facing is not None}

WIRE_WIDTH = 3  # every wire on the board, made, shadow or being drawn, whatever the zoom [px]
ARROW_HALF = 0.14  # half-length of every arrowhead on a wire [hex sizes]
FACE = {Kind.EYE: EYE_FACE, Kind.THRUSTER: THRUSTER_BACK}  # the side that reads, that pushes
FACE_WIDTH = 0.1  # [hex sizes]
INFO_ICON = 16  # a menu row's info disc [px]
INFO_CHARS = 46  # an info box's line, at most: as wide as a part's circuit under it (D-094)
INFO_PAD = 12  # inside the info box [px]

# Icon height as a fraction of the hex size.
ICON_SCALE = {Kind.EYE: 0.68, Kind.THRUSTER: 0.62}  # the rest: 0.5

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
    if scene.layout.action_at is not None and scene.main is MainView.DIAGRAM:  # D-068, D-069
        _draw_action(screen, scene, fonts)
    draw_tabs(screen, scene, fonts)
    _draw_status(screen, scene, fonts)
    draw_bar(screen, scene, fonts)
    draw_drawer(screen, scene, fonts, _draw_rows, _draw_foot)
    draw_tooltip(screen, scene, fonts)
    _draw_wheel_tip(screen, scene, fonts)
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
        elif cell == scene.focused:  # the Wheel's cell, the keyboard's (D-068)
            pygame.draw.polygon(screen, ACTIVE, hexagon)
        elif cell in scene.guide_cells:  # a cell a tutorial's step acts on (D-063)
            pygame.draw.polygon(screen, FOCUS_CELL, hexagon)
        else:
            pygame.draw.polygon(screen, HOVER if cell == scene.hover else ZONE, hexagon)
        pygame.draw.polygon(screen, GRID_LINE if cell in zone else OUTSIDE_LINE, hexagon, 1)
    if board.cells:
        draw_body(screen, board.cells, view.size, view.origin)

    wired = {(board.nodes[w.source].cell, board.nodes[w.target].cell) for w in board.wires}
    for start, end in scene.ghost_wires:  # the model's wires, faint, until each is made (D-074)
        path = None if (start, end) in wired else board.route(start, end)
        if path is not None:
            target = board.node_at(end) or next((g for g in scene.ghosts if g.cell == end), None)
            reach = extent(target.kind) if target is not None else 0.3
            _draw_wire(screen, view, path, GHOST_FILL, reach)
    doomed_node, doomed_wires = scene.doomed()  # what a Delete click would take, darkened
    for wire in board.wires:
        colour = DOOMED if wire in doomed_wires else WIRE
        _draw_wire(screen, view, wire.path, colour, extent(board.nodes[wire.target].kind))
    way = scene.ghost if isinstance(scene.ghost, tuple) else scene.ghost_way  # D-069
    if way is not None:  # last, over a shadow on the same route (D-087)
        colour = WIRING_OK if scene.ghost_connects else WIRING
        target = board.node_at(way[-1])
        reach = extent(target.kind) if target is not None else 0.3
        _draw_wire(screen, view, way, colour, reach)

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
    opens Tools. Beside it, in the accent, its name and its key (D-069)."""
    box = pygame.Rect(scene.layout.action_at)
    what, key = scene.action()
    draw_disc(screen, fonts, box.center, what, ACTIVE, LIT, ACTION_WIDTH / 2)  # as the Wheel's
    shown = fonts.text.render(_named(scene, what, key), True, LIT)
    at = shown.get_rect(midleft=(box.right + 10, box.centery))
    pygame.draw.rect(screen, BAR, at.inflate(14, 6), border_radius=5)  # legible over the grid
    screen.blit(shown, at)
    says = fonts.small.render(_action_says(scene, what), True, TEXT)
    at = says.get_rect(midtop=(box.centerx, box.bottom + 8))  # its patch clear of the disc
    pygame.draw.rect(screen, BAR, at.inflate(14, 6), border_radius=5)  # legible over the grid
    screen.blit(says, at)


ACTION_SAYS = {  # under the action atop the main screen: what it is (D-068)
    Mode.WRITE: "Write: a click on a cell shows what can be done there",
    Mode.DELETE: "Delete: a click removes the part or the wire under it",
    Mode.LOCK: "Lock: a click makes the part the level's, or frees it",
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


def draw_disc(
    screen, fonts: Fonts, at, what: Kind | Tool | Mode | Piece | None, fill, edge, radius: float
) -> None:
    """One of the Wheel's icons, or the action atop the main screen, alike (D-068): a disc of
    `radius` [px], the part on it just smaller than the Wheel's cell's, or the action's glyph,
    or the Maker's object's (D-301); empty for None."""
    pygame.draw.circle(screen, fill, at, radius)
    pygame.draw.circle(screen, edge, at, radius, 2)
    if isinstance(what, Kind):  # its tips well inside the disc, a diamond's too
        draw_part(screen, fonts, what, MENU_ANGLE.get(what), at, 1.15 * radius, False)
    elif what is not None:
        fonts.icons.draw(screen, _action_icon(what), at, round(1.05 * radius), TEXT)


def _action_icon(what: Tool | Mode | Piece) -> str:
    if isinstance(what, Mode):
        return MODE_ICON[what]
    if isinstance(what, Piece):
        return PIECE_ICON[what]
    return VIEW_ICON[ViewButton.PAN] if what is Tool.PAN else TOOL_ICON[what]


def _draw_wheel(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """At the foot of Tools and of Parts (D-068, D-069): a rule, The Wheel's title, which folds;
    unless folded, the Wheel: the focused cell, large, as the board has it, its icons round it, a
    line under it saying what the cell holds."""
    layout = scene.layout
    fx, fy, fw, fh = layout.wheel_fold
    pygame.draw.line(screen, RULE, (fx, fy - 3), (fx + fw, fy - 3), 2)  # the bar that divides
    draw_fold_title(screen, fonts, WHEEL_TITLE, layout.wheel_fold, scene.wheel_folded, DIM_TEXT)
    if layout.wheel_view is None:
        return
    x, y, w, h = layout.wheel_view
    centre = scene.cell_centre()
    corners = _small_hexagon(centre, WHEEL_HEX)
    focused = scene.focused is not None
    if focused:
        pygame.draw.polygon(screen, ACTIVE, corners)
        pygame.draw.polygon(screen, LIT, corners, 2)
        node = scene.board.node_at(scene.focused)
        if node is not None:
            fill = DOOMED if node.id == scene.doomed()[0] else None
            angle = placed_angle(node.kind, node.facing)
            draw_part(screen, fonts, node.kind, angle, centre, WHEEL_HEX, node.locked, fill)
    else:
        pygame.draw.polygon(screen, RULE, corners, 1)
    wheel = scene.wheel()
    k = scene.choice if scene.going_round() and scene.choice is not None else len(wheel)
    chosen = wheel[k] if k < len(wheel) else None
    in_hand = scene.tool if scene.tool in (Tool.WIRE, Tool.MOVE) else None
    radius = ICON * WHEEL_HEX
    for slot in sorted(wheel, key=lambda s: -s.depth):  # down a pile, the further first, under
        if slot.depth:  # piled: an empty disc, its edge showing past the one over it
            turning = (slot.at[0] > centre[0]) == (scene.piling > 0) and scene.piling != 0
            edge = LIT if turning else ICON_EDGE
            draw_disc(screen, fonts, slot.at, None, BUTTON, edge, radius)
            continue
        lit = slot == chosen or slot.what is in_hand
        fill = ACTIVE if lit else HOVER if slot == scene.wheel_hover else BUTTON
        draw_disc(screen, fonts, slot.at, slot.what, fill, LIT if lit else ICON_EDGE, radius)
    lowest = max([centre[1] + WHEEL_HEX] + [slot.at[1] + radius for slot in wheel])
    lit = scene.wheel_lit()  # the icon chosen or in hand, named in the accent (D-069)
    says, ink = (_named(scene, lit.what, lit.key), LIT) if lit else (_cell_says(scene), DIM_TEXT)
    line = fonts.small.render(_fitted(fonts.small, says, w), True, ink)
    screen.blit(line, line.get_rect(midtop=(round(centre[0]), round(lowest) + LINE_BELOW)))


def _draw_tools(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """Tools' rows (D-068): Write and Delete, undo and redo."""
    layout = scene.layout
    for mode, rect in layout.mode_buttons:
        status = ("key", LOCK_KEY if mode is Mode.LOCK else MODE_KEY)
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


def _named(scene: EditorScene, what: Kind | Tool | Mode, key: str) -> str:
    """An action, a Wheel's icon, named as the bar's tooltips name a drawer: its name, then its
    key while the key hints are on (D-069)."""
    if isinstance(what, Kind):
        name = NAME[what]
    else:
        name = ROW_NAME[ViewButton.PAN] if what is Tool.PAN else ROW_NAME[what]
    return f"{name} ({key})" if scene.settings.key_hints else name


def _draw_wheel_tip(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """The Wheel's icon under the mouse, named in a tooltip as the bar's are, after the same
    rest (D-069), centred over the icon, kept clear of the bar."""
    slot = scene.wheel_tip()
    if slot is None:
        return
    text = _named(scene, slot.what, slot.key)
    half = fonts.text.size(text)[0] // 2 + 8  # the box's half width
    x = max(round(slot.at[0]), BAR_WIDTH + 4 + half)
    draw_tip(screen, fonts, text, midbottom=(x, round(slot.at[1] - ICON * WHEEL_HEX - 10)))


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


def _draw_wire(screen, view: View, path: tuple[Cell, ...], colour, reach: float = 0.3) -> None:
    """One width for every wire (D-087); one arrow in each free cell crossed; between neighbours,
    which have none, one just outside the target's shape instead. reach: how far that shape
    extends [hex sizes]."""
    points = wire_points(path, view.size, view.origin)  # arcs where it turns
    pygame.draw.lines(screen, colour, False, points, WIRE_WIDTH)
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
    return SHAPES[kind.spec.shape]


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
        ink = TEXT if on else DIM_TEXT  # a tutorial's target too: its sparks say it (D-095)
        fonts.icons.draw(screen, DRAWER_ICON[drawer], box.center, 22, ink)
    for button, rect in layout.level_buttons:  # the switch
        box = pygame.Rect(rect)
        pygame.draw.rect(screen, ACTIVE, box, border_radius=8)
        fonts.icons.draw(screen, LEVEL_ICON[button], box.center, 18, TEXT)


@contextmanager
def clipped(screen: pygame.Surface, rect) -> Iterator[None]:
    """Drawing kept inside `rect` and inside the clip already set, which is set again after;
    None keeps the clip as it is. A drawer's rows, clipped to where they scroll, may hold a
    picture clipped to its own frame (D-096)."""
    before = screen.get_clip()
    if rect is not None:
        screen.set_clip(before.clip(pygame.Rect(rect)))
    try:
        yield
    finally:
        screen.set_clip(before)


def draw_drawer(
    screen: pygame.Surface, scene: Frame, fonts: Fonts, rows: Callable, foot: Callable
) -> None:
    """The open drawer: its title, its sections or groups and its rows, which scroll within
    their area if they do not fit, with a scroll bar then (D-096); what stays at its foot; the
    arrow that folds it. `rows(screen, scene, fonts)` draws the environment's own rows, and
    `foot(screen, scene, fonts)` its foot, the Wheel or the objectives; Hints', Settings' and
    Chapters' rows are drawn here."""
    layout = scene.layout
    if layout.drawer is None:
        return
    area = pygame.Rect(layout.drawer_area)
    pygame.draw.rect(screen, PANEL, area)
    pygame.draw.line(screen, RULE, (area.right - 1, 0), (area.right - 1, area.bottom), 2)
    lit = layout.drawer.value in scene.lit  # a tutorial step explains it (D-050)
    ink = LIT if lit else DIM_TEXT
    draw_title(screen, fonts, TIP[layout.drawer], layout.drawer_title_at, lit=lit)
    with clipped(screen, layout.list_area):  # None: the rows fit, or there are none
        _draw_sections(screen, scene, fonts, ink, at_foot=False)
        for title, rect in layout.group_titles:
            draw_fold_title(screen, fonts, title, rect, title in scene.folded, ink)
        rows(screen, scene, fonts)
        _draw_hints(screen, scene, fonts)
        _draw_settings(screen, scene, fonts)
        _draw_chapters(screen, scene, fonts)
        _draw_passkey(screen, scene, fonts)
    _draw_sections(screen, scene, fonts, ink, at_foot=True)
    foot(screen, scene, fonts)
    if layout.scroll_bar is not None:  # while the rows do not fit
        pygame.draw.rect(screen, RULE, layout.scroll_bar, border_radius=2)
        pygame.draw.rect(screen, SCROLL_THUMB, scroll_thumb(layout), border_radius=2)
    handle = pygame.Rect(layout.fold_handle)
    corners = {"border_top_right_radius": 6, "border_bottom_right_radius": 6}
    pygame.draw.rect(screen, PANEL, handle, **corners)
    pygame.draw.rect(screen, RULE, handle, 1, **corners)
    fonts.icons.draw(screen, "chevron-left", handle.center, 11, DIM_TEXT)


def _draw_sections(screen: pygame.Surface, scene: Frame, fonts: Fonts, ink, at_foot: bool) -> None:
    """The drawer's section titles, lit with it or by their name: those over its rows, or with
    `at_foot` those at its foot, over the run's objectives, which never scroll (D-065)."""
    goals = scene.layout.goal_area
    for title, rect in scene.layout.section_titles:
        if (goals is not None and pygame.Rect(goals).collidepoint(rect[:2])) is not at_foot:
            continue
        x, y, _, h = rect
        shown = fonts.label.render(title.upper(), True, LIT if title.lower() in scene.lit else ink)
        screen.blit(shown, (x, y + (h - shown.get_height()) // 2))


def draw_fold_title(screen, fonts: Fonts, title: str, rect, folded: bool, ink) -> None:
    """A title that folds what is under it, as Parts' groups and The Wheel (D-069): a caret, right
    while folded, down while open, then the title in upper case."""
    x, y, _, h = rect
    caret = "caret-right" if folded else "caret-down"
    fonts.icons.draw(screen, caret, (x + 5, y + h // 2), 14, ink)
    shown = fonts.label.render(title.upper(), True, ink)
    screen.blit(shown, (x + 16, y + (h - shown.get_height()) // 2))


def _draw_files(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """Files (D-059, D-092): this session's wins, each level's under its title, which folds; the
    best first, a tick on those no other beats, the one on the board now lit; a click puts its
    board on this level's, if it fits. The list scrolls within its area, as Parts'."""
    now = scene.board.snapshot()
    for row, rect in scene.layout.win_rows:
        won = scene.wins[row.group].wins[row.index]
        status = ("tick", "") if won.best else ("none", "")
        active = (won.board.nodes, won.board.wires) == (now.nodes, now.wires)  # not the stock
        draw_row(screen, scene, fonts, rect, row, _win_name(won), status, active, icon="trophy")
    if not scene.wins:
        note = "No win yet. Each win of each level will be kept here for the session."
        draw_note(screen, fonts, note, DIAGNOSTIC_MAP[:2], DIAGNOSTIC_MAP[2])


def _win_name(won) -> str:
    return f"{won.score.ticks * DT:.2f} s, {won.score.parts} parts"


def draw_level_map(
    screen: pygame.Surface,
    level,
    area: pygame.Rect,
    pose: tuple[float, float, float],
    frame: pygame.Rect | None = None,
    view=None,
    body: AtWork | None = None,
) -> None:
    """The level seen whole and small in `area`: its obstacles, its marks, its lights, and
    the swimmer at `pose` (x, y [u], heading [rad]); `frame`, what the main screen shows of it,
    outlined (Diagnostic's map, the run's overview, D-058, D-060); `view`, how it is seen, else the
    level seen whole; `body`, the swimmer at work, drawn round it (Diagnostic's map, D-076)."""
    view, arena = view or level_view(level, tuple(area)), level.arena
    pygame.draw.rect(screen, SHADOW, area, border_radius=6)
    with clipped(screen, area):
        for disc in arena.obstacles:
            pygame.draw.circle(
                screen, OBSTACLE, view.to_screen(disc.x, disc.y), disc.radius * view.scale
            )
        for mark in level.marks:  # D-306
            centre = view.to_screen(*mark.at)
            pygame.draw.circle(screen, MARK, centre, max(2.0, mark.value * view.scale), 1)
        for light in arena.lights:
            pygame.draw.circle(
                screen, LIGHT, view.to_screen(light.x, light.y), LIGHT_RADIUS * view.scale
            )
        x, y, heading = pose
        if body is not None:
            draw_under(screen, view, body)
        draw_symbol(screen, BODY, view.to_screen(x, y), BASE_RADIUS * view.scale, heading, 2)
        if body is not None:
            draw_over(screen, view, body)
        if frame is not None:
            pygame.draw.rect(screen, LIT, frame, 1)
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
    draw_track(screen, scene.layout.zoom_bar, level)


def draw_track(screen: pygame.Surface, rect, level: float, held: bool = False) -> None:
    """A bar across the middle of `rect`, filled to `level`, 0 at its left end, 1 at its right,
    a knob where it stands, lit while `held`: Navigator's zoom, the Maker's sliders (D-308)."""
    x, y, w, h = rect
    track = pygame.Rect(x, y + h // 2 - 3, w, 6)
    pygame.draw.rect(screen, RULE, track, border_radius=3)
    filled = track.copy()
    filled.width = round(w * level)
    if filled.width > 0:
        pygame.draw.rect(screen, FULL, filled, border_radius=3)
    knob = (x + round(w * level), track.centery)
    pygame.draw.circle(screen, LIT if held else FULL, knob, 6)
    pygame.draw.circle(screen, DARK, knob, 6, 1)


def _draw_overview(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """Navigator's overview (D-060): the whole board small, its parts as dots, and a frame round
    what the main screen shows; a press or a drag there moves the view."""
    area = pygame.Rect(scene.layout.overview)
    pygame.draw.rect(screen, SHADOW, area, border_radius=6)
    small = overview_view(scene.layout, sorted(scene.board.cells))
    with clipped(screen, area):
        for cell in scene.board.cells:
            pygame.draw.polygon(screen, ZONE, _hexagon(small, cell))
        for node in scene.board.nodes.values():
            pygame.draw.circle(screen, COMPONENT, _centre(small, node.cell), 0.45 * small.size)
        pygame.draw.rect(screen, LIT, shown_frame(scene.layout, scene.view, small), 1)
    pygame.draw.rect(screen, RULE, area, 1, border_radius=6)


def _draw_diagnostic(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """Diagnostic (D-058, D-069): the level small, its obstacles, its marks, its lights,
    and the probe, the swimmer the Run preview runs at, to drag and turn, at work (D-076)."""
    area = pygame.Rect(DIAGNOSTIC_MAP)
    probe = scene.probe
    if scene.level is not None and probe is not None:
        frame = probe.ticks // TICKS_PER_FRAME
        cells = probe.circuit.board.cells
        body = at_work(scene.level.arena, probe.net, cells, probe.y, probe.pose, BASE_RADIUS, frame)
        draw_level_map(screen, scene.level, area, probe.pose, body=body)
    else:
        pygame.draw.rect(screen, SHADOW, area, border_radius=6)
        pygame.draw.rect(screen, RULE, area, 1, border_radius=6)
    note = (
        "Drag the swimmer anywhere; the mouse wheel, or L and R, turn it. The main screen runs your"
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


def _draw_foot(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """What stays at the foot of the editor's drawers: the Wheel, in Tools and Parts; the board
    as text, in Files."""
    if scene.layout.wheel_fold is not None:
        _draw_wheel(screen, scene, fonts)
    if scene.layout.board_field is not None:
        _draw_board_text(screen, scene, fonts)


def _draw_board_text(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """Files' foot (D-206): Save/Load, Copy a board, then the field to paste one: what is
    pasted or typed, its end showing, with a caret, lit while it is open; else what to do."""
    layout = scene.layout
    _, top, _, room = layout.list_area
    for title, rect in layout.section_titles:
        if rect[1] >= top + room:  # under the wins' list, which is clipped: the foot's title
            x, y, _, h = rect
            shown = fonts.label.render(title.upper(), True, DIM_TEXT)
            screen.blit(shown, (x, y + (h - shown.get_height()) // 2))
    for button, rect in layout.file_buttons:
        draw_row(screen, scene, fonts, rect, button, ROW_NAME[button], ("none", ""), icon="copy")
    loading = scene.loading
    text, caret = (loading.text, loading.caret) if loading is not None else ("", None)
    draw_field(screen, fonts, layout.board_field, text, caret, "paste", "Paste a board")


def _draw_rows(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """The editor's own drawers' rows: Tools, Parts, Files, Navigator; Diagnostic's map."""
    layout, board = scene.layout, scene.board
    if layout.drawer is Drawer.TOOLS:
        _draw_tools(screen, scene, fonts)
    if layout.drawer is Drawer.DIAGNOSTIC:
        _draw_diagnostic(screen, scene, fonts)
    if layout.drawer is Drawer.FILES:
        _draw_files(screen, scene, fonts)
    if layout.overview is not None:
        _draw_overview(screen, scene, fonts)
        draw_zoom(screen, scene, fonts, level_of(scene.view.size, scene.least_zoom(), MAX_HEX))
    for kind, rect in layout.menu_items:
        left = board.remaining(kind)
        status = ("infinity", "") if left is None else ("count", f"{left}/{board.total(kind)}")
        picked = kind == scene.picked
        draw_row(screen, scene, fonts, rect, kind, NAME[kind], status, picked, left == 0, part=kind)
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


def _draw_hints(screen: pygame.Surface, scene: Frame, fonts: Fonts) -> None:
    """Hints (D-078): a row locked until the one before it is taken, ticked once taken, the
    shadow's on or off; under each taken one, its lines; under the shadow's, its picture. A
    level with none, or whose tutorial leads, says so."""
    layout, hints = scene.layout, scene.hints
    if layout.drawer is not Drawer.HINTS:
        return
    taken = len(hints.lines) if hints is not None else 0
    for row, rect in layout.hint_rows:
        k = row.index
        if k == SHADOW_HINT and k < taken:
            status = ("tick", "on") if hints.shadow else ("count", "off")
        elif k < taken:
            status = ("tick", "")
        else:
            status = ("none", "") if k == taken and not hints.locked else ("lock", "")
        greyed = status[0] == "lock"
        draw_row(screen, scene, fonts, rect, row, NAMES[k], status, False, greyed, HINT[k][0])
    for k, (x, y, _, _) in layout.hint_texts:
        for n, line in enumerate(hints.lines[k]):
            screen.blit(fonts.small.render(line, True, TEXT), (x, y + n * HINT_LINE))
    if layout.shadow_picture is not None and hints.board is not None:
        _draw_shadow(screen, hints.board, layout.shadow_picture)
        _draw_with_icons(screen, fonts, BUILD_IT, layout.shadow_line)
    note = None
    if hints is None:  # the sandbox, and the levels after the first five (D-098)
        note = "No hints here."
    elif hints.locked:
        note = "Skip or finish the tutorial for hints."
    if note is not None:
        rows = layout.hint_rows
        top = rows[-1][1][1] + rows[-1][1][3] + 12 if rows else DIAGNOSTIC_MAP[1]
        draw_note(screen, fonts, note, (DIAGNOSTIC_MAP[0], top), DIAGNOSTIC_MAP[2])


def _draw_with_icons(
    screen: pygame.Surface, fonts: Fonts, parts: tuple[str | Drawer, ...], rect
) -> None:
    """A line of words and drawers' icons, as the bar draws them, centred in `rect`."""
    gap, size = 6, 14  # between the parts; an icon's height [px]
    words = [fonts.small.render(p, True, TEXT) if isinstance(p, str) else None for p in parts]
    width = sum(w.get_width() if w else size for w in words) + gap * (len(parts) - 1)
    x, y, w, h = rect
    left, middle = x + (w - width) / 2, y + h / 2
    for part, word in zip(parts, words, strict=True):
        if word is None:
            fonts.icons.draw(
                screen, DRAWER_ICON[part], (round(left + size / 2), round(middle)), size, TEXT
            )
            left += size + gap
        else:
            screen.blit(word, word.get_rect(midleft=(round(left), round(middle))))
            left += word.get_width() + gap


def _draw_shadow(screen: pygame.Surface, board: Board, rect) -> None:
    """The shadow's picture (D-078): the level's board, small, the shadow on it as the editor's
    board draws one, its parts and wires faint."""
    area = pygame.Rect(rect)
    pygame.draw.rect(screen, SHADOW, area, border_radius=6)
    view = fitted_view(rect, [to_pixel(cell, 1.0, (0.0, 0.0)) for cell in board.cells], 1.2)
    for cell in board.cells:
        hexagon = _hexagon(view, cell)
        pygame.draw.polygon(screen, ZONE, hexagon)
        pygame.draw.polygon(screen, GRID_LINE, hexagon, 1)
    draw_body(screen, board.cells, view.size, view.origin)
    for wire in board.wires:
        reach = extent(board.nodes[wire.target].kind)
        _draw_wire(screen, view, wire.path, GHOST_FILL, reach)
    for node in board.nodes.values():
        angle = placed_angle(node.kind, node.facing)
        shape = _shape(node.kind, angle, _centre(view, node.cell), view.size)
        pygame.draw.polygon(screen, GHOST_FILL, shape)
    pygame.draw.rect(screen, RULE, area, 1, border_radius=6)


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


def _draw_passkey(screen: pygame.Surface, scene: Frame, fonts: Fonts) -> None:
    """Chapters' passkey field (D-075): a key, then what is typed with a caret, lit while it
    is typed; else what to do, its key hinted."""
    if scene.layout.passkey_field is None:
        return
    typing = scene.typing
    hint = f"Type a word ({PASSKEY_KEY})" if scene.settings.key_hints else "Type a word"
    caret = None if typing is None else len(typing)
    draw_field(screen, fonts, scene.layout.passkey_field, typing or "", caret, "key", hint)


def draw_field(
    screen: pygame.Surface,
    fonts: Fonts,
    rect,
    text: str,
    caret: int | None,
    icon: str | None = None,
    hint: str = "",
) -> None:
    """A field of text (D-075, D-206, D-305): a box, outlined in the accent while typed in, its
    icon if it has one; the text, slid left as far as the caret needs to show, the caret a bar
    where it is while typed in; with no text and not typed in, `hint`, dimmed."""
    box = pygame.Rect(rect)
    pygame.draw.rect(screen, BUTTON, box, border_radius=6)
    if caret is not None:
        pygame.draw.rect(screen, LIT, box, 2, border_radius=6)
    ink = TEXT if caret is not None or text else DIM_TEXT
    left = box.left + (42 if icon else 12)
    if icon:
        fonts.icons.draw(screen, icon, (box.left + 20, box.centery), 16, ink)
    font, room = fonts.text, box.right - 10 - left
    if not text and caret is None:
        shown = font.render(_fitted(font, hint, room), True, DIM_TEXT)
        screen.blit(shown, (left, box.centery - shown.get_height() // 2))
        return
    start = 0
    while caret is not None and start < caret and font.size(text[start:caret])[0] > room:
        start += 1  # the caret always shows: the text slides left
    end = len(text)
    while end > start and font.size(text[start:end])[0] > room:
        end -= 1
    shown = font.render(text[start:end], True, ink)
    screen.blit(shown, (left, box.centery - shown.get_height() // 2))
    if caret is not None:
        x = left + font.size(text[start:caret])[0]
        pygame.draw.line(screen, LIT, (x, box.centery - 9), (x, box.centery + 9), 2)


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
        ink = LIT if f"tab:{name}" in scene.lit else TEXT if on else DIM_TEXT  # D-080
        label = fonts.label.render(TAB_NAME[name], True, ink)
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
    another tab's, under it, with its key: Tab or Shift+Tab (D-304)."""
    target = scene.tooltip
    if target is None:
        return
    if isinstance(target, str):  # another tab
        x, y, _, h = dict(scene.layout.tabs)[target]
        key = tab_key_to(scene.layout, target) if scene.settings.key_hints else None
        text = TAB_TIP[target] + (f" ({key})" if key else "")
        draw_tip(screen, fonts, text, topleft=(x + 8, y + h + 8))
        return
    rects = dict(scene.layout.drawer_buttons) | dict(scene.layout.level_buttons)
    if target not in rects:  # the scene's own: the Wheel's icons draw theirs (D-069)
        return
    _, y, _, h = rects[target]
    key = (LEVEL_KEYS | DRAWER_KEYS).get(target) if scene.settings.key_hints else None
    text = TIP[target] + (f" ({key})" if key else "")
    draw_tip(screen, fonts, text, midleft=(BAR_WIDTH + 10, y + h // 2))


def draw_info(screen: pygame.Surface, scene: Frame, fonts: Fonts, about: Callable) -> None:
    """The open info box, beside the drawer at its row: the name, then what it does; a part's
    entry, then the part at work in its own circuit (D-082). A setting's and a place's are told
    here; `about(scene, what)` tells the environment's own, as a name and its lines."""
    if scene.info is None:
        return
    what = scene.info
    places = {row.index: row for row in scene.chapters}
    if isinstance(what, Setting):
        name, _, line = SETTING[what]
        lines = (line,)
    elif isinstance(what, HintRow):
        name, lines = NAMES[what.index], (HINT[what.index][1],)
    elif isinstance(what, int) and what in places:
        place = places[what]
        name, lines = place.title, (place.spec,)
        if place.best is not None:
            lines += (f"Fastest win: {place.best.ticks * DT:.2f} s, {place.best.parts} parts.",)
        if place.passkey:  # won: its word, to copy down (D-075)
            lines += (f"Passkey: {place.passkey}, opens {level_label(place.index + 1)}.",)
    else:
        name, lines = about(scene, what)
    rows = [fonts.name.render(name, True, TEXT)]
    dim = ports(what) if isinstance(what, Kind) else ()  # a part's In and Out, in grey
    for text in lines:  # each a paragraph, wrapped to the box, ragged right (D-094)
        ink = DIM_TEXT if text in dim else TEXT
        rows += [fonts.small.render(line, True, ink) for line in textwrap.wrap(text, INFO_CHARS)]
    entry = scene.entry if scene.entry is not None and scene.entry.kind is what else None
    _, _, circuit_w, circuit_h = ENTRY_AREA
    widths = [row.get_width() for row in rows] + ([] if entry is None else [circuit_w])
    width = max(widths) + 2 * INFO_PAD
    height = sum(row.get_height() + 4 for row in rows) + 2 * INFO_PAD
    height += 0 if entry is None else circuit_h + INFO_PAD
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
    if entry is not None:  # under the lines, across the box: the light, the flames, the circuit
        place = pygame.Rect(box.centerx - circuit_w // 2, y + INFO_PAD - 4, circuit_w, circuit_h)
        pygame.draw.rect(screen, PANEL, place, border_radius=6)
        inside = screen.subsurface(place)
        for specks, colour in ((entry.light(), INTAKE), (entry.flames(), FLAME)):
            for sx, sy in specks:  # on the grid of the run's specks (D-076)
                inside.fill(colour, (sx // SPECK * SPECK, sy // SPECK * SPECK, SPECK, SPECK))
        draw_circuit(inside, entry.circuit, entry.y, fonts, plain=True, meters=False)


def _about(scene: EditorScene, what: object) -> tuple[str, tuple[str, ...]]:
    """What the editor's info boxes say: a part's entry, a win, or what a row does."""
    if isinstance(what, Kind):
        return NAME[what], tuple(info(what))
    if isinstance(what, WinRow):
        group = scene.wins[what.group]
        won = group.wins[what.index]
        beaten = "No other win beats it." if won.best else "Another win beats it."
        title = group.title.split(" ", 1)[1]
        return "A win", (
            f"This board won {title} in {_win_name(won)}. {beaten}",
            "A click puts it on the board, if the level hands out its parts.",
            "Undo brings yours back.",
        )
    return ROW_NAME[what], (TIP[what],)


def _draw_status(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    if scene.message:
        text, colour = scene.message, REFUSED
    elif scene.said:  # a passkey that opened a level (D-075)
        text, colour = scene.said, LIT
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


# The circuit, as Inside, Diagnostic, the developer view (F2) and a part's entry draw it

METER_WIDTH = 10  # a part's level meter [px]
_TEXT_CACHE: dict[tuple[int, str, tuple[int, int, int]], pygame.Surface] = {}
_TEXT_CACHE_LIMIT = 2000


def cached_text(font: pygame.font.Font, text: str, colour: tuple[int, int, int]) -> pygame.Surface:
    """Rendered text, kept: the panel shows the same lines frame after frame."""
    key = (id(font), text, colour)
    if key not in _TEXT_CACHE:
        if len(_TEXT_CACHE) >= _TEXT_CACHE_LIMIT:
            _TEXT_CACHE.clear()
        _TEXT_CACHE[key] = font.render(text, True, colour)
    return _TEXT_CACHE[key]


def draw_circuit(
    screen: pygame.Surface,
    circuit: Circuit,
    y: np.ndarray,
    fonts: Fonts,
    belt: bool = False,
    plain: bool = False,
    meters: bool = True,
) -> None:
    """Wires, beads and parts at the rates y (n,): the beads, and a level meter by each eye and
    thruster unless not `meters`, show the rates; the parts keep their colour (D-052). Unless
    `plain`, every part has its name and its rate as a number, and every thruster a bar."""
    _draw_wires(screen, circuit, belt)
    _draw_parts(screen, circuit, y, fonts, plain, meters)


def _draw_wires(screen: pygame.Surface, circuit: Circuit, belt: bool) -> None:
    view = circuit.view
    radius = max(2, round(BEAD_RADIUS * view.size))
    for k, path in enumerate(circuit.paths):
        points = wire_points(path, view.size, view.origin)
        flux = float(circuit.flux[k])
        pygame.draw.lines(screen, WIRE, False, points, 2)  # one colour: the beads show the rate
        along = cumulative_lengths(points)
        for s in circuit.beads.positions(k, BEAD_RATE_AT_FULL / RATE_MAX * flux, belt=belt):
            x, y = point_at(points, along, s * view.size)
            pygame.draw.circle(screen, BEAD, (round(x), round(y)), radius)


def _draw_parts(
    screen: pygame.Surface,
    circuit: Circuit,
    y: np.ndarray,
    fonts: Fonts,
    plain: bool,
    meters: bool = True,
) -> None:
    net, size = circuit.net, circuit.view.size
    for i, node_id in enumerate(net.ids):
        kind, rate = net.kinds[i], float(y[i])
        cx, cy = circuit.centre(i)
        facing = circuit.board.nodes[node_id].facing
        draw_part(screen, fonts, kind, placed_angle(kind, facing), (cx, cy), size, False)
        if meters and kind in (Kind.EYE, Kind.THRUSTER):
            _draw_meter(screen, (cx + METER_AT * size, cy), size, rate)
        if plain:
            continue
        name = cached_text(fonts.small, label(net, i), DIM_TEXT)
        screen.blit(name, name.get_rect(center=(cx, cy - 1.35 * size)))
        number = cached_text(fonts.small, f"{rate:.2f}", TEXT)
        screen.blit(number, number.get_rect(center=(cx, cy + 1.3 * size)))


def _draw_meter(
    screen: pygame.Surface, centre: tuple[float, float], size: float, rate: float
) -> None:
    """A part's level meter: filled from the foot up to its rate, in the colour of its face."""
    outline = pygame.Rect(0, 0, METER_WIDTH, round(METER_HEIGHT * size))
    outline.center = (round(centre[0]), round(centre[1]))
    filled = outline.inflate(-4, -4)
    foot = filled.bottom
    filled.height = round(filled.height * min(1.0, rate / RATE_MAX))
    filled.bottom = foot
    pygame.draw.rect(screen, RULE, outline, 1)
    pygame.draw.rect(screen, METER, filled)
