"""The Board's state and input handling. Mutates the board only through its methods.

One button is held at a time (D-401, D-402, `buttons.py`): Select when no other is. With Select,
a click on an empty cell picks it, and the next ones too; a click on a part picks parts instead,
the first click saying which; a click on a picked one drops it, a click off the zone drops them
all (`picking.py`). With something picked, a lit button acts on it at once, in the order picked,
and Select stays held with the pick kept: a part's button fills the empty cells, the new parts
picked then, or swaps the picked parts for one of its group; Turn turns each part, at each press;
Delete deletes them; Wire chains them, or with one part picked is held to wire from it; Move is
held, and the next click puts the first part picked there, the others keeping their places round
it, refused whole if a cell is taken. With nothing picked, a button is held for the clicks on the
board: a part's places one on each empty cell clicked while one is left, Delete and Turn act on
each part clicked, Lock locks or frees it (D-319), Wire chains the parts clicked, the chain going
on from the last, and Move carries a part clicked to the empty cell clicked next. A press on the
held button puts it down.

Drags (D-402, D-404): a held button acts along a drag on each cell it enters, a part's on each
empty cell, Delete, Turn and Lock once on each part, Wire chaining the parts in the order crossed.
With Select, a drag from an empty cell picks the empty cells it crosses; one from a picked part
moves the pick, one from another part moves it, their wires following while they find a path
(D-011); let go off the body, what was dragged goes (D-085). Right clicks wire whatever is held:
a part right-clicked, then another, wired, the chain going on from it, or a right drag through
them; Esc, a left click, which acts too, or a right click off a part ends the chain. The mouse
wheel over a part turns it 60° a notch, up to the right, the whole pick if it is picked; a
trackpad's small scrolls add up to a notch (`notches.py`, D-405).

Keyboard: the arrows move a cursor from cell to cell and Enter clicks there; the keys press the
buttons: M, L, R, W, Backspace or Delete, K on the sandbox, a part's number. Esc goes back one
step: a wire's chain or a part carried, then the pick, then the held button, then, with nothing
left, it opens Chapters (D-304). The board shows at one size, centred, and
nothing moves the view (D-401).

Undo and Redo (D-027), two buttons, also Ctrl+Z, Ctrl+Shift+Z and Ctrl+Y (Cmd on a Mac): one
step is one gesture, from press to release, so a whole drag goes back at once. Space asks
`main.py` for a run, Tab opens Chapters: the scene sets `request` and `main.py` acts on it. A
part's info disc in Parts opens a box that says what the part does; the next click or key closes
it and does nothing else (D-036). Every refusal flashes the cell and puts the reason in the status
line. At Files' foot, Save/Load: Copy a board puts its text on the clipboard, and Paste a board, a
field, takes one, which Enter puts on the board (D-205, D-206); under it, Erase all (D-321, D-401).
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
    MENU_GROUPS,
    TURNS,
    Drawer,
    EditButton,
    FileButton,
    Layout,
    MainView,
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
from nektoids.editor.notches import RUN, Notches
from nektoids.editor.picking import (
    NOTHING,
    Drag,
    Pick,
    Picked,
    begin,
    clicked,
    extend,
    kept,
    moved,
    of_parts,
    parts,
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
ADD_KEYS = pygame.KMOD_SHIFT | pygame.KMOD_META  # held, a click or a drag adds to the pick
TOOLTIP_FRAMES = 60  # hover this long over a palette button to see its name and key [frames]
KEY_BUTTONS = {key: b for b, key in KEYS.items() if len(key) == 1}  # M, K, L, R, W (D-402)
TOOL_OF = {  # the tool a held button stands for, as a tutorial's step reads it (D-048)
    Button.WIRE: Tool.WIRE,
    Button.MOVE: Tool.MOVE,
    Button.DELETE: Tool.DELETE,
    Button.TURN_LEFT: Tool.TURN_LEFT,
    Button.TURN_RIGHT: Tool.TURN_RIGHT,
}
TURNING = {
    Button.TURN_LEFT: TURNS[Tool.TURN_LEFT],
    Button.TURN_RIGHT: TURNS[Tool.TURN_RIGHT],
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
DELETE_SCANCODES = (
    pygame.KSCAN_BACKSPACE,
    pygame.KSCAN_DELETE,
)  # Delete, as everywhere else
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
        self.held: Button | Kind = Button.SELECT  # the button in hand (D-401, D-402)
        self.pick: Pick = NOTHING  # what Select has picked, in the order clicked (D-402)
        self.cursor: Cell | None = None  # the keyboard's cell: the arrows move it, Enter clicks
        self.source: int | None = None  # Wire held: the part the next one clicked is wired from
        self.lifted: int | None = None  # Move held, nothing picked: the part to carry
        self.press_cell: Cell | None = None  # a part pressed: a click or a drag, told on release
        self.pressed = False  # the left button down: a gesture under way, one step for undo
        self.sweeping = False  # ... with a button held that acts along it (D-404)
        self.swept: set[Cell] = set()  # the cells it has acted on
        self.pick_from: Cell | None = None  # Select pressed on an empty cell: a click or a drag
        self.picked_along = False  # ... which has picked cells along it
        self.drag: Drag | None = None  # ... the path it has made, to be cut back
        self.adding = False  # the add key (Shift or Cmd) down at the press: the pick is added to
        self.group: tuple[int, ...] = ()  # the picked parts a drag moves together
        self.group_from: Cell | None = None  # the cell it was pressed on
        self.group_pick: Pick = NOTHING  # the pick as the drag began
        self.group_offset: Cell = (0, 0)  # how far it has moved them
        self.right: int | None = None  # right clicks' chain: the part the next is wired from
        self.right_down = False  # the right button down: a drag chains the parts crossed
        self.notches = Notches()  # the mouse wheel's scrolls, made turns (D-405)
        self.turning: frozenset[int] = frozenset()  # the parts the wheel has been turning
        self.run_frames = 0  # ... frames left before that run of turns is one step for undo
        self.keyboard = False  # the keyboard drives, until the mouse moves
        self.wins: tuple[WinGroup, ...] = ()  # this session's wins, for Files; main.py's
        self.caption = caption  # the level's title and spec, under the tabs
        self.view = board_view(layout)  # one size, centred, never moved (D-401)
        self.dragging = False  # a part's row held since it was pressed in Parts
        self.moving: int | None = None  # a part being dragged
        self.counted: Kind | None = None  # the part just placed: its count shows on its button
        self.count_frames = 0  # ... this many frames more (D-401)
        self.ghost: tuple[Cell, ...] | Refused | None = None  # Wire: route to the hovered cell
        self.ghost_connects = False  # Wire: the ghost ends on a target it may connect to
        self.ghost_way: tuple[Cell, ...] | None = None  # ... over a part it cannot: the way only
        self.folded: set[str] = set()  # Parts' and Files' groups shown closed
        self.mouse = (0, 0)
        self.pointed: Cell | None = None  # grid cell under the mouse, in the zone or not
        self.hover: Cell | None = None  # the same, if it is in the zone
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

    @property
    def tool(self) -> Tool:
        """The tool the held button stands for, as a tutorial's step reads it (D-048)."""
        return TOOL_OF.get(self.held, Tool.ADD)

    def at_hand(self) -> list[Cell]:
        """The cells of the parts at hand, outlined as the pick is: a wire's chain's last part,
        the right clicks' too, a part Move carries."""
        held = (self.source, self.right, self.lifted)
        ids = [i for i in held if i is not None and i in self.board.nodes]
        return [self.board.nodes[i].cell for i in ids]

    @property
    def in_hand(self) -> Kind | None:
        """The part whose button is held, to place."""
        return self.held if isinstance(self.held, Kind) else None

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
        self.notches.tick()
        if self.run_frames > 0:
            self.run_frames -= 1
            if self.run_frames == 0:  # the wheel's run of turns ends: one step for undo
                self._keep()
        self.frame_update()
        if self.main is MainView.PREVIEW or self.layout.drawer is Drawer.DIAGNOSTIC:
            self._probe_now()
        if self.probe is not None:
            self.probe.see(self.view)  # the board's own scale and place
        if self.main is MainView.PREVIEW:
            for _ in range(TICKS_PER_FRAME):
                self.probe.tick()

    def _tip_target(self, pos: tuple[int, int]) -> object | None:
        """The bar's icons, and the buttons round the board (D-401)."""
        if self.main is MainView.DIAGRAM and contains(self.layout.board_area, pos):
            button = button_at(self.shown_buttons(), self.view.size, self.view.origin, pos)
            if button is not None:
                return button
        return super()._tip_target(pos)

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
        if event.type not in (pygame.MOUSEWHEEL, pygame.MOUSEMOTION):
            self.run_frames = 0  # anything else ends the wheel's run of turns
        if event.type == pygame.MOUSEMOTION:
            self._track(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._track(event.pos)
            self.pressed = True
            self._press(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.pressed = False
            self._release(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self._track(event.pos)
            self._right_press(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 3:
            self.right_down = False
        elif event.type == pygame.MOUSEWHEEL and self._on_map(self.mouse):
            self.probe.turn(event.y * PROBE_TURN)  # up: counter-clockwise
        elif event.type == pygame.MOUSEWHEEL and self.frame_wheel(self.mouse, event.y):
            pass  # the drawer's rows scrolled (D-096)
        elif event.type == pygame.MOUSEWHEEL:
            self._wheel_turn(event)
        elif event.type == pygame.KEYDOWN and self.loading is not None:  # natively (D-206)
            self._field_key(event)
        elif event.type == pygame.KEYDOWN and self.typing is not None:  # a passkey (D-075)
            self.type_key(pygame.key.name(event.key), event.unicode)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if not self._escape():  # nothing left to back out of: the levels (D-304)
                self.toggle_drawer(Drawer.CHAPTERS)
        elif event.type == pygame.KEYDOWN:
            self._key(event)
        if not self.pressed and not self.right_down and self.run_frames == 0:  # D-027
            self._keep()  # between gestures

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
        """The cursor from cell to cell, the mouse's hover with it."""
        left, right, up, _ = ARROWS
        if self.cursor is None or self.cursor not in self.board.cells:
            step = self._start_cell()
        elif key == left:
            step = neighbour(self.cursor, W)
        elif key == right:
            step = neighbour(self.cursor, E)
        else:
            step = vertical_step(self.cursor, -1 if key == up else 1)
        if step in self.board.cells:
            self.cursor = step
            self._track(self._cursor_pos())

    def _enter(self) -> None:
        """The keyboard's click, on the cursor's cell."""
        if self.cursor is None or self.cursor not in self.board.cells:
            self.cursor = self._start_cell()
            self._track(self._cursor_pos())
            return
        self.adding = bool(pygame.key.get_mods() & ADD_KEYS)
        self._click(self.cursor, self._cursor_pos())

    def _start_cell(self) -> Cell:
        if self.hover is not None:
            return self.hover
        return min(self.board.cells, key=lambda cell: hex_distance(cell, (0, 0)))

    def _cursor_pos(self) -> tuple[int, int]:
        x, y = to_pixel(self.cursor, self.view.size, self.view.origin)
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
            self.run_frames = 0  # off the part the wheel turned: its run ends
            self._update_ghost()
        if self.press_cell is not None and pointed != self.press_cell and not self._dragged():
            start = self.press_cell
            picked = self.pick.what is Picked.PARTS and start in self.pick.cells
            if self._picks_along(pointed):
                self.press_cell, self.pick_from = None, start  # a pick of parts along the drag
                self.picked_along, self.drag = False, None
            elif picked and len(self.pick.cells) > 1:
                self._grab_group(start)  # a drag from a picked part: the pick moves (D-404)
            else:
                self._grab(start)  # the press was the start of a drag: a move (D-068)
        on_board = moved_on and pointed in self.board.cells
        if on_board and self.moving is not None:
            self._drag_to(pointed)  # off the body, it waits, to go if let go there (D-085)
        if on_board and self.group:
            self._group_to(pointed)
        if on_board and self.pick_from is not None:
            self._pick_along(pointed)
        if on_board and self.sweeping and pointed not in self.swept:
            self.swept.add(pointed)
            self._sweep(pointed)
        if on_board and self.right_down:
            node = self.board.node_at(pointed)
            if node is not None and node.id != self.right:
                self._right_to(node)  # a right drag chains the parts it crosses

    def _press(self, pos: tuple[int, int]) -> None:
        if self.right is not None:  # a left click ends the right clicks' chain, and acts (D-404)
            self.right = None
            self._update_ghost()
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
        if kind is not None:  # a part's row: held, and dragged, or placed by the next clicks
            if self._hold(kind):
                self.dragging = True
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
                self.pick = clicked(NOTHING, self.board, cell)
            return
        if not contains(self.layout.board_area, pos):
            return
        cell, held = self.hover, self.held
        node = self.board.node_at(cell) if cell is not None else None
        self.adding = bool(pygame.key.get_mods() & ADD_KEYS)
        if node is not None and held in (Button.SELECT, Button.MOVE):
            self.press_cell = cell  # a click, or the start of a drag: the release tells
        elif cell is not None and held is Button.SELECT:
            self.pick_from, self.picked_along, self.drag = cell, False, None  # click or drag
        else:
            self._click(self.pointed, pos)  # the others act as the button goes down
            if cell is not None and held is not Button.SELECT and held is not Button.MOVE:
                self.sweeping, self.swept = True, {cell}  # ... and along a drag (D-404)

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
        self.sweeping, self.swept = False, set()
        if self.pick_from is not None:  # Select on an empty cell: a click, unless a drag picked
            cell, self.pick_from, self.drag = self.pick_from, None, None
            if not self.picked_along:
                self.pick = clicked(self.pick, self.board, cell, self.adding)
            return
        if self.group:  # the pick dragged: let go off the body, it goes (D-085, D-404)
            ids, self.group, self.press_cell = self.group, (), None
            if self.pointed not in self.board.cells:
                self._drop_group(ids)
            return
        if self.press_cell is not None:  # a press on a part: a drag moved it, or it was a click
            cell, self.press_cell = self.press_cell, None
            if self.moving is not None:
                node = self.board.nodes.get(self.moving)
                self.moving = None
                if node is not None and self.pointed not in self.board.cells:
                    self._drop_off(node)  # let go off the body (D-085)
                elif node is not None:  # a picked part keeps its place in the pick
                    swapped = tuple(node.cell if c == cell else c for c in self.pick.cells)
                    self.pick = kept(Pick(self.pick.what, swapped), self.board)
            else:
                self._click(cell, pos)
            return
        self.moving = None
        if not self.dragging:
            return
        self.dragging = False
        if self.pointed is not None and self.in_hand is not None:  # a part's row let go here
            self._place_held(self.pointed)

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
            self.pick = NOTHING

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
        self.pick, self.said = NOTHING, said
        self._keep()  # the board it replaced goes to Undo

    def _allowed(self, action: Action, cell: Cell | None = None) -> bool:
        """Whether the tutorial's step lets `action` through (D-048); if not, say so."""
        if self.gate is None or self.gate(action):
            return True
        self._refuse(REFUSAL, cell)
        return False

    def _drop_gesture(self) -> None:
        """Whatever was under way, a part dragged, a wire's chain or a part carried, given up."""
        self.dragging, self.sweeping, self.pick_from, self.group = False, False, None, ()
        self.drag = None
        self.source, self.right, self.lifted, self.ghost = None, None, None, None
        self.moving, self.press_cell = None, None

    def _cancel(self) -> None:
        self._drop_gesture()
        self.message = ""

    # The buttons (D-401, D-402)

    def shown_buttons(self) -> tuple[Button | Kind, ...]:
        return shown(self.layout.kinds, self.layout.editor)

    def button_states(self) -> dict[Button | Kind, State]:
        history = self.history
        return states(
            self.board,
            self.shown_buttons(),
            self.held,
            self.pick,
            history.can_undo or self.board.snapshot() != self._kept,
            history.can_redo,
            self.layout.kinds,
        )

    def _press_button(self, button: Button | Kind) -> None:
        """A button pressed, clicked or by its key. Undo and Redo act at once; the held button
        put down, Select is held; greyed, it says why not; lit, it acts on what is picked;
        else it is held, for the clicks on the board, the pick dropped."""
        if button in (Button.UNDO, Button.REDO):
            self._edit(EditButton.UNDO if button is Button.UNDO else EditButton.REDO)
            return
        if not self._editing():
            return
        look = self.button_states().get(button)
        if button is Button.SELECT or look is State.CHOSEN:
            self._hold(Button.SELECT)
        elif look is State.GREYED:
            self._refuse(self._why_not(button), None)
        elif look is State.LIT and self.pick:
            self._on_pick(button)
        else:
            self._hold(button)

    def _hold(self, button: Button | Kind) -> bool:
        """`button` held for the clicks on the board (D-402), if the tutorial lets it: the pick
        dropped, but by Select, which keeps it; False if refused."""
        if isinstance(button, Kind):
            if not self._allowed(Action("pick", kind=button)):
                return False
            if self.board.remaining(button) == 0:
                self._refuse("none left", None)
                return False
        elif button in TOOL_OF and not self._allowed(Action("tool", tool=TOOL_OF[button])):
            return False
        self._cancel()
        if button is not Button.SELECT:
            self.pick = NOTHING
        self.held = button
        self._update_ghost()
        return True

    def _why_not(self, button: Button | Kind) -> str:
        """What a greyed button says, pressed."""
        if isinstance(button, Kind):
            if self.board.remaining(button) == 0:
                return "none left"
            return "it may become only a part of its group, still left"
        if self.pick.what is Picked.CELLS:
            return "empty cells picked: a part's button fills them"
        if button in TURNING:
            return "nothing here turns: only an eye or a thruster, not the level's"
        if button is Button.WIRE:
            return "a wire runs from a part to another"
        if button is Button.LOCK:
            return "no part to lock"
        return "placed by the level" if self.pick else "no part to " + button.value

    def _on_pick(self, button: Button | Kind) -> None:
        """A lit button on what is picked, at once, in the order picked (D-402); Select stays
        held, the pick kept, or the parts just placed picked."""
        picked = parts(self.pick, self.board)
        loose = [n for n in picked if not n.locked]
        if isinstance(button, Kind) and self.pick.what is Picked.CELLS:
            self._fill(button)
        elif isinstance(button, Kind):
            for node in picked:
                if button in swaps(self.board, node.cell, self.layout.kinds):
                    self._swap(node, button)
        elif button in TURNING:
            back = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
            for node in loose:
                if node.facing is not None:
                    self._turn(node.cell, -TURNING[button] if back else TURNING[button])
        elif button is Button.DELETE:
            for node in loose:
                self._delete_part(node)
        elif button is Button.LOCK:
            locking = any(not n.locked for n in picked)  # all the level's, or all freed
            for node in picked:
                if node.locked != locking:
                    self._lock(node.cell)
        elif button is Button.WIRE and len(picked) == 1:  # held, to wire from it (D-402)
            if self._hold(Button.WIRE):
                self.source = picked[0].id
                self._update_ghost()
            return
        elif button is Button.WIRE:  # a chain, in the order picked
            for source, target in zip(picked, picked[1:], strict=False):
                if not self._try_wire(source, target, target.cell):
                    break
        elif button is Button.MOVE:  # held: the next click says where the first one goes
            if self._allowed(Action("tool", tool=Tool.MOVE)):
                self.held = Button.MOVE
            return
        self.pick = kept(self.pick, self.board)

    def _fill(self, kind: Kind) -> None:
        """A part's button on empty cells picked: one in each, in the order picked, the last
        left empty if the parts run out; the parts placed are picked then (D-402)."""
        placed = []
        for cell in self.pick.cells:
            if self.board.remaining(kind) == 0:
                break
            if self._place(kind, cell):
                placed.append(cell)
        if placed:
            self.pick = of_parts(placed)

    # Picking and clicking (D-402)

    def _click(self, cell: Cell | None, pos: tuple[int, int]) -> None:
        """A click on the board, or Enter on the cursor: what the held button does there."""
        held = self.held
        if held is Button.SELECT:
            self.pick = clicked(self.pick, self.board, cell, self.adding)
        elif isinstance(held, Kind):
            self._place_held(cell)
        elif held is Button.DELETE:
            self._erase(cell, pos)
        elif held is Button.LOCK:
            self._lock(cell)
        elif held in TURNING:
            back = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
            node = self.board.node_at(cell) if cell is not None else None
            if node is None:
                self._refuse("click an eye or a thruster", cell)
            else:
                self._turn(cell, -TURNING[held] if back else TURNING[held])
        elif held is Button.WIRE:
            self._wire_click(cell)
        elif held is Button.MOVE:
            self._move_click(cell)

    def _place_held(self, cell: Cell | None) -> None:
        """The part held placed on `cell`; it stays held while one of its kind is left, then
        Select is (D-402)."""
        kind = self.in_hand
        if kind is None:
            return
        if cell is None or cell not in self.board.cells:
            self._refuse("outside the zone", cell)
            return
        self._place(kind, cell)
        if self.board.remaining(kind) == 0:
            self.held = Button.SELECT

    def _wire_click(self, cell: Cell | None) -> None:
        """Wire held: a part clicked starts the chain, the next is wired to it, and the chain
        goes on from there (D-402); an empty cell ends it."""
        node = self.board.node_at(cell) if cell is not None else None
        source = self.board.nodes.get(self.source) if self.source is not None else None
        if node is None:
            if source is not None:
                self._refuse("a wire runs from a part to a part", cell)
            self.source = None
        elif source is None or source.id == node.id:
            self.source = node.id
        elif self._try_wire(source, node, cell):
            self.source = node.id  # on from the part just wired to
        self._update_ghost()

    def _move_click(self, cell: Cell | None) -> None:
        """Move held. Parts picked: the first one goes to the empty cell clicked, the others
        keeping their places round it, or none if a cell is taken (D-402); Select is held
        again, the pick kept. Nothing picked: a part clicked is lifted, and goes to the empty
        cell clicked next."""
        if cell is None or cell not in self.board.cells:
            self._refuse("outside the zone", cell)
            return
        picked = parts(self.pick, self.board)
        if picked:
            first = picked[0].cell
            offset = (cell[0] - first[0], cell[1] - first[1])
            if not all(self._allowed(Action("move", cell=n.cell), n.cell) for n in picked):
                return
            refused = self.board.move_group([n.id for n in picked], offset)
            if refused is not None:
                self._refuse(refused.reason, self._in_the_way(picked, offset) or cell)
                return
            self.pick, self.held, self.message = moved(self.pick, offset), Button.SELECT, ""
            return
        node = self.board.node_at(cell)
        lifted = self.board.nodes.get(self.lifted) if self.lifted is not None else None
        if node is not None:
            if node.locked:
                self._refuse("placed by the level", cell)
            elif self._allowed(Action("move", cell=cell), cell):
                self.lifted = node.id
        elif lifted is None:
            self._refuse("click the part to move first", cell)
        elif self._move_to(lifted, cell):
            self.lifted = None

    def _in_the_way(self, picked: list[Node], offset: Cell) -> Cell | None:
        """The first cell a group moved by `offset` would land on that it may not: off the zone,
        or holding a part that stays."""
        ids = {n.id for n in picked}
        for node in picked:
            cell = (node.cell[0] + offset[0], node.cell[1] + offset[1])
            other = self.board.node_at(cell)
            if cell not in self.board.cells or (other is not None and other.id not in ids):
                return cell
        return None

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
        self.pick = kept(self.pick, self.board)

    # On the board

    def _place(self, kind: Kind, cell: Cell) -> bool:
        """`kind` placed on `cell`, facing its default way, its count shown a moment (D-401);
        False, with the reason, if not."""
        if not self._allowed(Action("pick", kind=kind)):
            return False
        if not self._allowed(Action("place", kind=kind, cell=cell), cell):
            return False
        result = self.board.place(kind, cell)
        if isinstance(result, Refused):
            self._refuse(result.reason, cell)
            return False
        self.message = ""
        self.counted, self.count_frames = kind, COUNT_FRAMES
        return True

    def _turn(self, cell: Cell, steps: int) -> None:
        """Turn the part on `cell` by `steps` x 60° (counter-clockwise if positive)."""
        node = self.board.node_at(cell)
        if node is None:
            self._refuse("click an eye or a thruster", cell)
            return
        if not self._allowed(Action("turn", cell=cell), cell):
            return
        result = self.board.rotate(node.id, steps)
        if isinstance(result, Refused):
            self._refuse(result.reason, cell)
        else:
            self.message = ""

    def _swap(self, node: Node, kind: Kind) -> None:
        """`node` swapped for one of `kind`, in its place (D-068); the wires it cannot take are
        said in the status line."""
        result = self.board.replace(node.id, kind)
        if isinstance(result, Refused):
            self._refuse(result.reason, node.cell)
            return
        _, lost = result
        if lost:
            self._refuse(f"{lost} wire{'s' if lost > 1 else ''} could not follow", node.cell)
        else:
            self.message = ""

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
        """Whether what is dragged, a part or the pick, is off the body, the zone's cells, on the
        drawer or the bar too, where letting it go deletes it, if the tutorial lets it (D-085)."""
        ids = self.group or ((self.moving,) if self.moving is not None else ())
        nodes = [self.board.nodes[i] for i in ids if i in self.board.nodes]
        if not nodes or self.pointed in self.board.cells:
            return False
        return self.gate is None or all(self.gate(Action("delete", cell=n.cell)) for n in nodes)

    def _drop_off(self, node: Node) -> None:
        """A part let go off the body (D-085): it goes, with its wires, out of the pick too; if
        the tutorial's step does not let it, it stays where it waited, the reason said."""
        if not self._allowed(Action("delete", cell=node.cell), node.cell):
            return
        self.board.remove_node(node.id)  # never locked: a locked part is not grabbed
        self.message = ""
        self.pick = kept(self.pick, self.board)

    def _drag_to(self, cell: Cell) -> None:
        """One step of a move: the part stays at the last cell its wires could follow it to."""
        result = self._step(self.moving, cell)
        if isinstance(result, Refused):
            self._refuse(result.reason, cell)
        else:
            self.message = ""

    def _dragged(self) -> bool:
        """Whether a drag already carries a part or the pick."""
        return self.moving is not None or bool(self.group)

    def _grab_group(self, cell: Cell) -> None:
        """A drag from a picked part: the pick moves with the mouse, together (D-404), if none
        is the level's and the tutorial lets each go."""
        picked = parts(self.pick, self.board)
        if any(n.locked for n in picked):
            self._refuse("placed by the level", cell)
            self.press_cell = None
            return
        if not all(self._allowed(Action("move", cell=n.cell), n.cell) for n in picked):
            self.press_cell = None
            return
        self.group, self.group_from = tuple(n.id for n in picked), cell
        self.group_pick, self.group_offset, self.message = self.pick, (0, 0), ""
        self._grabbed = self.board.snapshot()

    def _group_to(self, cell: Cell) -> None:
        """One step of the pick's move: worked out from the board as it was picked up, so a wire
        it passed over goes back (D-086); refused, it stays where it last could go."""
        offset = (cell[0] - self.group_from[0], cell[1] - self.group_from[1])
        if offset == self.group_offset:
            return
        before = self.board.snapshot()
        self.board.restore(self._grabbed)
        refused = self.board.move_group(self.group, offset)
        if refused is not None:
            self.board.restore(before)
            picked = [self.board.nodes[i] for i in self.group]
            way = (offset[0] - self.group_offset[0], offset[1] - self.group_offset[1])
            self._refuse(refused.reason, self._in_the_way(picked, way) or cell)
            return
        self.group_offset, self.message = offset, ""
        self.pick = moved(self.group_pick, offset)

    def _drop_group(self, ids: tuple[int, ...]) -> None:
        """The pick let go off the body: it goes, each part with its wires (D-085, D-404)."""
        for i in ids:
            node = self.board.nodes.get(i)
            if node is not None and self._allowed(Action("delete", cell=node.cell), node.cell):
                self.board.remove_node(i)
        self.pick, self.message = kept(self.pick, self.board), ""

    def _pick_along(self, cell: Cell) -> None:
        """A drag with Select: the cells it crosses picked, those of the kind it started on,
        and going back over its path cuts the path back (D-404)."""
        if self.drag is None:
            self.picked_along = True
            self.drag = begin(self.pick, self.board, self.pick_from, self.adding)
        self.drag = extend(self.drag, self.board, cell)
        self.pick = self.drag.pick

    def _picks_along(self, cell: Cell | None) -> bool:
        """Whether a drag from a part, its first step into `cell`, picks parts rather than moves
        the part: it does if `cell` holds a part not picked; into an empty cell or a picked part,
        it moves (D-404)."""
        if self.held is not Button.SELECT or cell is None or cell not in self.board.cells:
            return False
        picked = self.pick.cells if self.pick.what is Picked.PARTS else ()
        return self.board.node_at(cell) is not None and cell not in picked

    def _sweep(self, cell: Cell) -> None:
        """The held button along a drag, on a cell it enters (D-404): a part's on an empty cell,
        Delete, Turn and Lock on a part, once each; Wire on a part, the chain going on."""
        node, held = self.board.node_at(cell), self.held
        x, y = to_pixel(cell, self.view.size, self.view.origin)
        if isinstance(held, Kind) and node is None and self.board.remaining(held) != 0:
            self._place_held(cell)
        elif node is not None and (held in TURNING or held in (Button.DELETE, Button.LOCK)):
            self._click(cell, (round(x), round(y)))
        elif node is not None and held is Button.WIRE:
            self._wire_click(cell)

    def _wheel_turn(self, event: pygame.event.Event) -> None:
        """The mouse wheel over a part turns it 60° a notch, up to the right; over a picked part,
        each picked part that turns (D-402, D-405). A run of turns on the same parts is one step
        for undo, kept once the wheel has rested RUN frames."""
        node = self.board.node_at(self.hover) if self.hover is not None else None
        if node is None or self.main is not MainView.DIAGRAM:
            return
        up = getattr(event, "precise_y", event.y)  # a trackpad's scrolls are small
        if getattr(event, "flipped", False):  # natural scrolling: the wheel's own way back
            up = -up
        steps = self.notches.feed(up)
        if steps == 0:
            return
        picked = parts(self.pick, self.board)
        targets = picked if node.id in {n.id for n in picked} else [node]
        turning = [n for n in targets if n.facing is not None and not n.locked]
        if not turning:
            self._refuse(
                "nothing here turns: only an eye or a thruster, not the level's", node.cell
            )
            return
        ids = frozenset(n.id for n in turning)
        if ids != self.turning:  # other parts: the run before is a step of its own
            self._keep()
            self.turning = ids
        for n in turning:
            self._turn(n.cell, -steps)  # up: to the right, clockwise
        self.run_frames = RUN

    def _right_press(self, pos: tuple[int, int]) -> None:
        """A right click wires (D-402, D-404): on a part, the chain's first, or the next, wired
        to the one before; off a part, the chain ends. The held button stays as it is."""
        if self.main is not MainView.DIAGRAM or not contains(self.layout.board_area, pos):
            return
        node = self.board.node_at(self.hover) if self.hover is not None else None
        self.right_down = node is not None
        if node is None:
            self.right = None
            self._update_ghost()
        else:
            self._right_to(node)

    def _right_to(self, node: Node) -> None:
        """The right clicks' chain on to `node`: wired from the part before, if there is one."""
        source = self.board.nodes.get(self.right) if self.right is not None else None
        if source is None or source.id == node.id or self._try_wire(source, node, node.cell):
            self.right = node.id
        self._update_ghost()

    def doomed(self) -> tuple[frozenset[int], list[Wire]]:
        """What a deletion would remove, darkened before it happens: with Delete held, what is
        under the mouse, or under the cursor; with parts picked, those Delete would take, while
        the mouse is on its button (D-401); a part dragged off the body (D-085)."""
        if self._dropping():
            ids = frozenset(self.group or (self.moving,))
            return ids, [w for w in self.board.wires if w.source in ids or w.target in ids]
        if self.held is Button.DELETE:
            if self.keyboard and self.cursor is not None:
                node_id, wires = self._under(self.cursor, self._cursor_pos())
            elif contains(self.layout.board_area, self.mouse):
                node_id, wires = self._under(self.hover, self.mouse)
            else:
                return frozenset(), []
            return frozenset() if node_id is None else frozenset({node_id}), wires
        size, origin = self.view.size, self.view.origin
        on_delete = button_at(self.shown_buttons(), size, origin, self.mouse) is Button.DELETE
        if self.keyboard or not on_delete:
            return frozenset(), []
        ids = frozenset(n.id for n in parts(self.pick, self.board) if not n.locked)
        return ids, [w for w in self.board.wires if w.source in ids or w.target in ids]

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
        If the board was edited otherwise since the last step, from the board as it is now.
        Refused, the board stays as it was."""
        before = self.board.snapshot()
        if self.moving is not None:
            if self._grabbed is not None and before == self._landed:
                self.board.restore(self._grabbed)
            else:
                self._grabbed = before  # edited since: the move goes on from here
        result = self.board.move_node(node_id, cell)
        if isinstance(result, Refused):
            self.board.restore(before)
        self._landed = self.board.snapshot()
        return result

    # Helpers

    def _update_ghost(self) -> None:
        """Where a wire from the chain's part would run to the hovered cell, and whether it may
        end there: over an empty cell it only shows the way; over a part it is the real preview,
        where a click would wire (D-068). Over a part it cannot wire to, the way still shows,
        dimmed, as over an empty cell (D-069)."""
        self.ghost, self.ghost_connects, self.ghost_way = None, False, None
        start = self.source if self.held is Button.WIRE else None
        if self.right is not None:  # the right clicks' chain
            start = self.right
        if start is None or self.hover is None or start not in self.board.nodes:
            return
        target, begin = self.board.node_at(self.hover), self.board.nodes[start]
        if begin.kind.emits:
            way = self.board.route(begin.cell, self.hover)
        else:  # a thruster: the way a wire into it would come
            way = self.board.route(self.hover, begin.cell)
        if target is None:
            self.ghost = way
            return
        if target.id == start:
            return
        self.ghost = self.board.preview(*self.board.orient(start, target.id))
        self.ghost_connects = isinstance(self.ghost, tuple)
        if not self.ghost_connects:
            self.ghost_way = way

    def _erase_all(self) -> None:
        """Erase all: every wire and every part but the level's off the board, one step for
        undo, as a board put back is one (D-321); refused with nothing to erase."""
        if not self._allowed(Action("load")):
            return
        self._cancel()
        parts_off, wires = self.board.clear()
        if not parts_off and not wires:
            self._refuse("nothing to erase", None)
            return
        self.pick = kept(self.pick, self.board)
        s = "s" * (parts_off != 1), "s" * (wires != 1)
        self.said = f"Erased: {parts_off} part{s[0]}, {wires} wire{s[1]}."

    def _lock(self, cell: Cell | None) -> None:
        """Lock, clicked on `cell` or on a pick: its part made the level's, fixed and using no
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
        """The part deleted, with its wires."""
        if not self._allowed(Action("delete", cell=node.cell), node.cell):
            return
        result = self.board.remove_node(node.id)
        if isinstance(result, Refused):
            self._refuse(result.reason, node.cell)
            return
        self.message = ""

    def _delete_wire(self, wire: Wire) -> None:
        cell = self.board.nodes[wire.target].cell
        if not self._allowed(Action("delete", cell=cell), cell):
            return
        self.board.remove_wire(wire)
        self.message = ""

    def _erase(self, cell: Cell | None, pos: tuple[int, int]) -> None:
        """Delete held, clicked at `pos` or entered on the cursor: the part on `cell` with its
        wires, or the wire there."""
        node_id, wires = self._under(cell, pos)
        if node_id is not None:
            self._delete_part(self.board.nodes[node_id])
        elif wires:
            self._delete_wire(wires[0])
        elif cell is not None and self.board.node_at(cell) is not None:
            self._refuse("placed by the level", cell)

    def _escape(self) -> bool:
        """Esc: back one step (D-402): a wire's chain, the right clicks' too, or a part carried;
        then the pick; then the held button, Select held again; False if there was nothing left."""
        if self.source is not None or self.lifted is not None or self.right is not None:
            self.source = self.lifted = self.right = None
            self._update_ghost()
        elif self.pick:
            self.pick = NOTHING
        elif self.held is not Button.SELECT:
            self.held = Button.SELECT
            self._cancel()
        else:
            return False
        self.message = ""
        return True

    def hint(self) -> str:
        """What the status line says the player can do now."""
        held, picked = self.held, parts(self.pick, self.board)
        if self.main is MainView.PREVIEW:  # nothing to edit here (D-069)
            return "Drag an eye's knob to set what it reads. Shut Diagnostic to edit."
        if self._dropping():
            return "Let go and what you drag goes, with its wires; back on the body, it stays."
        if self.right is not None:
            return "Right-click the part to wire to; the chain goes on. Esc ends it."
        if held is Button.WIRE:
            if self.source is None:
                return "Click the part a wire starts from. Esc: back."
            return "Click the part to wire to; the chain goes on from it. Esc ends it."
        if held is Button.MOVE and picked:
            return "Click where the first part picked goes; the others keep their places."
        if held is Button.MOVE:
            if self.lifted is None:
                return "Click the part to move, then where it goes. Esc: back."
            return "Click the empty cell it goes to. Esc: back."
        if held is Button.DELETE:
            return "Click a part or a wire to delete it. Esc: back."
        if held is Button.LOCK:
            return "Click a part to lock it, or to free it. Esc: back."
        if held in TURNING:
            return "Click an eye or a thruster to turn it. Esc: back."
        if isinstance(held, Kind):
            return "Click empty cells to place one each, while one is left. Esc: back."
        if self.pick.what is Picked.CELLS:
            return "A part's button, or its number, puts one in each, in the order picked."
        if picked:
            return "The lit buttons act on what is picked. Esc drops it."
        return "Click or drag over cells or parts to pick them, Shift adds; or press a button."

    def _refuse(self, reason: str, cell: Cell | None = None) -> None:
        self.message = reason
        self.flash_cell, self.flash_frames = cell, FLASH_FRAMES
