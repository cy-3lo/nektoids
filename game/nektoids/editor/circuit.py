"""A board seen as a running circuit: what the developer view (F2) and the arena's panel share.

Holds the compiled network, where its parts and wires are drawn in a given screen area, the
beads and the flux on each wire in each channel: a wire carries a stream of beads a channel,
amber then violet, the violet half a bead behind (D-502, D-503): stream `stream(k, c)`. The
rates themselves belong to whoever runs the circuit: the developer view drives its eyes with
sliders, the arena with the light. Mutates nothing in the board. Pure numbers, no pygame.
"""

from __future__ import annotations

import numpy as np

from nektoids.editor.beads import BEAD_RATE_AT_FULL, Beads, Travelling
from nektoids.editor.geometry import body_circle, cumulative_lengths, wire_points
from nektoids.editor.layout import HEX_SIZE, Rect, View, fitted_view
from nektoids.graph.board import Board
from nektoids.graph.dynamics import RATE_MAX, wire_flux
from nektoids.graph.hexgrid import Cell, to_pixel
from nektoids.graph.laws import CHANNELS
from nektoids.graph.network import Network

BEAD_RADIUS = 0.12  # a bead on a wire, and a handle's knob [hex sizes]
METER_HEIGHT = 1.0  # every part's level meter, eye or thruster alike (D-052) [hex sizes]
METER_AT = 0.86  # its centre right of the part's, past every part's reach [hex sizes]


class Circuit:
    def __init__(
        self,
        board: Board,
        area: Rect,
        margin: float,
        body: bool = False,
        view: View | None = None,
        travelling: bool = False,
    ):
        """area: where to draw it [px]; margin: room kept round it [hex sizes]. body: fit the
        swimmer's whole body too, not only the parts and the wires. view: drawn through this
        view instead, as the Board shows the board (the Run preview, D-060). travelling: beads
        that keep their speed once out (`beads.Travelling`), as a part's entry runs them."""
        self.board = board
        self.net = net = Network.from_board(board)
        self.cells: list[Cell] = [board.nodes[i].cell for i in net.ids]
        self.paths = [wire.path for wire in board.wires]
        unit = [wire_points(path, 1.0, (0.0, 0.0)) for path in self.paths]
        bx, by, bw, bh = area
        self.view: View = View(HEX_SIZE, (bx + bw / 2, by + bh / 2))  # an empty board
        if view is not None:
            self.view = view
        elif self.cells:
            shown = [to_pixel(cell, 1.0, (0.0, 0.0)) for cell in self.cells]
            shown += [point for points in unit for point in points]
            if body:
                (cx, cy), r = body_circle(board.cells, 1.0, (0.0, 0.0))
                shown += [(cx - r, cy - r), (cx + r, cy + r)]
            self.view = fitted_view(area, shown, margin)
        lengths = [cumulative_lengths(points)[-1] for points in unit] * CHANNELS
        starts = [c / CHANNELS for c in range(CHANNELS) for _ in self.paths]  # violet: half behind
        self.beads = (Travelling if travelling else Beads)(lengths, starts=starts)
        self.flux = np.zeros((len(self.paths), CHANNELS))  # each wire's rate in each channel

    def centre(self, i: int) -> tuple[float, float]:
        """Where network node i is drawn."""
        return to_pixel(self.cells[i], self.view.size, self.view.origin)

    def stream(self, wire: int, channel: int) -> int:
        """The stream of beads of `wire` in `channel`."""
        return channel * len(self.paths) + wire

    def rates(self) -> list[float]:
        """Each stream's beads a second, in `stream` order."""
        return (BEAD_RATE_AT_FULL / RATE_MAX * self.flux.T).ravel().tolist()

    def show(self, y: np.ndarray) -> None:
        """Set the flux on the wires from the rates y (n, C), without moving the beads."""
        self.flux = wire_flux(self.net, y[None])[0]

    def advance(self, y: np.ndarray, dt: float) -> None:
        """The rates y (n, C) after a tick of dt [s]: set the flux and move the beads."""
        self.show(y)
        self.beads.step(self.rates(), dt)
