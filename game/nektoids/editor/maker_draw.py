"""Drawing the Maker (D-301). Reads the scene; never changes it.

The plane at large, as the run shows it, over its grid: a dot wherever a position may fall,
every 0.5 u, every whole u farther out, none farther still; a line every 5 u, its coordinate at
the top and left edges, every other one's when they crowd (`grid_steps`). Over the grid the
light's rays, as they stand when the run starts, the obstacles, the lights, and the swimmer
where it starts, its wedge where it heads. Round it, the frame (`draw.py`): the tabs and the
level's caption, the bar, the open drawer, Navigator's overview, zoom and rays, the status line.
"""

from __future__ import annotations

import numpy as np
import pygame

from nektoids.editor.arena_draw import SYMBOL_WIDTH, draw_items, draw_overview, draw_rays
from nektoids.editor.arena_view import LINE_STEP, grid_steps, lattice, shown
from nektoids.editor.draw import (
    ROW_NAME,
    TIP,
    Fonts,
    cached_text,
    draw_bar,
    draw_drawer,
    draw_info,
    draw_row,
    draw_status_line,
    draw_symbol,
    draw_tabs,
    draw_tooltip,
)
from nektoids.editor.icons import VIEW_ICON
from nektoids.editor.layout import HANDLE, VIEW_KEYS
from nektoids.editor.maker import MakerScene
from nektoids.editor.palette import (
    BACKGROUND,
    BODY,
    DARK,
    DIM_TEXT,
    LIT,
    PLANE_DOT,
    PLANE_LABEL,
    PLANE_LINE,
    REFUSED,
    SHADOW,
)

LABEL_INSET = 3  # a line's coordinate, from the line and from the plane's edge [px]

_dots_cache: dict[str, object] = {"key": None, "surface": None}


def draw_maker(screen: pygame.Surface, scene: MakerScene, fonts: Fonts) -> None:
    screen.fill(BACKGROUND)
    screen.set_clip(scene.arena_area)
    _draw_grid(screen, scene)
    if scene.show_rays:  # as they stand at the run's start
        view, area = scene.view, scene.arena_area
        draw_rays(screen, view, area, scene.arena, scene.rays, 0.0, scene.pos, scene.radius)
    draw_items(screen, fonts, scene.view, scene.arena)
    centre, radius = scene.view.to_screen(*scene.pos[0]), float(scene.radius[0]) * scene.view.scale
    draw_symbol(screen, DARK, centre, radius + 1, scene.heading, SYMBOL_WIDTH + 2)
    draw_symbol(screen, BODY, centre, radius, scene.heading, SYMBOL_WIDTH)
    _draw_coordinates(screen, scene, fonts)
    screen.set_clip(None)
    draw_tabs(screen, scene, fonts)
    _draw_status(screen, scene, fonts)
    draw_bar(screen, scene, fonts)
    draw_drawer(screen, scene, fonts, _draw_rows, _draw_foot)
    draw_tooltip(screen, scene, fonts)
    draw_info(screen, scene, fonts, _about)


def _draw_grid(screen: pygame.Surface, scene: MakerScene) -> None:
    """The plane as far as it shows: its dots, if they do not crowd, and a line every 5 u."""
    view, area = scene.view, pygame.Rect(scene.arena_area)
    dots, _ = grid_steps(view.scale)
    if dots is None:
        pygame.draw.rect(screen, SHADOW, area)
    else:
        screen.blit(_dotted(scene, area, dots), area.topleft)
    left, bottom, right, top = shown(view, tuple(area))
    for x in lattice(left, right, LINE_STEP):
        px = round(view.to_screen(x, 0.0)[0])
        pygame.draw.line(screen, PLANE_LINE, (px, area.top), (px, area.bottom))
    for y in lattice(bottom, top, LINE_STEP):
        py = round(view.to_screen(0.0, y)[1])
        pygame.draw.line(screen, PLANE_LINE, (area.left, py), (area.right, py))


def _dotted(scene: MakerScene, area: pygame.Rect, step: float) -> pygame.Surface:
    """The plane's ground with a dot every `step` [u], as `area` shows it; made again only when
    the view or the area changes."""
    view = scene.view
    key = (view, tuple(area), step)
    if _dots_cache["key"] != key:
        left, bottom, right, top = shown(view, tuple(area))
        xs = np.round(view.origin[0] + view.scale * lattice(left, right, step)).astype(int)
        ys = np.round(view.origin[1] - view.scale * lattice(bottom, top, step)).astype(int)
        xs, ys = xs - area.x, ys - area.y
        xs, ys = xs[(xs >= 0) & (xs < area.w)], ys[(ys >= 0) & (ys < area.h)]
        pixels = np.empty((area.h, area.w, 3), dtype=np.uint8)
        pixels[...] = SHADOW
        pixels[np.ix_(ys, xs)] = PLANE_DOT
        flat = pygame.image.frombuffer(pixels.tobytes(), area.size, "RGB")
        _dots_cache["surface"], _dots_cache["key"] = flat.copy(), key  # its own pixels
    return _dots_cache["surface"]


def _draw_coordinates(screen: pygame.Surface, scene: MakerScene, fonts: Fonts) -> None:
    """Each labelled line's coordinate [u]: x along the plane's top edge, y down its left, clear
    of the drawer's fold arrow."""
    view, area = scene.view, pygame.Rect(scene.arena_area)
    _, step = grid_steps(view.scale)
    left, bottom, right, top = shown(view, tuple(area))
    height = fonts.label.get_height()
    edge = area.left + LABEL_INSET + (HANDLE[0] if scene.layout.fold_handle else 0)
    for x in lattice(left, right, step):
        px = round(view.to_screen(x, 0.0)[0])
        shown_x = cached_text(fonts.label, f"{x + 0.0:g}", PLANE_LABEL)  # no "-0"
        screen.blit(shown_x, (px + LABEL_INSET, area.top + LABEL_INSET))
    for y in lattice(bottom, top, step):
        py = round(view.to_screen(0.0, y)[1])
        if py < area.top + LABEL_INSET + height:
            continue  # among the x's
        shown_y = cached_text(fonts.label, f"{y + 0.0:g}", PLANE_LABEL)
        screen.blit(shown_y, (edge, py + LABEL_INSET))


def _draw_rows(screen: pygame.Surface, scene: MakerScene, fonts: Fonts) -> None:
    """The Maker's own drawer: Navigator, its rays' row, its overview and zoom."""
    for button, rect in scene.layout.view_buttons:
        key = ("key", VIEW_KEYS[button])
        icon = VIEW_ICON[button]
        draw_row(
            screen, scene, fonts, rect, button, ROW_NAME[button], key, scene.show_rays, icon=icon
        )
    if scene.layout.overview is not None:
        draw_overview(screen, scene, fonts, (*scene.pos[0], scene.heading))


def _draw_foot(screen: pygame.Surface, scene: MakerScene, fonts: Fonts) -> None:
    """Nothing stays at the foot of the Maker's drawers."""


def _about(scene: MakerScene, what: object) -> tuple[str, tuple[str, ...]]:
    """What the Maker's info boxes say: a view's button."""
    return ROW_NAME[what], (TIP[what],)


def _draw_status(screen: pygame.Surface, scene: MakerScene, fonts: Fonts) -> None:
    """The keys; why something was refused; what a passkey opened (D-075)."""
    text, colour = (
        "Space: run.  Drag or arrows: move the view.  + and -: zoom.  C: centre.",
        DIM_TEXT,
    )
    if scene.message:
        text, colour = scene.message, REFUSED
    elif scene.said:
        text, colour = scene.said, LIT
    draw_status_line(screen, scene, fonts, text, colour)
