"""The arena view (F3, developer): a swimmer running your board in a lit arena (D-018, D-019).

Left, the arena: the light as rays (or, with I, as a map), the obstacles and the lights, and the
swimmer as a circle round a wedge; its eyes and thrusters sit where the board puts them on it.
Right, from the top (`arena_layout.py`): the player's and the view's palettes, the objectives and
how many of each are met, and the selected swimmer's wiring, live: its eyes read the light every
tick and every node follows with its lag (D-017), as it will in the game. The thrusters push
against Stokes drag (D-022): the swimmer swims, sliding round the obstacles, in an open plane.
A run stops when every objective is met or the level's time is up (D-023); 0 starts it again.
P shows, over the arena, the light at its eyes as a polar
plot: what a flat eye there would read facing each way, E(phi), with a tick where each eye looks.

Mouse: the palettes' buttons; click the swimmer to show its wiring (it is shown to begin with),
click beside it to hide it, drag it to move it (with the hand, drag the view); the wheel turns
it by 15°, as do L (left, counter-clockwise) and R, the editor's turn keys. Keys
(`arena_layout.BUTTON_KEYS`, named in the tooltips), the same as the editor's wherever they do
the same: 0 starts again, `,` goes one frame back, Space plays or pauses, `.` runs one frame, F
fast forwards, + and - zoom, H takes the hand (then the arrows drag the view), C centres, X
shows or hides the rays; and I (light map), P (polar plot), Tab and Shift-Tab (arena). One frame
back replays nothing: the scene keeps the last HISTORY frames as they were, so it also takes
back the end of a run. Moving and turning the swimmer by hand are for trying things out; the run
takes no notice. Mutates nothing in the board.
"""

from __future__ import annotations

import math
import time
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pygame

from nektoids.editor.arena_layout import (
    ARENA_AREA,
    CIRCUIT_AREA,
    KEY_BUTTONS,
    MAP_KEY,
    POLAR_KEY,
    TURN_KEYS,
    ArenaButton,
    button_at,
)
from nektoids.editor.arena_view import (
    ZOOM_STEP,
    ArenaView,
    Rays,
    body_at,
    frame,
    map_grid,
    map_points,
    pan_view,
    shown,
    zoom_view,
)
from nektoids.editor.circuit import Circuit
from nektoids.editor.devdrive import DT, Clock
from nektoids.editor.layout import KEY_ALIASES
from nektoids.editor.scene import ARROW_SCANCODES, ARROWS, TOOLTIP_FRAMES
from nektoids.graph.board import Board
from nektoids.graph.dynamics import initial_state
from nektoids.graph.network import Network
from nektoids.levels.level import Level
from nektoids.levels.objectives import Outcome, outcome, touching
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
FAST = 4  # fast forward runs this many frames' worth of ticks a frame
ARROW_PAN = 2.0  # with the hand, an arrow drags the view this far [u]
HISTORY = 1200  # frames kept for going back: 20 s at 60 frames a second


@dataclass(frozen=True)
class Snapshot:
    """What one frame back puts back: the clock, the swimmers, their controllers, the lights
    they have visited, the beads."""

    tick: int
    pos: np.ndarray
    heading: np.ndarray
    state: np.ndarray
    visited: np.ndarray
    phase: tuple[float, ...]


class ArenaScene:
    def __init__(self, board: Board, levels: Sequence[Level]):
        self.levels = list(levels)
        self.index = 0
        self.clock = Clock()
        self.circuit = Circuit(board, CIRCUIT_AREA, CIRCUIT_MARGIN, body=True)
        self.eye_mount, self.eye_facing = world.parts(self.net, self.net.eyes)
        self.selected: int | None = 0  # the swimmer whose wiring the panel shows
        self.dragging: int | None = None
        self.show_rays = True  # the light's rays, drawn or not
        self.show_map = False  # the light as a smoothed map instead of rays (developer)
        self.show_polar = False  # the polar plot of the light at the eyes (developer)
        self.hand = False  # dragging moves the view, not a swimmer
        self.panning: tuple[int, int] | None = None  # where the hand last was, while it drags
        self.history: deque[Snapshot] = deque(maxlen=HISTORY)
        self.pointer = (0, 0)  # where the mouse is [px]
        self.tip_target: ArenaButton | None = None  # the button under the mouse
        self.tip_frames = 0  # ... for this many frames
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
    def tooltip(self) -> ArenaButton | None:
        """The button whose tooltip shows now, if any."""
        return self.tip_target if self.tip_frames >= TOOLTIP_FRAMES else None

    # Loading an arena, starting again

    def _load(self) -> None:
        self.title, self.arena = self.level.title, self.level.arena
        self.map_key: tuple | None = None  # the light map's grid: corner, cell, shape
        self.rays = Rays(self.arena.light_power)
        self._restart()
        x, y, _ = self.level.start  # the open plane (D-028): frame what the level holds
        points = np.concatenate(([[x, y]], self.arena.light_xy, self.arena.disc_xy))
        reach = float(np.concatenate(([LIGHT_RADIUS], self.arena.disc_radius, self.radius)).max())
        self._look(frame(ARENA_AREA, points, FRAME_MARGIN + reach))

    def _restart(self) -> None:
        x, y, heading = self.level.start
        self.pos = np.array([[x, y]])  # (N, 2) [u]
        self.heading = np.array([math.radians(heading)])  # (N,) [rad]
        self.radius = np.full(1, BASE_RADIUS)  # (N,) [u], until complexity() sets it
        self.state = initial_state(self.net, len(self.pos))  # (N, n), from rest
        self.visited = touching(self.arena, self.pos, self.radius)  # (N, L): lights touched
        self.clock.reset()
        self.circuit.beads.reset()
        self.history.clear()
        self._moved()

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
        key = map_grid(shown(self.view, ARENA_AREA), LIGHT_CELL)
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
        target = button_at(self.pointer)
        self.tip_frames = self.tip_frames + 1 if target is self.tip_target else 0
        self.tip_target = target
        if self.outcome is not None:
            return  # over: 0 starts it again, one frame back takes the end back
        before = self._snapshot()
        ticks = self.clock.frame()
        if len(ticks):
            self.history.append(before)
        for tick in ticks:
            self._tick()
            if outcome(self.level, self.visited, tick + 1, DT) is not None:
                self.clock.tick, self.clock.paused = tick + 1, True  # stop where it ended
                break
        if len(ticks) and self.show_map:
            self._map()  # the swimmers' shadows moved

    def _snapshot(self) -> Snapshot:
        return Snapshot(
            self.clock.tick,
            self.pos.copy(),
            self.heading.copy(),
            self.state.copy(),
            self.visited.copy(),
            tuple(self.circuit.beads.phase),
        )

    def _back(self) -> None:
        """One frame back, paused: the frame before the last one run, as it was."""
        self.clock.paused = True
        if not self.history:
            return
        then = self.history.pop()
        self.clock.tick = then.tick
        self.pos, self.heading, self.state = then.pos, then.heading, then.state
        self.visited = then.visited
        self.circuit.beads.phase = list(then.phase)
        self.eyes = self._read_eyes()
        self.circuit.show(self.y)
        if self.show_map:
            self._map()

    def _tick(self) -> None:
        self.pos, self.heading, self.state = world.step(
            self.arena, self.net, self.pos, self.heading, self.radius, self.state, DT
        )
        self.eyes = self.state[:, self.net.eyes]  # what they read where the swimmers now are
        self.visited |= touching(self.arena, self.pos, self.radius)
        self.circuit.advance(self.y, DT)

    @property
    def outcome(self) -> Outcome | None:
        """How the run stands now; None while it runs."""
        return outcome(self.level, self.visited, self.clock.tick, DT)

    @property
    def time_left(self) -> float:
        """Of the level's time limit, how much is left now [s]."""
        return max(0.0, self.level.time_limit - self.clock.seconds)

    def counts(self) -> list[tuple[str, int, int]]:
        """Each objective of the level: its name, how many are met, out of how many."""
        return [(o.name, *o.count(self.visited)) for o in self.level.objectives]

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

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            button = button_at(event.pos)
            if button is not None:
                self.press(button)
            elif self.hand:
                self.panning = event.pos
            else:
                self.selected = self.dragging = body_at(self.view, self.pos, self.radius, event.pos)
        elif event.type == pygame.MOUSEMOTION:
            self.pointer = event.pos
            if self.panning is not None:
                dx, dy = event.pos[0] - self.panning[0], event.pos[1] - self.panning[1]
                self._look(pan_view(self.view, dx, dy))
                self.panning = event.pos
            elif self.dragging is not None:
                self._drag(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = self.panning = None
        elif event.type == pygame.MOUSEWHEEL:
            self._turn(float(event.y))
        elif event.type == pygame.KEYDOWN:
            self._key(event)

    def press(self, button: ArenaButton) -> None:
        if button is ArenaButton.RESTART:
            self._restart()
        elif button is ArenaButton.BACK:
            self._back()
        elif button is ArenaButton.FAST:
            self.clock.speed = 1 if self.clock.speed > 1 else FAST
        elif button is ArenaButton.HAND:
            self.hand = not self.hand
        elif button is ArenaButton.LIGHT:
            self.show_rays = not self.show_rays
        elif button in (ArenaButton.PLAY, ArenaButton.STEP) and self.outcome is not None:
            return  # over: 0 starts it again
        elif button is ArenaButton.PLAY:
            self.clock.toggle_pause()
        elif button is ArenaButton.STEP:
            self.clock.paused = True  # one frame, then it waits
            self.clock.step()
        elif button in (ArenaButton.ZOOM_IN, ArenaButton.ZOOM_OUT):
            factor = ZOOM_STEP if button is ArenaButton.ZOOM_IN else 1.0 / ZOOM_STEP
            x, y, w, h = ARENA_AREA
            self._look(zoom_view(self.view, factor, (x + w / 2, y + h / 2)))
        elif button is ArenaButton.CENTRE:
            points = np.concatenate((self.pos, self.arena.light_xy))
            margin = FRAME_MARGIN + max(float(self.radius.max()), LIGHT_RADIUS)
            self._look(frame(ARENA_AREA, points, margin))

    def _key(self, event: pygame.event.Event) -> None:
        arrow = ARROW_SCANCODES.get(event.scancode) or (event.key if event.key in ARROWS else None)
        typed = KEY_ALIASES.get(event.unicode, event.unicode).upper()
        if arrow is not None:
            self._arrow(arrow)
        elif event.scancode == pygame.KSCAN_SPACE:
            self.press(ArenaButton.PLAY)
        elif event.scancode in (pygame.KSCAN_0, pygame.KSCAN_KP_0):  # "à" on AZERTY, unshifted
            self.press(ArenaButton.RESTART)
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

    def _drag(self, point: tuple[int, int]) -> None:
        """Move the dragged swimmer under the mouse, outside the obstacles."""
        k = self.dragging
        x, y = self.view.to_world(*point)
        self.pos[k] = confine(self.arena, np.array([[x, y]]), self.radius[k : k + 1])[0]
        self._moved()

    def _turn(self, steps: float) -> None:
        """Turn the selected swimmer by `steps` x 15°, counter-clockwise if positive."""
        if self.selected is not None:
            self.heading[self.selected] += steps * TURN
            self._moved()
