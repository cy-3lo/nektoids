"""Drawing the swimmer at work (D-076) through an arena view. Under the swimmer, the specks of the
light its eyes draw in and of its flames, each on a grid of SPECK pixels, so they read as pixels
scattered; over it, its parts' outlines and faces, its velocity and its spin. The run and the
map in Diagnostic share it. Reads; never changes anything.
"""

from __future__ import annotations

import numpy as np
import pygame

from nektoids.editor.arena_view import ArenaView
from nektoids.editor.marks import AtWork
from nektoids.editor.palette import EYE_FACE, FLAME, INTAKE, MOTION, PART_OUTLINE, THRUSTER_BACK

SPECK = 3  # a speck's side, and the pitch of the grid the specks sit on [px]
FACE_WIDTH = 2  # an eye's face, a thruster's back [px]
MOTION_WIDTH = 2  # the velocity's segment, the spin's arc [px]
SHORTEST = 2.0  # a segment or an arc shorter than this is not drawn [px]


def draw_under(screen: pygame.Surface, view: ArenaView, body: AtWork) -> None:
    """The specks, drawn before the swimmer: the light drawn in, then the flames."""
    _specks(screen, view, body.intake, INTAKE)
    _specks(screen, view, body.flames, FLAME)


def draw_over(screen: pygame.Surface, view: ArenaView, body: AtWork) -> None:
    """The parts, the velocity and the spin, drawn after the swimmer."""
    for outlines, colour in ((body.eyes, EYE_FACE), (body.thrusters, THRUSTER_BACK)):
        for outline in outlines:
            points = _on_screen(view, outline)
            pygame.draw.aalines(screen, PART_OUTLINE, False, points)
            pygame.draw.aaline(screen, colour, points[-1], points[0], FACE_WIDTH)
    draw_motion(screen, view, body.velocity, body.spin)


def draw_motion(
    screen: pygame.Surface, view: ArenaView, velocity: np.ndarray | None, spin: np.ndarray | None
) -> None:
    """The velocity's segment and the spin's arc, each a polyline in the plane [u], or None."""
    for line in (velocity, spin):
        if line is None:
            continue
        points = _on_screen(view, line)
        steps = np.diff(np.array(points), axis=0)
        if np.hypot(steps[:, 0], steps[:, 1]).sum() < SHORTEST:
            continue
        for a, b in zip(points[:-1], points[1:], strict=True):
            pygame.draw.aaline(screen, MOTION, a, b, MOTION_WIDTH)


def _on_screen(view: ArenaView, points: np.ndarray) -> list[tuple[float, float]]:
    x = view.origin[0] + view.scale * points[:, 0]
    y = view.origin[1] - view.scale * points[:, 1]
    return list(zip(x.tolist(), y.tolist(), strict=True))


def _specks(screen: pygame.Surface, view: ArenaView, points: np.ndarray, colour) -> None:
    x = np.floor((view.origin[0] + view.scale * points[:, 0]) / SPECK) * SPECK
    y = np.floor((view.origin[1] - view.scale * points[:, 1]) / SPECK) * SPECK
    for left, top in zip(x.tolist(), y.tolist(), strict=True):
        screen.fill(colour, (left, top, SPECK, SPECK))
