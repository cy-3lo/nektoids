"""The Maker (D-301): the sandbox's own environment, where its level is made while the editor and
the run try it.

The main screen shows the level's plane at large over its grid, the lattice its positions fall
on: its lights, obstacles and rays, and the swimmer where it starts, facing where it heads.
Round it, the frame the editor and the run have (`frame.Frame`, D-051): Navigator, with the
overview, the zoom and the rays; Hints, Settings and Chapters at the bar's foot. A drag on the
plane moves the view, as do the arrows; + and - zoom, C centres, X shows or hides the rays;
Space, the switch and the Run tab run the level, the Editor tab wires its swimmer.
"""

from __future__ import annotations

import math

import numpy as np
import pygame

from nektoids.editor.arena_view import (
    MAX_SCALE,
    OPENING_SCALE,
    ROOM,
    ZOOM_STEP,
    ArenaView,
    Rays,
    extent,
    grown,
    kept_in,
    pan_view,
    shown,
    union,
    view_of,
    widened,
    zoom_view,
)
from nektoids.editor.frame import Frame
from nektoids.editor.layout import (
    KEY_ALIASES,
    VIEW_KEYS,
    Drawer,
    Env,
    Layout,
    Rect,
    ViewButton,
    contains,
    drawer_key,
    make_layout,
    overview_at,
    value_at,
    view_button_at,
    zoom_bar_at,
    zoom_button_at,
)
from nektoids.editor.scene import ARROW_SCANCODES, ARROWS
from nektoids.editor.settings import Settings
from nektoids.levels.level import Level
from nektoids.sim.arena import BASE_RADIUS, LIGHT_RADIUS

ARROW_PAN = 2.0  # an arrow drags the view this far [u]
MAKER_VIEW = (ViewButton.ZOOM_IN, ViewButton.ZOOM_OUT, ViewButton.CENTRE, ViewButton.RAYS)
VIEWS = {VIEW_KEYS[b]: b for b in MAKER_VIEW}  # the keys the Maker's view answers: + - C X


class MakerScene(Frame):
    def __init__(
        self,
        level: Level,
        label: str,
        settings: Settings | None = None,
        chapter: int = 0,
        drawer: Drawer | None = Drawer.NAVIGATOR,
    ):
        layout = make_layout(drawer, env=Env.MAKER, chapter=chapter, maker=True)
        self._start_frame(layout, settings)  # also `request`: "run", "edit"... for main.py
        self.level = level  # the level being made
        self.label = label  # "SANDBOX", before its title in the caption
        self.show_rays = True  # the light's rays, drawn or not
        self.pointer = (0, 0)  # where the mouse is [px]
        self.panning: tuple[int, int] | None = None  # where a drag on the plane last was
        self.overviewing = False  # Navigator's overview held: the view follows the mouse
        self.zooming = False  # Navigator's zoom bar held: the zoom follows the mouse
        self._load()

    @property
    def caption(self) -> tuple[str, str]:
        """The level's place and title, and what it asks: under the tabs (D-056)."""
        return f"{self.label}. {self.level.title}", self.level.spec

    @property
    def arena_area(self) -> Rect:
        """The main screen: the plane, beside the drawer, between the tabs and the status line."""
        return self.layout.board_area

    def _relayout(self, drawer: Drawer | None) -> Layout:
        scroll = self.scrolls.get(drawer, 0)  # D-096
        chapter = self.layout.chapter
        return make_layout(
            drawer, env=Env.MAKER, chapter=chapter, maker=True, scroll=scroll, **self._hint_layout()
        )

    def _slid(self, before: Layout, after: Layout) -> None:
        """The plane moved: the view slides with its centre, so nothing jumps."""
        (x0, y0, w0, h0), (x1, y1, w1, h1) = before.board_area, after.board_area
        dx, dy = (x1 + w1 / 2) - (x0 + w0 / 2), (y1 + h1 / 2) - (y0 + h0 / 2)
        self.view = pan_view(self.view, dx, dy)

    def _load(self) -> None:
        """The level as it stands: its plane, its rays, the swimmer at its start, the view it
        opens on, and the least the overview shows: that view and a zoom click out (D-101)."""
        self.arena = self.level.arena
        self.rays = Rays(self.arena.light_power)
        x, y, heading = self.level.start
        self.pos = np.array([[x, y]])  # (1, 2) [u]
        self.heading = math.radians(heading)  # [rad]
        self.radius = np.full(1, BASE_RADIUS)  # (1,) [u]
        self.view = self._opening()
        self._floor = union(self._needed(), grown(shown(self.view, self.arena_area), ZOOM_STEP))

    def update(self) -> None:
        """Once a frame: the tooltip's rest; the view kept inside the overview (D-066)."""
        self.frame_update()
        self.view = kept_in(self.view, self.arena_area, self.extent())

    # The view, as the run's (D-066, D-101)

    def extent(self) -> tuple[float, float, float, float]:
        """What Navigator's overview shows, and the most the plane may: what matters, never less
        than as the Maker opened, widened to the main screen's shape."""
        _, _, w, h = self.arena_area
        return widened(union(self._needed(), self._floor), w / h)

    def _needed(self, room: float = ROOM) -> tuple[float, float, float, float]:
        """What matters: the lights, the obstacles and the swimmer, `room` times over."""
        arena = self.arena
        points = np.concatenate((self.pos, arena.light_xy, arena.disc_xy))
        reach = float(np.concatenate(([LIGHT_RADIUS], arena.disc_radius, self.radius)).max())
        _, _, w, h = self.arena_area
        return extent(points, reach, w / h, room)

    def _opening(self) -> ArenaView:
        """What matters, centred, at OPENING_SCALE, or farther out if that would not show it."""
        return view_of(self.arena_area, self._needed(1.0), OPENING_SCALE)

    def least_zoom(self) -> float:
        """The farthest the zoom goes: the plane shows the overview's extent [px/u]."""
        return view_of(self.arena_area, self.extent()).scale

    def _zoom_by(self, factor: float) -> None:
        x, y, w, h = self.arena_area
        self.view = zoom_view(self.view, factor, (x + w / 2, y + h / 2))

    def _overview_to(self, point: tuple[int, int]) -> None:
        """The view, at its zoom, centred where the mouse is on Navigator's overview (D-060)."""
        bounds = self.extent()
        wx, wy = view_of(self.layout.overview, bounds).to_world(*point)
        x, y, w, h = self.arena_area
        s = self.view.scale
        moved = ArenaView(s, (x + w / 2 - s * wx, y + h / 2 + s * wy))
        self.view = kept_in(moved, self.arena_area, bounds)

    def _zoom_to(self, point: tuple[int, int]) -> None:
        """The zoom where the mouse is along Navigator's zoom bar, about the plane's centre."""
        x, _, w, _ = self.layout.zoom_bar
        self._zoom_by(value_at((point[0] - x) / w, self.least_zoom(), MAX_SCALE) / self.view.scale)

    def _view(self, button: ViewButton) -> None:
        """A view's button or key: zoom out or in, centre, the rays."""
        if button is ViewButton.ZOOM_IN:
            self._zoom_by(ZOOM_STEP)
        elif button is ViewButton.ZOOM_OUT:
            self._zoom_by(1.0 / ZOOM_STEP)
        elif button is ViewButton.CENTRE:
            self.view = self._opening()
        elif button is ViewButton.RAYS:
            self.show_rays = not self.show_rays

    # Input

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
            elif self.panning is not None:
                dx, dy = event.pos[0] - self.panning[0], event.pos[1] - self.panning[1]
                self.view = pan_view(self.view, dx, dy)
                self.panning = event.pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.panning = None
            self.overviewing = self.zooming = False
            self.frame_release()
        elif event.type == pygame.MOUSEWHEEL:
            self.frame_wheel(self.pointer, event.y)  # the drawer's rows scrolled (D-096)
        elif event.type == pygame.KEYDOWN:
            self._key(event)

    def _press(self, pos: tuple[int, int]) -> None:
        """A click: the frame's, Navigator's overview, zoom and rows, then the plane, to drag."""
        if self.frame_press(pos):
            return
        if overview_at(self.layout, pos):
            self.overviewing = True
            self._overview_to(pos)
        elif (step := zoom_button_at(self.layout, pos)) is not None:
            self._view(step)
        elif zoom_bar_at(self.layout, pos) is not None:
            self.zooming = True
            self._zoom_to(pos)
        elif (button := view_button_at(self.layout, pos)) is not None:
            self._view(button)
        elif contains(self.arena_area, pos):
            self.panning = pos

    def _key(self, event: pygame.event.Event) -> None:
        if self.typing is not None:  # a passkey in Chapters takes every key (D-075)
            self.type_key(pygame.key.name(event.key), event.unicode)
            return
        arrow = ARROW_SCANCODES.get(event.scancode) or (event.key if event.key in ARROWS else None)
        typed = KEY_ALIASES.get(event.unicode, event.unicode).upper()
        drawer = drawer_key(Env.MAKER, typed)  # the character first: AZERTY's ? is on the comma
        if drawer is None and event.key == pygame.K_COMMA:  # with Ctrl or Cmd, none is typed
            drawer = Drawer.SETTINGS
        if arrow is not None:
            self._arrow(arrow)
        elif event.scancode == pygame.KSCAN_SPACE:  # the switch: the run (D-021)
            self._ask("run")
        elif event.scancode == pygame.KSCAN_TAB:  # DRAWER_KEYS[CHAPTERS], as elsewhere
            self.toggle_drawer(Drawer.CHAPTERS)
        elif self.start_passkey(typed):  # P in Chapters: a passkey (D-075)
            pass
        elif drawer is not None:  # its initial, or the comma, with Ctrl or Cmd too (D-069)
            self.toggle_drawer(drawer)
        elif typed in VIEWS:
            self._view(VIEWS[typed])

    def _arrow(self, key: int) -> None:
        """Drag the view one step the way of the arrow, as the mouse would."""
        left, right, up, _ = ARROWS
        step = ARROW_PAN * self.view.scale
        dx, dy = {left: (-step, 0.0), right: (step, 0.0), up: (0.0, -step)}.get(key, (0.0, step))
        self.view = pan_view(self.view, dx, dy)
