"""The Editor (D-301): the sandbox's own environment, where its level is made while the Board and
the run try it.

The main screen shows the level's plane at large over its grid, the lattice its positions fall
on: its lights, obstacles, marks and rays, and the swimmer where it starts, facing where it
heads. Round it, the frame the Board and the run have (`frame.Frame`, D-051): Objects, as Parts
is the board's: the objects as rows, undo and redo, and at its foot the Wheel round what is
focused (D-068, D-069, `objects.py`); Goals, the time allowed and the goals, each a sentence
whose words are buttons, with a slider for its setting (D-308); Text, the level's title and
spec (D-305); Files, the level copied as text, another's text pasted, or a blank plane or a
shipped level to start from (D-310); Parts, the board's size and how many of each part, which
the Board takes at once, or refuses while it has more (D-315); Navigator, with
the overview, the zoom and the rays; Hints, Settings and Chapters at the bar's foot.

Round the plane, its keys (D-410, `editor_keys.py`), floating over it at its edges: at its left
the tools in pairs, Select and Hand, Bigger and Smaller, Zoom in and out, Undo and Redo, Copy
and Paste, Cut and Erase all; at its right the objects, Light, Obstacle, Mark and the Swimmer.
With Select, a click picks the object clicked, Shift or Cmd adds one, a click on the open plane
drops the pick (`plane_pick.py`); a drag from the open plane picks the objects it crosses, going
back cutting its path back; a drag from an object moves it, or the whole pick if it is picked,
on the lattice. With Hand, a drag moves the view; a right drag does, whatever is held. An
object's key held, each click on the plane places one, the least of its kind, while it stays
held; dragged from its key or its row onto the plane, one lands there and it is held. The
Swimmer's key picks the swimmer's start; dragged, it moves it. Bigger, Smaller, Cut and Copy act
on the items picked; Paste puts the copied ones where the mouse is, else beside them; Erase all
asks first. A value shows a moment under an object placed or set. The mouse wheel over an item
makes it more or less, over the swimmer turns it, over the open plane zooms there. Keys: S, H,
1 to 4, < and >, + and -, Del, Ctrl+C, Ctrl+V, Ctrl+X, Ctrl+Z and Ctrl+Y; the arrows move what
is picked, else the view; L and R turn the swimmer while it is picked; C centres, X shows or
hides the rays; Esc opens Chapters (D-406); Tab the next tab, Space the run. Each change is a new
`Level` (`making.py`), which `main.py` hands to the router, the Board and the next run.
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
from nektoids.editor.buttons import COUNT_FRAMES, State
from nektoids.editor.devdrive import DT
from nektoids.editor.editor_keys import Key, confirm_box, key_at, states
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
    along,
    bin_at,
    brief_field_at,
    contains,
    drawer_key,
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
from nektoids.editor.notches import RUN, Notches
from nektoids.editor.objects import ONE, PLACED, object_at, reach
from nektoids.editor.plane_pick import (
    NOTHING,
    Object,
    Pick,
    after_removal,
    boxed,
    clicked,
    items,
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
from nektoids.graph import boardtext
from nektoids.graph.board import Board, complexity
from nektoids.levels.lattice import POSITION, Range
from nektoids.levels.level import Item, Level, to_json
from nektoids.levels.making import (
    AUTHOR_LONGEST,
    GOALS_MOST,
    SPEC_LONGEST,
    TIME,
    TITLE_LONGEST,
    Unmade,
    added,
    authored,
    blank,
    boarded,
    erased,
    goal_added,
    goal_removed,
    goal_set,
    goal_worded,
    group_adjusted,
    group_moved,
    group_removed,
    number,
    placed,
    read_level,
    specified,
    start_moved,
    stocked,
    taken,
    timed,
    titled,
    turned,
    zoned,
)
from nektoids.levels.objectives import Outcome, at_start, settings
from nektoids.levels.proof import Proof, Replay
from nektoids.levels.score import Score
from nektoids.sim.arena import BASE_RADIUS, LIGHT_RADIUS

ARROW_PAN = 2.0  # an arrow drags the view this far [u]
CLICK = 4  # a press that moves less than this is a click, not a drag [px]
EDITOR_VIEW = (ViewButton.ZOOM_IN, ViewButton.ZOOM_OUT, ViewButton.CENTRE, ViewButton.RAYS)
VIEWS = {VIEW_KEYS[b]: b for b in EDITOR_VIEW}  # the keys the Editor's view answers: + - C X
KEYS_TYPED = {"S": Key.SELECT, "H": Key.HAND, "<": Key.SMALLER, ">": Key.BIGGER}  # D-410
TURN_KEYS = {TOOL_KEYS[Tool.TURN_LEFT]: 1, TOOL_KEYS[Tool.TURN_RIGHT]: -1}  # the start, picked
DIGITS = (Piece.LIGHT, Piece.OBSTACLE, Piece.MARK)  # 1 to 3, on their physical keys; 0 swims
PASTE_BESIDE = (2.0, 0.0)  # a paste with the mouse off the plane: beside what was copied [u]
ADD_KEYS = pygame.KMOD_SHIFT | pygame.KMOD_META  # held, a click or a drag adds to the pick
_copied: tuple[Item, ...] = ()  # what Copy and Cut keep, for every level of the session (D-410)
NUMBER = frozenset("0123456789.")  # what a slider's box takes, typed (D-308)
NUMBER_LONGEST = 5  # ... and how long it grows: 300, 12.5
LEVEL_LONGEST = 20_000  # what a level's text, pasted in Files, may run to (D-310)
CHECK_TICKS = 120  # a pasted level's proof run so many ticks a frame, a second of it (D-320)


class Paste(Enum):  # the field of the Editor's Files: a level's text pasted there (D-310)
    LEVEL = "level"


class EditorScene(Frame):
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
        layout = make_layout(drawer, env=Env.EDITOR, chapters=chapters, editor=True)
        self._start_frame(layout, settings)  # also `request`: "run", "board"... for main.py
        self.label = label  # "YOUR LEVEL", before its title in the caption (D-341)
        self.starts = tuple(starts)  # Start from's levels, each with its label: "1.2", or ""
        self.board = board  # the Board, which takes what the level hands out (D-315)
        self.proof: Proof | None = None  # the board that won the level, its score (D-320)
        self.proved: Level | None = None  # ... the level as it was won: shared while it holds
        self.checking: tuple[Replay, Proof, Level] | None = None  # a pasted proof, run again
        self.shared = False  # Share level's box says how to share what it copied (D-346)
        self.show_rays = True  # the light's rays, drawn or not
        self.pointer = (0, 0)  # where the mouse is [px]
        self.panning: tuple[int, int] | None = None  # a drag moving the view: where it last was
        self.overviewing = False  # Navigator's overview held: the view follows the mouse
        self.zooming = False  # Navigator's zoom bar held: the zoom follows the mouse
        self.held: Key | Piece = Key.SELECT  # the key in hand (D-410)
        self.pick: Pick = NOTHING  # the objects picked, in the order picked
        self.box_from: tuple[int, int] | None = None  # a drag from the open plane: a rectangle
        self.box_to: tuple[int, int] | None = None  # ... its other corner, under the mouse
        self.start_off = False  # the swimmer cut off the plane, to be placed again (D-410)
        self.laid: list[int] = []  # the items a drag with an object's key held has placed
        self.clicking = False  # ... the key used by clicks: a drag now is Select's (D-410)
        self.waiting = False  # ... a press whose release places one, unless it drags
        self.adding = False  # the add key down at the press
        self.press_at: tuple[int, int] | None = None  # a press on the plane: click, or drag?
        self.press_on: Object | None = None  # ... on an object
        self.grab_from: tuple[float, float] | None = None  # ... where on the plane [u]
        self.moving: tuple[Object, ...] = ()  # the objects a drag moves together
        self.before: Level | None = None  # the level as a drag began: one step for undo
        self.key_down: Key | Piece | None = None  # an object's key pressed: a click, or a drag
        self.right_at: tuple[int, int] | None = None  # a right press: a click, or a drag?
        self.carrying: Piece | None = None  # an object dragged from its key or its row
        self.confirming = False  # Erase all asked: Confirm or Cancel, Cancel the default
        self.counted: Object | None = None  # an object whose value shows a moment (D-410)
        self.count_frames = 0
        self.notches = Notches()  # the mouse wheel's scrolls, made steps (D-405)
        self.run_frames = 0  # ... frames left before a run of them is one step for undo
        self.history: History[tuple[Level, bool]] = History()  # the level, the swimmer off
        self.wheel_folded = False  # the Wheel left the Editor (D-410)
        self.writing: Brief | Knob | Paste | None = None  # a field typed in: Brief's, a box...
        self.field: TextField | None = None  # ... what it holds (D-305)
        self.field_pressed: Brief | Knob | Paste | None = None  # opens once the click is over
        self.sliding: Knob | None = None  # a slider of Goals held: its value follows the mouse
        self.folded: set[str] = set()  # Parts' groups shown closed, as the Board's (D-315),
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
            env=Env.EDITOR,
            chapters=self.layout.chapters,
            editor=True,
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
        self.pick = tuple(o for o in self.pick if not isinstance(o, int) or o < len(level.items))
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
        self.count_frames = max(0, self.count_frames - 1)
        self.notches.tick()
        if self.run_frames > 0:
            self.run_frames -= 1
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
        if self.confirming:
            return "Erase every object?  Erase all erases them; Cancel, Enter or Esc keeps them."
        if self.held is Piece.START:
            return "Click the plane: the swimmer starts there."
        if isinstance(self.held, Piece):
            return f"Click the plane: {ONE[self.held]} at each click; drag, a row.  S: Select."
        if self.start_off:
            return "The swimmer is off the plane: 0, or its key, then a click places it."
        if self.held is Key.HAND:
            return "Drag the plane to move it.  S: back to Select."
        if self.pick:
            return "Drag to move what is picked.  Arrows: 1 u.  The lit keys act on it."
        return "Click or drag over objects to pick them, Shift adds.  Or press a key."

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
                self.history.record((self.level, self.start_off))
            self._take(level)
        return True

    def follow_board(self) -> None:
        """Once a frame: the level placing what the Board has locked, as the maker locks
        or frees its parts there (D-319); a step for the Editor's undo, which frees it again."""
        if self.board is None:
            return
        level = boarded(self.level, self.board)
        if level != self.level:
            self.history.record((self.level, self.start_off))
            self._take(level)

    def _handed(self, level: Level) -> bool:
        """The Board handed out what `level` hands out, its zone and its parts, at once;
        False, refused with its reason, while the board has more of a part or lies outside, which
        is the player's to take off on the Board (D-315)."""
        if self.board is None or level.board == self.level.board:
            return True
        refused = self.board.rehand(level.new_board())  # its zone, stock and locked parts
        if refused is not None:
            self._refuse(f"{refused.reason}: take it off on the Board first")
            return False
        return True

    def _place(self, piece: Piece, at: tuple[float, float], record: bool = True) -> bool:
        """A light, an obstacle or a mark at the lattice point nearest `at` [u], the least of
        its kind, picked, its value shown a moment; the swimmer, if it was off the plane, and
        Select in hand again: a level has one (D-410)."""
        if piece is Piece.START:
            if self._make(lambda level: start_moved(level, at), record):
                self.start_off, self.held, self.pick = False, Key.SELECT, (Piece.START,)
                return True
            return False
        if self._make(lambda level: placed(level, PLACED[piece], at), record):
            self.pick = (len(self.level.items) - 1,)
            self._count(self.pick[0])
            return True
        return False

    def _object_at(self, pos: tuple[int, int]) -> Object | None:
        """The object under `pos`: the swimmer only while it is on the plane."""
        found = object_at(self.level, self.view, pos)
        return None if found is Piece.START and self.start_off else found

    def _ask(self, request: str) -> None:
        """As the frame's; the run refused while the swimmer is off the plane (D-410)."""
        if request == "run" and self.start_off:
            self._refuse("the swimmer is off the plane: place it with its key, 0")
            return
        super()._ask(request)

    def _count(self, obj: Object) -> None:
        """`obj`'s value under it, a moment, as the Board's count of parts left (D-401, D-410)."""
        self.counted, self.count_frames = obj, COUNT_FRAMES

    def key_states(self) -> dict:
        return states(
            self.level,
            self.held,
            self.pick,
            self.history.can_undo,
            self.history.can_redo,
            bool(_copied),
            self.start_off,
        )

    def _press_key(self, key: Key | Piece) -> None:
        """A key round the plane, clicked or by its key (D-410)."""
        looks = self.key_states()
        if key in (Key.SELECT, Key.HAND):
            self.held = key
        elif key is Piece.START and looks[key] is State.GREYED:
            self._refuse("the swimmer is on the plane: drag it, or cut it first")
        elif isinstance(key, Piece):  # held for the clicks on the plane; pressed again, put down
            self.held = Key.SELECT if self.held is key else key
            self.clicking = False  # its first gesture says: a drag lays a row, a click clicks
        elif key is Key.ZOOM_IN:
            self._view(ViewButton.ZOOM_IN)
        elif key is Key.ZOOM_OUT:
            self._view(ViewButton.ZOOM_OUT)
        elif key in (Key.UNDO, Key.REDO):
            self._edit(EditButton.UNDO if key is Key.UNDO else EditButton.REDO)
        elif looks[key].value == "greyed":
            self._refuse(_why_not(key))
        elif key in (Key.BIGGER, Key.SMALLER):
            self._resize(items(self.pick), 1 if key is Key.BIGGER else -1)
        elif key is Key.COPY:
            self._copy()
        elif key is Key.PASTE:
            self._paste()
        elif key is Key.CUT:
            self._cut()
        elif key is Key.ERASE:  # asked first: the goals go too (D-410)
            self.confirming = True

    def _resize(self, chosen: list[int], steps: int) -> None:
        """Items `chosen` set `steps` more, or less; the first one's value shown."""
        if chosen and self._make(lambda level: group_adjusted(level, chosen, steps)):
            self._count(chosen[0])

    def _copy(self) -> None:
        """The items picked kept, for Paste, in any level of the session (D-410)."""
        global _copied
        _copied = tuple(self.level.items[k] for k in items(self.pick))
        self.said = f"Copied: {len(_copied)} object{'s' * (len(_copied) != 1)}."

    def _paste(self) -> None:
        """Copies of what was copied, centred where the mouse is on the plane, else beside where
        they were; picked once there."""
        if not _copied:
            self._refuse(_why_not(Key.PASTE))
            return
        over = contains(self.arena_area, self.pointer)
        if over and key_at(self.arena_area, self.pointer) is None:
            x, y = self.view.to_world(*self.pointer)
            cx = sum(i.at[0] for i in _copied) / len(_copied)
            cy = sum(i.at[1] for i in _copied) / len(_copied)
            offset = (x - cx, y - cy)
        else:
            offset = PASTE_BESIDE
        first = len(self.level.items)
        if self._make(lambda level: added(level, _copied, offset)):
            self.pick = tuple(range(first, len(self.level.items)))

    def _cut(self) -> None:
        """The items picked kept, as Copy keeps them, and taken off the plane; the swimmer, if
        picked, taken off too, to be placed again with its key (D-410). One step for undo."""
        chosen, swimmer = items(self.pick), Piece.START in self.pick and not self.start_off
        kept = tuple(self.level.items[k] for k in chosen)
        if chosen:
            if not self._make(lambda level: group_removed(level, chosen)):
                return
            global _copied
            _copied = kept
        elif swimmer:
            self.history.record((self.level, self.start_off))
        self.start_off = self.start_off or swimmer
        self.pick = after_removal(tuple(o for o in self.pick if o is not Piece.START), chosen)

    def _erase(self) -> None:
        """Erase all, confirmed: every item and every goal, one step for undo; the swimmer
        stays."""
        self.confirming = False
        if self._make(erased):
            self.pick = tuple(o for o in self.pick if not isinstance(o, int))
            self.said = "Erased.  Ctrl+Z brings them back."

    def _edit(self, button: EditButton) -> None:
        """Undo or redo (D-027): the level as it was before the last change, or after."""
        now = (self.level, self.start_off)
        made = self.history.undo(now) if button is EditButton.UNDO else self.history.redo(now)
        self.said = ""  # "Pasted" no longer holds (D-310)
        if made is None:
            self._refuse(f"nothing to {button.value}")
        elif not self._handed(made[0]):  # the history put back as it was
            back = self.history.redo if button is EditButton.UNDO else self.history.undo
            back(made)
        else:
            self.start_off = made[1]
            self._take(made[0])

    def _move_pick(self, offset: tuple[float, float], record: bool = True) -> bool:
        """The objects picked moved together by `offset` [u], from the level before the drag if
        one is under way."""
        chosen, start = items(self.moving or self.pick), Piece.START in (self.moving or self.pick)
        base = self.before if self.before is not None else self.level
        return self._make(lambda _: group_moved(base, chosen, start, offset), record)

    # The view, as the run's (D-066, D-101)

    def extent(self) -> tuple[float, float, float, float]:
        """What Navigator's overview shows, and the most the plane may: what matters, never less
        than as the Editor opened, widened to the main screen's shape."""
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
        """The view as the Editor opens on the level: what matters, centred; the overview never
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
        """As the frame's, and the key round the plane under the mouse (D-410)."""
        return super()._tip_target(pos) or key_at(self.arena_area, pos)

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.info is not None and event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
            self.info = None  # the next click or key closes the box, and only that
            return
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
            self.message = ""
        if self.confirming and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._confirm_press(event.pos)
        elif self.confirming and event.type == pygame.KEYDOWN:
            self.confirming = False  # Cancel, the default: Enter, Esc or any key (D-410)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._press(event.pos)
        elif event.type == pygame.MOUSEMOTION:
            self._track(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._release(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if contains(self.arena_area, event.pos):  # a right drag moves the view (D-410)
                self.panning = self.right_at = event.pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 3:
            if self.right_at is not None and math.dist(event.pos, self.right_at) < CLICK:
                self.held, self.pick = Key.SELECT, NOTHING  # a right click: put it all down
            self.panning = self.right_at = None
        elif event.type == pygame.MOUSEWHEEL:
            if not self.frame_wheel(self.pointer, event.y):  # else the drawer's rows (D-096)
                self._wheel_on(event)
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
        if self.frame_press(pos):
            return
        piece = piece_row_at(self.layout, pos)
        key = key_at(self.arena_area, pos) if contains(self.arena_area, pos) else None
        if key is not None and isinstance(key, Piece):  # a click, or a drag: the release tells
            self.key_down = key
        elif key is not None:
            self._press_key(key)
        elif overview_at(self.layout, pos):
            self.overviewing = True
            self._overview_to(pos)
        elif (step := zoom_button_at(self.layout, pos)) is not None:
            self._view(step)
        elif zoom_bar_at(self.layout, pos) is not None:
            self.zooming = True
            self._zoom_to(pos)
        elif (button := view_button_at(self.layout, pos)) is not None:
            self._view(button)
        elif piece is not None:  # a row of Objects: as its key, and dragged onto the plane
            self.key_down = piece
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
        elif contains(self.arena_area, pos):
            self._press_plane(pos)

    def _press_plane(self, pos: tuple[int, int]) -> None:
        """A press on the plane: with an object's key held, one placed there; with Hand, the
        view held; with Select, an object pressed, to pick it or drag it, or the open plane, to
        drop the pick or sweep a pick along a drag (D-410)."""
        at = self.view.to_world(*pos)
        self.adding = bool(pygame.key.get_mods() & ADD_KEYS)
        if isinstance(self.held, Piece) and self.clicking:  # a click places; a drag selects
            self.press_at, self.before, self.waiting = pos, self.level, True
            self.press_on, self.grab_from = self._object_at(pos), at
            return
        if isinstance(self.held, Piece):  # one here; a drag lays more along its way
            self.press_at, self.before, self.laid = pos, self.level, []
            if self._place(self.held, at) and self.held is not Key.SELECT:
                self.laid = [len(self.level.items) - 1]
            return
        if self.held is Key.HAND:
            self.panning = pos
            return
        self.press_at, self.before = pos, self.level
        self.press_on = self._object_at(pos)
        self.grab_from = at

    def _track(self, pos: tuple[int, int]) -> None:
        """The mouse moved: the tooltip, a held overview, zoom bar or slider; the view dragged;
        an object's key dragged off it; the pick swept, or moved, on the lattice."""
        self.pointer = pos
        self.frame_track(pos)
        if self.key_down is not None and key_at(self.arena_area, pos) != self.key_down:
            if piece_row_at(self.layout, pos) != self.key_down:  # off its key, or its row
                self.carrying, self.key_down = self.key_down, None
        if self.overviewing:
            self._overview_to(pos)
        elif self.zooming:
            self._zoom_to(pos)
        elif self.sliding is not None:
            self._slide(pos[0])
        elif self.panning is not None:
            dx, dy = pos[0] - self.panning[0], pos[1] - self.panning[1]
            self.view = pan_view(self.view, dx, dy)
            self.panning = pos
        elif self.press_at is not None and math.dist(pos, self.press_at) >= CLICK:
            self._drag(pos)

    def _drag(self, pos: tuple[int, int]) -> None:
        """A drag on the plane with Select: from an object, it moves, with the pick if it is
        picked; from the open plane, the objects it crosses are picked."""
        if self.waiting:  # clicks placed some: a drag puts the key down, Select's (D-410)
            self.held, self.waiting = Key.SELECT, False
        if isinstance(self.held, Piece):
            self._lay(pos)
            return
        if self.press_on is None:  # a rectangle, its first corner where the press was
            self.box_from, self.box_to = self.press_at, pos
            return
        if not self.moving:
            self.moving = self.pick if self.press_on in self.pick else (self.press_on,)
            self.pick = self.moving
        x, y = self.view.to_world(*pos)
        offset = (round(x - self.grab_from[0]), round(y - self.grab_from[1]))
        self._move_pick(offset, record=False)

    def _lay(self, pos: tuple[int, int]) -> None:
        """An object's key held, the drag on: one more each time the mouse is a width past the
        last laid, touching it; back over one laid before, those laid after it go, however far
        back, as the Board's parts (D-404, D-410)."""
        at = self.view.to_world(*pos)
        for k, index in enumerate(self.laid[:-1]):
            if math.dist(at, self.level.items[index].at) < reach(self.level, index):
                gone = self.laid[k + 1 :]
                self._make(lambda level, gone=gone: group_removed(level, gone), record=False)
                self.laid = self.laid[: k + 1]
                self.pick = (self.laid[-1],)
                return
        if self.laid:
            last = self.laid[-1]
            if math.dist(at, self.level.items[last].at) < 2 * reach(self.level, last):
                return
        if self._place(self.held, at, record=False):
            self.laid.append(len(self.level.items) - 1)
        else:
            self.message = ""  # a point the level refuses along the way: passed over quietly

    def centres(self) -> dict:
        """Each object's centre on the screen [px], the swimmer while it is on the plane."""
        found = {k: self.view.to_screen(*item.at) for k, item in enumerate(self.level.items)}
        if not self.start_off:
            found[Piece.START] = self.view.to_screen(*self.level.start[:2])
        return found

    def _release(self, pos: tuple[int, int]) -> None:
        """The mouse let go: an object's key let go on itself, a click; carried onto the plane,
        one lands there; a drag's move, or a slider's, one step for undo; a click on the plane
        picks, or drops the pick; a field pressed opens, now the click is over: Safari wants it
        so (D-206)."""
        if self.field_pressed is not None:
            self._open_field(self.field_pressed)
            self.field_pressed = None
        if self.key_down is not None:  # let go on its key, or its row: a click
            self._press_key(self.key_down)
        elif self.carrying is not None and contains(self.arena_area, pos):
            if key_at(self.arena_area, pos) is None:
                at = self.view.to_world(*pos)
                if self.carrying is not Piece.START:
                    self.held = self.carrying
                self._place(self.carrying, at)
        if self.box_from is not None:  # the rectangle's pick, once let go
            self.pick = boxed(self.pick, self.centres(), self.box_from, pos, self.adding)
        if self.waiting:  # a click with the key used by clicks: one placed where it was pressed
            self.waiting = False
            self._place(self.held, self.view.to_world(*self.press_at))
            self.press_at = None
        laying = isinstance(self.held, Piece) and self.press_at is not None
        moved = self.moving or self.sliding is not None or laying
        if moved and self.before is not None and self.level != self.before:
            self.history.record((self.before, self.start_off))
        clicked_ = self.press_at is not None and math.dist(pos, self.press_at) < CLICK
        if laying and len(self.laid) > 1:  # a drag laid a row: Select in hand again (D-410)
            self.held = Key.SELECT
        elif laying:  # a click: the key used by clicks from now on
            self.clicking = True
        elif clicked_ and not laying:
            self.pick = clicked(self.pick, self.press_on, self.adding)
        self.overviewing = self.zooming = False
        self.key_down = self.carrying = self.box_from = self.box_to = None
        self.laid = []
        self.panning = self.press_at = self.press_on = self.grab_from = None
        self.before = self.sliding = None
        self.moving = ()
        self.frame_release()

    def _confirm_press(self, pos: tuple[int, int]) -> None:
        """Erase all's box: Confirm erases; Cancel, or a click anywhere else, keeps it all."""
        _, _, erase = confirm_box(self.arena_area)
        if contains(erase, pos):
            self._erase()
        else:
            self.confirming = False

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
        fewer or more, the Board with it."""
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
        if at_start(self.level) is not None:  # nothing a run can win (D-349)
            self._refuse("its goals are decided where the swimmer starts: nothing to share")
            return
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
        """The Editor opened for the first time: a blank plane to make (D-317), two of each part
        unless the Board holds more, when the parts stay as they were; the sandbox's
        plane one undo away."""
        if self._made_anew(blank):
            self.said = "A blank plane to make.  Ctrl+Z: the plane of two lights."
            return
        self.message = ""  # refused for the board: the parts as they were, then
        if self._made_anew(lambda level: replace(blank(level), board=level.board)):
            self.said = "A blank plane, the parts as they were: the board holds more than two."

    def _made_anew(self, change: Callable[[Level], Level]) -> bool:
        """`change`, a level made anew, as `_make` makes any; once made, nothing is focused or
        in hand, and the view opens on it as the Editor opens."""
        if not self._make(change):
            return False
        self.pick, self.held = NOTHING, Key.SELECT
        self._open_view()
        return True

    def _wheel_on(self, event: pygame.event.Event) -> None:
        """The mouse wheel: over an item, more or less of it, the whole pick if it is picked;
        over the swimmer, turned; over the open plane, the view zoomed about the mouse (D-410).
        A trackpad's small scrolls add up to a notch (D-405); a run of steps on the same objects
        is one step for undo."""
        pos = self.pointer
        if not contains(self.arena_area, pos) or key_at(self.arena_area, pos) is not None:
            return
        up = getattr(event, "precise_y", event.y)
        if getattr(event, "flipped", False):
            up = -up
        steps = self.notches.feed(up)
        if steps == 0:
            return
        target = self._object_at(pos)
        if target is None:
            self.view = zoom_view(self.view, ZOOM_STEP**steps, pos)
            return
        if self.run_frames == 0:  # a new run: one step for undo, the level as it was
            self.history.record((self.level, self.start_off))
        self.run_frames = RUN
        if target is Piece.START:
            self._make(lambda level: turned(level, steps), record=False)
            self._count(target)
            return
        chosen = items(self.pick) if target in self.pick else [target]
        if self._make(lambda level: group_adjusted(level, chosen, steps), record=False):
            self._count(target)

    def _key(self, event: pygame.event.Event) -> None:
        if event.mod & (pygame.KMOD_CTRL | pygame.KMOD_META):
            if event.key == pygame.K_z:
                self._edit(EditButton.REDO if event.mod & pygame.KMOD_SHIFT else EditButton.UNDO)
            elif event.key == pygame.K_y:
                self._edit(EditButton.REDO)
            elif event.key == pygame.K_c:
                self._press_key(Key.COPY)
            elif event.key == pygame.K_v:
                self._press_key(Key.PASTE)
            elif event.key == pygame.K_x:
                self._press_key(Key.CUT)
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
        drawer = drawer_key(Env.EDITOR, typed)  # the character first: AZERTY's ? is on the comma
        digits = DIGIT_SCANCODES + KEYPAD_SCANCODES
        if arrow is not None:
            self._arrow(arrow)
        elif event.scancode == pygame.KSCAN_SPACE:  # the switch: the run (D-021)
            self._ask("run")
        elif event.scancode == pygame.KSCAN_TAB:  # the next tab, or the one before (D-304)
            self.next_tab(bool(event.mod & pygame.KMOD_SHIFT))
        elif event.key == pygame.K_ESCAPE:  # Chapters' key only, as on the Board (D-406)
            self.toggle_drawer(Drawer.CHAPTERS)
        elif event.scancode in DELETE_SCANCODES:  # Cut, on the physical key (D-410)
            self._press_key(Key.CUT)
        elif event.scancode in (pygame.KSCAN_0, pygame.KSCAN_KP_0):  # the swimmer (D-410)
            self._press_key(Piece.START)
        elif event.scancode in digits and digits.index(event.scancode) % 9 < len(DIGITS):
            self._press_key(DIGITS[digits.index(event.scancode) % 9])
        elif self.start_passkey(typed):  # P in Chapters: a passkey (D-075)
            pass
        elif drawer is not None:  # its initial, or the comma (D-069)
            self.toggle_drawer(drawer)
        elif typed in KEYS_TYPED:
            self._press_key(KEYS_TYPED[typed])
        elif typed in TURN_KEYS and Piece.START in self.pick:
            self._make(lambda level: turned(level, TURN_KEYS[typed]))
            self._count(Piece.START)
        elif typed in VIEWS:
            self._view(VIEWS[typed])

    def _arrow(self, key: int) -> None:
        """What is picked moved 1 u the way of the arrow, a step for undo each; with nothing
        picked, the view dragged a step, as the mouse would."""
        left, right, up, _ = ARROWS
        if self.pick:
            dx, dy = {left: (-1, 0), right: (1, 0), up: (0, 1)}.get(key, (0, -1))  # y up
            self._move_pick((dx * POSITION, dy * POSITION))
            return
        step = ARROW_PAN * self.view.scale
        dx, dy = {left: (-step, 0.0), right: (step, 0.0), up: (0.0, -step)}.get(key, (0.0, step))
        self.view = pan_view(self.view, dx, dy)


def _why_not(key: Key) -> str:
    """Why a greyed key does nothing now, for the status line (D-410)."""
    if key is Key.PASTE:
        return "nothing copied yet: pick objects, then Copy"
    if key is Key.ERASE:
        return "nothing to erase"
    return "pick a light, an obstacle or a mark first"
