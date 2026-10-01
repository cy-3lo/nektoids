"""Drawing the arena view. Reads the scene; never changes it.

The arena shows only the light, the obstacles, the lights and the swimmers. The light is drawn
as rays of one grey, from each light until the first obstacle or swimmer, or out of view
(`Rays`): their density is the light's 1/r, and a shadow is where no ray goes; X hides them.
With I (developer) the light is a map instead, grey, dark in shadow and white where an eye
looking at a light saturates; the square root of the reading sets the grey (`tone`), and it is
smoothed over a few cells (`smooth`). Obstacles are grey discs, lights white discs with a sun,
as big as a swimmer (`LIGHT_RADIUS`), their rays leaving from the rim, a ring round the ones
visited, and a swimmer its body's circle round a wedge, its tip forward, bright when selected.
When the run is over, a banner over the arena says how it ended.

The column on the right (`arena_layout.py`): the palettes, with a tooltip naming each button and
its key; the objectives, each counted (so many of so many) and with a bar, and the time left,
its bar running down to zero, red if it runs out; the selected
swimmer's wiring on its body, plain: the parts shaded by their rate and the beads on the wires,
no numbers. With P, an inset over the
arena shows the light at its eyes as a polar plot in the arena's frame: E(phi) for each eye, a
circle for the scale, and a tick along each eye's look as long as what it reads. The plot is
exact; the map is smoothed.
"""

from __future__ import annotations

import math

import numpy as np
import pygame

from nektoids.editor.arena import POLAR_ANGLES, ArenaScene
from nektoids.editor.arena_layout import (
    ARENA_AREA,
    BANNER,
    BUTTON_KEYS,
    CIRCUIT_AREA,
    MARGIN,
    PANEL_LEFT,
    PANEL_WIDTH,
    POLAR_BOX,
    POLAR_CENTRE,
    POLAR_RADIUS,
    RULES,
    SCORE_AREA,
    TITLE_AT,
    ArenaButton,
    banner_rects,
    button_rects,
)
from nektoids.editor.arena_view import (
    DARKEST,
    edge_marker,
    polar_scale,
    ray_ends,
    shown,
    smooth,
    tone,
)
from nektoids.editor.draw import (
    ACTIVE,
    BACKGROUND,
    DARK,
    DIM_TEXT,
    PANEL,
    REFUSED,
    RULE,
    TEXT,
    Fonts,
    draw_body,
    draw_button,
    draw_symbol,
    draw_tip,
)
from nektoids.editor.schematic_draw import FULL, draw_circuit
from nektoids.graph.dynamics import RATE_MAX
from nektoids.graph.network import label
from nektoids.levels.objectives import Outcome
from nektoids.sim.arena import LIGHT_RADIUS
from nektoids.sim.optics import discs

OBSTACLE = (84, 88, 102)
RAY = (36, 38, 47)  # every ray, whatever its light
RAY_WIDTH = 2  # [px]
SUN = 1.3  # the sun's height on a light, in light radii
DARK_ARENA = tuple(int(v) for v in DARKEST)  # the arena under the rays
LIGHT = (236, 238, 244)
BODY = (228, 231, 240)  # the selected swimmer
BODY_UNSELECTED = (132, 136, 150)
SYMBOL_WIDTH = 2  # [px]
MARKER = 9  # half the length of the arrow that points at a swimmer out of view [px]
PART_DOT = 4  # an eye's reading in the polar plot [px]
POLAR_CLIP = 1.25  # the polar plot shows readings up to this many times its circle
EYE_SHADES = ((232, 234, 242), (150, 154, 166))  # one per eye in the polar plot, in turn
BAR_HEIGHT = 8  # an objective's bar [px]
ROW_PITCH = 40  # one objective [px]
VISITED_GAP = 4  # between a visited light and its ring [px]
ICON = {
    ArenaButton.EDIT: "pen",
    ArenaButton.RESTART: "backward-fast",  # to t = 0; rotate-left is the editor's Turn left
    ArenaButton.BACK: "backward-step",
    ArenaButton.STEP: "forward-step",
    ArenaButton.FAST: "forward",
    ArenaButton.ZOOM_IN: "magnifying-glass-plus",
    ArenaButton.ZOOM_OUT: "magnifying-glass-minus",
    ArenaButton.HAND: "hand",
    ArenaButton.CENTRE: "location-crosshairs",
    ArenaButton.LIGHT: "lightbulb",
}
TIP = {
    ArenaButton.EDIT: "Back to the editor",
    ArenaButton.RESTART: "Start again",
    ArenaButton.BACK: "One frame back",
    ArenaButton.STEP: "One frame",
    ArenaButton.FAST: "Fast forward",
    ArenaButton.ZOOM_IN: "Zoom in",
    ArenaButton.ZOOM_OUT: "Zoom out",
    ArenaButton.HAND: "Move the view",
    ArenaButton.CENTRE: "Centre on the swimmers and lights",
}

_map_cache: dict[str, object] = {"key": None, "surface": None}


def draw_arena(screen: pygame.Surface, scene: ArenaScene, fonts: Fonts) -> None:
    screen.fill(BACKGROUND)
    screen.set_clip(ARENA_AREA)
    _draw_field(screen, scene, fonts)
    _draw_swimmers(screen, scene)
    if scene.show_polar:
        _draw_polar(screen, scene, fonts)
    screen.set_clip(None)
    _draw_banner(screen, scene, fonts)
    _draw_panel(screen, scene, fonts)
    _draw_status(screen, scene, fonts)


def _map_rect(scene: ArenaScene) -> pygame.Rect:
    """Where the light map's grid lies on screen [px]."""
    corner, cell, (rows, cols) = scene.map_key
    left, top = scene.view.to_screen(*corner)
    size = cell * scene.view.scale
    return pygame.Rect(round(left), round(top), round(cols * size), round(rows * size))


def _map_surface(scene: ArenaScene, size: tuple[int, int]) -> pygame.Surface:
    """The light map scaled to `size` [px], rebuilt only when it or the zoom changed."""
    key = (id(scene), scene.map_version, size)
    if _map_cache["key"] != key:
        rows, cols = scene.map_key[2]
        greys = tone(smooth(scene.shade))
        small = pygame.image.frombuffer(greys.tobytes(), (cols, rows), "RGB")
        _map_cache["surface"] = pygame.transform.smoothscale(small, size)
        _map_cache["key"] = key
    return _map_cache["surface"]


def _draw_field(screen: pygame.Surface, scene: ArenaScene, fonts: Fonts) -> None:
    view, arena = scene.view, scene.arena
    pygame.draw.rect(screen, DARK_ARENA, ARENA_AREA)  # the open plane, as far as it shows
    if scene.show_map:
        rect = _map_rect(scene)
        screen.blit(_map_surface(scene, rect.size), rect.topleft)
    elif scene.show_rays:
        _draw_rays(screen, scene)
    for disc in arena.obstacles:
        centre = view.to_screen(disc.x, disc.y)
        pygame.draw.circle(screen, OBSTACLE, centre, disc.radius * view.scale)
    for light in arena.lights:
        centre = view.to_screen(light.x, light.y)
        pygame.draw.circle(screen, LIGHT, centre, LIGHT_RADIUS * view.scale)
        pygame.draw.aacircle(screen, DARK, centre, LIGHT_RADIUS * view.scale + 1, 1)
        fonts.icons.draw(screen, "sun", centre, round(SUN * LIGHT_RADIUS * view.scale), DARK)
    for light in np.flatnonzero(scene.visited.any(axis=0)):  # by any swimmer
        centre = view.to_screen(*arena.light_xy[light])
        pygame.draw.circle(screen, LIGHT, centre, LIGHT_RADIUS * view.scale + VISITED_GAP, 2)


def _draw_rays(screen: pygame.Surface, scene: ArenaScene) -> None:
    view, arena = scene.view, scene.arena
    centres, radii = discs(arena, scene.pos, scene.radius)
    left, bottom, right, top = shown(view, ARENA_AREA)
    t = scene.clock.seconds
    for light, (x, y) in enumerate(arena.light_xy):
        angles = scene.rays.angles(light, t)
        length = max(math.hypot(cx - x, cy - y) for cx in (left, right) for cy in (bottom, top))
        ends = ray_ends((x, y), angles, centres, radii, length)  # out of view, or a disc
        for a, (ex, ey) in zip(angles, ends, strict=True):
            if math.hypot(ex - x, ey - y) > LIGHT_RADIUS:  # from the light's rim outwards
                rim = (x + LIGHT_RADIUS * math.cos(a), y + LIGHT_RADIUS * math.sin(a))
                start, end = view.to_screen(*rim), view.to_screen(ex, ey)
                pygame.draw.aaline(screen, RAY, start, end, RAY_WIDTH)


def _draw_swimmers(screen: pygame.Surface, scene: ArenaScene) -> None:
    """Each swimmer its body's circle round a wedge, its tip where it heads; the selected one
    bright, the others dimmer. The view keeps angles (y flips, heading stays counter-clockwise).
    A swimmer out of view gets an arrow at the edge, pointing to where it is."""
    view = scene.view
    for k in range(len(scene.pos)):
        centre = view.to_screen(*scene.pos[k])
        colour = BODY if k == scene.selected else BODY_UNSELECTED
        radius, heading = float(scene.radius[k]) * view.scale, float(scene.heading[k])
        draw_symbol(screen, DARK, centre, radius + 1, heading, SYMBOL_WIDTH + 2)  # on a light map
        draw_symbol(screen, colour, centre, radius, heading, SYMBOL_WIDTH)
        marker = edge_marker(view, ARENA_AREA, tuple(scene.pos[k]))
        if marker is not None:
            _draw_marker(screen, *marker, colour)


def _draw_marker(screen: pygame.Surface, at: tuple[float, float], angle: float, colour) -> None:
    """An arrowhead centred on `at`, pointing along `angle` [rad, on screen], outlined so that
    it shows on the rays and on the light map alike."""
    c, s = math.cos(angle), math.sin(angle)
    tip = (at[0] + MARKER * c, at[1] + MARKER * s)
    left = (at[0] - MARKER * c - 0.8 * MARKER * s, at[1] - MARKER * s + 0.8 * MARKER * c)
    right = (at[0] - MARKER * c + 0.8 * MARKER * s, at[1] - MARKER * s - 0.8 * MARKER * c)
    pygame.draw.polygon(screen, colour, [tip, left, right])
    pygame.draw.polygon(screen, DARK, [tip, left, right], 1)


def _dot(screen: pygame.Surface, at: tuple[float, float], fill: tuple[int, int, int]) -> None:
    pygame.draw.circle(screen, fill, at, PART_DOT)
    pygame.draw.circle(screen, DARK, at, PART_DOT, 1)


# The column on the right


def _draw_panel(screen: pygame.Surface, scene: ArenaScene, fonts: Fonts) -> None:
    height = screen.get_height()
    pygame.draw.rect(screen, PANEL, (PANEL_LEFT, 0, PANEL_WIDTH, height))
    pygame.draw.line(screen, RULE, (PANEL_LEFT, 0), (PANEL_LEFT, height), 2)
    count = f"  ({scene.index + 1}/{len(scene.levels)})" if scene.developer else ""  # for Tab
    screen.blit(fonts.text.render(f"{scene.title}{count}", True, TEXT), TITLE_AT)
    for y in RULES:
        pygame.draw.line(
            screen, RULE, (PANEL_LEFT + MARGIN, y), (PANEL_LEFT + PANEL_WIDTH - MARGIN, y)
        )
    _draw_palettes(screen, scene, fonts)
    _draw_score(screen, scene, fonts)
    _draw_wiring(screen, scene, fonts)
    _draw_button_tip(screen, scene, fonts)


def _icon(scene: ArenaScene, button: ArenaButton) -> str:
    if button is ArenaButton.PLAY:
        return "play" if scene.clock.paused else "pause"
    return ICON[button]


def _tip(scene: ArenaScene, button: ArenaButton) -> str:
    if button is ArenaButton.PLAY:
        return "Play" if scene.clock.paused else "Pause"
    if button is ArenaButton.LIGHT:
        return "Hide the rays" if scene.show_rays else "Show the rays"
    return TIP[button]


def _on(scene: ArenaScene, button: ArenaButton) -> bool:
    """Whether a button that stays pressed is: fast forward, the hand, the rays."""
    return (
        (button is ArenaButton.FAST and scene.clock.speed > 1)
        or (button is ArenaButton.HAND and scene.hand)
        or (button is ArenaButton.LIGHT and scene.show_rays)
    )


def _draw_palettes(screen: pygame.Surface, scene: ArenaScene, fonts: Fonts) -> None:
    for button, rect in button_rects():
        draw_button(screen, fonts, rect, _icon(scene, button), _on(scene, button))


def _draw_button_tip(screen: pygame.Surface, scene: ArenaScene, fonts: Fonts) -> None:
    """Name and key of the button under the mouse, below it and kept on screen."""
    button = scene.tooltip
    if button is None:
        return
    x, y, w, h = dict(button_rects())[button]
    text = f"{_tip(scene, button)} ({BUTTON_KEYS[button]})"
    width = fonts.text.size(text)[0] + 16
    right = min(x + w // 2 + width // 2, screen.get_width() - 4) - 8
    draw_tip(screen, fonts, text, topright=(right, y + h + 12))


def _draw_score(screen: pygame.Surface, scene: ArenaScene, fonts: Fonts) -> None:
    """Each objective: its name, so many met of so many, a tick once all are, and a bar filling
    up; then the time left, its bar running down, all red once the time is up."""
    x, y, _, _ = SCORE_AREA
    screen.blit(fonts.small.render("Objectives", True, DIM_TEXT), (x + MARGIN, y + 4))
    rows = scene.counts()
    if not rows:
        none = fonts.small.render("None in this arena yet.", True, DIM_TEXT)
        screen.blit(none, (x + MARGIN, y + 30))
    for k, (name, met, needed) in enumerate(rows):
        fraction = met / needed if needed else 1.0
        _draw_row(screen, fonts, k, name, f"{met} of {needed}", fraction, met >= needed)
    left, limit = scene.time_left, scene.level.time_limit
    late = scene.outcome is Outcome.TIME_UP
    k = max(1, len(rows))
    fraction = left / limit if limit > 0 else 0.0
    _draw_row(screen, fonts, k, "Time left", f"{left:.1f} s", fraction, False, late)


def _draw_row(
    screen: pygame.Surface,
    fonts: Fonts,
    k: int,
    name: str,
    value: str,
    fraction: float,
    done: bool,
    failed: bool = False,
) -> None:
    """Row k of the objectives: its name, its value at the right with a tick if `done`, and a
    bar `fraction` full; the text and the bar's track red if `failed`."""
    x, y, w, _ = SCORE_AREA
    left, width, top = x + MARGIN, w - 2 * MARGIN, y + 28 + k * ROW_PITCH
    colour = REFUSED if failed else TEXT
    screen.blit(fonts.text.render(name, True, colour), (left, top))
    shown = fonts.text.render(value, True, colour)
    screen.blit(shown, shown.get_rect(topright=(left + width, top)))
    if done:
        tick_at = (left + width - shown.get_width() - 14, top + 7)
        fonts.icons.draw(screen, "check", tick_at, 14, FULL)
    bar = pygame.Rect(left, top + 20, width, BAR_HEIGHT)
    pygame.draw.rect(screen, REFUSED if failed else RULE, bar, border_radius=3)
    filled = bar.copy()
    filled.width = round(width * min(1.0, max(0.0, fraction)))
    if filled.width > 0:
        pygame.draw.rect(screen, FULL, filled, border_radius=3)


def _draw_wiring(screen: pygame.Surface, scene: ArenaScene, fonts: Fonts) -> None:
    """The selected swimmer's wiring on its body: parts shaded by rate, beads, no numbers."""
    x, y, w, h = CIRCUIT_AREA
    if scene.selected is None:
        note = "Click the swimmer to see its wiring"
    elif not scene.circuit.cells:
        back = "F3" if scene.developer else BUTTON_KEYS[ArenaButton.EDIT]
        note = f"Your board is empty: build one in the editor ({back})"
    else:
        circuit = scene.circuit
        screen.set_clip(CIRCUIT_AREA)
        draw_body(screen, circuit.board.cells, circuit.view.size, circuit.view.origin)
        draw_circuit(screen, circuit, scene.y, fonts, plain=True)
        screen.set_clip(None)
        return
    text = fonts.small.render(note, True, DIM_TEXT)
    screen.blit(text, text.get_rect(center=(x + w // 2, y + h // 2)))


# Developer tools


def _draw_polar(screen: pygame.Surface, scene: ArenaScene, fonts: Fonts) -> None:
    """The light at the selected swimmer's eyes: E(phi) at each eye, y up as in the arena."""
    curves = scene.eye_polar()
    if len(curves) == 0:
        return
    pygame.draw.rect(screen, PANEL, POLAR_BOX, border_radius=6)
    pygame.draw.rect(screen, RULE, POLAR_BOX, 1, border_radius=6)
    (cx, cy), big = POLAR_CENTRE, POLAR_RADIUS
    title = fonts.small.render("E(phi) = integral of I cos theta", True, DIM_TEXT)
    screen.blit(title, title.get_rect(center=(cx, cy - big - 26)))
    pygame.draw.line(screen, RULE, (cx - big, cy), (cx + big, cy), 1)
    pygame.draw.line(screen, RULE, (cx, cy - big), (cx, cy + big), 1)
    pygame.draw.circle(screen, RULE, (cx, cy), big, 1)
    k = scene.selected
    heading = float(scene.heading[k])
    scale = polar_scale(float(curves.max()), RATE_MAX)
    for e, curve in enumerate(curves):
        shade = EYE_SHADES[e % len(EYE_SHADES)]
        rho = big * np.minimum(curve / scale, POLAR_CLIP)
        outline = np.column_stack(
            (cx + rho * np.cos(POLAR_ANGLES), cy - rho * np.sin(POLAR_ANGLES))
        )
        pygame.draw.lines(screen, shade, False, outline.tolist(), 2)
        look = heading + math.radians(60.0 * int(scene.eye_facing[e]))
        reach = big * min(float(scene.eyes[k, e]) / scale, POLAR_CLIP)
        tip = (cx + reach * math.cos(look), cy - reach * math.sin(look))
        pygame.draw.line(screen, shade, (cx, cy), tip, 1)
        _dot(screen, tip, shade)
        name = fonts.small.render(label(scene.net, int(scene.net.eyes[e])), True, shade)
        at = (cx + (big + 14) * math.cos(look), cy - (big + 14) * math.sin(look))
        screen.blit(name, name.get_rect(center=at))
    draw_symbol(screen, BODY, (cx, cy), 9, heading, 1)
    legend = fonts.small.render(f"circle: {scale:g} (saturation: 1)", True, DIM_TEXT)
    screen.blit(legend, legend.get_rect(center=(cx, cy + big + 26)))


def _draw_banner(screen: pygame.Surface, scene: ArenaScene, fonts: Fonts) -> None:
    """Over the arena's top, once the run is over: how it ended, and what each objective got."""
    ended = scene.outcome
    if ended is None:
        return
    if ended is Outcome.WON:
        head = f"Done in {scene.clock.seconds:.2f} s"
    else:
        head = f"Time is up ({scene.level.time_limit:g} s)"
    rows = [f"{name}: {met} of {needed}" for name, met, needed in scene.counts()]
    lines = [fonts.text.render(head, True, TEXT)]
    lines += [fonts.small.render(row, True, DIM_TEXT) for row in [*rows, "0: start again"]]
    box = pygame.Rect(BANNER)
    pygame.draw.rect(screen, PANEL, box, border_radius=6)
    pygame.draw.rect(screen, LIGHT if ended is Outcome.WON else RULE, box, 2, border_radius=6)
    top = box.top + 10
    for line in lines:
        screen.blit(line, line.get_rect(midtop=(box.centerx, top)))
        top += line.get_height() + 4
    for button, rect in banner_rects(scene.banner_buttons):
        label = "Next level" if button is ArenaButton.NEXT else "Edit"
        pygame.draw.rect(screen, ACTIVE, rect, border_radius=6)
        shown = fonts.text.render(f"{label} ({BUTTON_KEYS[button]})", True, TEXT)
        screen.blit(shown, shown.get_rect(center=pygame.Rect(rect).center))


def _draw_status(screen: pygame.Surface, scene: ArenaScene, fonts: Fonts) -> None:
    clock = scene.clock
    state = "over" if scene.outcome is not None else "paused" if clock.paused else "running"
    speed = f" x{clock.speed}" if clock.speed > 1 else ""
    cost = f" ({scene.map_ms:.1f} ms)" if scene.show_map else ""
    limit = f"{scene.level.time_limit:g}"
    if scene.developer:
        keys = f"I: map{cost}.  P: polar plot.  Wheel, L, R: turn.  Tab: arena.  F3: editor."
    else:
        keys = "Space: play.  0: start again.  Esc: back to the editor."
    text = f"t = {clock.seconds:5.2f} / {limit} s, {state}{speed}.  {keys}"
    screen.blit(fonts.small.render(text, True, DIM_TEXT), (16, screen.get_height() - 22))
