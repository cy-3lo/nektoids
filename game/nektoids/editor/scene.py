"""Editor state and input handling. Mutates the board only through its methods.

Tools:
- Add: drag a component from the menu onto a cell, or pick it and click cells.
- Wire: drag from a source to a target, or click one then the other. The route shows first,
  bright when it may connect.
- Rotate: click an eye or a thruster to turn it 60° clockwise, shift-click to turn it back (D-009).
- Move: drag a component; its wires follow while they find a path (D-011).
- Delete: click a component's shape, or a wire.
- Pan (the hand, next to the zoom buttons): drag the grid to move the view (D-013).

Clicking a menu title folds or unfolds its group. Right click or Escape cancels. Every refusal
flashes the cell and puts the reason in the status line.
"""

from __future__ import annotations

import math

import pygame

from nektoids.editor.geometry import nearest_wire
from nektoids.editor.layout import (
    ZOOM_STEP,
    Layout,
    Tool,
    ViewButton,
    cell_at,
    centred_view,
    group_at,
    make_layout,
    menu_item_at,
    pan,
    tool_at,
    view_button_at,
    zoom,
)
from nektoids.graph.board import Board, Kind, Refused
from nektoids.graph.hexgrid import Cell, to_pixel

FLASH_FRAMES = 30  # how long a refused cell stays red [frames]
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
        self.flash_cell: Cell | None = None
        self.flash_frames = 0

    def update(self) -> None:
        """Once per frame."""
        if self.flash_frames > 0:
            self.flash_frames -= 1

    def handle_event(self, event: pygame.event.Event) -> None:
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

    # Mouse

    def _track(self, pos: tuple[int, int]) -> None:
        if self.panning_from is not None:
            dx, dy = pos[0] - self.panning_from[0], pos[1] - self.panning_from[1]
            self.view, self.panning_from = pan(self.view, dx, dy), pos
        self.mouse = pos
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
        self.moving = None
        self.message = ""

    # View

    def _view_button(self, button: ViewButton) -> None:
        if button is ViewButton.PAN:
            self._cancel()
            self.tool = Tool.PAN
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
        """A click on a component's shape deletes it; otherwise the wire drawn under the click.

        Wires count before the rest of a component's cell, because a wire between two
        neighbouring components crosses no free cell: it only shows between their shapes.
        """
        size, origin = self.view.size, self.view.origin
        node = self.board.node_at(cell)
        on_shape = (
            node is not None and math.dist(pos, to_pixel(cell, size, origin)) < NODE_HIT * size
        )
        wire = (
            None if on_shape else nearest_wire(pos, self.board.wires, size, origin, WIRE_HIT * size)
        )
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
