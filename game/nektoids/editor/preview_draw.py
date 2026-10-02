"""Drawing the Run preview on the editor's main screen (D-058): the board as it runs where the
probe stands, on its body, plain, as Inside draws it in the run: beads on the wires, a meter by
each eye and thruster, no numbers (D-052). Each eye's meter is a handle: a knob as big as a bead
at what the eye sends, lit while the player holds it there. Reads the scene; never changes it.
"""

from __future__ import annotations

import pygame

from nektoids.editor.circuit import BEAD_RADIUS
from nektoids.editor.draw import Fonts, draw_body
from nektoids.editor.palette import BACKGROUND, BEAD, DARK, DIM_TEXT, LIT
from nektoids.editor.scene import EditorScene
from nektoids.editor.schematic_draw import draw_circuit
from nektoids.graph.dynamics import RATE_MAX


def draw_preview(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    area = pygame.Rect(scene.layout.board_area)
    pygame.draw.rect(screen, BACKGROUND, area)
    probe = scene.probe
    if probe is None or not probe.circuit.cells:
        note = fonts.small.render(
            "Your board is empty: place a part to see it run.", True, DIM_TEXT
        )
        screen.blit(note, note.get_rect(center=area.center))
        return
    circuit = probe.circuit
    screen.set_clip(area)
    draw_body(screen, circuit.board.cells, circuit.view.size, circuit.view.origin)
    draw_circuit(screen, circuit, probe.y, fonts, plain=True)
    radius = max(3, round(BEAD_RADIUS * circuit.view.size))
    for k, i in enumerate(probe.net.eyes):
        track = probe.track(int(i))
        sent = float(probe.eyes()[k]) / RATE_MAX
        knob = (round(track.x), round(track.bottom - sent * (track.bottom - track.top)))
        held = int(i) in probe.held
        pygame.draw.circle(screen, LIT if held else BEAD, knob, radius)
        pygame.draw.circle(screen, DARK, knob, radius, 1)
    screen.set_clip(None)
