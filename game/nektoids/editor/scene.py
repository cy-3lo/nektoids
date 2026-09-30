"""Editor state and input handling. Mutates the board only through its methods.

Tools:
- Add: drag a component from the menu onto a cell, or pick it and click cells.
- Wire: drag from a source to a target, or click one then the other. The route shows first,
  bright when it may connect.
- Rotate: click an eye or a thruster to turn it 60° clockwise, shift-click to turn it back (D-009).
- Move: drag a component; its wires follow while they find a path (D-011).
- Delete: click a component's shape, or a wire.
- Pan (the hand, next to the zoom buttons): drag the grid to move the view (D-013); the centre
  button brings the central cell back to the middle.

Keyboard: letters pick tools (see the tooltips), digits pick a component, the arrows move a cursor
over the zone, and Enter clicks there; in the Move tool a first Enter grabs, a second drops;
with the hand, the arrows drag the view the way they point, as the mouse would.

Clicking a menu title folds or unfolds its group. Right click or Escape cancels. Every refusal
flashes the cell and puts the reason in the status line.
"""

from __future__ import annotations

import math

import pygame

from nektoids.editor.geometry import nearest_wire
from nektoids.editor.layout import (
    KEY_ALIASES,
    MENU_GROUPS,
    TOOL_KEYS,
    VIEW_KEYS,
    ZOOM_STEP,
    Layout,
    Tool,
    ViewButton,
    cell_at,
    centred_view,
    group_at,
    make_layout,
    menu_item_at,
    palette_target_at,
    pan,
    tool_at,
    view_button_at,
    zoom,
)
from nektoids.graph.board import Board, Kind, Node, Refused, Wire
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

FLASH_FRAMES = 30  # how long a refused cell stays red [frames]
TOOLTIP_FRAMES = 60  # hover this long over a palette button to see its name and key [frames]
KEY_TOOLS = {key: tool for tool, key in TOOL_KEYS.items()}
KEY_VIEWS = {key: button for button, key in VIEW_KEYS.items()}
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
DIGIT_SCANCODES = tuple(getattr(pygame, f"KSCAN_{n}") for n in range(1, 10))
KEYPAD_SCANCODES = tuple(getattr(pygame, f"KSCAN_KP_{n}") for n in range(1, 10))
NODE_HIT = 0.5  # a click this close to a component's centre is on its shape [hex sizes]
WIRE_HIT = 0.2  # a click this close to a drawn wire is on it [hex sizes]


class EditorScene:
    def __init__(self, board: Board, layout: Layout):
        self.board = board
        self.layout = layout
        self.view = centred_view(layout)
        self.tool = Tool.ADD
        self.picked: Kind | None = None  # Add: the menu kind in hand
        self.dragging = False  # Add: mouse held since picking from the menu
        self.source: int | None = None  # Wire: node id of the chosen source
        self.moving: int | None = None  # Move: node id being dragged
        self.panning_from: tuple[int, int] | None = None  # Pan: last mouse position
        self.pressed: int | None = None  # Wire: node under the press, while the button is held
        self.fresh = False  # Wire: that press is what chose the source
        self.ghost: tuple[Cell, ...] | Refused | None = None  # Wire: route to the hovered cell
        self.ghost_connects = False  # Wire: the ghost ends on a target it may connect to
        self.folded: set[str] = set()  # menu groups shown closed
        self.mouse = (0, 0)
        self.pointed: Cell | None = None  # grid cell under the mouse, in the zone or not
        self.hover: Cell | None = None  # the same, if it is in the zone
        self.message = ""  # last refusal, empty once something succeeds
        self.cursor: Cell | None = None  # keyboard cursor, while the keyboard drives
        self.carrying = False  # Move by keyboard: grabbed with Enter, not yet dropped
        self.tip_target: Tool | ViewButton | str | None = None  # palette button under the mouse
        self.tip_frames = 0  # how long it has been there
        self.flash_cell: Cell | None = None
        self.flash_frames = 0

    def update(self) -> None:
        """Once per frame."""
        if self.flash_frames > 0:
            self.flash_frames -= 1
        if self.tip_target is not None:
            self.tip_frames += 1

    @property
    def tooltip(self) -> Tool | ViewButton | str | None:
        """The palette button whose tooltip shows now, if any."""
        return self.tip_target if self.tip_frames >= TOOLTIP_FRAMES else None

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION and self.cursor is not None and event.rel == (0, 0):
            # Browsers re-send the pointer position without any movement (Chrome does, whenever
            # the page redraws under a still mouse): that is not the mouse taking over.
            return
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            self.cursor = None  # the mouse takes over
        if event.type == pygame.MOUSEMOTION:
            self._track(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._track(event.pos)
            self._press(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._release(event.pos)
        elif (event.type == pygame.MOUSEBUTTONDOWN and event.button == 3) or (
            event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
        ):
            self._cancel()
        elif event.type == pygame.KEYDOWN:
            self._key(event)

    # Keyboard

    def _key(self, event: pygame.event.Event) -> None:
        arrow = ARROW_SCANCODES.get(event.scancode) or (event.key if event.key in ARROWS else None)
        if arrow is not None:
            self._arrow(arrow)
        elif event.scancode in ENTER_SCANCODES or event.key in ENTER:
            self._enter()
        elif event.scancode in DIGIT_SCANCODES + KEYPAD_SCANCODES:
            digit = (DIGIT_SCANCODES + KEYPAD_SCANCODES).index(event.scancode) % 9
            kinds = [kind for _, group in MENU_GROUPS for kind in group]
            if digit < len(kinds):
                self._pick(kinds[digit])
                self.dragging = False  # placed with Enter, not by releasing a button
        else:
            self._shortcut(event.unicode)

    def _arrow(self, key: int) -> None:
        """Move the keyboard cursor one cell within the zone; with the hand, drag the view one
        cell the way of the arrow, as the mouse would."""
        left, right, up, _ = ARROWS
        if self.tool is Tool.PAN:
            sx, sy = SQRT3 * self.view.size, 1.5 * self.view.size
            dx, dy = {left: (-sx, 0), right: (sx, 0), up: (0, -sy)}.get(key, (0, sy))
            self.view = pan(self.view, dx, dy)
            return
        if self.cursor is None:
            self.cursor = self._cursor_start()
        else:
            if key == left:
                step = neighbour(self.cursor, W)
            elif key == right:
                step = neighbour(self.cursor, E)
            else:
                step = vertical_step(self.cursor, -1 if key == up else 1)
            if step in self.board.cells:
                self.cursor = step
        self._track(self._cursor_pos())

    def _enter(self) -> None:
        """A click at the keyboard cursor; in the Move tool, grab on one Enter, drop on the next."""
        if self.cursor is None:
            self.cursor = self._cursor_start()
            self._track(self._cursor_pos())
            return
        pos = self._cursor_pos()
        if self.tool is Tool.MOVE and self.carrying:
            self._release(pos)
            self.carrying = False
            return
        self._press(pos)
        if self.tool is Tool.MOVE:
            self.carrying = self.moving is not None
        else:
            self._release(pos)

    def _cursor_start(self) -> Cell:
        if self.hover is not None:
            return self.hover
        return min(self.board.cells, key=lambda cell: hex_distance(cell, (0, 0)))

    def _cursor_pos(self) -> tuple[int, int]:
        x, y = to_pixel(self.cursor, self.view.size, self.view.origin)
        return (round(x), round(y))

    def _shortcut(self, typed: str) -> None:
        key = KEY_ALIASES.get(typed, typed.upper())
        if key in KEY_TOOLS:
            self._cancel()
            self.tool = KEY_TOOLS[key]
        elif key in KEY_VIEWS:
            self._view_button(KEY_VIEWS[key])

    # Mouse

    def _track(self, pos: tuple[int, int]) -> None:
        if self.panning_from is not None:
            dx, dy = pos[0] - self.panning_from[0], pos[1] - self.panning_from[1]
            self.view, self.panning_from = pan(self.view, dx, dy), pos
        self.mouse = pos
        target = palette_target_at(self.layout, pos)
        if target != self.tip_target:
            self.tip_target, self.tip_frames = target, 0
        pointed = cell_at(self.layout, self.view, pos)
        moved_on = pointed != self.pointed
        self.pointed = pointed
        hover = pointed if pointed in self.board.cells else None
        if hover != self.hover:
            self.hover = hover
            self._update_ghost()
        if moved_on and self.moving is not None and pointed is not None:
            self._drag_to(pointed)

    def _press(self, pos: tuple[int, int]) -> None:
        tool = tool_at(self.layout, pos)
        if tool is not None:
            self._cancel()
            self.tool = tool
            return
        button = view_button_at(self.layout, pos)
        if button is not None:
            self._view_button(button)
            return
        title = group_at(self.layout, pos)
        if title is not None:
            self.folded ^= {title}
            self.layout = make_layout(frozenset(self.folded))
            return
        kind = menu_item_at(self.layout, pos)
        if kind is not None:
            self._pick(kind)
            return
        if self.pointed is None:
            return
        if self.tool is Tool.PAN:
            self.panning_from = pos
        elif self.tool is Tool.ADD:
            self._add(self.pointed)  # the zone refuses cells outside it, with a reason
        elif self.hover is None:
            return
        elif self.tool is Tool.WIRE:
            self._wire(self.hover)
        elif self.tool is Tool.ROTATE:
            self._rotate(self.hover, back=bool(pygame.key.get_mods() & pygame.KMOD_SHIFT))
        elif self.tool is Tool.MOVE:
            self._grab(self.hover)
        else:
            self._delete(self.hover, pos)

    def _release(self, pos: tuple[int, int]) -> None:
        self.moving, self.panning_from = None, None
        if self.pressed is not None:
            self._end_wiring()
        if not self.dragging:
            return
        self.dragging = False
        if self.pointed is not None:
            self._add(self.pointed)

    def _cancel(self) -> None:
        self.picked, self.dragging = None, False
        self.source, self.ghost, self.pressed = None, None, None
        self.moving, self.carrying = None, False
        self.message = ""

    # View

    def _view_button(self, button: ViewButton) -> None:
        if button is ViewButton.PAN:
            self._cancel()
            self.tool = Tool.PAN
            return
        if button is ViewButton.CENTRE:
            self.view = centred_view(self.layout, self.view.size)
            return
        x, y, w, h = self.layout.board_area
        factor = ZOOM_STEP if button is ViewButton.ZOOM_IN else 1.0 / ZOOM_STEP
        self.view = zoom(self.view, factor, (x + w / 2, y + h / 2))

    # Tools

    def _pick(self, kind: Kind) -> None:
        self._cancel()
        self.tool = Tool.ADD
        if self.board.remaining(kind) == 0:
            self._refuse("none left", None)
            return
        self.picked, self.dragging = kind, True

    def _add(self, cell: Cell) -> None:
        if self.picked is None:
            self._refuse("pick a component in the menu first", None)
            return
        result = self.board.place(self.picked, cell)
        if isinstance(result, Refused):
            self._refuse(result.reason, cell)
            return
        self.message = ""
        if self.board.remaining(self.picked) == 0:
            self.picked = None

    def _wire(self, cell: Cell) -> None:
        """Press in the Wire tool. What it does is decided on release (_end_wiring)."""
        node = self.board.node_at(cell)
        if node is None:
            self.source, self.ghost = None, None
            return
        self.pressed, self.fresh = node.id, False
        if self.source is None:
            if not node.kind.emits:
                self.pressed = None
                self._refuse("thrusters have no output", cell)
                return
            self.source, self.fresh = node.id, True
        self.message = ""
        self._update_ghost()

    def _end_wiring(self) -> None:
        """Release in the Wire tool. Where the press was is a click: it picks the source,
        connects the chosen source to it, or, on the chosen source again, drops it. Anywhere
        else is a drag: it wires from where the press was to here, or gives up over an empty
        cell."""
        pressed, self.pressed = self.pressed, None
        target = self.board.node_at(self.hover) if self.hover is not None else None
        if target is not None and target.id == pressed:
            if pressed != self.source:
                self._connect(self.source, pressed, self.hover)
            elif not self.fresh:
                self.source, self.ghost = None, None
        elif target is None:
            self.source, self.ghost = None, None
        elif not self.board.nodes[pressed].kind.emits:
            self._refuse("thrusters have no output", self.board.nodes[pressed].cell)
        else:
            self.source = pressed
            self._connect(pressed, target.id, self.hover)
        self._update_ghost()

    def _connect(self, source_id: int, target_id: int, cell: Cell) -> None:
        result = self.board.connect(source_id, target_id)
        if isinstance(result, Refused):
            self._refuse(result.reason, cell)  # keep the source: try another target
            return
        self.source, self.ghost, self.message = None, None, ""

    def _wire_start(self) -> int | None:
        """The node a wire would start from now: while dragging away from a press, that
        press; otherwise the chosen source."""
        if self.pressed is not None and self.hover != self.board.nodes[self.pressed].cell:
            start = self.board.nodes[self.pressed]
            return start.id if start.kind.emits else None
        return self.source

    def _rotate(self, cell: Cell, back: bool) -> None:
        node = self.board.node_at(cell)
        if node is None:
            self._refuse("click an eye or a thruster", cell)
            return
        # Direction indices run counter-clockwise on screen, so clockwise is -1.
        result = self.board.rotate(node.id, 1 if back else -1)
        if isinstance(result, Refused):
            self._refuse(result.reason, cell)
        else:
            self.message = ""

    def _grab(self, cell: Cell) -> None:
        node = self.board.node_at(cell)
        if node is None:
            self._refuse("drag a component", cell)
        elif node.locked:
            self._refuse("placed by the level", cell)
        else:
            self.moving, self.message = node.id, ""

    def _drag_to(self, cell: Cell) -> None:
        """One step of a move: the part stays at the last cell its wires could follow it to."""
        result = self.board.move_node(self.moving, cell)
        if isinstance(result, Refused):
            self._refuse(result.reason, cell)
        else:
            self.message = ""

    def _delete(self, cell: Cell, pos: tuple[int, int]) -> None:
        node, wire = self._delete_target(cell, pos)
        if wire is not None:
            self.board.remove_wire(wire)
            self.message = ""
        elif node is not None:
            result = self.board.remove_node(node.id)
            if isinstance(result, Refused):
                self._refuse(result.reason, cell)
            else:
                self.message = ""
        else:
            self._refuse("nothing to delete here", cell)

    def _delete_target(self, cell: Cell, pos: tuple[int, int]) -> tuple[Node | None, Wire | None]:
        """What a Delete click at `pos` would take: a component (with its wires) or one wire.

        A click on a component's shape takes the component. Otherwise wires come first, before
        the rest of a component's cell, because a wire between two neighbouring components
        crosses no free cell: it only shows between their shapes.
        """
        size, origin = self.view.size, self.view.origin
        node = self.board.node_at(cell)
        if node is not None and math.dist(pos, to_pixel(cell, size, origin)) < NODE_HIT * size:
            return node, None
        wire = nearest_wire(pos, self.board.wires, size, origin, WIRE_HIT * size)
        if wire is None and node is None and self.board.wires_in(cell):
            # Anywhere in a crossed cell: the nearest of its wires (the keyboard cursor sits at
            # the centre, which a turning wire does not pass through).
            wire = nearest_wire(pos, self.board.wires_in(cell), size, origin, math.inf)
        return (None, wire) if wire is not None else (node, None)

    def doomed(self) -> tuple[int | None, list[Wire]]:
        """In the Delete tool, what a click here would remove, darkened before it happens:
        a component's id and its wires, or one wire. Nothing for a part the level locked."""
        if self.tool is not Tool.DELETE or self.hover is None:
            return None, []
        node, wire = self._delete_target(self.hover, self.mouse)
        if wire is not None:
            return None, [wire]
        if node is None or node.locked:
            return None, []
        return node.id, [w for w in self.board.wires if node.id in (w.source, w.target)]

    # Helpers

    def _update_ghost(self) -> None:
        """Where a wire from its start would run to the hovered cell, and whether it may end
        there: over an empty cell it only shows the way; over a target it is the real preview."""
        self.ghost, self.ghost_connects = None, False
        start = self._wire_start() if self.tool is Tool.WIRE else None
        if start is None or self.hover is None:
            return
        target = self.board.node_at(self.hover)
        if target is None:
            self.ghost = self.board.route(self.board.nodes[start].cell, self.hover)
        elif target.id != start:
            self.ghost = self.board.preview(start, target.id)
            self.ghost_connects = isinstance(self.ghost, tuple)

    def _refuse(self, reason: str, cell: Cell | None) -> None:
        self.message = reason
        self.flash_cell, self.flash_frames = cell, FLASH_FRAMES
