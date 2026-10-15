"""Drawing the swimmer at work (D-076) through an arena view. Under the swimmer, the specks of the
light its eyes draw in and of its flames, each on a grid of SPECK pixels, so they read as pixels
scattered; over it, its parts' outlines and faces, its velocity and its spin; and the tracers of
the flow round it, on the same grid (D-608). The run and the map in Diagnostic share it. Reads;
never changes anything.
"""

from __future__ import annotations

import numpy as np
import pygame

from nektoids.editor.arena_view import ArenaView
from nektoids.editor.flowfield import Tracers
from nektoids.editor.marks import AtWork
from nektoids.editor.palette import (
    EYE_FACE,
    FLAME,
    FLOW_ADDED,
    FLOW_CUT,
    FLOW_KEEP,
    IDLE,
    INTAKE,
    MOTION,
    NOTHING,
    PAINT_AMBER,
    PAINT_VIOLET,
    PART_OUTLINE,
    SHADOW,
    THRUSTER_BACK,
    mix,
)
from nektoids.graph.kinds import Hue

OUTLINE_OF = {Hue.AMBER: PAINT_AMBER, Hue.VIOLET: PAINT_VIOLET}  # an outline by its paint

SPECK = 3  # a speck's side, and the pitch of the grid the specks sit on [px]
FACE_WIDTH = 2  # an eye's face, a thruster's back [px]
MOTION_WIDTH = 2  # the velocity's segment, the spin's arc [px]
SHORTEST = 2.0  # a segment or an arc shorter than this is not drawn [px]


def draw_tracers(
    screen: pygame.Surface, area: pygame.Rect, tracers: Tracers, view: ArenaView, cache: dict
) -> None:
    """The tracers (D-608) in `area`, specks on a grid of SPECK pixels, each a comet: a layer at a
    third of the screen's resolution, faded each frame and added onto the plane, scaled up;
    `cache`, its own for each place they are drawn, keeps the layer from frame to frame."""
    size = (area.width // SPECK + 1, area.height // SPECK + 1)
    if cache.get("key") != (size, tracers.seeded):  # a new field: its tails start again
        specks = pygame.Surface(size)
        specks.fill(NOTHING)
        lut = np.array([specks.map_rgb(colour) for colour in FLOW_ADDED])
        cache.update(key=(size, tracers.seeded), specks=specks, lut=lut)
    specks = cache["specks"]
    specks.fill(FLOW_KEEP, special_flags=pygame.BLEND_RGB_MULT)
    specks.fill(FLOW_CUT, special_flags=pygame.BLEND_RGB_SUB)
    if len(tracers.x):
        px = ((view.origin[0] + view.scale * tracers.x[:, 0] - area.left) // SPECK).astype(int)
        py = ((view.origin[1] - view.scale * tracers.x[:, 1] - area.top) // SPECK).astype(int)
        inside = (px >= 0) & (px < size[0]) & (py >= 0) & (py < size[1])
        pixels = pygame.surfarray.pixels2d(specks)
        pixels[px[inside], py[inside]] = cache["lut"][tracers.levels()[inside]]
        del pixels  # the surface unlocked
    scaled = pygame.transform.scale(specks, (size[0] * SPECK, size[1] * SPECK))
    screen.blit(scaled, area.topleft, special_flags=pygame.BLEND_RGB_ADD)


def draw_under(
    screen: pygame.Surface,
    view: ArenaView,
    body: AtWork,
    intake: bool = True,
    flames: bool = True,
) -> None:
    """The specks, drawn before the swimmer: the light drawn in, then the flames, each if shown
    (D-608)."""
    if intake:
        _specks(screen, view, body.intake, INTAKE)
    if flames:
        _specks(screen, view, body.flames, FLAME)


def draw_over(screen: pygame.Surface, view: ArenaView, body: AtWork) -> None:
    """The parts, the velocity and the spin, drawn after the swimmer."""
    draw_parts(screen, view, body)
    draw_motion(screen, view, body.velocity, body.spin)


def draw_parts(screen: pygame.Surface, view: ArenaView, body: AtWork) -> None:
    """Each part's outline in its paint (D-503), and its face in its accent; an idle thruster's
    faded into the plane (D-605)."""
    for outlines, hues, colour, idle in (
        (body.eyes, body.eye_hues, EYE_FACE, (False,) * len(body.eyes)),
        (body.thrusters, body.thruster_hues, THRUSTER_BACK, body.idle),
    ):
        for k, outline in enumerate(outlines):
            points = _on_screen(view, outline)
            ink = PART_OUTLINE if hues is None else OUTLINE_OF[hues[k]]  # no colour shown (D-509)
            face = colour
            if idle[k]:
                ink, face = mix(ink, SHADOW, IDLE), mix(face, SHADOW, IDLE)
            pygame.draw.aalines(screen, ink, False, points)
            pygame.draw.aaline(screen, face, points[-1], points[0], FACE_WIDTH)


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
