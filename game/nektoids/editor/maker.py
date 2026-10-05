"""The Maker (D-301): the sandbox's own environment, where its level is made while the editor and
the run try it.

The main screen shows the level's plane at large over its grid, the lattice its positions fall
on: its lights, obstacles and rays, and the swimmer where it starts, facing where it heads.
Round it, the frame the editor and the run have (`frame.Frame`, D-051): Objects, as Parts is the
board's: the objects as rows, undo and redo, and at its foot the Wheel round what is focused
(D-068, D-069, `objects.py`); Navigator, with the overview, the zoom and the rays; Hints,
Settings and Chapters at the bar's foot.

A click on an object focuses it, and its Wheel offers what can be done to it; a drag moves it,
on the lattice. A click on the open plane focuses its nearest lattice point, whose Wheel offers
a light and an obstacle to put there; a drag there moves the view, as do the arrows. A row of
Objects picks what the next click puts on the plane, or is dragged there. The mouse wheel on an
object makes it more or less, or turns the swimmer. Keys: 1 and 2 a light and an obstacle, M
Move (then the arrows move the focus 0.5 u at a time), L and R turn, < and > less and more,
Delete; Ctrl+Z and Ctrl+Y undo and redo; Esc puts down what is in hand, then lets go of the
focus; + and - zoom, C centres, X shows or hides the rays. Space, the switch and the Run tab
run the level, the Editor tab wires its swimmer. Each change is a new `Level` (`making.py`),
which `main.py` hands to the router, the editor and the next run.
"""

from __future__ import annotations

import math
from collections.abc import Callable

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
from nektoids.editor.history import History
from nektoids.editor.layout import (
    KEY_ALIASES,
    TOOL_KEYS,
    VIEW_KEYS,
    Drawer,
    EditButton,
    Env,
    Layout,
    Piece,
    Rect,
    Tool,
    ViewButton,
    contains,
    drawer_key,
    edit_button_at,
    make_layout,
    overview_at,
    piece_row_at,
    value_at,
    view_button_at,
    wheel_fold_at,
    zoom_bar_at,
    zoom_button_at,
)
from nektoids.editor.objects import KEYS, ONE, PLACED, Focus, Point, object_at, offer, where
from nektoids.editor.scene import (
    ARROW_SCANCODES,
    ARROWS,
    DELETE_SCANCODES,
    DIGIT_SCANCODES,
    KEYPAD_SCANCODES,
)
from nektoids.editor.settings import Settings
from nektoids.editor.wheel import WHEEL_HEX, Slot, centre_in, slot_at, slots
from nektoids.levels.lattice import POSITION, snapped
from nektoids.levels.level import Level
from nektoids.levels.making import (
    Unmade,
    adjusted,
    moved,
    placed,
    removed,
    start_moved,
    turned,
)
from nektoids.sim.arena import BASE_RADIUS, LIGHT_RADIUS

ARROW_PAN = 2.0  # an arrow drags the view this far [u]
CLICK = 4  # a press that moves less than this is a click, not a drag [px]
MAKER_VIEW = (ViewButton.ZOOM_IN, ViewButton.ZOOM_OUT, ViewButton.CENTRE, ViewButton.RAYS)
VIEWS = {VIEW_KEYS[b]: b for b in MAKER_VIEW}  # the keys the Maker's view answers: + - C X
ACTIONS = (Tool.MOVE, Tool.TURN_LEFT, Tool.TURN_RIGHT, Tool.LESS, Tool.MORE)
ACTION_KEYS = {TOOL_KEYS[a]: a for a in ACTIONS}  # M L R < >; Delete on its physical key
DIGITS = (Piece.LIGHT, Piece.OBSTACLE)  # 1 and 2, on their physical keys, as Parts' numbers


class MakerScene(Frame):
    def __init__(
        self,
        level: Level,
        label: str,
        settings: Settings | None = None,
        chapter: int = 0,
        drawer: Drawer | None = Drawer.OBJECTS,
    ):
        layout = make_layout(drawer, env=Env.MAKER, chapter=chapter, maker=True)
        self._start_frame(layout, settings)  # also `request`: "run", "edit"... for main.py
        self.label = label  # "SANDBOX", before its title in the caption
        self.show_rays = True  # the light's rays, drawn or not
        self.pointer = (0, 0)  # where the mouse is [px]
        self.panning: tuple[int, int] | None = None  # where a drag on the plane last was
        self.overviewing = False  # Navigator's overview held: the view follows the mouse
        self.zooming = False  # Navigator's zoom bar held: the zoom follows the mouse
        self.focus: Focus | None = None  # what the Wheel is round (D-068)
        self.picked: Piece | None = None  # a row of Objects picked: the next click puts it
        self.carrying = False  # ... the mouse still held since: let go on the plane, it lands
        self.moving = False  # Move in hand: a click on the plane, or an arrow, moves the focus
        self.press_at: tuple[int, int] | None = None  # a press on the plane: click, or drag?
        self.grab: tuple[float, float] | None = None  # ... on an object: from the mouse to it [u]
        self.dragged = False  # ... and the mouse has moved: the object follows it
        self.before: Level | None = None  # the level as the drag began: one step for undo
        self.history: History[Level] = History()  # D-027
        self.wheel_folded = False  # The Wheel's picture folded, as in Tools and Parts (D-069)
        self.wheel_hover: Slot | None = None  # the Wheel's icon under the mouse
        self._take(level)
        self.view = self._opening()
        self._floor = union(self._needed(), grown(shown(self.view, self.arena_area), ZOOM_STEP))

    @property
    def caption(self) -> tuple[str, str]:
        """The level's place and title, and what it asks: under the tabs (D-056)."""
        return f"{self.label}. {self.level.title}", self.level.spec

    @property
    def arena_area(self) -> Rect:
        """The main screen: the plane, beside the drawer, between the tabs and the status line."""
        return self.layout.board_area

    def _relayout(self, drawer: Drawer | None) -> Layout:
        return make_layout(
            drawer,
            env=Env.MAKER,
            chapter=self.layout.chapter,
            maker=True,
            wheel_folded=self.wheel_folded,
            scroll=self.scrolls.get(drawer, 0),  # D-096
            **self._hint_layout(),
        )

    def _slid(self, before: Layout, after: Layout) -> None:
        """The plane moved: the view slides with its centre, so nothing jumps."""
        (x0, y0, w0, h0), (x1, y1, w1, h1) = before.board_area, after.board_area
        dx, dy = (x1 + w1 / 2) - (x0 + w0 / 2), (y1 + h1 / 2) - (y0 + h0 / 2)
        self.view = pan_view(self.view, dx, dy)

    def _take(self, level: Level) -> None:
        """The level as it now stands: its plane, its rays, the swimmer at its start; the focus
        let go if its item is gone."""
        self.level = level
        self.arena = level.arena
        self.rays = Rays(self.arena.light_power)
        x, y, heading = level.start
        self.pos = np.array([[x, y]])  # (1, 2) [u]
        self.heading = math.radians(heading)  # [rad]
        self.radius = np.full(1, BASE_RADIUS)  # (1,) [u]
        if isinstance(self.focus, int) and self.focus >= len(level.items):
            self.focus = None

    def update(self) -> None:
        """Once a frame: the tooltip's rest; the view kept inside the overview (D-066)."""
        self.frame_update()
        self.view = kept_in(self.view, self.arena_area, self.extent())

    def hint(self) -> str:
        """The status line, while nothing was refused: what a click or a key does now."""
        if self.picked is not None:
            return f"Click the plane: {ONE[self.picked]} goes there.  Esc: put it back."
        if self.moving:
            return "Click where it goes, or move it with the arrows.  Esc: done."
        if self.focus is None:
            return "Click an object, or the plane.  Drag an object to move it.  Space: run."
        if isinstance(self.focus, Point):
            return "1: a light here.  2: an obstacle here.  Drag the plane to move the view."
        if self.focus is Piece.START:
            return "Drag it, or M and the arrows.  L and R: turn it."
        return "Drag it, or M and the arrows.  < and >: less, more.  Del: delete."

    # Making

    def _make(self, change: Callable[[Level], Level], record: bool = True) -> bool:
        """`change` made to the level, a step for undo unless `record` is off; refused, and the
        status line says why, if the level could not hold it."""
        try:
            level = change(self.level)
        except Unmade as why:
            self._refuse(str(why))
            return False
        if level != self.level:
            if record:
                self.history.record(self.level)
            self._take(level)
        return True

    def _place(self, piece: Piece, at: tuple[float, float]) -> None:
        """A light or an obstacle at the lattice point nearest `at` [u], focused once there."""
        if self._make(lambda level: placed(level, PLACED[piece], at)):
            self.focus, self.picked, self.moving = len(self.level.items) - 1, None, False

    def _move_to(self, at: tuple[float, float], record: bool = True) -> None:
        """The focused object at the lattice point nearest `at` [u]."""
        focus = self.focus
        if focus is Piece.START:
            self._make(lambda level: start_moved(level, at), record)
        elif isinstance(focus, int):
            self._make(lambda level: moved(level, focus, at), record)

    def _do(self, what: Piece | Tool) -> None:
        """An icon of the Wheel, or its key, on the focus: what it offers, else refused."""
        focus = self.focus
        if what not in offer(focus):
            self._refuse(_why_not(focus, what))
        elif isinstance(what, Piece):  # on an empty point
            self._place(what, focus.at)
        elif what is Tool.MOVE:
            self.moving = not self.moving
        elif what is Tool.DELETE:
            at = self.level.items[focus].at
            if self._make(lambda level: removed(level, focus)):
                self.focus, self.moving = Point(snapped(at)), False  # its point, to put another
        elif what in (Tool.LESS, Tool.MORE):
            steps = 1 if what is Tool.MORE else -1
            self._make(lambda level: adjusted(level, focus, steps))
        else:
            steps = 1 if what is Tool.TURN_LEFT else -1  # counter-clockwise
            self._make(lambda level: turned(level, steps))

    def _edit(self, button: EditButton) -> None:
        """Undo or redo (D-027): the level as it was before the last change, or after."""
        if button is EditButton.UNDO:
            level = self.history.undo(self.level)
        else:
            level = self.history.redo(self.level)
        if level is None:
            self._refuse(f"nothing to {button.value}")
        else:
            self._take(level)

    def wheel(self) -> list[Slot]:
        """The Wheel's icons round the focus, where Objects draws it; none elsewhere."""
        view = self.layout.wheel_view
        if view is None:
            return []
        return slots(offer(self.focus), centre_in(view), WHEEL_HEX, frozenset(), keys=KEYS)

    def _pick(self, piece: Piece) -> None:
        """A row of Objects: the swimmer's start focused; a light or an obstacle in hand, for the
        next click on the plane, or put back if it was."""
        self.moving = False
        if piece is Piece.START:
            self.focus, self.picked = Piece.START, None
        else:  # in hand, the Wheel has nothing to show
            self.picked = None if self.picked is piece else piece
            self.carrying = self.picked is not None
            self.focus = None if self.picked is not None else self.focus

    def _escape(self) -> None:
        """Esc: what is in hand put down, then the focus let go."""
        if self.picked is not None:
            self.picked = None
        elif self.moving:
            self.moving = False
        else:
            self.focus = None

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
        centred = ArenaView(s, (x + w / 2 - s * wx, y + h / 2 + s * wy))
        self.view = kept_in(centred, self.arena_area, bounds)

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

    def _tip_target(self, pos: tuple[int, int]) -> object | None:
        """As the frame's, and the Wheel's icon under the mouse (D-069)."""
        return super()._tip_target(pos) or slot_at(self.wheel(), pos, WHEEL_HEX)

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.info is not None and event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
            self.info = None  # the next click or key closes the box, and only that
            return
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
            self.message = ""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._press(event.pos)
        elif event.type == pygame.MOUSEMOTION:
            self._track(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._release(event.pos)
        elif event.type == pygame.MOUSEWHEEL:
            if not self.frame_wheel(self.pointer, event.y):  # else the drawer's rows (D-096)
                self._wheel_on(self.pointer, 1 if event.y > 0 else -1)
        elif event.type == pygame.KEYDOWN:
            self._key(event)

    def _press(self, pos: tuple[int, int]) -> None:
        """A click: the frame's, Navigator's, the Wheel's icons, Objects' rows, then the plane:
        an object focused and grabbed, or a piece in hand put down, or Move done, or the open
        plane pressed, to focus a point or move the view."""
        if self.frame_press(pos):
            return
        slot = slot_at(self.wheel(), pos, WHEEL_HEX)
        piece = piece_row_at(self.layout, pos)
        edit = edit_button_at(self.layout, pos)
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
        elif slot is not None:
            self._do(slot.what)
        elif wheel_fold_at(self.layout, pos):  # in Objects as in Tools and Parts (D-069)
            self.wheel_folded = not self.wheel_folded
            self.layout = self._relayout(self.layout.drawer)
        elif piece is not None:
            self._pick(piece)
        elif edit is not None:
            self._edit(edit)
        elif contains(self.arena_area, pos):
            self._press_plane(pos)

    def _press_plane(self, pos: tuple[int, int]) -> None:
        at = self.view.to_world(*pos)
        if self.picked is not None:
            self._place(self.picked, at)
        elif self.moving:
            self._move_to(at)
        elif (target := object_at(self.level, self.view, pos)) is not None:
            self.focus, self.press_at, self.before = target, pos, self.level
            x, y = where(self.level, target)
            self.grab, self.dragged = (x - at[0], y - at[1]), False
        else:  # the open plane: a click focuses its point, a drag moves the view
            self.press_at = self.panning = pos

    def _track(self, pos: tuple[int, int]) -> None:
        """The mouse moved: the tooltip, a held overview, zoom bar or plane, a dragged object."""
        self.pointer = pos
        self.frame_track(pos)
        self.wheel_hover = slot_at(self.wheel(), pos, WHEEL_HEX)
        if self.overviewing:
            self._overview_to(pos)
        elif self.zooming:
            self._zoom_to(pos)
        elif self.grab is not None:
            if self.dragged or math.dist(pos, self.press_at) >= CLICK:
                self.dragged = True
                x, y = self.view.to_world(*pos)
                self._move_to((x + self.grab[0], y + self.grab[1]), record=False)
        elif self.panning is not None:
            dx, dy = pos[0] - self.panning[0], pos[1] - self.panning[1]
            self.view = pan_view(self.view, dx, dy)
            self.panning = pos

    def _release(self, pos: tuple[int, int]) -> None:
        """The mouse let go: a row carried lands where it is let go on the plane; a dragged
        object's move is one step for undo; a click on the open plane focuses its point."""
        if self.carrying and contains(self.arena_area, pos):
            self._place(self.picked, self.view.to_world(*pos))
        if self.grab is not None and self.before is not None and self.level != self.before:
            self.history.record(self.before)
        clicked = self.press_at is not None and math.dist(pos, self.press_at) < CLICK
        if clicked and self.grab is None:
            self.focus, self.moving = Point(snapped(self.view.to_world(*self.press_at))), False
        self.carrying = self.overviewing = self.zooming = False
        self.panning = self.press_at = self.grab = self.before = None
        self.frame_release()

    def _wheel_on(self, pos: tuple[int, int], steps: int) -> None:
        """The mouse wheel on an object: a light brighter or dimmer, an obstacle bigger or
        smaller, the swimmer turned; it is focused."""
        if not contains(self.arena_area, pos):
            return
        target = object_at(self.level, self.view, pos)
        if target is None:
            return
        self.focus = target
        if target is Piece.START:
            self._make(lambda level: turned(level, steps))
        else:
            self._make(lambda level: adjusted(level, target, steps))

    def _key(self, event: pygame.event.Event) -> None:
        if event.mod & (pygame.KMOD_CTRL | pygame.KMOD_META):
            if event.key == pygame.K_z:
                self._edit(EditButton.REDO if event.mod & pygame.KMOD_SHIFT else EditButton.UNDO)
            elif event.key == pygame.K_y:
                self._edit(EditButton.REDO)
            elif event.key == pygame.K_COMMA:  # Settings, as in desktop apps (D-069)
                self.toggle_drawer(Drawer.SETTINGS)
            return  # no other shortcut with Ctrl or Cmd: they are the browser's
        if self.typing is not None:  # a passkey in Chapters takes every key (D-075)
            self.type_key(pygame.key.name(event.key), event.unicode)
            return
        arrow = ARROW_SCANCODES.get(event.scancode) or (event.key if event.key in ARROWS else None)
        typed = KEY_ALIASES.get(event.unicode, event.unicode).upper()
        drawer = drawer_key(Env.MAKER, typed)  # the character first: AZERTY's ? is on the comma
        digits = DIGIT_SCANCODES + KEYPAD_SCANCODES
        if arrow is not None:
            self._arrow(arrow)
        elif event.scancode == pygame.KSCAN_SPACE:  # the switch: the run (D-021)
            self._ask("run")
        elif event.scancode == pygame.KSCAN_TAB:  # DRAWER_KEYS[CHAPTERS], as elsewhere
            self.toggle_drawer(Drawer.CHAPTERS)
        elif event.key == pygame.K_ESCAPE:
            self._escape()
        elif event.scancode in DELETE_SCANCODES:  # TOOL_KEYS[DELETE], on the physical key
            self._do(Tool.DELETE)
        elif event.scancode in digits and digits.index(event.scancode) % 9 < len(DIGITS):
            piece = DIGITS[digits.index(event.scancode) % 9]  # on a point, put; else in hand
            if isinstance(self.focus, Point):
                self._do(piece)
            else:
                self._pick(piece)
        elif self.start_passkey(typed):  # P in Chapters: a passkey (D-075)
            pass
        elif drawer is not None:  # its initial, or the comma (D-069)
            self.toggle_drawer(drawer)
        elif typed in ACTION_KEYS:
            self._do(ACTION_KEYS[typed])
        elif typed in VIEWS:
            self._view(VIEWS[typed])

    def _arrow(self, key: int) -> None:
        """With Move in hand, the focus moved 0.5 u the way of the arrow, a step for undo each;
        else the view dragged a step, as the mouse would."""
        left, right, up, _ = ARROWS
        if self.moving and self.focus is not None:
            dx, dy = {left: (-1, 0), right: (1, 0), up: (0, 1)}.get(key, (0, -1))  # y up
            x, y = where(self.level, self.focus)
            self._move_to((x + dx * POSITION, y + dy * POSITION))
            return
        step = ARROW_PAN * self.view.scale
        dx, dy = {left: (-step, 0.0), right: (step, 0.0), up: (0.0, -step)}.get(key, (0.0, step))
        self.view = pan_view(self.view, dx, dy)


def _why_not(focus: Focus | None, what: Piece | Tool) -> str:
    """Why the Wheel's key `what` does nothing on `focus`, for the status line."""
    if focus is None:
        return "click an object, or the plane, first"
    if isinstance(focus, Point):
        return "click an object first"
    if isinstance(what, Piece):
        return "click an empty point of the plane first"
    if what is Tool.DELETE:
        return "the swimmer's start stays: move it or turn it"
    if what in (Tool.TURN_LEFT, Tool.TURN_RIGHT):
        return "only the swimmer turns"
    return "the swimmer's start has no setting"
