"""Drawing the developer view. Reads the scene; never changes it.

Wires are plain lines, dimmer the less they carry, with beads running along them. A part's fill
shows its rate in shades of grey, from dim (nothing) to light (R); every part shows its rate as a
number. Each sensor has a slider beside it (the knob is what you set, the bar is what it sends
now) and each thruster a bar. No hex grid and no arrows. The circuit itself is `draw.draw_circuit`,
which Inside, Diagnostic and a part's entry draw too.
"""

from __future__ import annotations

import pygame

from nektoids.editor.devdrive import knob_y, track_for
from nektoids.editor.draw import Fonts, cached_text, draw_circuit
from nektoids.editor.palette import (
    BACKGROUND,
    DARK,
    DIM_TEXT,
    FULL,
    PANEL,
    RULE,
    TEXT,
    VALUE,
    WARN,
)
from nektoids.editor.schematic import BOARD_AREA, PANEL_WIDTH, STATUS_HEIGHT, SchematicScene

BAR_WIDTH = 6  # [px]
HEADINGS = {"head": DIM_TEXT, "eq": TEXT, "warn": WARN}
LINE_HEIGHT = 17  # [px]
HINTS = (
    "Drag a slider to set a sensor.  Space: pause.  . : a step (0.1 s).",
    "W: waveform.  B: beads.  0: restart.  Tab: board.  F6: editor.",
)


def draw_schematic(screen: pygame.Surface, scene: SchematicScene, fonts: Fonts) -> None:
    screen.fill(BACKGROUND)
    _draw_panel(screen, scene, fonts)
    screen.set_clip(BOARD_AREA)
    draw_circuit(screen, scene.circuit, scene.y, fonts, belt=scene.belt)
    for i in scene.levels:
        _draw_slider(screen, scene, i)
    if not scene.circuit.cells:
        note = cached_text(fonts.text, "This board is empty: Tab for the examples", DIM_TEXT)
        screen.blit(note, note.get_rect(center=(BOARD_AREA[0] + BOARD_AREA[2] // 2, 300)))
    screen.set_clip(None)
    pygame.draw.line(screen, RULE, (PANEL_WIDTH, 0), (PANEL_WIDTH, screen.get_height()), 2)
    _draw_status(screen, scene, fonts)


def _draw_slider(screen: pygame.Surface, scene: SchematicScene, i: int) -> None:
    track = track_for(scene.circuit.centre(i), scene.circuit.view.size)
    x = round(track.x)
    pygame.draw.line(screen, RULE, (x, track.top), (x, track.bottom), 3)
    sending = knob_y(track, float(scene.y[i]))  # what it sends now, from the foot up
    pygame.draw.line(screen, FULL, (x, track.bottom), (x, sending), BAR_WIDTH - 2)
    knob = (x, round(knob_y(track, scene.levels[i])))
    pygame.draw.circle(screen, TEXT, knob, 7)
    pygame.draw.circle(screen, DARK, knob, 7, 2)


def _draw_panel(screen: pygame.Surface, scene: SchematicScene, fonts: Fonts) -> None:
    pygame.draw.rect(screen, PANEL, (0, 0, PANEL_WIDTH, screen.get_height()))
    count = f"{scene.index + 1}/{len(scene.boards)}"
    screen.blit(cached_text(fonts.text, f"{scene.title}  ({count})", TEXT), (12, 10))
    y = 34
    for kind, text, node in scene.lines:
        if y > screen.get_height() - STATUS_HEIGHT - (len(HINTS) + 1) * LINE_HEIGHT:
            screen.blit(cached_text(fonts.small, "...", DIM_TEXT), (12, y))
            break
        y += 6 if kind == "head" else 0
        screen.blit(cached_text(fonts.small, text, HEADINGS[kind]), (12, y))
        if node is not None:
            rate = cached_text(fonts.small, f"{scene.y[node]:.2f}", VALUE)
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
        screen.blit(
            cached_text(fonts.small, hint, DIM_TEXT), (12, y - (len(HINTS) - k) * LINE_HEIGHT)
        )
