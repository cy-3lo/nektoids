"""The Maker (D-301): the sandbox's own environment, where its level is made while the editor and
the run try it.

The main screen shows the level's plane at large over its grid, the lattice its positions fall
on: its lights, obstacles, marks and rays, and the swimmer where it starts, facing where it
heads. Round it, the frame the editor and the run have (`frame.Frame`, D-051): Objects, as Parts
is the board's: the objects as rows, undo and redo, and at its foot the Wheel round what is
focused (D-068, D-069, `objects.py`); Goals, the time allowed and the goals, each a sentence
whose words are buttons, with a slider for its setting (D-308); Text, the level's title and
spec (D-305); Files, the level copied as text, another's text pasted, or a blank plane or a
shipped level to start from (D-310); Parts, the board's size and how many of each part, which
the Editor's board takes at once, or refuses while it has more (D-315); Navigator, with
the overview, the zoom and the rays; Hints, Settings and Chapters at the bar's foot.

The Wheel works as the Editor's (D-314): atop the plane, what the next click or Enter does. A
click on an object focuses it with Move in hand, so the next click on the open plane moves it
there; a drag moves it too, on the lattice. An object just placed is focused with More lit,
the least to begin with, so Enter makes it more. A click on the open plane, inside a mark too,
focuses its nearest lattice point, whose Wheel offers a light, an obstacle and a mark to put
there (D-306); a drag there moves the view. With something focused the arrows go round the
Wheel, stopping at its ends, and Enter uses the icon lit: less and more and the turns at once,
again at each Enter; Move in hand, when the arrows carry the object 1 u at a time until Enter
or Esc puts it down; Delete. With nothing focused the arrows move the view. A row of Objects
picks what the next click puts on the plane, or is dragged there. The mouse wheel on an object
makes it more or less, or turns the swimmer. Keys: 1, 2, 3 a light, an obstacle, a mark; M
Move; L and R turn; < and > less and more; Delete; Ctrl+Z and Ctrl+Y undo and redo; Esc puts
down what is in hand, then lets go of the focus, then opens Chapters (D-304); + and - zoom, C
centres, X shows or hides the rays; Tab the next tab, Space the run. Each change is a new `Level`
(`making.py`), which `main.py` hands to the router, the editor and the next run.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import replace
from enum import Enum

import numpy as np
import pygame

from nektoids.editor import clipboard
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
    rims,
    shown,
    union,
    view_of,
    widened,
    zoom_view,
)
from nektoids.editor.boardfield import load
from nektoids.editor.devdrive import DT
from nektoids.editor.frame import Frame
from nektoids.editor.history import History
from nektoids.editor.layout import (
    KEY_ALIASES,
    TOOL_KEYS,
    VIEW_KEYS,
    Brief,
    Drawer,
    EditButton,
    Env,
    FileButton,
    GoalButton,
    Knob,
    Layout,
    Piece,
    Rect,
    Start,
    Stepper,
    Tool,
    ViewButton,
    action_at,
    along,
    bin_at,
    brief_field_at,
    contains,
    drawer_key,
    edit_button_at,
    file_button_at,
    goal_button_at,
    group_at,
    knob_at,
    level_field_at,
    make_layout,
    overview_at,
    piece_row_at,
    slider_parts,
    start_row_at,
    stepper_at,
    value_at,
    view_button_at,
    word_at,
    zoom_bar_at,
    zoom_button_at,
)
from nektoids.editor.objects import (
    KEYS,
    ONE,
    PLACED,
    POINT_PIECES,
    Focus,
    Point,
    chosen,
    object_at,
    offer,
    turned_to,
    where,
)
from nektoids.editor.scene import (
    ARROW_SCANCODES,
    ARROWS,
    DELETE_SCANCODES,
    DIGIT_SCANCODES,
    KEYPAD_SCANCODES,
)
from nektoids.editor.settings import Settings
from nektoids.editor.textfield import TextField
from nektoids.editor.wheel import WHEEL_HEX, Slot, centre_in, slot_at, slots
from nektoids.graph import boardtext
from nektoids.graph.board import Board, complexity
from nektoids.levels.lattice import POSITION, Range, snapped
from nektoids.levels.level import Level, to_json
from nektoids.levels.making import (
    AUTHOR_LONGEST,
    GOALS_MOST,
    SPEC_LONGEST,
    TIME,
    TITLE_LONGEST,
    Unmade,
    adjusted,
    authored,
    blank,
    boarded,
    goal_added,
    goal_removed,
    goal_set,
    goal_worded,
    moved,
    number,
    placed,
    read_level,
    removed,
    specified,
    start_moved,
    stocked,
    taken,
    timed,
    titled,
    turned,
    zoned,
)
from nektoids.levels.objectives import Outcome, settings
from nektoids.levels.proof import Proof, Replay
from nektoids.levels.score import Score
from nektoids.sim.arena import BASE_RADIUS, LIGHT_RADIUS

ARROW_PAN = 2.0  # an arrow drags the view this far [u]
CLICK = 4  # a press that moves less than this is a click, not a drag [px]
MAKER_VIEW = (ViewButton.ZOOM_IN, ViewButton.ZOOM_OUT, ViewButton.CENTRE, ViewButton.RAYS)
VIEWS = {VIEW_KEYS[b]: b for b in MAKER_VIEW}  # the keys the Maker's view answers: + - C X
ACTIONS = (Tool.MOVE, Tool.TURN_LEFT, Tool.TURN_RIGHT, Tool.LESS, Tool.MORE)
ACTION_KEYS = {TOOL_KEYS[a]: a for a in ACTIONS}  # M L R < >; Delete on its physical key
DIGITS = POINT_PIECES  # 1, 2, 3, on their physical keys, as Parts' numbers
NUMBER = frozenset("0123456789.")  # what a slider's box takes, typed (D-308)
NUMBER_LONGEST = 5  # ... and how long it grows: 300, 12.5
LEVEL_LONGEST = 20_000  # what a level's text, pasted in Files, may run to (D-310)
CHECK_TICKS = 120  # a pasted level's proof run so many ticks a frame, a second of it (D-320)


class Paste(Enum):  # the field of the Maker's Files: a level's text pasted there (D-310)
    LEVEL = "level"


class MakerScene(Frame):
    def __init__(
        self,
        level: Level,
        label: str,
        settings: Settings | None = None,
        chapters: tuple[tuple[str, int], ...] = (),
        drawer: Drawer | None = Drawer.OBJECTS,
        starts: Sequence[tuple[str, Level]] = (),
        board: Board | None = None,
    ):
        layout = make_layout(drawer, env=Env.MAKER, chapters=chapters, maker=True)
        self._start_frame(layout, settings)  # also `request`: "run", "edit"... for main.py
        self.label = label  # "YOUR LEVEL", before its title in the caption (D-341)
        self.starts = tuple(starts)  # Start from's levels, each with its label: "1.2", or ""
        self.board = board  # the Editor's board, which takes what the level hands out (D-315)
        self.proof: Proof | None = None  # the board that won the level, its score (D-320)
        self.proved: Level | None = None  # ... the level as it was won: shared while it holds
        self.checking: tuple[Replay, Proof, Level] | None = None  # a pasted proof, run again
        self.shared = False  # Share level's box says how to share what it copied (D-346)
        self.show_rays = True  # the light's rays, drawn or not
        self.pointer = (0, 0)  # where the mouse is [px]
        self.panning: tuple[int, int] | None = None  # where a drag on the plane last was
        self.overviewing = False  # Navigator's overview held: the view follows the mouse
        self.zooming = False  # Navigator's zoom bar held: the zoom follows the mouse
        self.focus: Focus | None = None  # what the Wheel is round (D-068)
        self.picked: Piece | None = None  # a row of Objects picked: the next click puts it
        self.carrying = False  # ... the mouse still held since: let go on the plane, it lands
        self.moving = False  # Move in hand: a click on the plane, or an arrow, moves the focus
        self.choice: int | None = None  # the Wheel's icon lit: what Enter does (D-314)
        self.arming = False  # a press on an object: Move in hand once the click is over
        self.press_at: tuple[int, int] | None = None  # a press on the plane: click, or drag?
        self.grab: tuple[float, float] | None = None  # ... on an object: from the mouse to it [u]
        self.dragged = False  # ... and the mouse has moved: the object follows it
        self.before: Level | None = None  # the level as the drag began: one step for undo
        self.history: History[Level] = History()  # D-027
        self.wheel_folded = False  # the Maker's Wheel never folds, unlike the Editor's (D-317)
        self.wheel_hover: Slot | None = None  # the Wheel's icon under the mouse
        self.writing: Brief | Knob | Paste | None = None  # a field typed in: Brief's, a box...
        self.field: TextField | None = None  # ... what it holds (D-305)
        self.field_pressed: Brief | Knob | Paste | None = None  # opens once the click is over
        self.sliding: Knob | None = None  # a slider of Goals held: its value follows the mouse
        self.folded: set[str] = set()  # Parts' groups shown closed, as the Editor's (D-315),
        self.folded |= {title for title, _ in chapters}  # and Start from's chapters (D-342)
        self._take(level)
        self._open_view()
        self.layout = self._relayout(self.layout.drawer)  # its rows, now it knows its starts

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
            self._folded(drawer, self.folded),
            env=Env.MAKER,
            chapters=self.layout.chapters,
            maker=True,
            wheel_folded=self.wheel_folded,
            scroll=self.scrolls.get(drawer, 0),  # D-096
            made=tuple(bool(settings(goal)) for goal in self.level.objectives),  # D-308
            addable=len(self.level.objectives) < GOALS_MOST,
            starts=len(self.starts),  # D-310
            **self._hint_layout(),
        )

    def _slid(self, before: Layout, after: Layout) -> None:
        """The plane moved: the view slides with its centre, so nothing jumps."""
        (x0, y0, w0, h0), (x1, y1, w1, h1) = before.board_area, after.board_area
        dx, dy = (x1 + w1 / 2) - (x0 + w0 / 2), (y1 + h1 / 2) - (y0 + h0 / 2)
        self.view = pan_view(self.view, dx, dy)

    def _take(self, level: Level) -> None:
        """The level as it now stands: its plane, its rays, the swimmer at its start; the focus
        let go if its item is gone; Goals' rows, as many as its goals and their settings."""
        self.level = level
        self.arena = level.arena
        self.rays = Rays(self.arena.light_power)
        x, y, heading = level.start
        self.pos = np.array([[x, y]])  # (1, 2) [u]
        self.heading = math.radians(heading)  # [rad]
        self.radius = np.full(1, BASE_RADIUS)  # (1,) [u]
        if isinstance(self.focus, int) and self.focus >= len(level.items):
            self.focus, self.choice, self.moving = None, None, False
        if self.layout.drawer is Drawer.GOALS:
            self.layout = self._relayout(Drawer.GOALS)

    def update(self) -> None:
        """Once a frame: on the web, what the page's field holds (D-206); the tooltip's rest;
        the view kept inside the overview (D-066)."""
        if self.field is not None and clipboard.WEB:  # the page's field took the keys
            text, caret, ended = clipboard.field()
            self.field.take(text, caret)
            if ended is not None:
                self._field_done(ended)
        self._check_proof()
        self.frame_update()
        self.shared = self.shared and self.info is FileButton.SHARE  # while its box is open
        self.view = kept_in(self.view, self.arena_area, self.extent())

    def hint(self) -> str:
        """The status line, while nothing was refused: what a click or a key does now."""
        if self.writing is Paste.LEVEL:
            return "Paste a level's text: Ctrl+V, or Cmd+V.  Enter takes it.  Esc: no change."
        if self.writing is not None:
            kept = "Enter or a click elsewhere keeps it.  Esc: no change."
            return f"Type {self._what(self.writing)}.  {kept}"
        if self.layout.drawer is Drawer.TEXT:
            return "Click the title, the spec or the author to write it."
        if self.layout.drawer is Drawer.PARTS:
            return "- and +: how big the board is, and how many of each part it hands out."
        if self.checking is not None:
            return f"Checking its proof: {round(100 * self.checking[0].progress)}%."
        if self.layout.drawer is Drawer.FILES:
            return (
                "Copy level: the level as text.  Paste a level, or start from one or a blank plane."
            )
        if self.sliding is not None:
            return "Let go where it should stay."
        if self.layout.drawer is Drawer.GOALS and not self.level.objectives:
            return "No goal: a run ends only when its time is up.  Add one, two at most."
        if self.layout.drawer is Drawer.GOALS:
            return "Click a word to change a goal.  Drag a slider to set it.  Space: run."
        if self.picked is not None:
            return f"Click the plane: {ONE[self.picked]} goes there.  Esc: put it back."
        if self.moving:
            return "Click where it goes, or move it with the arrows.  Enter or Esc: done."
        if self.focus is None:
            return "Click an object, or the plane.  Drag an object to move it.  Space: run."
        if isinstance(self.focus, Point):
            return "1, 2, 3: a light, an obstacle, a mark here.  Or the arrows, then Enter."
        return "Arrows: round the Wheel.  Enter: what is lit.  Drag it to move it."

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
            if not self._handed(level):
                return False
            if record:
                self.history.record(self.level)
            self._take(level)
        return True

    def follow_board(self) -> None:
        """Once a frame: the level placing what the Editor's board has locked, as the maker locks
        or frees its parts there (D-319); a step for the Maker's undo, which frees it again."""
        if self.board is None:
            return
        level = boarded(self.level, self.board)
        if level != self.level:
            self.history.record(self.level)
            self._take(level)

    def _handed(self, level: Level) -> bool:
        """The Editor's board handed out what `level` hands out, its zone and its parts, at once;
        False, refused with its reason, while the board has more of a part or lies outside, which
        is the player's to take off in the Editor (D-315)."""
        if self.board is None or level.board == self.level.board:
            return True
        refused = self.board.rehand(level.new_board())  # its zone, stock and locked parts
        if refused is not None:
            self._refuse(f"{refused.reason}: take it off in the Editor first")
            return False
        return True

    def action(self) -> Piece | Tool | None:
        """What the next click or Enter does, shown atop the plane (D-314): the object in hand,
        Move while it is in hand, the Wheel's lit icon; else nothing."""
        if self.picked is not None:
            return self.picked
        if self.moving:
            return Tool.MOVE
        offered = offer(self.focus)
        return offered[self.choice] if self.choice is not None else None

    def _place(self, piece: Piece, at: tuple[float, float]) -> None:
        """A light, an obstacle or a mark at the lattice point nearest `at` [u], the least of
        its kind, focused once there with More lit: Enter makes it more (D-314)."""
        if self._make(lambda level: placed(level, PLACED[piece], at)):
            self.focus, self.picked, self.moving = len(self.level.items) - 1, None, False
            self.choice = chosen(self.focus, Tool.MORE)

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
            return
        self.choice = chosen(focus, what)  # lit, as the Editor's Wheel lights it (D-314)
        if isinstance(what, Piece):  # on an empty point
            self._place(what, focus.at)
        elif what is Tool.MOVE:
            self.moving = not self.moving
        elif what is Tool.DELETE:
            at = self.level.items[focus].at
            if self._make(lambda level: removed(level, focus)):  # its point, to put another
                self.focus, self.moving, self.choice = Point(snapped(at)), False, None
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
        self.said = ""  # "Pasted" no longer holds (D-310)
        if level is None:
            self._refuse(f"nothing to {button.value}")
        elif not self._handed(level):  # the history put back as it was
            back = self.history.redo if button is EditButton.UNDO else self.history.undo
            back(level)
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
        if piece is Piece.START:  # focused as a click on it focuses it: Move in hand (D-314)
            self.focus, self.picked, self.moving = Piece.START, None, True
            self.choice = chosen(Piece.START, Tool.MOVE)
        else:  # in hand, the Wheel has nothing to show
            self.picked = None if self.picked is piece else piece
            self.carrying = self.picked is not None
            self.focus = None if self.picked is not None else self.focus

    def _escape(self) -> bool:
        """Esc: what is in hand put down, then the focus let go; False if there was nothing."""
        if self.picked is not None:
            self.picked = None
        elif self.moving or self.choice is not None:  # nothing lit: the Wheel's empty tool
            self.moving, self.choice = False, None
        elif self.focus is not None:
            self.focus, self.choice = None, None
        else:
            return False
        return True

    def _enter(self) -> None:
        """Enter: Move put down while it is in hand; else the Wheel's lit icon used, or, with
        none lit, the first lit (D-084, D-314)."""
        if self.moving:
            self.moving = False
        elif self.focus is not None and self.choice is None:
            self.choice = turned_to(self.focus, None, 1)
        elif self.focus is not None:
            self._do(offer(self.focus)[self.choice])

    # The view, as the run's (D-066, D-101)

    def extent(self) -> tuple[float, float, float, float]:
        """What Navigator's overview shows, and the most the plane may: what matters, never less
        than as the Maker opened, widened to the main screen's shape."""
        _, _, w, h = self.arena_area
        return widened(union(self._needed(), self._floor), w / h)

    def _needed(self, room: float = ROOM) -> tuple[float, float, float, float]:
        """What matters: the lights, the obstacles, the marks whole and the swimmer, `room`
        times over."""
        arena, marks = self.arena, self.level.marks
        at, radii = (
            np.array([m.at for m in marks]).reshape(-1, 2),
            np.array([m.value for m in marks]),
        )
        points = np.concatenate((self.pos, arena.light_xy, arena.disc_xy, rims(at, radii)))
        reach = float(np.concatenate(([LIGHT_RADIUS], arena.disc_radius, self.radius)).max())
        _, _, w, h = self.arena_area
        return extent(points, reach, w / h, room)

    def _open_view(self) -> None:
        """The view as the Maker opens on the level: what matters, centred; the overview never
        less than that view, a step farther out."""
        self.view = self._opening()
        self._floor = union(self._needed(), grown(shown(self.view, self.arena_area), ZOOM_STEP))

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
        elif event.type == pygame.KEYDOWN and self.field is not None:  # natively (D-206)
            self._field_key(event)
        elif event.type == pygame.KEYDOWN:
            self._key(event)

    def _press(self, pos: tuple[int, int]) -> None:
        """A click: a field, Brief's or a slider's box in Goals, to open once the click is over,
        a field open kept if the click falls elsewhere; then the frame's, Navigator's, the
        Wheel's icons, Objects' rows, Goals', then the plane: an object focused and grabbed, or
        a piece in hand put down, or Move done, or the open plane pressed, to focus a point or
        move the view."""
        field = self._field_at(pos)
        if self.field is not None and field != self.writing:
            self._field_done("enter")  # a click elsewhere keeps what was typed
        if field is not None:
            self.field_pressed = None if field == self.writing else field
            return
        slot = slot_at(self.wheel(), pos, WHEEL_HEX)
        if self.moving and slot is None and not contains(self.arena_area, pos):
            self.moving, self.choice = False, None  # anything off the plane drops Move (D-317)
        if self.frame_press(pos):
            return
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
        elif piece is not None:
            self._pick(piece)
        elif edit is not None:
            self._edit(edit)
        elif file_button_at(self.layout, pos) is FileButton.LEVEL:  # Files (D-310)
            self._copy_level()
        elif file_button_at(self.layout, pos) is FileButton.SHARE:  # ... with its proof (D-320)
            self._share_level()
        elif (start := start_row_at(self.layout, pos)) is not None:
            self._start_from(start)
        elif (step := stepper_at(self.layout, pos)) is not None:  # Parts (D-315)
            self._step(*step)
        elif (group := group_at(self.layout, pos)) is not None:  # ... its groups fold (D-069)
            self.folded ^= {group}
            self.layout = self._relayout(self.layout.drawer)
        elif (word := word_at(self.layout, pos)) is not None:  # Goals (D-308)
            self._make(lambda level: goal_worded(level, word.goal, word.word))
        elif (index := bin_at(self.layout, pos)) is not None:
            self._make(lambda level: goal_removed(level, index))
        elif goal_button_at(self.layout, pos) is GoalButton.ADD:
            self._make(goal_added)
        elif (knob := knob_at(self.layout, pos)) is not None:  # its track: followed while held
            self.sliding, self.before = knob[0], self.level
            self._slide(pos[0])
        elif action_at(self.layout, pos) is not None:  # atop the plane: Objects, its Wheel
            self.open_drawer(Drawer.OBJECTS)
        elif contains(self.arena_area, pos):
            self._press_plane(pos)

    def _press_plane(self, pos: tuple[int, int]) -> None:
        """A press on the plane: what is in hand put down; an object focused, Move lit, and
        grabbed, a drag moving it; with Move in hand, the open plane where it goes; else the
        open plane, a click focusing its point and a drag moving the view (D-302, D-314)."""
        at = self.view.to_world(*pos)
        target = object_at(self.level, self.view, pos)
        if self.picked is not None:
            self._place(self.picked, at)
        elif target is not None:  # Move in hand once the click is over, unless it was already
            self.arming = not (self.moving and target != self.focus)  # ... on another (D-317)
            self.focus, self.moving = target, self.moving and target == self.focus
            self.choice = chosen(target, Tool.MOVE) if self.arming else None
            self.press_at, self.before = pos, self.level
            x, y = where(self.level, target)
            self.grab, self.dragged = (x - at[0], y - at[1]), False
        elif self.moving:
            self._move_to(at)
        else:
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
        elif self.sliding is not None:
            self._slide(pos[0])
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
        object's move, or a slider's, is one step for undo; a click on the open plane focuses
        its point; a point or an object chosen opens Objects, its Wheel showing (D-317); a field
        pressed opens, now the click is over: Safari wants it so (D-206)."""
        if self.field_pressed is not None:
            self._open_field(self.field_pressed)
            self.field_pressed = None
        if self.carrying and contains(self.arena_area, pos):
            self._place(self.picked, self.view.to_world(*pos))
        held = self.grab is not None or self.sliding is not None
        if held and self.before is not None and self.level != self.before:
            self.history.record(self.before)
        clicked = self.press_at is not None and math.dist(pos, self.press_at) < CLICK
        if clicked and self.grab is not None:  # a click on an object: Move in hand (D-314)
            self.moving = self.arming
        elif clicked:
            self.focus, self.moving = Point(snapped(self.view.to_world(*self.press_at))), False
            self.choice = None
        chose = clicked or self.grab is not None  # a point or an object, not the view dragged
        if chose and self.layout.drawer is not Drawer.OBJECTS:
            self.open_drawer(Drawer.OBJECTS)  # the plane clicked: its Wheel shows (D-317)
        self.carrying = self.overviewing = self.zooming = False
        self.panning = self.press_at = self.grab = self.before = self.sliding = None
        self.frame_release()

    # Goals' sliders (D-308)

    def scale(self, knob: Knob) -> Range:
        """What a slider of Goals may be: the time allowed, or its goal's setting."""
        return TIME if knob.goal is None else settings(self.level.objectives[knob.goal])[0][1]

    def value(self, knob: Knob) -> float:
        """Where a slider of Goals stands: the time allowed [s], or its goal's setting."""
        if knob.goal is None:
            return self.level.time_limit
        goal = self.level.objectives[knob.goal]
        return getattr(goal, settings(goal)[0][0])

    def _set_knob(self, knob: Knob, value: Callable[[], float], record: bool = True) -> None:
        """A slider of Goals at `value()`, on its range's steps and within it; refused, as any
        change, if `value` raises Unmade: a box with no number typed in it."""
        if knob.goal is None:
            self._make(lambda level: timed(level, value()), record)
        else:
            self._make(lambda level: goal_set(level, knob.goal, value()), record)

    def _slide(self, x: float) -> None:
        """The slider held, set where the pixel column `x` falls along its track; one step for
        undo once let go, as an object's drag."""
        knob = self.sliding
        rect = dict(self.layout.knobs).get(knob)
        if rect is None:
            return
        scale = self.scale(knob)
        value = scale.lo + along(slider_parts(rect)[1], x) * (scale.hi - scale.lo)
        self._set_knob(knob, lambda: value, record=False)

    # Fields: Brief's (D-305), a slider's box in Goals (D-308), a level's text in Files (D-310)

    def _field_at(self, pos: tuple[int, int]) -> Brief | Knob | Paste | None:
        """The field under `pos`: Brief's title or spec, a slider's value box, or Files' field
        for a level's text."""
        if level_field_at(self.layout, pos):
            return Paste.LEVEL
        knob = knob_at(self.layout, pos)
        return knob[0] if knob is not None and knob[1] else brief_field_at(self.layout, pos)

    def _what(self, which: Brief | Knob) -> str:
        """What a field holds, as the status line asks for it."""
        if isinstance(which, Brief):
            return f"its {which.value}"
        if which.goal is None:
            return "the time allowed, in seconds"
        return f"its {settings(self.level.objectives[which.goal])[0][0]}"

    def _open_field(self, which: Brief | Knob | Paste) -> None:
        """The title's field, the spec's or the author's, holding what the level says now, the
        author's without its "@", which stands outside the field (D-331, D-341); a slider's box,
        holding its number, the caret after it; or Files' field, empty, for a level's text."""
        self.said = ""  # what the status line said before gives way to how to fill it
        if which is Paste.LEVEL:
            text, longest, taken = "", LEVEL_LONGEST, None
        elif isinstance(which, Knob):
            text, longest, taken = f"{self.value(which):g}", NUMBER_LONGEST, NUMBER
        elif which is Brief.TITLE:
            text, longest, taken = self.level.title, TITLE_LONGEST, None
        elif which is Brief.AUTHOR:  # the name after the "@", which stands outside (D-341)
            text = (self.level.author or "").removeprefix("@")
            longest, taken = AUTHOR_LONGEST - 1, None
        else:
            text, longest, taken = self.level.spec, SPEC_LONGEST, None
        self.writing, self.field = which, TextField(text, taken, longest)
        clipboard.open_field(text, longest)

    def _field_key(self, event: pygame.event.Event) -> None:
        """A key while a field is open, natively: Ctrl/Cmd+V pastes, Enter keeps it, Esc gives
        it up; the rest types or moves the caret."""
        if event.key == pygame.K_v and event.mod & (pygame.KMOD_CTRL | pygame.KMOD_META):
            self.field.paste(clipboard.paste())
            return
        ended = self.field.type(pygame.key.name(event.key), event.unicode)
        if ended is not None:
            self._field_done(ended)

    def _field_done(self, ended: str) -> None:
        """Enter, or a click elsewhere: the level says what was typed, a step for undo, unless
        there is nothing in it, or no number in a slider's box; Esc: as it was."""
        which, text = self.writing, self.field.text
        self.writing = self.field = None
        clipboard.close_field()
        if ended != "enter":
            return
        if which is Paste.LEVEL:
            self._paste_level(text)
        elif isinstance(which, Knob):  # on its range's steps, within it
            self._set_knob(which, lambda: number(text))
        else:
            if which is Brief.AUTHOR:  # its "@" first, whatever was typed (D-341)
                text = "@" + text.strip().lstrip("@")
            write = {Brief.TITLE: titled, Brief.SPEC: specified, Brief.AUTHOR: authored}[which]
            self._make(lambda level: write(level, text))

    # Parts (D-315)

    def _step(self, what: Stepper, steps: int) -> None:
        """A − or a + of Parts: the board a ring smaller or bigger, or a part handed out one
        fewer or more, the Editor's board with it."""
        if what.kind is None:
            self._make(lambda level: zoned(level, steps))
        else:
            self._make(lambda level: stocked(level, what.kind, steps))

    # Files (D-310)

    def _copy_level(self) -> None:
        """Copy level: its JSON, as the shipped levels' files hold it, on the clipboard;
        too long for the status line, which says how long it is."""
        text = to_json(self.level)
        clipboard.copy(text)
        self.said = f"Copied: the level's text, {len(text.splitlines())} lines of JSON."

    def _paste_level(self, text: str) -> None:
        """The level `text` holds, taken onto this one but its board's free parts, one step for
        undo, the view on it; or why not, in the status line. Its proof, if it has one, is run
        again on it, a few ticks a frame (D-320)."""
        try:
            other = read_level(text)
        except Unmade as why:
            self._refuse(str(why))
            return
        if not self._made_anew(lambda level: taken(level, other)):
            return
        self.said = f"Pasted: {self.level.title}."
        if other.proof is not None:
            proof, board = Proof.from_dict(other.proof), self.level.new_board()
            fits, why = load(board, proof.board)
            if not fits:
                self._refuse(f"its proof does not fit the level ({why}): a draft")
                return
            proof = replace(proof, parts=complexity(board))  # counted here, not taken on trust
            self.checking = (Replay(self.level, board, DT), proof, self.level)

    # Share level (D-320)

    @property
    def shareable(self) -> bool:
        """Whether the level, as it stands, has been won: its proof holds."""
        return self.proof is not None and self.proved == self.level

    def won(self, level: Level, board: Board, score: Score) -> None:
        """A run of the sandbox won (main.py): the board that won, if it won the level as it
        stands, its proof; a board no text can hold is no proof."""
        if level != self.level:
            return
        if self.shareable and not score.beats(Score(self.proof.parts, self.proof.ticks)):
            return  # the proof it has is as good: kept
        try:
            text = boardtext.to_text(board)
        except ValueError:
            return
        self.proof, self.proved = Proof(text, score.ticks, score.parts), level

    def _share_level(self) -> None:
        """Share level: the level's text with its proof, on the clipboard, and its box open on
        how to share it (D-346); refused, saying how, while the level as it stands is not won."""
        if not self.shareable:
            self._refuse("win it in Run first, as it stands, to share it")  # D-321
            return
        clipboard.copy(to_json(replace(self.level, proof=self.proof.to_dict())))
        seconds = self.proof.ticks * DT
        self.said = f"Copied, with its proof: won in {seconds:.2f} s, {self.proof.parts} parts."
        self.info, self.shared = FileButton.SHARE, True

    def _check_proof(self) -> None:
        """Once a frame: a pasted level's proof run on, CHECK_TICKS more; won, the level is
        cleared, its proof kept, the score to beat; else a draft. Given up if the level changed."""
        if self.checking is None:
            return
        replay, proof, level = self.checking
        if level != self.level:
            self.checking = None
            return
        ended = replay.advance(CHECK_TICKS)
        if ended is None:
            return
        self.checking = None
        if ended is not Outcome.WON:
            self.message = "its proof does not win it: pasted as a draft"
            return
        self.proof, self.proved = replace(proof, ticks=replay.tick), level  # its own tick
        seconds = replay.tick * DT
        self.said = f"Cleared: won in {seconds:.2f} s with {proof.parts} parts, the score to beat."

    def _start_from(self, start: Start) -> None:
        """A blank plane, or a shipped level taken onto this one but its board, one step for
        undo, the view on it."""
        if start.index is None:
            if self._made_anew(blank):
                self.said = "Started from a blank level."
        elif self._made_anew(lambda level: taken(level, self.starts[start.index][1])):
            self.said = f"Started from {self.level.title}."

    def open_blank(self) -> None:
        """The Maker opened for the first time: a blank plane to make (D-317), two of each part
        unless the Editor's board holds more, when the parts stay as they were; the sandbox's
        plane one undo away."""
        if self._made_anew(blank):
            self.said = "A blank plane to make.  Ctrl+Z: the plane of two lights."
            return
        self.message = ""  # refused for the board: the parts as they were, then
        if self._made_anew(lambda level: replace(blank(level), board=level.board)):
            self.said = "A blank plane, the parts as they were: the board holds more than two."

    def _made_anew(self, change: Callable[[Level], Level]) -> bool:
        """`change`, a level made anew, as `_make` makes any; once made, nothing is focused or
        in hand, and the view opens on it as the Maker opens."""
        if not self._make(change):
            return False
        self.focus, self.picked, self.moving, self.choice = None, None, False, None
        self._open_view()
        return True

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
        if self.tab_key(pygame.key.name(event.key)):  # F1, F2, F3 (D-303)
            return
        arrow = ARROW_SCANCODES.get(event.scancode) or (event.key if event.key in ARROWS else None)
        typed = KEY_ALIASES.get(event.unicode, event.unicode).upper()
        drawer = drawer_key(Env.MAKER, typed)  # the character first: AZERTY's ? is on the comma
        digits = DIGIT_SCANCODES + KEYPAD_SCANCODES
        if arrow is not None:
            self._arrow(arrow)
        elif event.scancode == pygame.KSCAN_SPACE:  # the switch: the run (D-021)
            self._ask("run")
        elif event.scancode == pygame.KSCAN_TAB:  # the next tab, or the one before (D-304)
            self.next_tab(bool(event.mod & pygame.KMOD_SHIFT))
        elif event.key == pygame.K_ESCAPE and not self._escape():  # nothing left: the levels
            self.toggle_drawer(Drawer.CHAPTERS)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):  # the Wheel's lit icon (D-314)
            self._enter()
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
        """With Move in hand, the focus moved 1 u the way of the arrow, a step for undo each;
        with something else focused, the Wheel's next icon lit, → and ↓ on, ← and ↑ back
        (D-084, D-314); else the view dragged a step, as the mouse would."""
        left, right, up, down = ARROWS
        if self.moving and self.focus is not None:
            dx, dy = {left: (-1, 0), right: (1, 0), up: (0, 1)}.get(key, (0, -1))  # y up
            x, y = where(self.level, self.focus)
            self._move_to((x + dx * POSITION, y + dy * POSITION))
            return
        if offer(self.focus):
            self.choice = turned_to(self.focus, self.choice, 1 if key in (right, down) else -1)
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
