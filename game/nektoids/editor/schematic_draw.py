"""Drawing the developer view. Reads the scene; never changes it.

Wires are plain lines, dimmer the less they carry, with beads running along them. A part's fill
shows its rate in shades of grey, from dim (nothing) to light (R); every part shows its rate as a
number. Each sensor has a slider beside it (the knob is what you set, the bar is what it sends
now) and each thruster a bar. No hex grid and no arrows. `draw_circuit` draws the circuit alone,
for the arena's panel too.
"""

from __future__ import annotations

import numpy as np
import pygame

from nektoids.editor.beads import BEAD_RATE_AT_FULL
from nektoids.editor.circuit import BEAD_RADIUS, METER_AT, METER_HEIGHT, Circuit
from nektoids.editor.devdrive import knob_y, track_for
from nektoids.editor.draw import (
    Fonts,
    draw_part,
    placed_angle,
)
from nektoids.editor.geometry import cumulative_lengths, point_at, wire_points
from nektoids.editor.palette import (
    BACKGROUND,
    BEAD,
    DARK,
    DIM_TEXT,
    FULL,
    METER,
    PANEL,
    RULE,
    TEXT,
    VALUE,
    WARN,
    WIRE,
)
from nektoids.editor.schematic import BOARD_AREA, PANEL_WIDTH, STATUS_HEIGHT, SchematicScene
from nektoids.graph.board import Kind
from nektoids.graph.dynamics import RATE_MAX
from nektoids.graph.network import label

BAR_WIDTH = 6  # [px]
METER_WIDTH = 10  # [px]
HEADINGS = {"head": DIM_TEXT, "eq": TEXT, "warn": WARN}
LINE_HEIGHT = 17  # [px]
HINTS = (
    "Drag a slider to set a sensor.  Space: pause.  . : a step (0.1 s).",
    "W: waveform.  B: beads.  0: restart.  Tab: board.  F2: editor.",
)


_TEXT_CACHE: dict[tuple[int, str, tuple[int, int, int]], pygame.Surface] = {}
_TEXT_CACHE_LIMIT = 2000


def _text(font: pygame.font.Font, text: str, colour: tuple[int, int, int]) -> pygame.Surface:
    """Rendered text, kept: the panel shows the same lines frame after frame."""
    key = (id(font), text, colour)
    if key not in _TEXT_CACHE:
        if len(_TEXT_CACHE) >= _TEXT_CACHE_LIMIT:
            _TEXT_CACHE.clear()
        _TEXT_CACHE[key] = font.render(text, True, colour)
    return _TEXT_CACHE[key]


def draw_schematic(screen: pygame.Surface, scene: SchematicScene, fonts: Fonts) -> None:
    screen.fill(BACKGROUND)
    _draw_panel(screen, scene, fonts)
    screen.set_clip(BOARD_AREA)
    draw_circuit(screen, scene.circuit, scene.y, fonts, belt=scene.belt)
    for i in scene.levels:
        _draw_slider(screen, scene, i)
    if not scene.circuit.cells:
        note = _text(fonts.text, "This board is empty: Tab for the examples", DIM_TEXT)
        screen.blit(note, note.get_rect(center=(BOARD_AREA[0] + BOARD_AREA[2] // 2, 300)))
    screen.set_clip(None)
    pygame.draw.line(screen, RULE, (PANEL_WIDTH, 0), (PANEL_WIDTH, screen.get_height()), 2)
    _draw_status(screen, scene, fonts)


def draw_circuit(
    screen: pygame.Surface,
    circuit: Circuit,
    y: np.ndarray,
    fonts: Fonts,
    belt: bool = False,
    plain: bool = False,
) -> None:
    """Wires, beads and parts at the rates y (n,): the beads, and a level meter by each eye and
    thruster, show the rates; the parts keep their colour (D-052). Unless `plain`,
    every part has its name and its rate as a number, and every thruster a bar."""
    _draw_wires(screen, circuit, belt)
    _draw_parts(screen, circuit, y, fonts, plain)


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
    screen: pygame.Surface, circuit: Circuit, y: np.ndarray, fonts: Fonts, plain: bool
) -> None:
    net, size = circuit.net, circuit.view.size
    for i, node_id in enumerate(net.ids):
        kind, rate = net.kinds[i], float(y[i])
        cx, cy = circuit.centre(i)
        facing = circuit.board.nodes[node_id].facing
        draw_part(screen, fonts, kind, placed_angle(kind, facing), (cx, cy), size, False)
        if kind in (Kind.EYE, Kind.THRUSTER):
            _draw_meter(screen, (cx + METER_AT * size, cy), size, rate)
        if plain:
            continue
        name = _text(fonts.small, label(net, i), DIM_TEXT)
        screen.blit(name, name.get_rect(center=(cx, cy - 1.35 * size)))
        number = _text(fonts.small, f"{rate:.2f}", TEXT)
        screen.blit(number, number.get_rect(center=(cx, cy + 1.3 * size)))


def _draw_slider(screen: pygame.Surface, scene: SchematicScene, i: int) -> None:
    track = track_for(scene.circuit.centre(i), scene.circuit.view.size)
    x = round(track.x)
    pygame.draw.line(screen, RULE, (x, track.top), (x, track.bottom), 3)
    sending = knob_y(track, float(scene.y[i]))  # what it sends now, from the foot up
    pygame.draw.line(screen, FULL, (x, track.bottom), (x, sending), BAR_WIDTH - 2)
    knob = (x, round(knob_y(track, scene.levels[i])))
    pygame.draw.circle(screen, TEXT, knob, 7)
    pygame.draw.circle(screen, DARK, knob, 7, 2)


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


def _draw_panel(screen: pygame.Surface, scene: SchematicScene, fonts: Fonts) -> None:
    pygame.draw.rect(screen, PANEL, (0, 0, PANEL_WIDTH, screen.get_height()))
    count = f"{scene.index + 1}/{len(scene.boards)}"
    screen.blit(_text(fonts.text, f"{scene.title}  ({count})", TEXT), (12, 10))
    y = 34
    for kind, text, node in scene.lines:
        if y > screen.get_height() - STATUS_HEIGHT - (len(HINTS) + 1) * LINE_HEIGHT:
            screen.blit(_text(fonts.small, "...", DIM_TEXT), (12, y))
            break
        y += 6 if kind == "head" else 0
        screen.blit(_text(fonts.small, text, HEADINGS[kind]), (12, y))
        if node is not None:
            rate = _text(fonts.small, f"{scene.y[node]:.2f}", VALUE)
            screen.blit(rate, rate.get_rect(topright=(PANEL_WIDTH - 12, y)))
        y += LINE_HEIGHT


def _draw_status(screen: pygame.Surface, scene: SchematicScene, fonts: Fonts) -> None:
    clock = scene.clock
    state = "paused" if clock.paused else "running"
    style = "belt" if scene.belt else "spacing"
    text = f"t = {clock.seconds:5.2f} s, {state}.  Eyes follow: {scene.wave}.  Beads: {style}."
    y = screen.get_height() - 22
    screen.blit(
        fonts.small.render(text, True, DIM_TEXT), (PANEL_WIDTH + 16, y)
    )  # changes each frame
    for k, hint in enumerate(HINTS):
        screen.blit(_text(fonts.small, hint, DIM_TEXT), (12, y - (len(HINTS) - k) * LINE_HEIGHT))
