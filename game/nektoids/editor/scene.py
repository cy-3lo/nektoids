"""Editor state and input handling. Mutates the board only through its methods.

Tools: Add (drag a component from the palette onto a cell, or pick it and click cells), Wire
(click a source, then a target; hovering a target shows the route first), Delete (click a
component, or a wire where it crosses a cell). Right click or Escape cancels. Every refusal
flashes the cell and puts the reason in the status line.
"""

from __future__ import annotations

import math

import pygame

from nektoids.editor.layout import Layout, Tool, cell_at, palette_item_at, tool_at
from nektoids.graph.board import Board, Kind, Refused, Wire
from nektoids.graph.hexgrid import Cell, direction_to, opposite, to_pixel

FLASH_FRAMES = 30  # how long a refused cell stays red [frames]


class EditorScene:
    def __init__(self, board: Board, layout: Layout):
        self.board = board
        self.layout = layout
        self.tool = Tool.ADD
        self.picked: Kind | None = None  # Add: the palette kind in hand
        self.dragging = False  # Add: mouse held since picking from the palette
        self.source: int | None = None  # Wire: node id of the chosen source
        self.ghost: tuple[Cell, ...] | Refused | None = None  # Wire: route to the hovered target
        self.mouse = (0, 0)
        self.hover: Cell | None = None  # board cell under the mouse
        self.message = ""  # last refusal, empty once something succeeds
        self.flash_cell: Cell | None = None
        self.flash_frames = 0

    def update(self) -> None:
        """Once per frame."""
        if self.flash_frames > 0:
            self.flash_frames -= 1

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self._move(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._move(event.pos)
            self._press(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._release(event.pos)
        elif (event.type == pygame.MOUSEBUTTONDOWN and event.button == 3) or (
            event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
        ):
            self._cancel()

    # Mouse

    def _move(self, pos: tuple[int, int]) -> None:
        self.mouse = pos
        cell = cell_at(self.layout, pos)
        hover = cell if cell in self.board.cells else None
        if hover != self.hover:
            self.hover = hover
            self._update_ghost()

    def _press(self, pos: tuple[int, int]) -> None:
        tool = tool_at(self.layout, pos)
        if tool is not None:
            self._cancel()
            self.tool = tool
            return
        kind = palette_item_at(self.layout, pos)
        if kind is not None:
            self._pick(kind)
            return
        if self.hover is None:
            return
        if self.tool is Tool.ADD:
            self._add(self.hover)
        elif self.tool is Tool.WIRE:
            self._wire(self.hover)
        else:
            self._delete(self.hover, pos)

    def _release(self, pos: tuple[int, int]) -> None:
        if not self.dragging:
            return
        self.dragging = False
        if self.hover is not None:
            self._add(self.hover)

    def _cancel(self) -> None:
        self.picked, self.dragging = None, False
        self.source, self.ghost = None, None
        self.message = ""

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
            self._refuse("pick a component in the palette first", None)
            return
        result = self.board.place(self.picked, cell)
        if isinstance(result, Refused):
            self._refuse(result.reason, cell)
            return
        self.message = ""
        if self.board.remaining(self.picked) == 0:
            self.picked = None

    def _wire(self, cell: Cell) -> None:
        node = self.board.node_at(cell)
        if node is None:
            self.source, self.ghost = None, None
            return
        if self.source is None:
            if not node.kind.emits:
                self._refuse("thrusters have no output", cell)
                return
            self.source, self.message = node.id, ""
            return
        if node.id == self.source:
            self.source, self.ghost = None, None
            return
        result = self.board.connect(self.source, node.id)
        if isinstance(result, Refused):
            self._refuse(result.reason, cell)
            return
        self.source, self.ghost, self.message = None, None, ""

    def _delete(self, cell: Cell, pos: tuple[int, int]) -> None:
        node = self.board.node_at(cell)
        if node is not None:
            result = self.board.remove_node(node.id)
            if isinstance(result, Refused):
                self._refuse(result.reason, cell)
            else:
                self.message = ""
            return
        wires = self.board.wires_in(cell)
        if not wires:
            self._refuse("nothing to delete here", cell)
            return
        self.board.remove_wire(self._wire_toward(wires, cell, pos))
        self.message = ""

    # Helpers

    def _wire_toward(self, wires: list[Wire], cell: Cell, pos: tuple[int, int]) -> Wire:
        """Of the wires crossing `cell`, the one whose segment points closest to the click."""
        cx, cy = to_pixel(cell, self.layout.hex_size, self.layout.origin)
        click = math.degrees(math.atan2(pos[1] - cy, pos[0] - cx))

        def gap(wire: Wire) -> float:
            i = wire.path.index(cell)
            ends = (
                opposite(direction_to(wire.path[i - 1], cell)),
                direction_to(cell, wire.path[i + 1]),
            )
            # Direction d points at screen angle -60° * d (y down).
            return min(abs((click + 60.0 * d + 180.0) % 360.0 - 180.0) for d in ends)

        return min(wires, key=gap)

    def _update_ghost(self) -> None:
        self.ghost = None
        if self.tool is not Tool.WIRE or self.source is None or self.hover is None:
            return
        target = self.board.node_at(self.hover)
        if target is not None and target.id != self.source:
            self.ghost = self.board.preview(self.source, target.id)

    def _refuse(self, reason: str, cell: Cell | None) -> None:
        self.message = reason
        self.flash_cell, self.flash_frames = cell, FLASH_FRAMES
