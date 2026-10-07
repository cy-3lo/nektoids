"""The Board's state and input handling. Mutates the board only through its methods.

The focus (D-068): a click focuses a cell, lit on the board, and the buttons round the board
(D-401, `buttons.py`) light for what they would do there. On a part, Move, Turn, Wire, Delete and
Lock act on it at once, as their keys do, and a part's button swaps it for another of its group;
on an empty cell, a part's button places one there, facing its default way (the focus stands for
what is picked until picking comes, D-402). A click on a part chooses Wire too, so the next click
on another part wires the two, either way round (D-026), and the focus goes to that part. A part
focused without a click, placed or just wired to, wires on only forward, along the signal: a
chain goes on, eye to sum to thruster, but from a thruster a click on an eye only focuses it. A
drag from a part moves it, its wires following while they find a path (D-011). A click on the
focused cell, or off the zone, drops the focus.

With nothing focused, Delete and Lock are chosen for the clicks on the board: a click removes the
part under it with its wires, or the wire under it, darkened while the mouse is on it; or locks
it, on the sandbox (D-319). A part's button, or its row dragged from Parts, puts that part in
hand, and each click on an empty cell places one while one is left (D-402). Select drops whatever
is in hand.

Keyboard: the arrows move the focus from cell to cell, and Enter clicks there; the keys do what
the buttons do: M, L, R, W, Backspace or Delete, K on the sandbox, a part's number, Esc for
Select. After W the arrows go to the part to wire to and Enter wires it; after M they carry the
part and Enter puts it down. Esc, or a right click, goes back one step. The board shows at one
size, centred, and nothing moves the view (D-401).

Undo and Redo (D-027), two buttons, also Ctrl+Z, Ctrl+Shift+Z and Ctrl+Y (Cmd on a Mac): one
step is one gesture, from press to release, so a whole drag goes back
at once. Space asks `main.py` for a run, Tab opens Chapters: the scene sets `request` and
`main.py` acts on it. A part's info disc in Parts opens a box that says what the part does; the
next click or key closes it and does nothing else (D-036). Every refusal flashes the cell and
puts the reason in the status line. At Files' foot, Save/Load: Copy a board puts its text on the
clipboard, and Paste a board, a field, takes one, which Enter puts on the board (D-205, D-206);
under it, Erase all (D-321, D-401).
"""

from __future__ import annotations

import math
from dataclasses import replace

import pygame

from nektoids.editor import clipboard
from nektoids.editor.boardfield import board_field, load
from nektoids.editor.buttons import (
    COUNT_FRAMES,
    KEYS,
    Button,
    State,
    button_at,
    shown,
    states,
    swaps,
)
from nektoids.editor.devdrive import TICKS_PER_FRAME
from nektoids.editor.frame import Frame
from nektoids.editor.geometry import nearest_wire
from nektoids.editor.history import History
from nektoids.editor.layout import (
    DIAGNOSTIC_MAP,
    KEY_ALIASES,
    LOCK_KEY,
    MENU_GROUPS,
    TURNS,
    Drawer,
    EditButton,
    FileButton,
    Layout,
    MainView,
    Mode,
    Tool,
    WinRow,
    board_field_at,
    board_view,
    cell_at,
    contains,
    drawer_key,
    file_button_at,
    group_at,
    main_view_for,
    make_layout,
    menu_item_at,
    win_row_at,
)
from nektoids.editor.probe import Probe, level_view
from nektoids.editor.router import WinGroup
from nektoids.editor.settings import Settings
from nektoids.editor.textfield import TextField
from nektoids.editor.tutorial import REFUSAL, Action
from nektoids.graph import boardtext
from nektoids.graph.board import Board, BoardState, Kind, Node, Refused, Wire
from nektoids.graph.hexgrid import (
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
TOOLTIP_FRAMES = 60  # hover this long over a palette button to see its name and key [frames]
KEY_BUTTONS = {key: b for b, key in KEYS.items() if len(key) == 1}  # M, K, L, R, W (D-402)
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


class BoardScene(Frame):
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
        self.guide_cells: frozenset[Cell] = frozenset()  # a tutorial step's cells; main.py's
        self.focused: Cell | None = None  # the cell clicked, the keyboard's too (D-068)
        self.press_cell: Cell | None = None  # a part pressed: a click or a drag, told on release
        self.drawing = False  # Wire chosen, a drag from a part: it draws a wire (D-072)
        self.keyboard = False  # the keyboard drives, until the mouse moves
        self.wire_chosen = False  # Wire chosen by its button or key, not only at hand
        self.onward = False  # the focus came on to the part just wired to: it wires only forward
        self.wins: tuple[WinGroup, ...] = ()  # this session's wins, for Files; main.py's
        self.caption = caption  # the level's title and spec, under the tabs
        self.view = board_view(layout)  # one size, centred, never moved (D-401)
        self.mode = Mode.WRITE  # what a click on the board does: Write, Delete, Lock (D-319)
        self.tool = Tool.ADD
        self.picked: Kind | None = None  # Add: the menu kind in hand
        self.dragging = False  # Add: mouse held since picking from the menu
        self.source: int | None = None  # Wire: the focused part, wired to the next one clicked
        self.moving: int | None = None  # Move: node id being dragged
        self.selected: int | None = None  # what the turn buttons and keys act on
        self.counted: Kind | None = None  # the part just placed: its count shows on its button
        self.count_frames = 0  # ... this many frames more (D-401)
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
        if self.count_frames > 0:
            self.count_frames -= 1
        self.frame_update()
        if self.main is MainView.PREVIEW or self.layout.drawer is Drawer.DIAGNOSTIC:
            self._probe_now()
        if self.probe is not None:
            self.probe.see(self.view)  # the board's own scale and place
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
        the board otherwise. Diagnostic stays shut while a tutorial step leads, and with no level
        to run the board in."""
        if drawer is Drawer.DIAGNOSTIC:
            if self.level is None:
                self._refuse("there is no level to run the board in")
                return
            if not self._allowed(Action("view")):
                return
        super().open_drawer(drawer)
        view = main_view_for(drawer)
        if view is not self.main:
            self._cancel()
            self.main = view

    def _editing(self) -> bool:
        """Whether the board is on screen to edit; if the Run preview shows, say so (D-069)."""
        if self.main is MainView.PREVIEW:
            self._refuse("the Run preview shows: shut Diagnostic to edit")
            return False
        return True

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
            if self._editing():
                self._arrow(arrow)
        elif event.scancode in ENTER_SCANCODES or event.key in ENTER:
            if self._editing():
                self._enter()
        elif event.scancode == pygame.KSCAN_SPACE:  # LEVEL_KEYS[RUN], on the physical key
            self._ask("run")
        elif event.scancode == pygame.KSCAN_TAB:  # the next tab, or the one before (D-304)
            self.next_tab(bool(event.mod & pygame.KMOD_SHIFT))
        elif event.scancode in DELETE_SCANCODES:  # Delete's key, on the physical key
            self._press_button(Button.DELETE)
        elif event.scancode in DIGIT_SCANCODES + KEYPAD_SCANCODES:
            self._digit((DIGIT_SCANCODES + KEYPAD_SCANCODES).index(event.scancode) % 9)
        elif self._turns_probe(event.unicode):
            sign = 1.0 if event.unicode.upper() == KEYS[Button.TURN_LEFT] else -1.0
            self.probe.turn(sign * PROBE_TURN)
        else:
            self._shortcut(event.unicode)

    def _arrow(self, key: int) -> None:
        """From cell to cell, the focus with them, carrying a part being moved."""
        left, right, up, _ = ARROWS
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
        elif self.tool is Tool.WIRE and self.source is not None and self.wire_chosen:
            self.focused = step  # wiring by keyboard: the focus goes to the part to wire to
        else:
            self._focus_key(step)
        self._track(self._focus_pos())

    def _enter(self) -> None:
        """The keyboard's click on the focused cell: what Delete or Lock does there; a part in
        hand placed there; a part carried put down; while wiring, the wire made to the part the
        focus is on."""
        if self.focused is None:
            self._focus_key(self._start_cell())
            return
        if self.mode is Mode.DELETE:
            self._erase(self.focused, self._focus_pos())
            return
        if self.mode is Mode.LOCK:
            self._lock(self.focused)
            return
        if self.carrying:
            self.carrying, self.tool = False, Tool.ADD
            return
        node = self._focused_node()
        if self.picked is not None:
            self._add(self.focused)
            return
        if self.tool is Tool.WIRE and self.wire_chosen and self.source is not None:
            source = self.board.nodes.get(self.source)
            if node is None or source is None:
                self._refuse("a wire runs from a part to a part", self.focused)
            elif node.id == source.id:
                self._refuse("a part is not wired to itself", self.focused)
            elif self._try_wire(source, node, node.cell):
                self._focus_key(node.cell)  # on to the part wired to
                return
            self._focus_key(self.focused)  # the attempt ends: Wire goes, the cursor stays

    def _start_cell(self) -> Cell:
        if self.hover is not None:
            return self.hover
        return min(self.board.cells, key=lambda cell: hex_distance(cell, (0, 0)))

    def _focus_pos(self) -> tuple[int, int]:
        x, y = to_pixel(self.focused, self.view.size, self.view.origin)
        return (round(x), round(y))

    def _digit(self, k: int) -> None:
        """A number: that part's button, among the parts the level hands out (D-402)."""
        kinds = [kind for _, group in MENU_GROUPS for kind in group if kind in self.layout.kinds]
        if k < len(kinds):
            self._press_button(kinds[k])

    def _shortcut(self, typed: str) -> None:
        key = KEY_ALIASES.get(typed, typed.upper())
        drawer = drawer_key(self.layout.env, key)
        if self.start_passkey(key):  # P in Chapters: a passkey, not Parts (D-075)
            pass
        elif drawer is not None:  # not refused in the preview: the way out of it (D-069)
            self.toggle_drawer(drawer)
        elif key == LOCK_KEY and self.layout.editor and self.mode is Mode.LOCK:
            self._set_mode(Mode.WRITE)  # K again: Lock put down
        elif key in KEY_BUTTONS and KEY_BUTTONS[key] in self.shown_buttons():
            self._press_button(KEY_BUTTONS[key])

    # Mouse

    def _track(self, pos: tuple[int, int]) -> None:
        self.mouse = pos
        self.frame_track(pos)
        if self.probing and self.probe is not None:
            self._probe_to(pos)
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
        filed = file_button_at(self.layout, pos)
        if filed is FileButton.ERASE:  # Erase all, under the field (D-321, D-401)
            self._erase_all()
            return
        if filed is not None:
            self._save()
            return
        if self._on_map(pos):
            self.probing = True
            self._probe_to(pos)
            return
        won = win_row_at(self.layout, pos)
        if won is not None:
            self._put_back(won)
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
        if self.main is MainView.DIAGRAM:  # the buttons round the board (D-401)
            button = button_at(self.shown_buttons(), self.view.size, self.view.origin, pos)
            if button is not None and contains(self.layout.board_area, pos):
                self._press_button(button)
                return
        if self.main is MainView.PREVIEW:  # the board runs here: a part clicked, to edit it
            cell = cell_at(self.layout, self.view, pos)
            if cell is not None and self.board.node_at(cell) is not None:  # D-339
                self.open_drawer(Drawer.PARTS)  # the board back, its buttons round it
                self._focus(cell)
            return
        if not contains(self.layout.board_area, pos):
            return
        if self.mode is Mode.DELETE:
            self._erase(self.hover, pos)
            return
        if self.mode is Mode.LOCK:
            self._lock(self.hover)
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
        turns = typed.upper() in (KEYS[Button.TURN_LEFT], KEYS[Button.TURN_RIGHT])
        shown = self.main is MainView.PREVIEW and self.layout.drawer is Drawer.DIAGNOSTIC
        return turns and shown and self.probe is not None

    def _release(self, pos: tuple[int, int]) -> None:
        if self.field_pressed:
            self.field_pressed = False
            if board_field_at(self.layout, pos):
                self._open_field()
        self.probing = False
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
        """The board area changed: the board stays centred in it, and the Run preview fits its new
        room."""
        self.view = board_view(after)
        if self.probe is not None:
            self.probe.see(self.view)

    def _relayout(self, drawer: Drawer | None) -> Layout:
        """The layout with `drawer` open, the same parts handed out, chapters, wins, hints and
        tabs."""
        return make_layout(
            drawer,
            self._folded(drawer, self.folded),
            self.layout.kinds,
            self.layout.chapters,
            files=tuple((group.title, len(group.wins)) for group in self.wins),
            scroll=self.scrolls.get(drawer, 0),
            editor=self.layout.editor,
            **self._hint_layout(),
        )

    def revise(self, level: Level, caption: tuple[str, str]) -> None:
        """The level made again in the Editor (D-301): the caption follows, and the Run preview's
        probe is made again on its plane, where it stood. Handed out anew, the board's size or
        its parts (D-315), Parts shows what it now hands out, and undo starts afresh: its steps
        were taken on a board handing out other parts."""
        handed = any(level.board[key] != self.level.board[key] for key in ("zone", "stock"))
        self.level, self.caption = level, caption
        self._probed = None
        if handed:
            kinds = frozenset(kind for kind in Kind if self.board.total(kind) != 0)
            self.layout = self._relayout_on(replace(self.layout, kinds=kinds))
            self.history, self._kept = History(), self.board.snapshot()

    def _relayout_on(self, layout: Layout) -> Layout:
        self.layout = layout
        return self._relayout(layout.drawer)

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
        self.tool = Tool.ADD

    def _cancel(self) -> None:
        self._drop_gesture()
        self.message = ""

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
        """Move, Turn, Wire or Delete on the focused part (D-068, D-401), its button or its key."""
        if not self._editing():
            return
        if tool is not Tool.DELETE:
            self.mode = Mode.WRITE  # writing again
        if not self._allowed(Action("tool", tool=tool)):
            return
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
        """The part picked in Parts placed on `cell`, then focused; it stays picked while one of
        its kind is left, so that clicks repeat it (D-402)."""
        kind = self.picked
        if kind is None:
            self._refuse("pick a part in Parts first", None)
            return
        self._place(kind, cell)
        if self.board.remaining(kind) != 0 and self.board.node_at(cell) is not None:
            self.picked = kind

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
            self.onward = False
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
        mouse is on the Delete button (D-401); a part dragged off the body (D-085)."""
        if self._dropping():
            return self.moving, [w for w in self.board.wires if self.moving in (w.source, w.target)]
        if self.mode is Mode.DELETE:
            if self.keyboard and self.focused is not None:
                return self._under(self.focused, self._focus_pos())
            if not contains(self.layout.board_area, self.mouse):
                return None, []
            return self._under(self.hover, self.mouse)
        size, origin = self.view.size, self.view.origin
        on_delete = button_at(self.shown_buttons(), size, origin, self.mouse) is Button.DELETE
        if self.keyboard or not on_delete or self.focused is None:
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

    # The buttons (D-401)

    def shown_buttons(self) -> tuple[Button | Kind, ...]:
        return shown(self.layout.kinds, self.layout.editor)

    def chosen_button(self) -> Button | Kind:
        """The button in hand: what a click on the board does now."""
        if self.mode is Mode.DELETE:
            return Button.DELETE
        if self.mode is Mode.LOCK:
            return Button.LOCK
        if self.picked is not None:
            return self.picked
        if self.carrying or self.tool is Tool.MOVE:
            return Button.MOVE
        if self.tool is Tool.WIRE and self.wire_chosen:
            return Button.WIRE
        return Button.SELECT

    def button_states(self) -> dict[Button | Kind, State]:
        history = self.history
        return states(
            self.board,
            self.shown_buttons(),
            self.chosen_button(),
            self.focused,
            history.can_undo or self.board.snapshot() != self._kept,
            history.can_redo,
            self.layout.kinds,
        )

    def _press_button(self, button: Button | Kind) -> None:
        """A button clicked. On the focused part, the pick until picking comes (D-402), Move,
        Turn, Wire, Delete and Lock act at once, as their keys do, and a part swaps it; on a
        focused empty cell, a part goes there. Else Delete and Lock are chosen for the clicks on
        the board, and a part is picked for them; Select drops whatever is in hand."""
        node = self._focused_node()
        if button is Button.SELECT:
            self._set_mode(Mode.WRITE)
        elif button in (Button.UNDO, Button.REDO):
            self._edit(EditButton.UNDO if button is Button.UNDO else EditButton.REDO)
        elif button is Button.DELETE and node is None:
            self._set_mode(Mode.DELETE)
        elif button is Button.LOCK:
            if node is not None:
                self._lock(node.cell)
            else:
                self._set_mode(Mode.LOCK)
        elif isinstance(button, Kind):
            self._part_button(button, node)
        else:
            tool = {
                Button.MOVE: Tool.MOVE,
                Button.DELETE: Tool.DELETE,
                Button.TURN_LEFT: Tool.TURN_LEFT,
                Button.TURN_RIGHT: Tool.TURN_RIGHT,
                Button.WIRE: Tool.WIRE,
            }[button]
            if node is None:
                self._refuse("click a part first, then its button", None)
            else:
                self._choose(tool)

    def _part_button(self, kind: Kind, node: Node | None) -> None:
        """A part's button: the focused part swapped for it, if it may become one; on a focused
        empty cell, it placed there; else it picked, for the clicks on the board."""
        cell = self.focused
        if node is not None and kind in swaps(self.board, node.cell, self.layout.kinds):
            self._swap(kind)
        elif node is None and cell is not None and cell in self.board.cells and self._editing():
            self._place(kind, cell)
            if self.board.remaining(kind) != 0 and self.board.node_at(cell) is not None:
                self.picked = kind  # it stays in hand while one is left (D-402)
        else:
            self._pick(kind)
            self.dragging = False  # placed by a click, not by releasing the button

    def _focused_node(self) -> Node | None:
        return self.board.node_at(self.focused) if self.focused is not None else None

    def _focus(self, cell: Cell | None, keys: bool = False, onward: bool = False) -> None:
        """Focus `cell` (None: nothing), the buttons lit for it: on a part clicked, Wire chosen at
        hand, not for the keyboard (`keys`). `onward`: the focus goes on to the part just wired
        to, which wires on only forward (D-068, D-091)."""
        self._drop_gesture()
        self.focused, self.onward = cell, onward
        self.wire_chosen = False
        node = self._focused_node()
        self.selected = None if node is None else node.id
        if node is not None and not keys:  # a click on a part: wiring, from it, at hand
            self.tool, self.source = Tool.WIRE, node.id
        self._update_ghost()

    def _focus_key(self, cell: Cell) -> None:
        """The keyboard's focus moves to `cell`."""
        self._focus(cell, keys=True)

    def _set_mode(self, mode: Mode) -> None:
        """Write, Delete or Lock (D-068, D-319): what a click on the board does; the keyboard's
        focus stays where it is."""
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
        self.message, keys = "", self.keyboard
        self.counted, self.count_frames = kind, COUNT_FRAMES
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
        elif tool is Tool.MOVE:
            if self._allowed(Action("move", cell=node.cell), node.cell):
                self.tool = Tool.MOVE
                if self.keyboard:  # the arrows carry it, Enter puts it down
                    self.carrying = True
                    self._grabbed = self._landed = self.board.snapshot()
        elif tool is Tool.DELETE:
            self._delete_part(node)

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
            self._focus(node.cell, keys=True)
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

    def _erase_all(self) -> None:
        """Erase all: every wire and every part but the level's off the board, one step for
        undo, as a board put back is one (D-321); refused with nothing to erase."""
        if not self._allowed(Action("load")):
            return
        self._cancel()
        parts, wires = self.board.clear()
        if not parts and not wires:
            self._refuse("nothing to erase", None)
            return
        self._focus(None)
        self.said = f"Erased: {parts} part{'s' * (parts != 1)}, {wires} wire{'s' * (wires != 1)}."

    def _lock(self, cell: Cell | None) -> None:
        """Lock, clicked or entered on `cell`: its part made the level's, fixed and using no
        stock, or freed again (D-319); the Editor's level follows the board."""
        node = self.board.node_at(cell) if cell is not None else None
        if node is None:
            self._refuse("click a part to lock it, or to free it", cell)
            return
        refused = self.board.lock(node.id, not node.locked)
        if refused is not None:
            self._refuse(refused.reason, cell)
            return
        self.message = ""

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
        """Esc, or a right click: back one step, from a gesture to the focus, to nothing; False
        if there was nothing to back out of."""
        if self.mode in (Mode.DELETE, Mode.LOCK):
            self.mode = Mode.WRITE
        elif self.carrying or (self.tool is Tool.WIRE and self.wire_chosen and self.source):
            self.carrying, self.tool, self.source = False, Tool.ADD, None
            self._update_ghost()
        elif self.focused is not None or self.picked is not None or self.tool is not Tool.ADD:
            self._focus(None)  # and whatever was in hand
        else:
            return False
        self.message = ""
        return True

    def hint(self) -> str:
        """What the status line says the player can do now."""
        if self.main is MainView.PREVIEW:  # nothing to edit here (D-069)
            return "Drag an eye's knob to set what it reads. Shut Diagnostic to edit."
        if self._dropping():
            return "Let go and the part goes, with its wires; back on the body, it stays."
        if self.carrying:
            return "The arrows carry the part; Enter puts it down."
        if self.tool is Tool.WIRE and self.wire_chosen and self.source is not None:
            return "Click the part to wire to, or the arrows to it then Enter. Esc gives up."
        if self.mode is Mode.DELETE:
            return "Click a part or a wire to delete it. Select or Esc: back."
        if self.mode is Mode.LOCK:
            return "Click a part to lock it, or to free it. Select or Esc: back."
        if self.picked is not None:
            return "Click empty cells to place it, while one is left. Select or Esc: back."
        if self._focused_node() is not None:
            return "Click another part to wire it to; the lit buttons act on it."
        if self.focused is not None:
            return "A part's button, or its number, places it here."
        return "Click a cell or a part, or a button round the board."

    def _refuse(self, reason: str, cell: Cell | None = None) -> None:
        self.message = reason
        self.flash_cell, self.flash_frames = cell, FLASH_FRAMES
