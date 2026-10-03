"""The arena view: a swimmer running your board in a lit arena (D-018, D-019).

Two modes. The player's (`developer=False`): one level, opened by Run in the editor; Edit (Esc)
goes back to it, and once the level is won the banner's Next level (Enter) moves on. Nothing
touches the programmed swimmer: no dragging or turning it, and none of the developer's tools.
The developer's (F3): every level, Tab between them, and the tools below.

Left, the arena: the light as rays (or, with I, as a map), the obstacles and the lights, and the
swimmer as a circle round a wedge; its eyes and thrusters sit where the board puts them on it.
Round it, the frame the editor has (`frame.Frame`, D-057): Objectives, how many of each are met;
Inside, the selected swimmer's wiring, live: its eyes read the light every tick and every node
follows with its lag (D-017); Score; Navigator; under the arena the controls and the timeline.
The thrusters push against Stokes drag (D-022): the swimmer swims, sliding round the obstacles,
in an open plane. A run stops when every objective is met, one loses it, or the level's time is
up (D-023, D-040); 0 starts it again. P shows, over the arena, the light at its eyes as a polar
plot: what a flat eye there would read facing each way, E(phi), with a tick where each eye
looks.

Mouse: the frame, Navigator's rows, the controls; click the swimmer to show its wiring (it is
shown to begin with), click beside it to hide it, drag it to move it (with the hand, drag the
view); the wheel turns it by 15°, as do L (left, counter-clockwise) and R, the editor's turn
keys. Keys (`arena_layout.BUTTON_KEYS`, named in the tooltips), the same as the editor's
wherever they do the same: 0 starts again, Space plays or pauses, `.` runs a step of 0.1 s, F
fast forwards, + and - zoom, H takes the hand (then the arrows drag the view), C centres, X
shows or hides the rays; and I (light map), P (polar plot), Tab and Shift-Tab (arena). The
timeline under the buttons puts the run at any time, clicked or dragged (D-033): every tick run
is recorded, so going back restores it as it was, and going ahead of the furthest tick run races
there; a red mark across it is where the run ended. Moving or turning the swimmer by hand, for
trying things out, cuts the recording there. Mutates nothing in the board.
"""

from __future__ import annotations

import math
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import NamedTuple

import numpy as np
import pygame

from nektoids.editor.arena_layout import (
    CONTROLS,
    DRAWER_BODY,
    KEY_BUTTONS,
    MAP_KEY,
    POLAR_KEY,
    TURN_KEYS,
    VIEW_BUTTON,
    ArenaButton,
    banner_button_at,
    control_at,
    timeline_at,
    timeline_rect,
    timeline_time,
)
from nektoids.editor.arena_view import (
    MAX_SCALE,
    ZOOM_STEP,
    ArenaView,
    Rays,
    body_at,
    extent,
    frame,
    kept_in,
    map_grid,
    map_points,
    pan_view,
    shown,
    touches,
    union,
    view_of,
    widened,
    zoom_view,
)
from nektoids.editor.circuit import Circuit
from nektoids.editor.devdrive import DT, Clock
from nektoids.editor.frame import Frame
from nektoids.editor.layout import (
    KEY_ALIASES,
    Drawer,
    Env,
    Layout,
    contains,
    drawer_key,
    make_layout,
    value_at,
    view_button_at,
    zoom_bar_at,
    zoom_button_at,
)
from nektoids.editor.recording import Recording
from nektoids.editor.router import level_label
from nektoids.editor.scene import ARROW_SCANCODES, ARROWS
from nektoids.editor.settings import Settings
from nektoids.editor.tutorial import Action
from nektoids.graph.board import Board, complexity
from nektoids.graph.dynamics import initial_state
from nektoids.graph.network import Network
from nektoids.levels.level import Level
from nektoids.levels.objectives import (
    Kept,
    LeaveRing,
    Objective,
    Outcome,
    StayNear,
    VisitLights,
    begin,
    follow,
    met,
    outcome,
)
from nektoids.levels.score import Score
from nektoids.sim import world
from nektoids.sim.arena import BASE_RADIUS, LIGHT_RADIUS
from nektoids.sim.contact import confine
from nektoids.sim.optics import (
    angular_irradiance,
    eye_poses,
    eye_rates,
    light_map,
    still_light,
)

POLAR_ANGLES = np.radians(np.arange(0.0, 361.0, 5.0))  # closed curve, every 5°
CIRCUIT_MARGIN = 1.0  # room round the body's circle [hex sizes]
LIGHT_CELL = 0.25  # side of a light-map cell [u]
FRAME_MARGIN = 3.0  # room round the swimmers, lights and obstacles when framing [u]
TURN = math.radians(15.0)
ARROW_PAN = 2.0  # with the hand, an arrow drags the view this far [u]
SEEK_TICKS = 40  # a frame's worth of ticks while the run races ahead to a time asked for


@dataclass(frozen=True)
class Snapshot:
    """The run at one tick, as the timeline puts it back: the swimmers, their controllers,
    what their objectives keep (D-038, D-040), the beads."""

    pos: np.ndarray
    heading: np.ndarray
    state: np.ndarray
    kept: Kept
    phase: tuple[float, ...]


class Count(NamedTuple):
    """An objective as the run stands: so many met of so many, its bar, whether it lost."""

    name: str
    met: int
    needed: int
    progress: float  # [0, 1]
    lost: bool


class ArenaScene(Frame):
    def __init__(
        self,
        board: Board,
        levels: Sequence[Level],
        developer: bool = True,
        next_label: str | None = None,
        label: str | None = None,
        settings: Settings | None = None,
        drawer: Drawer | None = Drawer.INSIDE,
        chapter: int = 0,
        passkey: tuple[str, str] | None = None,
    ):
        self.levels = list(levels)
        self.index = 0
        layout = make_layout(drawer, env=Env.RUN, goals=len(self.level.objectives), chapter=chapter)
        self._start_frame(layout, settings)  # also `request`: "edit", "next"... for main.py
        self.label = label  # "LEVEL 1.2": the player's level; None for its place in `levels`
        self.developer = developer  # the developer's tools, every level; or the player's run
        self.next_label = next_label  # what the banner's next button says after a win; None: none
        self.passkey = passkey  # the word its win gives and the level it opens (D-075)
        self.clock = Clock()
        self.clock.paused = True  # a run waits for Play, to open the drawer it wants (D-060)
        self.circuit = Circuit(board, DRAWER_BODY, CIRCUIT_MARGIN, body=True)  # in Inside
        self.parts = complexity(board)  # what this board scores (D-045)
        self.scores: frozenset[Score] = frozenset()  # the level's wins this session: main.py's
        self.eye_mount, self.eye_facing = world.parts(self.net, self.net.eyes)
        self.selected: int | None = 0  # the swimmer whose wiring the panel shows
        self.dragging: int | None = None
        self.show_rays = True  # the light's rays, drawn or not
        self.show_map = False  # the light as a smoothed map instead of rays (developer)
        self.show_polar = False  # the polar plot of the light at the eyes (developer)
        self.hand = False  # dragging moves the view, not a swimmer
        self.panning: tuple[int, int] | None = None  # where the hand last was, while it drags
        self.overviewing = False  # Navigator's overview held: the view follows the mouse
        self.zooming = False  # Navigator's zoom bar held: the zoom follows the mouse
        self.seek_to: int | None = None  # the tick the run races ahead to, if it does
        self.scrubbing = False  # the timeline held down: the run follows the mouse along it
        self.pointer = (0, 0)  # where the mouse is [px]
        self.control_target: ArenaButton | str | None = None  # a control, or "timeline"
        self.control_frames = 0  # ... for this many frames
        self.map_version = 0  # goes up each time the light map changes
        self.map_ms = 0.0  # what computing it took, for the status line [ms]
        self._load()

    @property
    def net(self) -> Network:
        return self.circuit.net

    @property
    def y(self) -> np.ndarray:
        """The selected swimmer's rates now, shape (n,)."""
        return self.state[0 if self.selected is None else self.selected]

    @property
    def level(self) -> Level:
        return self.levels[self.index]

    @property
    def caption(self) -> tuple[str, str]:
        """The level's number and title, and what it asks: under the tabs (D-034, D-056)."""
        return f"{self.label or level_label(self.index)}. {self.level.title}", self.level.spec

    @property
    def control_tip(self) -> ArenaButton | str | None:
        """The control whose tooltip shows now, if any."""
        rested = self.control_frames >= self.settings.tooltip_frames
        return self.control_target if rested else None

    @property
    def arena_area(self):
        """The main screen: the arena, beside the drawer, between the tabs and the controls."""
        return self.layout.board_area

    def _relayout(self, drawer: Drawer | None) -> Layout:
        goals, chapter = len(self.level.objectives), self.layout.chapter
        return make_layout(drawer, env=Env.RUN, goals=goals, chapter=chapter)

    def _slid(self, before: Layout, after: Layout) -> None:
        """The arena moved: the view slides with its centre, so nothing jumps."""
        (x0, y0, w0, h0), (x1, y1, w1, h1) = before.board_area, after.board_area
        dx, dy = (x1 + w1 / 2) - (x0 + w0 / 2), (y1 + h1 / 2) - (y0 + h0 / 2)
        self._look(pan_view(self.view, dx, dy))

    # Loading an arena, starting again

    def _load(self) -> None:
        self.layout = self._relayout(self.layout.drawer)  # as many rows as objectives
        self.title, self.arena = self.level.title, self.level.arena
        self.map_key: tuple | None = None  # the light map's grid: corner, cell, shape
        self.rays = Rays(self.arena.light_power)
        self._restart()
        x, y, _ = self.level.start  # the open plane (D-028): frame what the level holds
        rims = [
            self.arena.light_xy + d
            for r, _ in self.rings
            for d in ((r, 0), (-r, 0), (0, r), (0, -r))
        ]
        points = np.concatenate(([[x, y]], self.arena.light_xy, self.arena.disc_xy, *rims))
        reach = float(np.concatenate(([LIGHT_RADIUS], self.arena.disc_radius, self.radius)).max())
        self._look(frame(self.arena_area, points, FRAME_MARGIN + reach))

    def _restart(self) -> None:
        x, y, heading = self.level.start
        self.pos = np.array([[x, y]])  # (N, 2) [u]
        self.heading = np.array([math.radians(heading)])  # (N,) [rad]
        self.radius = np.full(1, BASE_RADIUS)  # (N,) [u], every body alike (D-045)
        self.state = initial_state(self.net, len(self.pos))  # (N, n), from rest
        self.kept = begin(self.level, self.pos, self.radius)  # each objective's
        self.clock.reset()
        self.circuit.beads.reset()
        self._floor = self._needed()  # the overview's extent at the start: never less (D-073)
        self._extent = self._floor
        self._moved()
        self.recording: Recording[Snapshot] = Recording(self._snapshot())
        self.seek_to = None

    def _moved(self) -> None:
        """A swimmer moved or turned: what the eyes read now, even paused; the map if shown."""
        self.eyes = self._read_eyes()
        self.state[:, self.net.eyes] = self.eyes
        self.circuit.show(self.y)
        if self.show_map:
            self._map()

    def _look(self, view: ArenaView) -> None:
        """See the plane through `view`; the light map, if shown, covers what it now shows."""
        self.view = view
        if self.show_map:
            self._map()

    def _map(self) -> None:
        """The light map over the part of the plane in view, its grid built again only when that
        part changes; the obstacles' shadows on it with it, once."""
        start = time.perf_counter()
        key = map_grid(shown(self.view, self.arena_area), LIGHT_CELL)
        if key != self.map_key:
            self.map_key = key
            self.grid = map_points(*key)
            self.still = still_light(self.arena, self.grid)
        shade = light_map(self.arena, self.grid, self.pos, self.radius, self.still)
        self.shade = shade.reshape(key[2])
        self.map_ms = 1000.0 * (time.perf_counter() - start)
        self.map_version += 1

    def _read_eyes(self) -> np.ndarray:
        """(N, n_eyes): what each swimmer's eyes read where it is."""
        return eye_rates(
            self.arena, self.pos, self.heading, self.radius, self.eye_mount, self.eye_facing
        )

    # Per frame

    def update(self) -> None:
        self.frame_update()
        self._follow_extent()
        kept = kept_in(self.view, self.arena_area, self.extent())  # D-066
        if kept != self.view:
            self._look(kept)
        on_line = contains(timeline_rect(self.layout), self.pointer)
        target = control_at(self.layout, self.pointer) or ("timeline" if on_line else None)
        self.control_frames = self.control_frames + 1 if target is self.control_target else 0
        self.control_target = target
        if self.outcome is not None:
            return  # over: 0 starts it again, the timeline goes back into it
        if self.seek_to is not None:  # racing ahead to a time asked for
            first = self.clock.tick
            ticks = range(first, min(first + SEEK_TICKS, self.seek_to))
            self.clock.tick = ticks.stop
            if ticks.stop == self.seek_to:
                self.seek_to, self.clock.paused = None, True
        else:
            ticks = self.clock.frame()
        for tick in ticks:
            self._advance(tick)
            if outcome(self.level, self.kept, tick + 1, DT) is not None:
                self.clock.tick, self.clock.paused, self.seek_to = tick + 1, True, None
                break
        if len(ticks) and self.show_map:
            self._map()  # the swimmers' shadows moved

    def _advance(self, tick: int) -> None:
        """From `tick` to the next: as recorded if the run got there before, else run on."""
        if tick + 1 <= self.recording.frontier:
            self._restore(self.recording.at(tick + 1))
        else:
            self._tick()
            self.recording.add(self._snapshot())

    @property
    def ended_at(self) -> int | None:
        """The tick the run ended at, won, lost or out of time, once it got there; else None."""
        end = self.recording.frontier
        done = outcome(self.level, self.recording.at(end).kept, end, DT)
        return end if done is not None else None

    def seek(self, seconds: float) -> None:
        """Put the run at `seconds` [s], paused: a tick recorded comes back at once; ahead of the
        frontier the run races there and pauses on arriving; never past the run's end."""
        frontier = self.recording.frontier
        target = min(round(seconds / DT), round(self.level.time_limit / DT))
        if self.ended_at is not None:
            target = min(target, frontier)  # the run ended there: nothing comes after
        self._restore(self.recording.at(min(target, frontier)))
        self.clock.tick = min(target, frontier)
        self.clock.paused = target <= frontier
        self.seek_to = target if target > frontier else None

    def _restore(self, then: Snapshot) -> None:
        """The run as it was at a recorded tick, in copies: what follows changes them in place."""
        self.pos, self.heading = then.pos.copy(), then.heading.copy()
        self.state, self.kept = then.state.copy(), tuple(k.copy() for k in then.kept)
        self.circuit.beads.phase = list(then.phase)
        self.eyes = self.state[:, self.net.eyes]
        self.circuit.show(self.y)

    def _snapshot(self) -> Snapshot:
        return Snapshot(
            self.pos.copy(),
            self.heading.copy(),
            self.state.copy(),
            tuple(k.copy() for k in self.kept),
            tuple(self.circuit.beads.phase),
        )

    def _tick(self) -> None:
        self.pos, self.heading, self.state = world.step(
            self.arena, self.net, self.pos, self.heading, self.radius, self.state, DT
        )
        self.eyes = self.state[:, self.net.eyes]  # what they read where the swimmers now are
        self.kept = follow(self.level, self.kept, self.pos, self.radius, DT)
        self.circuit.advance(self.y, DT)

    @property
    def outcome(self) -> Outcome | None:
        """How the run stands now; None while it runs."""
        return outcome(self.level, self.kept, self.clock.tick, DT)

    @property
    def time_left(self) -> float:
        """Of the level's time limit, how much is left now [s]."""
        return max(0.0, self.level.time_limit - self.clock.seconds)

    def counts(self) -> list[Count]:
        """Each objective of the level as the run stands now."""
        pairs = zip(self.level.objectives, self.kept, strict=True)
        return [Count(o.name, *o.count(k), o.progress(k), o.lost(k)) for o, k in pairs]

    @property
    def lost_by(self) -> Objective | None:
        """The objective that lost the run, if one did."""
        pairs = zip(self.level.objectives, self.kept, strict=True)
        return next((o for o, k in pairs if o.lost(k)), None)

    @property
    def lights_reached(self) -> np.ndarray:
        """(L,): the lights a swimmer has reached, if the level asks for visits; else none."""
        for objective, kept in zip(self.level.objectives, self.kept, strict=True):
            if isinstance(objective, VisitLights):
                return kept.any(axis=0)
        return np.zeros(len(self.arena.lights), dtype=bool)

    @property
    def rings(self) -> list[tuple[float, bool]]:
        """Each ring an objective draws round the lights, to leave or to stay in: its radius [u],
        and whether that is done."""
        pairs = zip(self.level.objectives, self.kept, strict=True)
        return [(o.radius, met(o, k)) for o, k in pairs if isinstance(o, LeaveRing | StayNear)]

    def eye_polar(self) -> np.ndarray:
        """(n_eyes, A): E(phi) at each eye of the selected swimmer, for POLAR_ANGLES, uncapped.
        Empty when no swimmer is selected."""
        if self.selected is None:
            return np.zeros((0, len(POLAR_ANGLES)))
        k = self.selected
        points, _ = eye_poses(self.pos, self.heading, self.radius, self.eye_mount, self.eye_facing)
        curves = [
            angular_irradiance(self.arena, point, POLAR_ANGLES, self.pos, self.radius, own=k)
            for point in points[k]
        ]
        return np.array(curves).reshape(-1, len(POLAR_ANGLES))

    # Input

    @property
    def banner_buttons(self) -> tuple[ArenaButton, ...]:
        """What the banner offers once the run is over: the next level after a win, and Edit."""
        if self.outcome is None:
            return ()
        if self.outcome is Outcome.WON and (self.developer or self.next_label):
            return (ArenaButton.NEXT, ArenaButton.EDIT)
        return (ArenaButton.EDIT,)

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.info is not None and event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
            self.info = None  # the next click or key closes the box, and only that
            return
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
            self.message = ""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._press(event.pos)
        elif event.type == pygame.MOUSEMOTION:
            self.pointer = event.pos
            self.frame_track(event.pos)
            if self.overviewing:
                self._overview_to(event.pos)
            elif self.zooming:
                self._zoom_to(event.pos)
            elif self.scrubbing:
                self.seek(timeline_time(self.layout, event.pos[0], self.level.time_limit))
            elif self.panning is not None:
                dx, dy = event.pos[0] - self.panning[0], event.pos[1] - self.panning[1]
                self._look(pan_view(self.view, dx, dy))
                self.panning = event.pos
            elif self.dragging is not None:
                self._drag(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = self.panning = None
            self.scrubbing = self.overviewing = self.zooming = False
        elif event.type == pygame.MOUSEWHEEL and self.developer:
            self._turn(float(event.y))
        elif event.type == pygame.KEYDOWN:
            self._key(event)

    def _press(self, pos: tuple[int, int]) -> None:
        """A click: the frame's, Navigator's rows, the banner, the controls, the timeline, then
        the arena: to inspect, or, for a developer, to drag the swimmer about."""
        if self.frame_press(pos):
            return
        if self.layout.overview is not None and contains(self.layout.overview, pos):
            self.overviewing = True
            self._overview_to(pos)
            return
        step = zoom_button_at(self.layout, pos)
        if step is not None:
            self.press(VIEW_BUTTON[step])
            return
        if zoom_bar_at(self.layout, pos) is not None:
            self.zooming = True
            self._zoom_to(pos)
            return
        view = view_button_at(self.layout, pos)
        button = (
            (VIEW_BUTTON[view] if view is not None else None)
            or banner_button_at(self.layout, self.banner_buttons, pos)
            or control_at(self.layout, pos)
        )
        asked = timeline_at(self.layout, pos, self.level.time_limit)
        if button is not None:
            self.press(button)
        elif asked is not None:
            if self._allowed(Action("play")):
                self.scrubbing = True
                self.seek(asked)
        elif not contains(self.arena_area, pos):
            return
        elif self.hand:
            self.panning = pos
        else:
            self.selected = body_at(self.view, self.pos, self.radius, pos)
            self.dragging = self.selected if self.developer else None

    def press(self, button: ArenaButton) -> None:
        if button in CONTROLS and not self._allowed(Action("play")):
            return  # a step that leads holds the run, unless it asks for Play (D-060)
        if button is ArenaButton.EDIT:
            self._ask("edit")
        elif button is ArenaButton.NEXT:
            if ArenaButton.NEXT not in self.banner_buttons:
                return
            if self.developer:
                self.index = (self.index + 1) % len(self.levels)
                self._load()
            else:
                self._ask("next")
        elif button is ArenaButton.RESTART:
            self.seek_to = None
            self._restore(self.recording.at(0))  # the same run, from its start
            self.clock.tick = 0
        elif button is ArenaButton.FAST:
            self.clock.speed = 1 if self.clock.speed > 1 else self.settings.fast
        elif button is ArenaButton.HAND:
            self.hand = not self.hand
        elif button is ArenaButton.LIGHT:
            self.show_rays = not self.show_rays
        elif button is ArenaButton.MOTION:  # for the session, as the settings are (D-076)
            self.settings.motion = not self.settings.motion
        elif button is ArenaButton.STREAMS:
            self.settings.streams = not self.settings.streams
        elif button in (ArenaButton.PLAY, ArenaButton.STEP) and self.outcome is not None:
            return  # over: 0 starts it again
        elif button is ArenaButton.PLAY:
            self.seek_to = None
            self.clock.toggle_pause()
        elif button is ArenaButton.STEP:
            self.seek_to = None
            self.clock.paused = True  # a step, then it waits
            self.clock.step()
        elif button in (ArenaButton.ZOOM_IN, ArenaButton.ZOOM_OUT):
            factor = ZOOM_STEP if button is ArenaButton.ZOOM_IN else 1.0 / ZOOM_STEP
            x, y, w, h = self.arena_area
            self._look(zoom_view(self.view, factor, (x + w / 2, y + h / 2)))
        elif button is ArenaButton.CENTRE:
            points = np.concatenate((self.pos, self.arena.light_xy))
            margin = FRAME_MARGIN + max(float(self.radius.max()), LIGHT_RADIUS)
            self._look(frame(self.arena_area, points, margin))

    def _key(self, event: pygame.event.Event) -> None:
        if self.typing is not None:  # a passkey in Chapters takes every key (D-075)
            self.type_key(pygame.key.name(event.key), event.unicode)
            return
        arrow = ARROW_SCANCODES.get(event.scancode) or (event.key if event.key in ARROWS else None)
        typed = KEY_ALIASES.get(event.unicode, event.unicode).upper()
        if arrow is not None:
            self._arrow(arrow)
        elif event.scancode == pygame.KSCAN_SPACE:
            self.press(ArenaButton.PLAY)
        elif event.scancode in (pygame.KSCAN_0, pygame.KSCAN_KP_0):  # "à" on AZERTY, unshifted
            self.press(ArenaButton.RESTART)
        elif event.key == pygame.K_ESCAPE:
            self.press(ArenaButton.EDIT)
        elif event.scancode in (pygame.KSCAN_RETURN, pygame.KSCAN_KP_ENTER):
            self.press(ArenaButton.NEXT)
        elif not self.developer:
            drawer = Drawer.SETTINGS if event.key == pygame.K_COMMA else drawer_key(Env.RUN, typed)
            if event.scancode == pygame.KSCAN_TAB:  # DRAWER_KEYS[CHAPTERS], as in the editor
                self.toggle_drawer(Drawer.CHAPTERS)
            elif self.start_passkey(typed):  # P in Chapters: a passkey (D-075)
                pass
            elif drawer is not None:  # its initial, or the comma, with Ctrl or Cmd too (D-069)
                self.toggle_drawer(drawer)
            elif typed in KEY_BUTTONS:
                self.press(KEY_BUTTONS[typed])
        elif event.scancode == pygame.KSCAN_TAB:
            back = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
            self.index = (self.index + (-1 if back else 1)) % len(self.levels)
            self._load()
        elif typed in KEY_BUTTONS:
            self.press(KEY_BUTTONS[typed])
        elif typed in TURN_KEYS:
            self._turn(1.0 if typed == TURN_KEYS[0] else -1.0)
        elif typed == POLAR_KEY:
            self.show_polar = not self.show_polar
        elif typed == MAP_KEY:
            self.show_map = not self.show_map
            self._moved()

    def _arrow(self, key: int) -> None:
        """With the hand, drag the view one step the way of the arrow, as the mouse would."""
        if not self.hand:
            return
        left, right, up, _ = ARROWS
        step = ARROW_PAN * self.view.scale
        dx, dy = {left: (-step, 0.0), right: (step, 0.0), up: (0.0, -step)}.get(key, (0.0, step))
        self._look(pan_view(self.view, dx, dy))

    def swimmer_box(self) -> tuple[int, int, int, int]:
        """A square round the swimmer on screen, its body and a little: what Fear's tutorial
        outlines first (D-071)."""
        (cx, cy), r = self.view.to_screen(*self.pos[0]), float(self.radius[0]) * self.view.scale + 8
        return (round(cx - r), round(cy - r), round(2 * r), round(2 * r))

    def extent(self) -> tuple[float, float, float, float]:
        """What Navigator's overview shows, and the most the arena may (D-066), as this frame
        keeps it (D-073)."""
        return self._extent

    def _follow_extent(self) -> None:
        """The overview's extent this frame: what matters now, never less than at the start, and
        never less than it was while the main screen's frame touches its border, so the swimmer
        coming closer to the light never zooms the view in (D-073)."""
        bounds = union(self._needed(), self._floor)
        if touches(shown(self.view, self.arena_area), self._extent):
            bounds = union(bounds, self._extent)
        _, _, w, h = self.arena_area
        self._extent = widened(bounds, w / h)

    def _needed(self) -> tuple[float, float, float, float]:
        """What matters now (D-066): the lights and their rings, the obstacles and the swimmer
        where it is, with room to spare."""
        arena = self.arena
        rims = [
            arena.light_xy + d for r, _ in self.rings for d in ((r, 0), (-r, 0), (0, r), (0, -r))
        ]
        points = np.concatenate((self.pos, arena.light_xy, arena.disc_xy, *rims))
        reach = float(np.concatenate(([LIGHT_RADIUS], arena.disc_radius, self.radius)).max())
        _, _, w, h = self.arena_area
        return extent(points, reach, w / h)

    def least_zoom(self) -> float:
        """The farthest the zoom goes: the arena shows the overview's extent [px/u]."""
        return view_of(self.arena_area, self.extent()).scale

    def _overview_to(self, point: tuple[int, int]) -> None:
        """The view, at its zoom, centred where the mouse is on Navigator's overview (D-060)."""
        bounds = self.extent()
        wx, wy = view_of(self.layout.overview, bounds).to_world(*point)
        x, y, w, h = self.arena_area
        s = self.view.scale
        moved = ArenaView(s, (x + w / 2 - s * wx, y + h / 2 + s * wy))
        self._look(kept_in(moved, self.arena_area, bounds))

    def _zoom_to(self, point: tuple[int, int]) -> None:
        """The zoom where the mouse is along Navigator's zoom bar, about the arena's centre."""
        x, _, w, _ = self.layout.zoom_bar
        scale = value_at((point[0] - x) / w, self.least_zoom(), MAX_SCALE)
        ax, ay, aw, ah = self.arena_area
        self._look(zoom_view(self.view, scale / self.view.scale, (ax + aw / 2, ay + ah / 2)))

    def _drag(self, point: tuple[int, int]) -> None:
        """Move the dragged swimmer under the mouse, outside the obstacles."""
        k = self.dragging
        x, y = self.view.to_world(*point)
        self.pos[k] = confine(self.arena, np.array([[x, y]]), self.radius[k : k + 1])[0]
        self._moved()
        self.recording.cut(self.clock.tick, self._snapshot())  # the run is not what it was

    def _turn(self, steps: float) -> None:
        """Turn the selected swimmer by `steps` x 15°, counter-clockwise if positive."""
        if self.selected is not None:
            self.heading[self.selected] += steps * TURN
            self._moved()
            self.recording.cut(self.clock.tick, self._snapshot())
