"""The developer view's state and input: the board as a circuit that runs (D-017).

Shows the board as components joined by wires, without the grid or arrows, with beads on the
wires, a level on every part and the equations beside it. Sliders set what the eyes and the
sources send. One scene per entry, built from a list of boards (yours first, then the
scenarios); Tab steps through them. Mutates nothing in the boards.

Keys: Space pauses, `.` runs one frame while paused, W cycles the waveform the eyes follow, B
switches the bead style, R starts again from rest, Tab and Shift-Tab change board. Drag a slider
to set a sensor.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pygame

from nektoids.editor.beads import BEAD_RATE_AT_FULL, Beads
from nektoids.editor.devdrive import (
    DT,
    Clock,
    level_at,
    next_wave,
    on_track,
    track_for,
    waveform,
)
from nektoids.editor.geometry import cumulative_lengths, wire_points
from nektoids.editor.layout import HEX_SIZE, SCREEN, Rect, View, fitted_view
from nektoids.graph.analysis import LoopReport, loop_report, problems
from nektoids.graph.dynamics import (
    RATE_MAX,
    given_rates,
    initial_state,
    step,
    wire_flux,
)
from nektoids.graph.equations import node_equations, report_lines
from nektoids.graph.hexgrid import Cell, to_pixel
from nektoids.graph.network import Network
from nektoids.levels.scenarios import Scenario

PANEL_WIDTH = 400  # equations, left [px]
STATUS_HEIGHT = 32  # [px]
MARGIN = 2.6  # room round the graph for sliders, meters and labels [hex sizes]
BOARD_AREA: Rect = (PANEL_WIDTH, 0, SCREEN[0] - PANEL_WIDTH, SCREEN[1] - STATUS_HEIGHT)
EYE_LEVEL = RATE_MAX / 2  # where an eye's slider starts


class SchematicScene:
    def __init__(self, boards: Sequence[Scenario]):
        self.boards = list(boards)
        self.index = 0
        self.wave = "hold"
        self.belt = False  # bead style: spacing shows the rate, or (belt) speed does
        self.clock = Clock()
        self.dragging: int | None = None  # network index of the sensor whose slider is held
        self._load()

    # Loading a board

    def _load(self) -> None:
        current = self.boards[self.index]
        self.title, self.board = current.title, current.board
        self.net = net = Network.from_board(self.board)
        self.cells: list[Cell] = [self.board.nodes[i].cell for i in net.ids]
        self.paths = [wire.path for wire in self.board.wires]
        unit = [wire_points(path, 1.0, (0.0, 0.0)) for path in self.paths]
        bx, by, bw, bh = BOARD_AREA
        self.view: View = View(HEX_SIZE, (bx + bw / 2, by + bh / 2))  # an empty board
        if self.cells:
            shown = [to_pixel(cell, 1.0, (0.0, 0.0)) for cell in self.cells]
            shown += [point for points in unit for point in points]
            self.view = fitted_view(BOARD_AREA, shown, MARGIN)
        self.beads = Beads([cumulative_lengths(points)[-1] for points in unit])
        self.levels = {int(i): EYE_LEVEL for i in net.eyes}
        self.levels |= {int(i): current.source_level for i in net.sources}
        self.state = initial_state(net)  # (1, n): every rate, from rest
        self.flux = np.zeros(len(self.paths))
        self.report: LoopReport = loop_report(net)
        self.lines = _panel_lines(self)
        self.clock.reset()
        self._show_sensors(0)

    @property
    def y(self) -> np.ndarray:
        """The rate of every node now, shape (n,)."""
        return self.state[0]

    # Per frame

    def update(self) -> None:
        for tick in self.clock.frame():
            self._tick(tick)

    def _tick(self, tick: int) -> None:
        eyes, sources = self._sensor_inputs(tick)
        self.state = step(self.net, self.state, eyes, DT, sources)
        self.flux = wire_flux(self.net, self.state)[0]
        self.beads.step((BEAD_RATE_AT_FULL / RATE_MAX * self.flux).tolist(), DT)

    def _sensor_inputs(self, tick: int) -> tuple[np.ndarray, np.ndarray]:
        """What the eyes (following the waveform) and the sources send at `tick`."""
        net = self.net
        eyes = np.array([[waveform(self.wave, self.levels[int(i)], tick) for i in net.eyes]])
        return eyes, np.array([self.levels[int(i)] for i in net.sources])

    def _show_sensors(self, tick: int) -> None:
        """Put the sensors' rates at `tick` in the state now, e.g. paused; nothing else moves."""
        eyes, sources = self._sensor_inputs(tick)
        given = given_rates(self.net, eyes, sources)
        known = self.net.sensors
        self.state[:, known] = given[:, known]
        self.flux = wire_flux(self.net, self.state)[0]

    # Input

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.dragging = self._slider_at(event.pos)
            self._drag(event.pos)
        elif event.type == pygame.MOUSEMOTION and self.dragging is not None:
            self._drag(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = None
        elif event.type == pygame.KEYDOWN:
            self._key(event)

    def _key(self, event: pygame.event.Event) -> None:
        if event.scancode == pygame.KSCAN_SPACE:
            self.clock.toggle_pause()
        elif event.scancode == pygame.KSCAN_TAB:
            back = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
            self.index = (self.index + (-1 if back else 1)) % len(self.boards)
            self._load()
        elif event.unicode == ".":
            self.clock.step()
        elif event.unicode.lower() == "w":
            self.wave = next_wave(self.wave)
            self._show_sensors(self.clock.tick)
        elif event.unicode.lower() == "b":
            self.belt = not self.belt
        elif event.unicode.lower() == "r":
            self.clock.reset()
            self.beads.reset()
            self.state = initial_state(self.net)
            self._show_sensors(0)

    def centre(self, i: int) -> tuple[float, float]:
        """Where network node i is drawn."""
        return to_pixel(self.cells[i], self.view.size, self.view.origin)

    def _slider_at(self, point: tuple[int, int]) -> int | None:
        for i in self.levels:
            if on_track(track_for(self.centre(i), self.view.size), point):
                return i
        return None

    def _drag(self, point: tuple[int, int]) -> None:
        if self.dragging is not None:
            track = track_for(self.centre(self.dragging), self.view.size)
            self.levels[self.dragging] = level_at(track, point[1])
            self._show_sensors(self.clock.tick)  # also while paused


def _panel_lines(scene: SchematicScene) -> list[tuple[str, str, int | None]]:
    """Static text of the side panel as (kind, text, node): kind picks the colour, and a node's
    own line carries its index so that the drawing can add its live rate."""
    net = scene.net
    equations = node_equations(net)  # R first, then one line per node
    lines: list[tuple[str, str, int | None]] = [("head", "Equations", None)]
    lines.append(("eq", equations[0], None))
    lines += [("eq", text, i) for i, text in enumerate(equations[1:])]
    lines += [("head", "Loops", None)]
    lines += [("eq", text, None) for text in report_lines(net, scene.report)]
    found = problems(net)
    if found:
        lines += [("head", "Look at", None)]
        lines += [("warn", text, None) for text in found]
    return lines
