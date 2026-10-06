"""Drawing the arena view. Reads the scene; never changes it.

The arena shows only the light, the obstacles, the lights and the swimmers. The light is drawn
as rays of one grey, from each light until the first obstacle or swimmer, or out of view
(`Rays`): their density is the light's 1/r, and a shadow is where no ray goes; X hides them.
With I (developer) the light is a map instead, grey, dark in shadow and white where an eye
looking at a light saturates; the square root of the reading sets the grey (`tone`), and it is
smoothed over a few cells (`smooth`). Obstacles are grey discs, lights white discs with a bulb,
as big as a swimmer (`LIGHT_RADIUS`), their rays leaving from the rim, a ring round the ones
visited, the marks empty grey circles, lit once the goal on them is met (D-306, D-307), and
a swimmer its body's circle round a wedge, its tip forward, bright when selected, at work
(D-076, `marks`): its parts' faces and outlines, its flames, the light its eyes draw in, a
segment for its velocity and an arc for its spin. When the run is over, a banner over the arena
says how it ended: done, lost and why, or out of time.

Round the arena, the frame the editor has too (D-051, D-057, `draw.py`): the bar, the open
drawer, the tabs with the level's line under them. Under the arena, the controls, each with a
tooltip naming it and its key; the timeline, the part of the time allowed already run in a
lighter grey, the part played brighter, and a red mark where the run ended (D-033); the time.
The drawers: Objectives, each objective counted (so many of so many) with a bar, red if it lost
the run, and the time left, its bar running down to zero, red if it runs out; Inside, the
selected swimmer's wiring on its body, plain: the beads on the wires and a level meter by each
eye and thruster, no numbers; Score, the level's wins; Navigator, the view's buttons. The
status line under it all recalls the keys. With P, an inset over the arena shows the light at
its eyes as a polar plot in the arena's frame: E(phi) for each eye, a circle for the scale, and
a tick along each eye's look as long as what it reads. The plot is exact; the map is smoothed.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np
import pygame

from nektoids.editor.arena import POLAR_ANGLES, ArenaScene
from nektoids.editor.arena_layout import (
    BUTTON_KEYS,
    DRAWER_BODY,
    POLAR_RADIUS,
    TIMELINE_BAR,
    ArenaButton,
    banner_rect,
    banner_rects,
    control_rects,
    polar_box,
    summary_at,
    timeline_rect,
    timeline_x,
)
from nektoids.editor.arena_view import (
    MAX_SCALE,
    ArenaView,
    Rays,
    edge_marker,
    polar_scale,
    ray_ends,
    shown,
    smooth,
    tone,
    view_of,
)
from nektoids.editor.devdrive import DT, TICKS_PER_FRAME
from nektoids.editor.draw import (
    INFO_ICON,
    ROW_NAME,
    TIP,
    Fonts,
    draw_bar,
    draw_body,
    draw_button,
    draw_circuit,
    draw_drawer,
    draw_info,
    draw_level_map,
    draw_note,
    draw_row,
    draw_status_line,
    draw_symbol,
    draw_tabs,
    draw_tip,
    draw_tooltip,
    draw_zoom,
)
from nektoids.editor.icons import VIEW_ICON
from nektoids.editor.layout import MARGIN, VIEW_KEYS, Drawer, Goal, Rect, ViewButton, level_of
from nektoids.editor.marks import at_work
from nektoids.editor.marks_draw import draw_motion, draw_parts, draw_under
from nektoids.editor.palette import (
    ACTIVE,
    BACKGROUND,
    BODY,
    BODY_UNSELECTED,
    BUTTON,
    DARK,
    DIM_TEXT,
    EYE_SHADES,
    FULL,
    LIGHT,
    LIT,
    MARK,
    OBSTACLE,
    PANEL,
    RAY,
    REFUSED,
    RULE,
    RUN_SO_FAR,
    SHADOW,
    TEXT,
    TO_BEAT,
    WIN,
)
from nektoids.graph.dynamics import RATE_MAX
from nektoids.graph.network import label
from nektoids.levels.objectives import Outcome
from nektoids.levels.proof import to_beat
from nektoids.levels.score import Score, front
from nektoids.sim.arena import LIGHT_RADIUS, Arena
from nektoids.sim.optics import discs

if TYPE_CHECKING:
    from nektoids.editor.maker import MakerScene

RAY_WIDTH = 2  # [px]
BULB = 1.6  # the bulb's height on a light, in light radii (D-076)
SYMBOL_WIDTH = 2  # [px]
MARKER = 9  # half the length of the arrow that points at a swimmer out of view [px]
PLAYHEAD = 6  # [px]
END_MARK = 3  # the red mark across the timeline where the run ended [px]
PART_DOT = 4  # an eye's reading in the polar plot [px]
POLAR_CLIP = 1.25  # the polar plot shows readings up to this many times its circle
GOAL_BAR = 3  # an objective's bar, along its row's foot [px]
VISITED_GAP = 4  # between a visited light and its ring [px]
PLOT_PARTS = 4  # the plot of the wins spans at least this many parts
WIN_DOT = 4  # a win on that plot; this run's ring sits 4 px round it [px]
MARK_CROSS = 5  # the arms of the cross on a mark's centre [px]
ICON = {
    ArenaButton.RESTART: "backward-fast",  # to t = 0; rotate-left is the editor's Turn left
    ArenaButton.STEP: "forward-step",
    ArenaButton.FAST: "forward",
}
CONTROL_TIP = {
    ArenaButton.RESTART: "Start again",
    ArenaButton.STEP: "A step (0.1 s)",
    ArenaButton.FAST: "Fast forward",
}

_map_cache: dict[str, object] = {"key": None, "surface": None}


def draw_arena(screen: pygame.Surface, scene: ArenaScene, fonts: Fonts) -> None:
    screen.fill(BACKGROUND)
    screen.set_clip(scene.arena_area)
    _draw_field(screen, scene, fonts)
    _draw_swimmers(screen, scene)
    if scene.show_polar:
        _draw_polar(screen, scene, fonts)
    screen.set_clip(None)
    _draw_banner(screen, scene, fonts)
    draw_tabs(screen, scene, fonts)
    _draw_controls(screen, scene, fonts)
    _draw_status(screen, scene, fonts)
    draw_bar(screen, scene, fonts)
    draw_drawer(screen, scene, fonts, _draw_rows, _draw_foot)
    draw_tooltip(screen, scene, fonts)
    _draw_control_tip(screen, scene, fonts)
    draw_info(screen, scene, fonts, _about)


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
    pygame.draw.rect(screen, SHADOW, scene.arena_area)  # the open plane, as far as it shows
    if scene.show_map:
        rect = _map_rect(scene)
        screen.blit(_map_surface(scene, rect.size), rect.topleft)
    elif scene.show_rays:
        t, area = scene.clock.seconds, scene.arena_area
        draw_rays(screen, view, area, arena, scene.rays, t, scene.pos, scene.radius)
    draw_marks(screen, view, scene.level.marks, lit=scene.marks_lit)
    draw_items(screen, fonts, view, arena)
    for light in np.flatnonzero(scene.lights_reached):  # by any swimmer
        centre = view.to_screen(*arena.light_xy[light])
        pygame.draw.circle(screen, LIGHT, centre, LIGHT_RADIUS * view.scale + VISITED_GAP, 2)


def draw_items(screen: pygame.Surface, fonts: Fonts, view: ArenaView, arena: Arena) -> None:
    """The plane's items: the obstacles, grey discs; the lights, white discs with a bulb."""
    for disc in arena.obstacles:
        centre = view.to_screen(disc.x, disc.y)
        pygame.draw.circle(screen, OBSTACLE, centre, disc.radius * view.scale)
    for light in arena.lights:
        draw_light(screen, fonts, view.to_screen(light.x, light.y), LIGHT_RADIUS * view.scale)


def draw_marks(
    screen: pygame.Surface, view: ArenaView, marks, colour=MARK, width: int = 2, lit=()
) -> None:
    """The level's marks (D-306): each an empty circle `width` [px] wide, grey, or, where `lit`
    says so, lit (D-307, D-318), a cross on its centre, under the lights and the obstacles."""
    for k, mark in enumerate(marks):
        ink = LIGHT if k < len(lit) and lit[k] else colour
        draw_mark(screen, view.to_screen(*mark.at), mark.value * view.scale, width, ink)


def draw_mark(screen: pygame.Surface, centre, radius: float, width: int = 2, colour=MARK) -> None:
    """A mark of `radius` [px] at `centre` [px]: an empty circle, a small cross on its centre."""
    cx, cy = centre
    pygame.draw.circle(screen, colour, centre, radius, width)
    arm = min(MARK_CROSS, radius / 2)
    pygame.draw.line(screen, colour, (cx - arm, cy), (cx + arm, cy), width)
    pygame.draw.line(screen, colour, (cx, cy - arm), (cx, cy + arm), width)


def draw_light(screen: pygame.Surface, fonts: Fonts, centre, radius: float) -> None:
    """A light: a white disc of `radius` [px], outlined, a bulb on it (D-076)."""
    pygame.draw.circle(screen, LIGHT, centre, radius)
    pygame.draw.aacircle(screen, DARK, centre, radius + 1, 1)
    fonts.icons.draw(screen, "lightbulb", centre, round(BULB * radius), DARK)


def draw_rays(
    screen: pygame.Surface,
    view: ArenaView,
    area: Rect,
    arena: Arena,
    rays: Rays,
    t: float,
    pos: np.ndarray,
    radius: np.ndarray,
) -> None:
    """Each light's rays at `t` [s], from its rim to the first disc they meet, the swimmers' at
    `pos` (N, 2) [u] of `radius` (N,) [u] among them, or out of `area`."""
    centres, radii = discs(arena, pos, radius)
    left, bottom, right, top = shown(view, area)
    for light, (x, y) in enumerate(arena.light_xy):
        angles = rays.angles(light, t)
        length = max(math.hypot(cx - x, cy - y) for cx in (left, right) for cy in (bottom, top))
        ends = ray_ends((x, y), angles, centres, radii, length)  # out of view, or a disc
        for a, (ex, ey) in zip(angles, ends, strict=True):
            if math.hypot(ex - x, ey - y) > LIGHT_RADIUS:  # from the light's rim outwards
                rim = (x + LIGHT_RADIUS * math.cos(a), y + LIGHT_RADIUS * math.sin(a))
                start, end = view.to_screen(*rim), view.to_screen(ex, ey)
                pygame.draw.aaline(screen, RAY, start, end, RAY_WIDTH)


def _draw_swimmers(screen: pygame.Surface, scene: ArenaScene) -> None:
    """Each swimmer its body's circle round a wedge, its tip where it heads; the selected one
    bright, the others dimmer; each at work (D-076), its specks under it, its parts and motion
    over it, the specks moving with the run's frames; the specks and the motion as Navigator
    sets them. The view keeps angles (y flips, heading stays counter-clockwise). A swimmer out
    of view gets an arrow at the edge, pointing to where it is."""
    view = scene.view
    frame = scene.clock.tick // TICKS_PER_FRAME
    for k in range(len(scene.pos)):
        centre = view.to_screen(*scene.pos[k])
        colour = BODY if k == scene.selected else BODY_UNSELECTED
        radius, heading = float(scene.radius[k]) * view.scale, float(scene.heading[k])
        pose = (float(scene.pos[k, 0]), float(scene.pos[k, 1]), heading)
        body = at_work(
            scene.arena,
            scene.net,
            scene.circuit.board.cells,
            scene.state[k],
            pose,
            float(scene.radius[k]),
            frame,
        )
        if scene.settings.streams:
            draw_under(screen, view, body)
        draw_symbol(screen, DARK, centre, radius + 1, heading, SYMBOL_WIDTH + 2)  # on a light map
        draw_symbol(screen, colour, centre, radius, heading, SYMBOL_WIDTH)
        draw_parts(screen, view, body)
        if scene.settings.motion:
            draw_motion(screen, view, body.velocity, body.spin)
        marker = edge_marker(view, scene.arena_area, tuple(scene.pos[k]))
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


# Under the arena: the controls


def _draw_controls(screen: pygame.Surface, scene: ArenaScene, fonts: Fonts) -> None:
    """Start again, play or pause, a step, fast forward; the timeline; how many objectives are
    met, lit once all are, red once one is lost or the time is up (D-060). A level with none, the
    sandbox, shows its time there instead."""
    strip = pygame.Rect(scene.layout.controls_area)
    pygame.draw.rect(screen, PANEL, strip)
    pygame.draw.line(screen, RULE, strip.topleft, strip.topright)
    for button, rect in control_rects(scene.layout):
        lit = scene.lit_ink if button is ArenaButton.PLAY and "play" in scene.lit else None
        draw_button(screen, fonts, rect, _icon(scene, button), _on(scene, button), lit=lit)
    _draw_timeline(screen, scene, fonts)
    counts = scene.counts()
    met = sum(c.met >= c.needed and not c.lost for c in counts)
    if not counts:
        text, colour = _elapsed(scene), DIM_TEXT
    else:
        text = f"{met}/{len(counts)} objective" + ("s" if len(counts) > 1 else "")
        lost = any(c.lost for c in counts) or scene.outcome is Outcome.TIME_UP
        colour = REFUSED if lost else LIT if met == len(counts) else DIM_TEXT
    shown = fonts.small.render(text, True, colour)
    screen.blit(shown, shown.get_rect(midright=summary_at(scene.layout)))


def _elapsed(scene: ArenaScene) -> str:
    return f"{scene.clock.seconds:.1f} / {scene.level.time_limit:g} s"


def _draw_timeline(screen: pygame.Surface, scene: ArenaScene, fonts: Fonts) -> None:
    """The time allowed as a bar: run so far lighter, played brighter, the playhead, and a red
    mark where the run ended, won or out of time."""
    layout = scene.layout
    x, y, w, h = timeline_rect(layout)
    limit, run = scene.level.time_limit, scene.recording
    bar = pygame.Rect(x, y + (h - TIMELINE_BAR) // 2, w, TIMELINE_BAR)
    pygame.draw.rect(screen, RULE, bar, border_radius=3)
    for seconds, colour in ((run.frontier * DT, RUN_SO_FAR), (scene.clock.seconds, FULL)):
        part = bar.copy()
        part.width = round(timeline_x(layout, seconds, limit) - x)
        if part.width > 0:
            pygame.draw.rect(screen, colour, part, border_radius=3)
    if scene.ended_at is not None:
        end = round(timeline_x(layout, scene.ended_at * DT, limit))
        pygame.draw.rect(screen, REFUSED, (end - END_MARK // 2, y + 1, END_MARK, h - 2))
    head = (round(timeline_x(layout, scene.clock.seconds, limit)), bar.centery)
    pygame.draw.circle(screen, FULL, head, PLAYHEAD)
    pygame.draw.circle(screen, DARK, head, PLAYHEAD, 1)


def _icon(scene: ArenaScene, button: ArenaButton) -> str:
    if button is ArenaButton.PLAY:
        return "play" if scene.clock.paused else "pause"
    return ICON[button]


def _tip(scene: ArenaScene, button: ArenaButton) -> str:
    if button is ArenaButton.PLAY:
        return "Play" if scene.clock.paused else "Pause"
    return CONTROL_TIP[button]


def _on(scene: ArenaScene, button: ArenaButton) -> bool:
    """Whether a control that stays pressed is: fast forward."""
    return button is ArenaButton.FAST and scene.clock.speed > 1


def _draw_control_tip(screen: pygame.Surface, scene: ArenaScene, fonts: Fonts) -> None:
    """Name and key of the control under the mouse, over it."""
    button = scene.control_tip
    if button is None:
        return
    if button == "timeline":  # the time, at the mouse
        _, y, _, _ = timeline_rect(scene.layout)
        draw_tip(screen, fonts, _elapsed(scene), midbottom=(scene.pointer[0], y - 8))
        return
    x, y, w, _ = dict(control_rects(scene.layout))[button]
    key = f" ({BUTTON_KEYS[button]})" if scene.settings.key_hints else ""
    draw_tip(screen, fonts, _tip(scene, button) + key, midbottom=(x + w // 2, y - 10))


# The drawers


def _draw_foot(screen: pygame.Surface, scene: ArenaScene, fonts: Fonts) -> None:
    """What stays at the foot of the run's drawers: the objectives, under every one (D-065)."""
    if scene.layout.goal_area is not None:
        x, y, w, _ = scene.layout.goal_area
        pygame.draw.line(screen, RULE, (x + MARGIN, y), (x + w - MARGIN, y))
        _draw_goals(screen, scene, fonts)


def _draw_rows(screen: pygame.Surface, scene: ArenaScene, fonts: Fonts) -> None:
    """The run's own drawers: Inside, Score, Navigator."""
    drawer = scene.layout.drawer
    if drawer is Drawer.INSIDE:
        _draw_wiring(screen, scene, fonts)
    elif drawer is Drawer.SCORE:
        _draw_wins(screen, scene, fonts)
    if scene.layout.overview is not None:
        draw_overview(screen, scene, fonts, (*scene.pos[0], float(scene.heading[0])))
    for button, rect in scene.layout.view_buttons:
        active = {
            ViewButton.PAN: scene.hand,
            ViewButton.RAYS: scene.show_rays,
            ViewButton.MOTION: scene.settings.motion,
            ViewButton.STREAMS: scene.settings.streams,
        }.get(button, False)
        key = ("key", VIEW_KEYS[button])
        draw_row(
            screen,
            scene,
            fonts,
            rect,
            button,
            ROW_NAME[button],
            key,
            active,
            icon=VIEW_ICON[button],
        )


def draw_overview(
    screen: pygame.Surface,
    scene: ArenaScene | MakerScene,
    fonts: Fonts,
    pose: tuple[float, float, float],
) -> None:
    """Navigator's overview (D-060): the level small, as far as the overview's extent (D-066),
    the swimmer at `pose` (x, y [u], heading [rad]), a frame round what the main screen shows;
    under it, the zoom (D-065)."""
    area = pygame.Rect(scene.layout.overview)
    small = view_of(scene.layout.overview, scene.extent())
    left, bottom, right, top = shown(scene.view, scene.arena_area)
    (x0, y0), (x1, y1) = small.to_screen(left, top), small.to_screen(right, bottom)
    frame = pygame.Rect(round(x0), round(y0), round(x1 - x0), round(y1 - y0))
    draw_level_map(screen, scene.level, area, pose, frame, small)
    draw_zoom(screen, scene, fonts, level_of(scene.view.scale, scene.least_zoom(), MAX_SCALE))


def _about(scene: ArenaScene, what: object) -> tuple[str, tuple[str, ...]]:
    """What the run's info boxes say: an objective, the time left, a view's button."""
    if isinstance(what, Goal) and what.index is None:
        return "Time left", (f"The run ends after {scene.level.time_limit:g} s.",)
    if isinstance(what, Goal):
        objective = scene.level.objectives[what.index]
        level = scene.level
        return objective.name(level), (objective.about(level),)
    return ROW_NAME[what], (TIP[what],)


def _draw_goals(screen: pygame.Surface, scene: ArenaScene, fonts: Fonts) -> None:
    """Each objective: its name; under it a bar filling up and so many met of so many, a tick
    once all are, all red if it lost the run; then the time left, its bar running down, red once
    up."""
    counts = scene.counts()
    for goal, rect in scene.layout.goal_rows:
        if goal.index is None:
            left, limit = scene.time_left, scene.level.time_limit
            fraction = left / limit if limit > 0 else 0.0
            late = scene.outcome is Outcome.TIME_UP
            row = ("Time left", f"{left:.1f} s", "clock", fraction, False, late)
        else:
            count, objective = counts[goal.index], scene.level.objectives[goal.index]
            done = count.met >= count.needed and not count.lost
            fraction = 0.0 if count.lost else count.progress
            value = f"{count.met} of {count.needed}"
            row = (count.name, value, objective.icon, fraction, done, count.lost)
        _draw_goal(screen, scene, fonts, goal, rect, *row)


def _draw_goal(
    screen: pygame.Surface,
    scene: ArenaScene,
    fonts: Fonts,
    goal: Goal,
    rect,
    name: str,
    value: str,
    icon: str,
    fraction: float,
    done: bool,
    failed: bool,
) -> None:
    """An objective's row, on two lines: its icon, name and info disc; its bar and count."""
    box = pygame.Rect(rect)
    pygame.draw.rect(screen, BUTTON, box, border_radius=6)
    ink = REFUSED if failed else TEXT
    first, second = box.top + 14, box.bottom - 12
    fonts.icons.draw(screen, icon, (box.left + 20, first), 16, ink)
    shown = fonts.name.render(name, True, ink)
    screen.blit(shown, (box.left + 42, first - shown.get_height() // 2))
    disc = pygame.Rect(dict(scene.layout.info_buttons)[goal]).center
    fonts.icons.draw(
        screen, "circle-info", disc, INFO_ICON, TEXT if goal == scene.info else DIM_TEXT
    )
    right = box.right - 10
    count = fonts.small.render(value, True, ink)
    screen.blit(count, count.get_rect(midright=(right, second)))
    end = right - count.get_width() - 10
    if done:
        fonts.icons.draw(screen, "check", (end - 6, second), 12, LIT)
        end -= 18
    bar = pygame.Rect(box.left + 42, second - GOAL_BAR // 2, end - box.left - 42, GOAL_BAR)
    pygame.draw.rect(screen, REFUSED if failed else RULE, bar)
    filled = bar.copy()
    filled.width = round(bar.width * min(1.0, max(0.0, fraction)))
    if filled.width > 0:
        pygame.draw.rect(screen, FULL, filled)


def _draw_wiring(screen: pygame.Surface, scene: ArenaScene, fonts: Fonts) -> None:
    """The selected swimmer's wiring on its body: beads, a meter by each eye and thruster."""
    x, y, w, h = DRAWER_BODY
    if scene.selected is None:
        note = "Click the swimmer to see its wiring"
    elif not scene.circuit.cells:
        back = "F7" if scene.developer else BUTTON_KEYS[ArenaButton.EDIT]
        note = f"Your board is empty: build one in the editor ({back})"
    else:
        circuit = scene.circuit
        screen.set_clip(DRAWER_BODY)
        draw_body(screen, circuit.board.cells, circuit.view.size, circuit.view.origin)
        draw_circuit(screen, circuit, scene.y, fonts, plain=True)
        screen.set_clip(None)
        return
    draw_note(screen, fonts, note, (x + MARGIN, y + 8), DRAWER_BODY[2] - 2 * MARGIN)


# Developer tools


def _draw_polar(screen: pygame.Surface, scene: ArenaScene, fonts: Fonts) -> None:
    """The light at the selected swimmer's eyes: E(phi) at each eye, y up as in the arena."""
    curves = scene.eye_polar()
    if len(curves) == 0:
        return
    box = pygame.Rect(polar_box(scene.layout))
    pygame.draw.rect(screen, PANEL, box, border_radius=6)
    pygame.draw.rect(screen, RULE, box, 1, border_radius=6)
    (cx, cy), big = (box.centerx, box.top + 128), POLAR_RADIUS
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
        head = f"Done in {scene.clock.seconds:.2f} s with {scene.parts} parts"
    elif ended is Outcome.LOST and scene.lost_by is not None:
        head = f"{scene.lost_by.broken(scene.level)} at {scene.clock.seconds:.2f} s"
    else:
        head = f"Time is up ({scene.level.time_limit:g} s)"
    rows = [f"{row.name}: {row.met} of {row.needed}" for row in scene.counts()]
    lines = [fonts.text.render(head, True, TEXT)]
    lines += [fonts.small.render(row, True, DIM_TEXT) for row in rows]  # 0 starts again
    if ended is Outcome.WON and scene.passkey is not None:  # to keep: it opens the next (D-075)
        word, label = scene.passkey
        lines.append(fonts.small.render(f"Passkey for {label}: {word}", True, LIT))
    box = pygame.Rect(banner_rect(scene.layout))
    pygame.draw.rect(screen, PANEL, box, border_radius=6)
    pygame.draw.rect(screen, LIGHT if ended is Outcome.WON else RULE, box, 2, border_radius=6)
    top = box.top + 10
    for line in lines:
        screen.blit(line, line.get_rect(midtop=(box.centerx, top)))
        top += line.get_height() + 4
    for button, rect in banner_rects(scene.layout, scene.banner_buttons):
        label = (scene.next_label or "Next level") if button is ArenaButton.NEXT else "Edit"
        pygame.draw.rect(screen, ACTIVE, rect, border_radius=6)
        shown = fonts.name.render(f"{label} ({BUTTON_KEYS[button]})", True, TEXT)
        screen.blit(shown, shown.get_rect(center=pygame.Rect(rect).center))


def _won(scene: ArenaScene) -> bool:
    """The player's run stands won, at its end: Score rings its point."""
    return not scene.developer and scene.outcome is Outcome.WON and scene.ended_at is not None


def _draw_wins(screen: pygame.Surface, scene: ArenaScene, fonts: Fonts) -> None:
    """The level's wins this session (D-028, D-046): time against parts, the Pareto front a
    staircase through the points no other beats, the others dimmed, this run ringed if won; under
    them, the level's proof, the score to beat, a dark grey cross (D-330)."""
    this = Score(scene.parts, scene.ended_at) if _won(scene) else None
    scores = scene.scores | ({this} if this is not None else set())
    beat = to_beat(scene.level)
    x, y, w, h = DRAWER_BODY
    if not scores and beat is None:
        note = "No win yet. Each win is a point here: its time and its parts."
        draw_note(screen, fonts, note, (x + MARGIN, y + 8), w - 2 * MARGIN)
        return
    notes = ("Time against parts.", *(("The cross: one to beat.",) if beat else ()))
    line = fonts.small.get_linesize()
    for k, text in enumerate(notes):
        screen.blit(fonts.small.render(text, True, DIM_TEXT), (x + MARGIN, y + 4 + k * line))
    below = (len(notes) - 1) * line  # the plot, under the notes
    plot = pygame.Rect(x + MARGIN + 40, y + 36 + below, w - 2 * MARGIN - 52, h - 96 - below)
    shown = scores | ({beat} if beat is not None else set())
    low = min(s.parts for s in shown) - 1
    high = max(max(s.parts for s in shown) + 1, low + PLOT_PARTS)
    limit = round(scene.level.time_limit / DT)  # the time axis runs to the time allowed

    def at(parts: int, ticks: int) -> tuple[float, float]:
        return (
            plot.left + (parts - low) / (high - low) * plot.width,
            plot.bottom - ticks / limit * plot.height,
        )

    pygame.draw.line(screen, RULE, plot.topleft, plot.bottomleft)
    pygame.draw.line(screen, RULE, plot.bottomleft, plot.bottomright)
    for parts in range(low, high + 1):
        label = fonts.small.render(str(parts), True, DIM_TEXT)
        screen.blit(label, label.get_rect(midtop=(at(parts, 0)[0], plot.bottom + 4)))
    unit = fonts.small.render("parts", True, DIM_TEXT)
    screen.blit(unit, unit.get_rect(midtop=(plot.centerx, plot.bottom + 20)))
    for ticks, text in ((0, "0 s"), (limit, f"{scene.level.time_limit:g} s")):
        label = fonts.small.render(text, True, DIM_TEXT)
        screen.blit(label, label.get_rect(midright=(plot.left - 6, at(low, ticks)[1])))
    if beat is not None:  # under the wins: one on it covers it
        cx, cy, r = *at(beat.parts, beat.ticks), WIN_DOT + 1
        pygame.draw.line(screen, TO_BEAT, (cx - r, cy - r), (cx + r, cy + r), 2)
        pygame.draw.line(screen, TO_BEAT, (cx - r, cy + r), (cx + r, cy - r), 2)
    best = front(scores)
    if best:
        stairs = [(at(best[0].parts, 0)[0], plot.top)]
        for score in best:
            x, y = at(score.parts, score.ticks)
            stairs += [(x, stairs[-1][1]), (x, y)]
        stairs.append((plot.right, stairs[-1][1]))
        pygame.draw.lines(screen, LIGHT, False, stairs[1:])
    for score in sorted(scores):
        colour = WIN if score in best else DIM_TEXT
        pygame.draw.circle(screen, colour, at(score.parts, score.ticks), WIN_DOT)
    if this is not None:
        pygame.draw.circle(screen, TEXT, at(this.parts, this.ticks), WIN_DOT + 4, 1)


def _draw_status(screen: pygame.Surface, scene: ArenaScene, fonts: Fonts) -> None:
    """Only the keys: the time is on the timeline and over it."""
    keys = "Space: play.  .: a step.  0: again."  # F: fast, in its tooltip
    if scene.developer:
        cost = f" ({scene.map_ms:.1f} ms)" if scene.show_map else ""
        text = f"{keys}  I: map{cost}.  P: polar.  Wheel, L, R: turn.  Tab: arena.  F7: editor."
    else:
        text = f"{keys}  Tab: editor.  Esc: Chapters."
    text, colour = (scene.message, REFUSED) if scene.message else (text, DIM_TEXT)
    if scene.said and not scene.message:  # a passkey that opened a level (D-075)
        text, colour = scene.said, LIGHT
    draw_status_line(screen, scene, fonts, text, colour)
