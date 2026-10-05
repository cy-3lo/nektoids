"""Editor state and input handling. Mutates the board only through its methods.

The focus and its Wheel (D-068, D-069): a click focuses a cell, lit on the board; Tools and
Parts show it large at their foot, the Wheel's icons round it: what can be done there
(`wheel.py`). Whatever the drawer, what a click or Enter would do shows atop the main screen
with its key, and a click on it opens Tools. Round an empty cell, the parts still handed out: a
click on one places it there, facing its default way. Round a part, its actions: turn left and
turn right (eyes and thrusters, 60° at once, D-009), wire, move, delete. Wire is chosen as a
part is clicked, so the next click on another part wires the two, either way round (D-026), and
the focus goes to that part. A part focused without a click, placed or just wired to, wires on
only forward, along the signal: a chain goes on, eye to sum to thruster, but from a thruster a
click on an eye only focuses it. A drag from a part moves it, its wires following while they
find a path (D-011). A click on the focused cell, or off the zone, drops the focus. While the
mouse is on Delete, what it would remove is darkened. A part dragged from Parts still lands
where it is dropped.

Write and Delete (D-068), rows in Tools, E to go from one to the other: all the above is Write.
In Delete there is no focus and no Wheel: a click removes the part under it with its wires, or
the wire under it, darkened while the mouse is on it; Enter does the same on the keyboard's
focus. Esc, or any action of Write, goes back to Write.

Keyboard, Tools open or not: the arrows move the focus from cell to cell; Enter opens its Wheel,
the arrows go round it and Enter takes the icon chosen; a part's number places it on the focused
cell. Round a part the Wheel starts on "nothing", so a second Enter closes it. L, R, W, M and
Backspace or Delete act on the focused part: after W the arrows go to the part to wire to and
Enter wires it; after M they carry the part and Enter puts it down. Esc, or a right click, goes
back one step: from a gesture to the Wheel, from the Wheel to nothing. H takes the hand, which
drags the view (D-013); the arrows drag it too.

Undo and Redo (D-027), rows in Tools under Write and Delete, also Ctrl+Z, Ctrl+Shift+Z and
Ctrl+Y (Cmd on a Mac): one step is one gesture, from press to release, so a whole drag goes back
at once. Space asks `main.py` for a run, Tab opens Chapters: the scene sets `request` and
`main.py` acts on it. A part's info disc in Parts opens a box that says what the part does; the
next click or key closes it and does nothing else (D-036). Every refusal flashes the cell and
puts the reason in the status line. At Files' foot, Save/Load: Copy a board puts its text on the
clipboard, and Paste a board, a field, takes one, which Enter puts on the board (D-205, D-206).
"""

from __future__ import annotations

import math
from dataclasses import replace

import pygame

from nektoids.editor import clipboard
from nektoids.editor.boardfield import board_field, load
from nektoids.editor.devdrive import TICKS_PER_FRAME
from nektoids.editor.frame import Frame
from nektoids.editor.geometry import nearest_wire
from nektoids.editor.history import History
from nektoids.editor.layout import (
    DIAGNOSTIC_MAP,
    KEY_ALIASES,
    MAX_HEX,
    MENU_GROUPS,
    MODE_KEY,
    RUN_VIEWS,
    TOOL_KEYS,
    TURNS,
    VIEW_KEYS,
    ZOOM_STEP,
    Bounds,
    Drawer,
    EditButton,
    Layout,
    MainView,
    Mode,
    Tool,
    ViewButton,
    WinRow,
    action_at,
    board_extent,
    board_field_at,
    board_view_of,
    cell_at,
    centred_on,
    centred_view,
    contains,
    drawer_key,
    edit_button_at,
    file_button_at,
    group_at,
    kept_on_board,
    main_view_for,
    make_layout,
    menu_item_at,
    mode_button_at,
    moved_view,
    opening_view,
    overview_at,
    overview_view,
    pan,
    value_at,
    view_button_at,
    wheel_fold_at,
    win_row_at,
    zoom,
    zoom_bar_at,
    zoom_button_at,
)
from nektoids.editor.probe import Probe, level_view
from nektoids.editor.router import WinGroup
from nektoids.editor.settings import Settings
from nektoids.editor.textfield import TextField
from nektoids.editor.tutorial import REFUSAL, Action
from nektoids.editor.wheel import (
    SLIDE,
    WHEEL_HEX,
    Slot,
    centre_in,
    cycled,
    offer,
    part_key,
    pile_at,
    slid,
    slot_at,
    slots,
    swaps,
    turned,
)
from nektoids.graph import boardtext
from nektoids.graph.board import Board, BoardState, Kind, Node, Refused, Wire
from nektoids.graph.hexgrid import (
    SQRT3,
    Cell,
    E,
    W,
    hex_distance,
    neighbour,
    to_pixel,
    vertical_step,
)
from nektoids.levels.level import Level

FLASH_FRAMES = 30  # how long a refused cell stays red [frames]
PILE_FRAMES = 30  # the mouse resting on a pile turns the Wheel one icon this often: 0.5 s [frames]
TOOLTIP_FRAMES = 60  # hover this long over a palette button to see its name and key [frames]
KEY_TOOLS = {key: tool for tool, key in TOOL_KEYS.items()}
KEY_VIEWS = {  # the rays, the motion and the streams are the run's: M and W are tools here
    key: button for button, key in VIEW_KEYS.items() if button not in RUN_VIEWS
}
# Arrows, Enter and digits are matched on their scancode, the physical key, which every platform
# reports alike: Safari on macOS tags the arrows as keypad keys (its `key` for the right arrow is
# keypad 6), and the digits are shifted on AZERTY. The key code is only a fallback.
ARROWS = (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN)
ARROW_SCANCODES = dict(
    zip(
        (pygame.KSCAN_LEFT, pygame.KSCAN_RIGHT, pygame.KSCAN_UP, pygame.KSCAN_DOWN),
        ARROWS,
        strict=True,
    )
)
ENTER = (pygame.K_RETURN, pygame.K_KP_ENTER)
ENTER_SCANCODES = (pygame.KSCAN_RETURN, pygame.KSCAN_KP_ENTER)
# 1-9 on the top row or on the keypad: the menu's parts in order.
DELETE_SCANCODES = (pygame.KSCAN_BACKSPACE, pygame.KSCAN_DELETE)  # Delete, as everywhere else
DIGIT_SCANCODES = tuple(getattr(pygame, f"KSCAN_{n}") for n in range(1, 10))
KEYPAD_SCANCODES = tuple(getattr(pygame, f"KSCAN_KP_{n}") for n in range(1, 10))
MAX_WINS = 10  # the wins Files lists of each level, the best first
PROBE_TURN = math.radians(15.0)  # the mouse wheel, L or R, on the probe in Diagnostic
NODE_HIT = 0.5  # a click this close to a component's centre is on its shape [hex sizes]
WIRE_HIT = 0.2  # a click this close to a drawn wire is on it [hex sizes]


class EditorScene(Frame):
    def __init__(
        self,
        board: Board,
        layout: Layout,
        caption: tuple[str, str] = ("", ""),
        settings: Settings | None = None,
        level: Level | None = None,
    ):
        self._start_frame(layout, settings)
        self.board = board
        self.level = level  # where the Run preview's probe stands; None: no preview
        self.main = MainView.DIAGRAM  # what the main screen shows, by the drawer (D-069)
        self.probe: Probe | None = None  # the Run preview's engine, made when it first shows
        self._probed = None  # the board as the probe was made for it
        self.probing = False  # the probe held in Diagnostic's map, following the mouse
        self.holding: int | None = None  # the eye whose meter's knob the mouse holds
        self.overviewing = False  # Navigator's overview held: the view follows the mouse
        self.zooming = False  # Navigator's zoom bar held: the zoom follows the mouse
        self.wheel_folded = False  # the picture of the cell folded, in Tools and Parts (D-069)
        self.guide_cells: frozenset[Cell] = frozenset()  # a tutorial step's cells; main.py's
        self.focused: Cell | None = None  # the cell the Wheel is round, the keyboard's too (D-068)
        self.wheel_open = False  # the Wheel shows round the focus
        self.wheel_keys = False  # the keyboard opened it: the arrows go round it
        self.choice: int | None = None  # the Wheel's icon the keyboard is on; None: nothing
        self.wheel_hover: Slot | None = None  # the Wheel's icon under the mouse, in Tools or Parts
        self.press_cell: Cell | None = None  # a part pressed: a click or a drag, told on release
        self.drawing = False  # Wire chosen, a drag from a part: it draws a wire (D-072)
        self.keyboard = False  # the keyboard drives, until the mouse moves
        self.swapping = False  # Swap chosen: the Wheel offers the parts the focused one may become
        self.turn = 0  # the Wheel's turn: its first icon on the rim, the others piled
        self.slide_from = 0.0  # the turn the Wheel showed when its slide to `turn` began
        self.slide_left = 0  # the frames left in that slide (D-083)
        self.wire_chosen = False  # Wire chosen by its key or in the Wheel, not only at hand
        self.piling = 0  # the mouse on a pile of the Wheel: the way it turns the Wheel, -1 or 1
        self.pile_frames = 0  # how long it has rested there
        self.onward = False  # the focus came on to the part just wired to: it wires only forward
        self.wins: tuple[WinGroup, ...] = ()  # this session's wins, for Files; main.py's
        self.caption = caption  # the level's title and spec, under the tabs
        self.view = opening_view(layout, sorted(board.cells))
        self.mode = Mode.WRITE  # what a click on the board does: Write, or Delete (D-068)
        self.tool = Tool.ADD
        self.picked: Kind | None = None  # Add: the menu kind in hand
        self.dragging = False  # Add: mouse held since picking from the menu
        self.source: int | None = None  # Wire: the focused part, wired to the next one clicked
        self.moving: int | None = None  # Move: node id being dragged
        self.selected: int | None = None  # what the turn buttons and keys act on
        self.panning_from: tuple[int, int] | None = None  # Pan: last mouse position
        self.ghost: tuple[Cell, ...] | Refused | None = None  # Wire: route to the hovered cell
        self.ghost_connects = False  # Wire: the ghost ends on a target it may connect to
        self.ghost_way: tuple[Cell, ...] | None = None  # ... over a part it cannot: the way only
        self.folded: set[str] = set()  # Parts' and Files' groups shown closed
        self.mouse = (0, 0)
        self.pointed: Cell | None = None  # grid cell under the mouse, in the zone or not
        self.hover: Cell | None = None  # the same, if it is in the zone
        self.carrying = False  # Move by keyboard: grabbed with Enter, not yet dropped
        self._grabbed: BoardState | None = None  # the board as the part being moved was picked up
        self._landed: BoardState | None = None  # ... and as the move's last step left it
        self.flash_cell: Cell | None = None
        self.flash_frames = 0
        self.history = History()
        self._kept = board.snapshot()  # the board as of the last step undo can go back to
        self.loading: TextField | None = None  # Load's field, open: a board's text (D-206)
        self.field_pressed = False  # a press on it: it opens when the click is over
        self.ghosts: tuple = ()  # the tutorial's parts to build, drawn faintly (D-039); main.py's
        self.ghost_wires: tuple = ()  # ... and its wires, cell to cell (D-074); main.py's too

    def update(self) -> None:
        """Once per frame."""
        if self.loading is not None and clipboard.WEB:  # the page's field took the keys
            text, caret, ended = clipboard.field()
            self.loading.take(text, caret)
            if ended is not None:
                self._field_done(ended)
        if self.flash_frames > 0:
            self.flash_frames -= 1
        self.frame_update()
        if self.piling:  # the Wheel turns slowly while the mouse rests on a pile (D-068)
            self.pile_frames += 1
            if self.pile_frames % PILE_FRAMES == PILE_FRAMES // 2:
                self._turn_wheel(turned(self.turn + self.piling, None, len(self.offered())))
        if self.slide_left:  # after any step this frame: a slide shows SLIDE frames
            self.slide_left -= 1
        self.view = kept_on_board(self.layout, self.view, self.extent())  # D-066
        if self.main is MainView.PREVIEW or self.layout.drawer is Drawer.DIAGNOSTIC:
            self._probe_now()
        if self.probe is not None:
            self.probe.see(self.view)  # the board's own scale and place, zoomed or panned
        if self.main is MainView.PREVIEW:
            for _ in range(TICKS_PER_FRAME):
                self.probe.tick()

    def _probe_now(self) -> None:
        """The probe, made again if the board changed since; it stays where it stood."""
        if self.level is None:
            return
        now = self.board.snapshot()
        if self.probe is None or now != self._probed:
            pose = self.probe.pose if self.probe is not None else None
            self.probe = Probe(self.board, self.level, self.view, pose)
            self._probed = now

    def open_drawer(self, drawer: Drawer | None) -> None:
        """As the frame opens it; the main screen follows (D-069): the Run preview in Diagnostic,
        what it showed before in Navigator, the board otherwise. Diagnostic stays shut while a
        tutorial step leads, and with no level to run the board in."""
        if drawer is Drawer.DIAGNOSTIC:
            if self.level is None:
                self._refuse("there is no level to run the board in")
                return
            if not self._allowed(Action("view")):
                return
        super().open_drawer(drawer)
        view = main_view_for(drawer, self.main)
        if view is not self.main:
            self._cancel()
            self.main = view

    def _editing(self) -> bool:
        """Whether the board is on screen to edit; if the Run preview shows, say so (D-069)."""
        if self.main is MainView.PREVIEW:
            self._refuse("the Run preview shows: open Tools or Parts to edit")
            return False
        return True

    def _on_wheel(self, pos: tuple[int, int]) -> bool:
        """Whether `pos` is on Tools' picture of the focused cell, its Wheel round it."""
        return self.layout.wheel_view is not None and contains(self.layout.wheel_view, pos)

    def _on_map(self, pos: tuple[int, int]) -> bool:
        """Whether `pos` is on Diagnostic's map of the level, with a probe to move."""
        shown = self.layout.drawer is Drawer.DIAGNOSTIC and self.probe is not None
        return shown and contains(DIAGNOSTIC_MAP, pos)

    def _probe_to(self, pos: tuple[int, int]) -> None:
        """The probe where the mouse is on Diagnostic's map, outside the obstacles."""
        self.probe.place(*level_view(self.level, DIAGNOSTIC_MAP).to_world(*pos))

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION and self.keyboard and event.rel == (0, 0):
            # Browsers re-send the pointer position without any movement (Chrome does, whenever
            # the page redraws under a still mouse): that is not the mouse taking over.
            return
        if self.info is not None and event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
            self.info = None  # the next click or key closes the box, and only that
            return
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            self.keyboard = False  # the mouse takes over
        if event.type == pygame.MOUSEMOTION:
            self._track(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._track(event.pos)
            self._press(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._release(event.pos)
        elif event.type == pygame.MOUSEWHEEL and self._on_wheel(self.mouse):
            self._turn_wheel(turned(self.turn - event.y, None, len(self.offered())))  # it turns
        elif event.type == pygame.MOUSEWHEEL and self._on_map(self.mouse):
            self.probe.turn(event.y * PROBE_TURN)  # up: counter-clockwise
        elif event.type == pygame.MOUSEWHEEL and self.frame_wheel(self.mouse, event.y):
            pass  # the drawer's rows scrolled (D-096)
        elif event.type == pygame.KEYDOWN and self.loading is not None:  # natively (D-206)
            self._field_key(event)
        elif event.type == pygame.KEYDOWN and self.typing is not None:  # a passkey (D-075)
            self.type_key(pygame.key.name(event.key), event.unicode)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self._escape()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if not self._escape():  # nothing left to back out of: the levels (D-304)
                self.toggle_drawer(Drawer.CHAPTERS)
        elif event.type == pygame.KEYDOWN:
            self._key(event)
        if self.moving is None and not self.carrying:  # between gestures
            self._keep()

    # Keyboard

    def _key(self, event: pygame.event.Event) -> None:
        if self.tab_key(pygame.key.name(event.key)):  # F1, F2, F3 (D-303)
            return
        if event.mod & (pygame.KMOD_CTRL | pygame.KMOD_META):
            if event.key == pygame.K_z:
                self._edit(EditButton.REDO if event.mod & pygame.KMOD_SHIFT else EditButton.UNDO)
            elif event.key == pygame.K_y:
                self._edit(EditButton.REDO)
            elif event.key == pygame.K_COMMA:  # Settings, as in desktop apps (D-069)
                self.toggle_drawer(Drawer.SETTINGS)
            return  # no other shortcut with Ctrl or Cmd: they are the browser's
        self.keyboard = True
        arrow = ARROW_SCANCODES.get(event.scancode) or (event.key if event.key in ARROWS else None)
        if arrow is not None:
            if self.tool is Tool.PAN or self._editing():  # the hand moves the preview's view too
                self._arrow(arrow)
        elif event.scancode in ENTER_SCANCODES or event.key in ENTER:
            if self._editing():
                self._enter()
        elif event.scancode == pygame.KSCAN_SPACE:  # LEVEL_KEYS[RUN], on the physical key
            self._ask("run")
        elif event.scancode == pygame.KSCAN_TAB:  # the next tab, or the one before (D-304)
            self.next_tab(bool(event.mod & pygame.KMOD_SHIFT))
        elif event.scancode in DELETE_SCANCODES:  # TOOL_KEYS[DELETE], on the physical key
            self._choose(Tool.DELETE)
        elif event.scancode in DIGIT_SCANCODES + KEYPAD_SCANCODES:
            self._digit((DIGIT_SCANCODES + KEYPAD_SCANCODES).index(event.scancode) % 9)
        elif self._turns_probe(event.unicode):
            sign = 1.0 if event.unicode.upper() == TOOL_KEYS[Tool.TURN_LEFT] else -1.0
            self.probe.turn(sign * PROBE_TURN)
        else:
            self._shortcut(event.unicode)

    def _arrow(self, key: int) -> None:
        """Round the open Wheel, if the keyboard opened it; else from cell to cell, the focus
        with them, carrying a part being moved; with the hand, the view dragged one cell."""
        left, right, up, _ = ARROWS
        if self.tool is Tool.PAN:
            sx, sy = SQRT3 * self.view.size, 1.5 * self.view.size
            dx, dy = {left: (-sx, 0), right: (sx, 0), up: (0, -sy)}.get(key, (0, sy))
            self.view = pan(self.view, dx, dy)
            return
        items = self.offered()
        if self.going_round() and items:
            step = 1 if key in (right, ARROWS[3]) else -1
            self.choice = cycled(items, self.choice, step)
            self._turn_wheel(turned(self.turn, self.choice, len(items)))  # brought round
            return
        if self.focused is None:
            self._focus_key(self._start_cell())
            return
        if key == left:
            step = neighbour(self.focused, W)
        elif key == right:
            step = neighbour(self.focused, E)
        else:
            step = vertical_step(self.focused, -1 if key == up else 1)
        if step not in self.board.cells:
            return
        if self.carrying:  # Move by keyboard: the part goes with the focus
            node = self._focused_node()
            if node is not None and self._move_to(node, step):
                self.focused = step
        elif self.tool is Tool.WIRE and self.source is not None and not self.wheel_open:
            self.focused = step  # wiring by keyboard: the focus goes to the part to wire to
        else:
            self._focus_key(step)
        self._track(self._focus_pos())

    def _enter(self) -> None:
        """The keyboard's click: on a cell, its Wheel; in the Wheel, the icon chosen, or, on
        "nothing", the Wheel closed; a part carried is put down; while wiring, the wire made to
        the part the focus is on."""
        if self.focused is None:
            self._focus_key(self._start_cell())
            return
        if self.mode is Mode.DELETE:
            self._erase(self.focused, self._focus_pos())
            return
        if self.carrying:
            self.carrying, self.tool = False, Tool.ADD
            return
        node = self._focused_node()
        if self.tool is Tool.WIRE and not self.wheel_open and self.source is not None:
            source = self.board.nodes.get(self.source)
            if node is None or source is None:
                self._refuse("a wire runs from a part to a part", self.focused)
            elif node.id == source.id:
                self._refuse("a part is not wired to itself", self.focused)
            elif self._try_wire(source, node, node.cell):
                self._focus_key(node.cell)  # on to the part wired to
                return
            self._focus_key(self.focused)  # the attempt ends: Wire goes, the cursor stays
            return
        items = self.offered()
        if not self.wheel_open or not self.wheel_keys:
            self.wheel_open, self.wheel_keys = True, True
            self.choice = 0 if items and node is None else None
            return
        if self.choice is None or self.choice >= len(items):
            self.wheel_open, self.wheel_keys = False, False  # "nothing": the Wheel closes
            return
        self._use(items[self.choice])

    def _start_cell(self) -> Cell:
        if self.hover is not None:
            return self.hover
        return min(self.board.cells, key=lambda cell: hex_distance(cell, (0, 0)))

    def _focus_pos(self) -> tuple[int, int]:
        x, y = to_pixel(self.focused, self.view.size, self.view.origin)
        return (round(x), round(y))

    def _digit(self, k: int) -> None:
        """A number: on a focused empty cell, that part placed there (its key in the Wheel);
        elsewhere, that part picked, for a click to place (D-068)."""
        kinds = [kind for _, group in MENU_GROUPS for kind in group if kind in self.layout.kinds]
        if k >= len(kinds) or not self._editing():
            return
        cell = self.focused
        if self.swapping and kinds[k] in self.offered():
            self._swap(kinds[k])
        elif self.swapping:
            self._refuse("it may become only a part of its group, still left", cell)
        elif cell is not None and cell in self.board.cells and self.board.node_at(cell) is None:
            self._place(kinds[k], cell)
        else:
            self._pick(kinds[k])
            self.dragging = False  # placed with a click, not by releasing a button

    def _shortcut(self, typed: str) -> None:
        key = KEY_ALIASES.get(typed, typed.upper())
        drawer = drawer_key(self.layout.env, key)
        if self.start_passkey(key):  # P in Chapters: a passkey, not Parts (D-075)
            pass
        elif drawer is not None:  # not refused in the preview: the way out of it (D-069)
            self.toggle_drawer(drawer)
        elif key == MODE_KEY:
            self._set_mode(Mode.DELETE if self.mode is Mode.WRITE else Mode.WRITE)
        elif key in KEY_TOOLS:
            self._choose(KEY_TOOLS[key])
        elif key in KEY_VIEWS:
            self._view_button(KEY_VIEWS[key])

    # Mouse

    def _track(self, pos: tuple[int, int]) -> None:
        if self.panning_from is not None:
            dx, dy = pos[0] - self.panning_from[0], pos[1] - self.panning_from[1]
            self.view, self.panning_from = pan(self.view, dx, dy), pos
        self.mouse = pos
        self.frame_track(pos)
        if self.probing and self.probe is not None:
            self._probe_to(pos)
        if self.overviewing:
            self._overview_to(pos)
        if self.zooming:
            self._zoom_to(pos)
        self._hold(pos)
        self.wheel_hover = slot_at(self.wheel(), pos, WHEEL_HEX)
        piling = 0
        if self.layout.wheel_view is not None:
            piling = pile_at(len(self.offered()), self.turn, self.cell_centre(), WHEEL_HEX, pos)
        if piling != self.piling:
            self.piling, self.pile_frames = piling, 0
        pointed = cell_at(self.layout, self.view, pos)
        moved_on = pointed != self.pointed
        self.pointed = pointed
        hover = pointed if pointed in self.board.cells else None
        if hover != self.hover:
            self.hover = hover
            self._update_ghost()
        if self.press_cell is not None and pointed != self.press_cell and self.moving is None:
            source = self.board.nodes.get(self.source) if self.source is not None else None
            lit = source is not None and source.cell == self.press_cell  # Wire lit for it (D-090)
            if self.tool is Tool.WIRE and (self.wire_chosen or lit):  # a wire (D-072)
                self._draw_from(self.press_cell)
            else:
                self._grab(self.press_cell)  # the press was the start of a drag: a move (D-068)
        if moved_on and self.moving is not None and pointed in self.board.cells:
            self._drag_to(pointed)  # off the body, it waits, to go if let go there (D-085)

    def _press(self, pos: tuple[int, int]) -> None:
        if self.loading is not None and not board_field_at(self.layout, pos):
            self._close_field()  # a click elsewhere gives it up, as the passkey's (D-075)
        if self.frame_press(pos):
            return
        if board_field_at(self.layout, pos):
            self.field_pressed = True  # it opens when the click is over: Safari wants it so
            return
        if file_button_at(self.layout, pos) is not None:
            self._save()
            return
        if self._on_map(pos):
            self.probing = True
            self._probe_to(pos)
            return
        if overview_at(self.layout, pos):
            self.overviewing = True
            self._overview_to(pos)
            return
        step = zoom_button_at(self.layout, pos)
        if step is not None:
            self._view_button(step)
            return
        if zoom_bar_at(self.layout, pos) is not None:
            self.zooming = True
            self._zoom_to(pos)
            return
        won = win_row_at(self.layout, pos)
        if won is not None:
            self._put_back(won)
            return
        mode = mode_button_at(self.layout, pos)
        if mode is not None:
            self._set_mode(mode)
            return
        edit = edit_button_at(self.layout, pos)
        if edit is not None:
            self._edit(edit)
            return
        button = view_button_at(self.layout, pos)
        if button is not None:
            self._view_button(button)
            return
        if wheel_fold_at(self.layout, pos):  # The Wheel's title, in Tools or Parts (D-069)
            self.wheel_folded = not self.wheel_folded
            self.layout = self._relayout(self.layout.drawer)
            return
        title = group_at(self.layout, pos)
        if title is not None:
            self.folded ^= {title}
            self.layout = self._relayout(self.layout.drawer)
            return
        kind = menu_item_at(self.layout, pos)
        if kind is not None:
            self._pick(kind)
            return
        slot = slot_at(self.wheel(), pos, WHEEL_HEX)
        if slot is not None:  # an icon of the Wheel, in Tools or Parts
            self._use(slot.what)
            return
        shown = self.main is MainView.DIAGRAM  # the action atop shows only with the board
        if shown and action_at(self.layout, pos) is not None:  # the action: Tools, to see it all
            self.open_drawer(Drawer.TOOLS)
            return
        if self.main is MainView.PREVIEW:  # the board is not on screen to edit, but the eyes are
            if self.tool is Tool.PAN:  # the hand moves the view, the preview's as the board's
                self.panning_from = pos
                return
            self.holding = self.probe.handle_at(pos) if self.probe is not None else None
            self._hold(pos)
            return
        if not contains(self.layout.board_area, pos):
            return
        if self.tool is Tool.PAN:
            self.panning_from = pos
            return
        if self.mode is Mode.DELETE:
            self._erase(self.hover, pos)
            return
        if self.picked is not None:  # a part picked in Parts: it goes where the click falls
            if self.pointed is not None:
                self._add(self.pointed)
            return
        cell = self.hover
        if cell is not None and self.board.node_at(cell) is not None:
            self.press_cell = cell  # a click, or the start of a drag: the release tells
            return
        if cell is None:
            self._focus(None)  # off the zone: nothing focused
        else:
            self._click_empty(cell)

    def _wire_near(self, pos: tuple[int, int], cell: Cell | None) -> Wire | None:
        """The wire a click at `pos` falls on, off any part: one of a cell it crosses, or one
        drawn close by between two neighbouring parts."""
        size, origin = self.view.size, self.view.origin
        wire = nearest_wire(pos, self.board.wires, size, origin, WIRE_HIT * size)
        if wire is None and cell is not None and self.board.wires_in(cell):
            wire = nearest_wire(pos, self.board.wires_in(cell), size, origin, math.inf)
        return wire

    def _turns_probe(self, typed: str) -> bool:
        """L and R turn the probe while Diagnostic shows it with the Run preview; else the parts."""
        turns = typed.upper() in (TOOL_KEYS[Tool.TURN_LEFT], TOOL_KEYS[Tool.TURN_RIGHT])
        shown = self.main is MainView.PREVIEW and self.layout.drawer is Drawer.DIAGNOSTIC
        return turns and shown and self.probe is not None

    def extent(self) -> Bounds:
        """What Navigator's overview shows of the board, and the most the main screen may."""
        return board_extent(self.layout, sorted(self.board.cells))

    def least_zoom(self) -> float:
        """The farthest the zoom goes: the main screen shows the overview's extent [px]."""
        return board_view_of(self.layout.board_area, self.extent()).size

    def _overview_to(self, pos: tuple[int, int]) -> None:
        """The view, at its zoom, centred where the mouse is on Navigator's overview (D-060)."""
        small = overview_view(self.layout, sorted(self.board.cells))
        moved = centred_on(self.layout, self.view, small, pos)
        self.view = kept_on_board(self.layout, moved, self.extent())

    def _zoom_to(self, pos: tuple[int, int]) -> None:
        """The zoom where the mouse is along Navigator's zoom bar, about the board's centre."""
        x, _, w, _ = self.layout.zoom_bar
        size = value_at((pos[0] - x) / w, self.least_zoom(), MAX_HEX)
        bx, by, bw, bh = self.layout.board_area
        self.view = zoom(self.view, size / self.view.size, (bx + bw / 2, by + bh / 2))

    def _hold(self, pos: tuple[int, int]) -> None:
        """The eye whose knob is held reads what its meter says at the mouse: a test input."""
        if self.holding is not None and self.probe is not None:
            self.probe.hold(self.holding, self.probe.level_at(self.holding, pos[1]))

    def _release(self, pos: tuple[int, int]) -> None:
        if self.field_pressed:
            self.field_pressed = False
            if board_field_at(self.layout, pos):
                self._open_field()
        self.probing, self.holding, self.overviewing, self.zooming = False, None, False, False
        self.panning_from = None
        self.frame_release()
        if self.press_cell is not None:  # a press on a part: a drag moved it, or drew a wire,
            cell, self.press_cell = self.press_cell, None  # or it was a click
            if self.moving is not None:
                node = self.board.nodes.get(self.moving)
                self.moving = None
                if node is not None and self.pointed not in self.board.cells:
                    self._drop_off(node)  # let go off the body (D-085)
                elif node is not None:
                    self._focus(node.cell)  # where it landed
            elif self.drawing:
                self.drawing = False
                self._drawn_to(self.pointed)
            else:
                self._click_part(cell)
            return
        self.moving = None
        if not self.dragging:
            return
        self.dragging = False
        if self.pointed is not None:
            self._add(self.pointed)

    def _slid(self, before: Layout, after: Layout) -> None:
        """The board moved: the view slides with its centre, so nothing jumps; the Run preview
        fits its new room."""
        self.view = moved_view(self.view, before, after)
        if self.probe is not None:
            self.probe.see(self.view)

    def _relayout(self, drawer: Drawer | None) -> Layout:
        """The layout with `drawer` open, the same parts handed out, chapter, wins, hints and
        tabs."""
        return make_layout(
            drawer,
            frozenset(self.folded),
            self.layout.kinds,
            self.layout.chapter,
            files=tuple((group.title, len(group.wins)) for group in self.wins),
            wheel_folded=self.wheel_folded,
            scroll=self.scrolls.get(drawer, 0),
            maker=self.layout.maker,
            **self._hint_layout(),
        )

    def revise(self, level: Level, caption: tuple[str, str]) -> None:
        """The level made again in the Maker (D-301): the caption follows, and the Run preview's
        probe is made again on its plane, where it stood."""
        self.level, self.caption = level, caption
        self._probed = None

    def unfold_wheel(self) -> None:
        """The Wheel unfolded, if it was folded: a tutorial's step shows one of its icons."""
        if self.wheel_folded:
            self.wheel_folded = False
            self.layout = self._relayout(self.layout.drawer)

    def set_wins(self, groups: tuple[WinGroup, ...]) -> None:
        """Every level's wins this session, as Files lists them: at most MAX_WINS a level
        (D-059, D-092)."""
        groups = tuple(replace(group, wins=group.wins[:MAX_WINS]) for group in groups)
        if groups != self.wins:
            self.wins = groups
            self.layout = self._relayout(self.layout.drawer)

    def _put_back(self, row: WinRow) -> None:
        """A win's board on the board, this level's or another's that fits it; the one left
        goes to Undo (D-059, D-092)."""
        if self._allowed(Action("load")):
            self._cancel()
            refused = self.board.adopt(self.wins[row.group].wins[row.index].board)
            if refused is not None:
                self._refuse(refused.reason, None)
                return
            self.selected = None

    # The board as text (D-205, D-206)

    def _save(self) -> None:
        """Save: the board as text, on the clipboard and in the status line, to copy by hand if
        the clipboard is out of reach."""
        try:
            text = boardtext.to_text(self.board)
        except ValueError as error:
            self._refuse(str(error), None)
            return
        clipboard.copy(text)
        self.said = f"Copied: {text}"

    def _open_field(self) -> None:
        if self._allowed(Action("load")):  # as a win put back is (D-092)
            self._cancel()
            self.loading = board_field()
            clipboard.open_field("", self.loading.longest)

    def _close_field(self) -> None:
        self.loading = None
        clipboard.close_field()

    def _field_key(self, event: pygame.event.Event) -> None:
        """A key while Load's field is open, natively: Ctrl/Cmd+V pastes, Enter loads, Esc
        gives up; the rest types."""
        if event.key == pygame.K_v and event.mod & (pygame.KMOD_CTRL | pygame.KMOD_META):
            self.loading.paste(clipboard.paste())
            return
        ended = self.loading.type(pygame.key.name(event.key), event.unicode)
        if ended is not None:
            self._field_done(ended)

    def _field_done(self, ended: str) -> None:
        """Enter: the text's board on this one, or why not; Esc: the field closes, as it is."""
        text = self.loading.text
        self._close_field()
        if ended != "enter":
            return
        loaded, said = load(self.board, text)
        if not loaded:
            self._refuse(said, None)
            return
        self.selected, self.said = None, said
        self._keep()  # the board it replaced goes to Undo

    def _allowed(self, action: Action, cell: Cell | None = None) -> bool:
        """Whether the tutorial's step lets `action` through (D-048); if not, say so."""
        if self.gate is None or self.gate(action):
            return True
        self._refuse(REFUSAL, cell)
        return False

    def _drop_gesture(self) -> None:
        """Whatever was under way, a part in hand, a wire or a move, given up."""
        self.picked, self.dragging = None, False
        self.source, self.ghost = None, None
        self.moving, self.carrying, self.press_cell, self.drawing = None, False, None, False
        self.swapping = False
        if self.tool is not Tool.PAN:
            self.tool = Tool.ADD

    def _cancel(self) -> None:
        self._drop_gesture()
        self.message = ""

    # View

    def _view_button(self, button: ViewButton) -> None:
        if button is ViewButton.PAN:
            if not self._allowed(Action("tool", tool=Tool.PAN)):
                return
            self._cancel()
            self.tool = Tool.PAN
            return
        if button is ViewButton.CENTRE:
            self.view = centred_view(self.layout, self.view.size)
            return
        x, y, w, h = self.layout.board_area
        factor = ZOOM_STEP if button is ViewButton.ZOOM_IN else 1.0 / ZOOM_STEP
        self.view = zoom(self.view, factor, (x + w / 2, y + h / 2))

    # Undo (D-027)

    def _keep(self) -> None:
        """Between gestures: if the board changed since the last step kept, keep this one."""
        now = self.board.snapshot()
        if now != self._kept:
            self.history.record(self._kept)
            self._kept = now

    def _edit(self, button: EditButton) -> None:
        """Undo or redo one step; a gesture under way ends first, and counts as a step."""
        if not self._allowed(Action(button.value)):
            return
        self._cancel()
        self._keep()
        step = self.history.undo if button is EditButton.UNDO else self.history.redo
        state = step(self._kept)
        if state is None:
            self._refuse(f"nothing to {button.value}", None)
            return
        self.board.restore(state)
        self._kept = state
        if self.selected not in self.board.nodes:
            self.selected = None

    # Tools

    def _choose(self, tool: Tool) -> None:
        """A tool's key, on the focus (D-068): A opens the parts' Wheel of an empty cell; L, R, W,
        M and Backspace or Delete (D-069) act on the focused part; H takes the hand or puts it
        down."""
        if tool is Tool.PAN:
            self._drop_gesture()
            self.tool = Tool.ADD if self.tool is Tool.PAN else Tool.PAN
            return
        if not self._editing():
            return
        if tool is not Tool.DELETE:
            self.mode = Mode.WRITE  # writing again
        if tool is Tool.ADD:
            if self.focused is not None and self._focused_node() is None:
                self.wheel_open, self.wheel_keys, self.choice = True, True, 0
            return
        if not self._allowed(Action("tool", tool=tool)):
            return
        self.wheel_keys = self.wheel_keys or self.keyboard
        self._act(tool)

    def _pick(self, kind: Kind) -> None:
        """A part picked in Parts, or by its number with no empty cell focused: a drag, or the
        next click on a cell, places it."""
        if not self._allowed(Action("pick", kind=kind)):
            return
        self._cancel()
        self.mode = Mode.WRITE  # a part is for the board
        if self.board.remaining(kind) == 0:
            self._refuse("none left", None)
            return
        self.picked, self.dragging = kind, True

    def _add(self, cell: Cell) -> None:
        """The part picked in Parts placed on `cell`, then focused."""
        if self.picked is None:
            self._refuse("pick a part in Parts first", None)
            return
        self._place(self.picked, cell)

    def _turn(self, cell: Cell, steps: int) -> None:
        """Turn the part on `cell` by `steps` x 60° (counter-clockwise if positive)."""
        node = self.board.node_at(cell)
        if node is None:
            self._refuse("click an eye or a thruster", cell)
            return
        self.selected = node.id
        if not self._allowed(Action("turn", cell=cell), cell):
            return
        result = self.board.rotate(node.id, steps)
        if isinstance(result, Refused):
            self._refuse(result.reason, cell)
        else:
            self.message = ""

    def _draw_from(self, cell: Cell) -> None:
        """A drag from a part with Wire chosen (D-072), or from the part Wire is lit for, just
        placed or clicked (D-090): a wire from that part, as a click on it then on another would
        make; the ghost follows the mouse."""
        node = self.board.node_at(cell)
        if self.drawing or node is None:
            return
        self.drawing = True
        if node.id != self.source:  # from the part pressed, which wires either way round
            self.focused, self.source, self.selected = cell, node.id, node.id
            self.onward, self.turn, self.slide_left = False, 0, 0
        self._update_ghost()

    def _drawn_to(self, cell: Cell | None) -> None:
        """The drag released on `cell`: the wire made to the part there, the focus going on to it;
        on an empty cell the attempt ends (D-068); back on its own part, or off the board,
        nothing."""
        source = self.board.nodes.get(self.source) if self.source is not None else None
        if source is None or cell is None or cell not in self.board.cells:
            return
        target = self.board.node_at(cell)
        if target is None:
            self._refuse("a wire runs from a part to a part", cell)
            self._focus(None)
        elif target.id != source.id:
            wired = self._try_wire(source, target, cell)
            self._focus(cell if wired else None, onward=wired)

    def _grab(self, cell: Cell) -> None:
        """A drag from a part: it moves with the mouse (D-011, D-068), if it may."""
        if not self._allowed(Action("move", cell=cell), cell):
            self.press_cell = None
            return
        node = self.board.node_at(cell)
        if node is None or node.locked:
            self._refuse("placed by the level", cell)
            self.press_cell = None
            return
        self.moving, self.message = node.id, ""
        self._grabbed = self._landed = self.board.snapshot()

    def _dropping(self) -> bool:
        """Whether the part being dragged is off the body, the zone's cells, on the drawer or the
        bar too, where letting it go deletes it, if the tutorial lets it (D-085)."""
        node = self.board.nodes.get(self.moving) if self.moving is not None else None
        if node is None or self.pointed in self.board.cells:
            return False
        return self.gate is None or self.gate(Action("delete", cell=node.cell))

    def _drop_off(self, node: Node) -> None:
        """A part let go off the body (D-085): it goes, with its wires, and nothing is focused;
        if the tutorial's step does not let it, it stays where it waited, the reason said."""
        if not self._allowed(Action("delete", cell=node.cell), node.cell):
            self._focus(node.cell)
            return
        self.board.remove_node(node.id)  # never locked: a locked part is not grabbed
        self.message = ""
        self._focus(None)

    def _drag_to(self, cell: Cell) -> None:
        """One step of a move: the part stays at the last cell its wires could follow it to."""
        result = self._step(self.moving, cell)
        if isinstance(result, Refused):
            self._refuse(result.reason, cell)
        else:
            self.message = ""

    def doomed(self) -> tuple[int | None, list[Wire]]:
        """What a deletion would remove, darkened before it happens: in Delete, what is under the
        mouse, or on the keyboard's focus; in Write, the focused part and its wires, while the
        mouse or the keyboard is on its Wheel's Delete; a part dragged off the body (D-085)."""
        if self._dropping():
            return self.moving, [w for w in self.board.wires if self.moving in (w.source, w.target)]
        if self.mode is Mode.DELETE:
            if self.keyboard and self.focused is not None:
                return self._under(self.focused, self._focus_pos())
            if not contains(self.layout.board_area, self.mouse):
                return None, []
            return self._under(self.hover, self.mouse)
        hovered = None if self.wheel_hover is None else self.wheel_hover.what
        if self.keyboard and self.going_round() and self.choice is not None:
            items = self.offered()
            hovered = items[self.choice] if self.choice < len(items) else None
        if hovered is not Tool.DELETE:
            return None, []
        return self._under(self.focused, self._focus_pos())

    def _under(self, cell: Cell | None, pos: tuple[int, int]) -> tuple[int | None, list[Wire]]:
        """What deleting at `pos`, on `cell`, removes: the part there and its wires, unless the
        level placed it; or, on a wire, that wire."""
        node = self.board.node_at(cell) if cell is not None else None
        if node is not None:
            if node.locked:
                return None, []
            return node.id, [w for w in self.board.wires if node.id in (w.source, w.target)]
        wire = self._wire_near(pos, cell)
        return None, [] if wire is None else [wire]

    # Helpers

    def _update_ghost(self) -> None:
        """Where a wire from the focused part would run to the hovered cell, and whether it may
        end there: over an empty cell it only shows the way; over a part it is the real preview,
        where a click would wire (D-068). Over a part it cannot wire to, or would not, the way
        still shows, dimmed, as over an empty cell, and the reason, if any (D-069)."""
        self.ghost, self.ghost_connects, self.ghost_way = None, False, None
        start = self.source if self.tool is Tool.WIRE else None
        if start is None or self.hover is None or start not in self.board.nodes:
            return
        target, begin = self.board.node_at(self.hover), self.board.nodes[start]
        way = None  # the way only, as over an empty cell
        if begin.kind.emits:
            way = self.board.route(begin.cell, self.hover)
        elif not self.onward:  # a thruster: the way a wire into it would come
            way = self.board.route(self.hover, begin.cell)
        if target is None:
            self.ghost = way
            return
        if target.id == start:
            return
        if not self.onward or self._forward(begin, target):
            self.ghost = self.board.preview(*self.board.orient(start, target.id))
            self.ghost_connects = isinstance(self.ghost, tuple)
        if not self.ghost_connects:
            self.ghost_way = way

    # The focus and its Wheel (D-068)

    def offered(self) -> tuple[Kind | Tool, ...]:
        """What the focused cell offers, its Wheel's icons in order, whether a drawer shows them or
        not: none in Delete, or while the Run preview shows."""
        if self.focused is None or self.mode is not Mode.WRITE or self.main is not MainView.DIAGRAM:
            return ()
        if self.swapping:
            return swaps(self.board, self.focused, self.layout.kinds)
        return offer(self.board, self.focused, self.layout.kinds)

    def _tip_target(self, pos: tuple[int, int]) -> object | None:
        """As the frame's, and the Wheel's icon under the mouse (D-069)."""
        return super()._tip_target(pos) or slot_at(self.wheel(), pos, WHEEL_HEX)

    def wheel_tip(self) -> Slot | None:
        """The Wheel's icon whose tooltip shows, after the bar's rest, or at once after another
        tooltip (D-069): none while the keyboard drives, or once the Wheel has changed under it."""
        tip = self.tooltip
        if self.keyboard or not isinstance(tip, Slot):
            return None
        return tip if tip in self.wheel() else None

    def wheel_lit(self) -> Slot | None:
        """The Wheel's lit icon, which the line under it names in the accent (D-069): the
        keyboard's choice going round, else the tool in hand, Wire or Move; none otherwise."""
        wheel = self.wheel()
        if self.going_round() and self.choice is not None and self.choice < len(wheel):
            return wheel[self.choice]
        in_hand = self.tool if self.tool in (Tool.WIRE, Tool.MOVE) else None
        return next((s for s in wheel if s.what is in_hand and not s.depth), None)

    def going_round(self) -> bool:
        """Whether the keyboard goes round the Wheel: opened with Enter, until an icon is taken."""
        return self.wheel_keys and self.wheel_open

    def wheel(self) -> list[Slot]:
        """The focused cell's Wheel as Tools and Parts draw it, round their picture of the cell;
        none while neither shows the picture (D-069)."""
        if self.layout.wheel_view is None:
            return []
        turn = slid(self.slide_from, self.turn, self.slide_left)  # as it shows, sliding
        return slots(self.offered(), self.cell_centre(), WHEEL_HEX, self.layout.kinds, turn)

    def _turn_wheel(self, turn: int) -> None:
        """The Wheel turned to `turn`, sliding there in SLIDE frames; a step taken during a
        slide goes straight on, from where the Wheel shows (D-083)."""
        if turn != self.turn:
            self.slide_from = slid(self.slide_from, self.turn, self.slide_left)
            self.turn, self.slide_left = turn, SLIDE

    def cell_centre(self) -> tuple[float, float]:
        """Where Tools, or Parts, draws the focused cell (D-069)."""
        return centre_in(self.layout.wheel_view)

    def action(self) -> tuple[Kind | Tool | Mode, str]:
        """What the next click on the board, or Enter, does, and its key: shown atop the main
        screen while Tools is folded (D-068)."""
        items = self.offered()
        if self.tool is Tool.PAN:
            what: Kind | Tool | Mode = Tool.PAN
        elif self._dropping():  # a part dragged off the body: letting go deletes it (D-085)
            what = Tool.DELETE
        elif self.mode is Mode.DELETE:
            what = Mode.DELETE
        elif self.going_round() and self.choice is not None and self.choice < len(items):
            what = items[self.choice]
        elif self.swapping:
            what = Tool.SWAP
        elif self.carrying or self.tool is Tool.MOVE:
            what = Tool.MOVE
        elif self.tool is Tool.WIRE and self.source is not None:
            what = Tool.WIRE
        elif self.picked is not None:
            what = self.picked
        else:
            what = Mode.WRITE
        if isinstance(what, Kind):
            return what, part_key(what, self.layout.kinds)
        if isinstance(what, Mode):
            return what, MODE_KEY
        return what, VIEW_KEYS[ViewButton.PAN] if what is Tool.PAN else TOOL_KEYS[what]

    def _focused_node(self) -> Node | None:
        return self.board.node_at(self.focused) if self.focused is not None else None

    def _focus(self, cell: Cell | None, keys: bool = False, onward: bool = False) -> None:
        """Focus `cell` (None: nothing), its Wheel open: round a part, Wire chosen for the mouse,
        nothing for the keyboard; round an empty cell, its parts, the first chosen. `onward`: the
        focus goes on to the part just wired to, which wires on only forward (D-068, D-091)."""
        self._drop_gesture()
        self.focused, self.onward = cell, onward
        self.wire_chosen = False
        self.turn, self.slide_left = 0, 0  # the Wheel at its start, at once
        self.wheel_open, self.wheel_keys = cell is not None, keys
        node = self._focused_node()
        self.selected = None if node is None else node.id
        self.choice = None if node is not None or cell is None else 0
        if node is not None and not keys:  # a click on a part: wiring, from it, at hand
            self.tool, self.source = Tool.WIRE, node.id
        self._update_ghost()

    def _focus_key(self, cell: Cell) -> None:
        """The keyboard's focus moves to `cell`, its Wheel closed until Enter."""
        self._focus(cell, keys=True)
        self.wheel_open = False

    def _set_mode(self, mode: Mode) -> None:
        """Write or Delete (D-068): what a click on the board does. The hand is put down, the
        Wheel closes; the keyboard's focus stays where it is."""
        if not self._editing():
            return
        if mode is Mode.DELETE and not self._allowed(Action("tool", tool=Tool.DELETE)):
            return
        kept = self.focused if self.keyboard else None
        self._focus(None)
        if kept is not None:
            self._focus_key(kept)
        self.mode, self.tool = mode, Tool.ADD
        self.message = ""

    def _use(self, what: Kind | Tool) -> None:
        """An icon of the Wheel, clicked or chosen with Enter: a part placed, or an action."""
        if isinstance(what, Kind) and self.swapping:
            self._swap(what)
        elif isinstance(what, Kind):
            self._place(what, self.focused)
        else:
            self._act(what)

    def _place(self, kind: Kind, cell: Cell) -> None:
        """`kind` placed on `cell`, facing its default way; then the focus on it, its actions."""
        if not self._allowed(Action("pick", kind=kind)):
            return
        if not self._allowed(Action("place", kind=kind, cell=cell), cell):
            return
        self.mode = Mode.WRITE
        result = self.board.place(kind, cell)
        if isinstance(result, Refused):
            self._refuse(result.reason, cell)
            return
        self.message, keys = "", self.wheel_keys
        self._focus(cell, keys=keys)

    def _act(self, tool: Tool) -> None:
        """An action on the focused part: a turn at once, its Wire or Move chosen, or it
        deleted."""
        node = self._focused_node()
        if node is None:
            self._refuse("no part here", None)
            return
        if tool in TURNS:
            back = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
            self._turn(node.cell, -TURNS[tool] if back else TURNS[tool])
        elif tool is Tool.WIRE:
            if self._allowed(Action("tool", tool=Tool.WIRE)):
                self.tool, self.source, self.wire_chosen = Tool.WIRE, node.id, True
                if self.wheel_keys:  # the keyboard: the arrows go to the part to wire to
                    self.wheel_open = False
        elif tool is Tool.MOVE:
            if self._allowed(Action("move", cell=node.cell), node.cell):
                self.tool = Tool.MOVE
                if self.wheel_keys:  # the keyboard: the arrows carry it, Enter puts it down
                    self.wheel_open, self.carrying = False, True
                    self._grabbed = self._landed = self.board.snapshot()
        elif tool is Tool.DELETE:
            self._delete_part(node)
        elif tool is Tool.SWAP:
            if not self._allowed(Action("tool", tool=Tool.SWAP), node.cell):
                return
            if not swaps(self.board, node.cell, self.layout.kinds):
                self._refuse("no other part of its group left", node.cell)
                return
            self.swapping, self.turn, self.slide_left = True, 0, 0  # it offers what it may become
            self.choice = 0 if self.going_round() else None
            return
        if self.wheel_keys and self.wheel_open:
            items = self.offered()
            self.choice = next((k for k, what in enumerate(items) if what is tool), self.choice)
            self._turn_wheel(turned(self.turn, self.choice, len(items)))

    def _swap(self, kind: Kind) -> None:
        """The focused part swapped for one of `kind`, in its place (D-068); the wires it cannot
        take are said in the status line."""
        node = self._focused_node()
        result = self.board.replace(node.id, kind)
        if isinstance(result, Refused):
            self._refuse(result.reason, node.cell)
            return
        _, lost = result
        if self.keyboard:
            self._focus(node.cell, keys=True)  # its actions, the keyboard on "nothing"
        else:
            self._focus(node.cell)
        if lost:
            self._refuse(f"{lost} wire{'s' if lost > 1 else ''} could not follow", node.cell)
        else:
            self.message = ""

    def _click_empty(self, cell: Cell) -> None:
        """A click on an empty cell of the zone: the focused part moved there, if Move is chosen;
        nothing focused, if Wire was chosen: a wire cannot end there; else the focus there, or
        dropped if it was there already."""
        node = self._focused_node()
        if self.tool is Tool.MOVE and node is not None:
            if self._move_to(node, cell):
                self._focus(cell)
        elif self.tool is Tool.WIRE and self.wire_chosen:  # a failed wire: the attempt ends
            self._refuse("a wire runs from a part to a part", cell)
            self._focus(None)
        elif cell == self.focused:
            self._focus(None)
        else:
            self._focus(cell)

    def _click_part(self, cell: Cell) -> None:
        """A click on a part: the focused part wired to it, if Wire is chosen, and the focus
        then goes to it; if they cannot be wired, the attempt ends, nothing focused, the reason
        in the status line; the focus dropped if it was there already; else the focus there.

        A part clicked, placed or moved wires either way round (D-026, D-091): a thruster just
        placed is wired to by the eye clicked next. Only the part just wired to wires on only
        forward, along the signal: from an eye wired to a sum, a click on a thruster wires the
        sum to it; but from a thruster, a click on the other eye only focuses that eye, to start
        the next wire there."""
        node, source = self.board.node_at(cell), self._focused_node()
        if cell == self.focused:
            self._focus(None)
            return
        wiring = source is not None and self.tool is Tool.WIRE and node.id != source.id
        fresh = self.onward and not self.wire_chosen and not self._forward(source or node, node)
        if wiring and not fresh:
            if self._try_wire(source, node, cell):
                self._focus(cell, onward=True)  # on to the part wired to
            else:
                self._focus(None)  # the attempt ends, the reason in the status line
            return
        self._focus(cell)  # clicked: it wires either way round

    @staticmethod
    def _forward(source: Node, target: Node) -> bool:
        """Whether a wire may run out of `source` into `target`, as their kinds allow."""
        return source.kind.emits and target.kind.receives

    def _try_wire(self, source: Node, target: Node, cell: Cell) -> bool:
        """A wire between two parts, either way round (D-026), if the tutorial and the board
        let it; False, with the reason, if not."""
        ends = source.cell, target.cell
        if not self._allowed(Action("wire", cell=ends[0], other=ends[1]), cell):
            return False
        result = self.board.connect(*self.board.orient(source.id, target.id))
        if isinstance(result, Refused):
            self._refuse(result.reason, cell)
            return False
        self.message = ""
        return True

    def _move_to(self, node: Node, cell: Cell) -> bool:
        """The part moved to `cell`, its wires following (D-011); False, with the reason, if not."""
        if not self._allowed(Action("move", cell=node.cell), node.cell):
            return False
        if node.locked:
            self._refuse("placed by the level", node.cell)
            return False
        result = self._step(node.id, cell)
        if isinstance(result, Refused):
            self._refuse(result.reason, cell)
            return False
        self.message = ""
        return True

    def _step(self, node_id: int, cell: Cell) -> Node | Refused:
        """The part moved to `cell`; while a drag or the keyboard carries it, worked out from the
        board as it was picked up, so a wire it passed over, routed round it, goes back (D-086).
        If the board was edited otherwise since the last step, a turn or a swap while carrying,
        from the board as it is now. Refused, the board stays as it was."""
        before = self.board.snapshot()
        if self.moving is not None or self.carrying:
            if self._grabbed is not None and before == self._landed:
                self.board.restore(self._grabbed)
            else:
                self._grabbed = before  # edited since: the move goes on from here
        result = self.board.move_node(node_id, cell)
        if isinstance(result, Refused):
            self.board.restore(before)
        self._landed = self.board.snapshot()
        return result

    def _delete_part(self, node: Node) -> None:
        """The part deleted, with its wires; the focus stays on its cell, empty now."""
        if not self._allowed(Action("delete", cell=node.cell), node.cell):
            return
        result = self.board.remove_node(node.id)
        if isinstance(result, Refused):
            self._refuse(result.reason, node.cell)
            return
        self.message = ""
        if self.keyboard:  # the focus stays, its Wheel closed: a second Enter places nothing
            self._focus_key(node.cell)
        elif self.mode is Mode.WRITE:  # the cell's parts at hand
            self._focus(node.cell)

    def _delete_wire(self, wire: Wire) -> None:
        cell = self.board.nodes[wire.target].cell
        if not self._allowed(Action("delete", cell=cell), cell):
            return
        self.board.remove_wire(wire)
        self.message = ""

    def _erase(self, cell: Cell | None, pos: tuple[int, int]) -> None:
        """Delete, clicked at `pos` or entered on the focus: the part on `cell` with its wires,
        or the wire there."""
        node_id, wires = self._under(cell, pos)
        if node_id is not None:
            self._delete_part(self.board.nodes[node_id])
        elif wires:
            self._delete_wire(wires[0])
        elif cell is not None and self.board.node_at(cell) is not None:
            self._refuse("placed by the level", cell)

    def _escape(self) -> bool:
        """Esc, or a right click: back one step, from a gesture, to the Wheel, to nothing; False
        if there was nothing to back out of."""
        if self.tool is Tool.PAN:
            self.tool = Tool.ADD
        elif self.swapping:
            self.swapping, self.turn, self.slide_left = False, 0, 0  # back to the part's actions
            self.choice = None
        elif self.mode is Mode.DELETE:
            self.mode = Mode.WRITE
        elif self.carrying or (self.tool is Tool.WIRE and not self.wheel_open and self.source):
            self.carrying, self.tool, self.source = False, Tool.ADD, None
            self._update_ghost()
        elif self.wheel_open and self.focused is not None and self.wheel_keys:
            self.wheel_open, self.wheel_keys = False, False
        elif self.focused is not None or self.picked is not None or self.tool is not Tool.ADD:
            self._focus(None)  # and whatever was in hand
        else:
            return False
        self.message = ""
        return True

    def hint(self) -> str:
        """What the status line says the player can do now."""
        if self.tool is Tool.PAN:
            return "Drag the board to move the view. H or Esc puts the hand down."
        if self.main is MainView.PREVIEW:  # nothing to edit here (D-069)
            return "Drag an eye's knob to set what it reads. Tools or Parts to edit."
        if self._dropping():
            return "Let go and the part goes, with its wires; back on the body, it stays."
        if self.carrying:
            return "The arrows carry the part; Enter puts it down."
        if self.tool is Tool.WIRE and not self.wheel_open and self.source is not None:
            return "The arrows to the part to wire to, then Enter. Esc gives up."
        if self.mode is Mode.DELETE:
            return "Click a part or a wire to delete it. E or Esc: back to Write."
        if self.swapping:
            return "Pick what it becomes in the Wheel, or press its number. Esc: back."
        node = self._focused_node()
        if node is not None:
            return "Click or drag to another part to wire it; M moves it."
        if self.focused is not None:
            return "Pick a part in the Wheel, or press its number."
        return "Click a cell, or drag a part from Parts onto the board."

    def _refuse(self, reason: str, cell: Cell | None = None) -> None:
        self.message = reason
        self.flash_cell, self.flash_frames = cell, FLASH_FRAMES
