"""Where everything sits on the 960 x 640 screen, editor or run, and what is under a pixel (D-051).

- Left, the activity bar: an icon for each drawer, Parts, Tools and Navigator at the top in the
  editor, Objectives, Inside, Score and Navigator in the run, Objects, Parts, Goals, Brief,
  Files and Navigator in the Maker; Hints, Settings and Chapters at its foot, over the accented
  switch to the run, or from the run to the editor (`Env`).
- Beside it, one drawer at a time, or none: its title, then rows all alike (icon, name, an
  info disc, then a count or a key). Parts: the groups (sensors, actuators, operators) that fold
  under their title, only the parts the level hands out; Tools: Mode (Write, Delete), Edit
  (undo, redo); Files: each level's wins, groups that fold as Parts' do (D-092), then
  Save/Load: Copy a board, Paste a board (D-206); Navigator: the view's buttons; Hints: the
  level's, asked for in turn (D-078); Settings: what the player sets (D-054); Chapters: the
  levels, then the sandbox, which replaces the full-screen map. Goals, in the Maker: the time
  allowed, a slider, then each goal's name over three rows of buttons, its words (D-308);
  Files, in the Maker: Copy level, then a field to paste a level's text into (D-310); Parts,
  in the Maker: the board's size and how many of each part, each with − and + (D-315).
  Rows that do not fit scroll, above the Wheel in Tools and Parts and above the objectives in
  the run (D-096). An arrow on the drawer's edge folds it.
- The rest is the main screen: the tabs over it (Run, Editor, and on the sandbox the Maker,
  D-301), the level's caption under them, then the board's hex grid, in the run the arena with
  its controls under it, in the Maker the plane; one status line at its foot. A drawer opening
  pushes the main screen aside.

The View says how big a hex is and where the grid sits in the board's area; zoom and pan change
only the View (D-013). Plain numbers and tuples, no pygame, so hit-testing is testable headless.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from nektoids.graph.board import Kind
from nektoids.graph.hexgrid import SQRT3, Cell, from_pixel, to_pixel
from nektoids.graph.kinds import Category
from nektoids.levels.objectives import Count, Target, Verb

Rect = tuple[int, int, int, int]  # x, y, width, height [px]

SCREEN = (960, 640)  # [px]
BAR_WIDTH = 48  # the activity bar, down the left edge [px]
BAR_BUTTON = 40  # an icon's square in it [px]
BAR_PITCH = 48  # from one icon to the next [px]
SWITCH = 36  # the accented switch at its foot, square [px]
ACTION_WIDTH = 50  # atop the editor's main screen, what a click does: a Wheel's icon, square [px]
ACTION_ROOM = 96  # from the board's top: the action, the line under it, a little more [px]
DRAWER_WIDTH = 248  # [px]
DRAWER_TOP = 40  # the first row or section title, under the drawer's own title [px]
ROW_HEIGHT = 40  # a drawer's row [px]
OVERVIEW_HEIGHT = 168  # Navigator's overview, under its rows [px]
ZOOM_BUTTON = 28  # zoom out and in, either end of the zoom bar, under the overview [px]
FOOT_MARGIN = 6  # under the objectives, at the drawer's foot [px]
WHEEL_HEIGHT = 236  # the Wheel at a drawer's foot: the cell, its icons, piles and all, its line
WHEEL_TITLE = "The Wheel"  # its title, at the foot of Tools and of Parts; a click folds it (D-069)
SCROLL_WIDTH = 5  # a drawer's scroll bar, in its right margin, while its rows do not fit [px]
SCROLL_STEP = 23  # what a notch of the mouse wheel scrolls a list by: half a row [px]
SCROLL_THUMB = 24  # the scroll bar's thumb, at its shortest [px]
GOAL_HEIGHT = 48  # an objective's row in the run: its name, then its bar and count [px]
HINT_ROWS = 3  # Hints' rows: the idea, the parts, the shadow (D-078)
HINT_LINE = 20  # a line of a hint under its row, as a note's [px]; of Brief's spec's field
SPEC_LINES = 6  # Brief's spec's field: so many lines, enough for SPEC_LONGEST (D-305)
FIELD_PAD = 10  # ... and so much over and under them [px]
HEAD_HEIGHT = 28  # a goal's name in Goals, over its words, a bin at its right end (D-308) [px]
BIN = 28  # ... the bin's square, where a click takes the goal out [px]
WORD_HEIGHT = 26  # a word's button: a verb, how many, a target [px]
WORD_GAP = 4  # ... between two, either way; under a slider [px]
SLIDER_HEIGHT = 30  # a slider of Goals: its label, its track, its value [px]
KNOB_LABEL = 64  # ... its label, at its left [px]
KNOB_VALUE = 56  # ... its value's box, at its right [px]
STEP_BUTTON = 28  # a row of the Maker's Parts: its − and +, square, the count between [px]
SHADOW_GAP = 6  # from the shadow's picture to the line under it [px]
SHADOW_LEAST = 140  # the shadow's picture shrinks to fit Hints, no smaller: then it scrolls [px]
ROW_PITCH = 46  # from one row to the next [px]
ROW_INSET = 12  # a row's sides from the drawer's [px]
TITLE_HEIGHT = 24  # a group's or a section's title in a drawer [px]
SECTION_GAP = 6  # before a section title or a group [px]
INFO_AT = 156  # a row's info disc: its centre, this far from the row's left [px]
INFO_HIT = 20  # ... and the square a click on it falls in [px]
HANDLE = (14, 44)  # the arrow on the drawer's edge that folds it [px]
TABS_HEIGHT = 32  # the strip of tabs over the board [px]
CAPTION_HEIGHT = 26  # under the tabs, inside the Editor's: the level's title and spec [px]
TOP = TABS_HEIGHT + CAPTION_HEIGHT  # the board's top edge [px]
TABS = ("run", "editor")  # a level's tabs, Run first (D-069)
MAKER_TABS = (*TABS, "maker")  # the sandbox's: the Maker makes its level (D-301)
TAB_WIDTHS = {"run": 64, "editor": 84, "maker": 80}  # [px]
TAB_KEYS = {"run": "F1", "editor": "F2", "maker": "F3"}  # each tab's key, in their order (D-303)
STATUS_HEIGHT = 28  # [px]
CONTROLS_HEIGHT = 48  # the run's controls, a strip under the arena [px]
MARGIN = 16  # [px]
BUTTON = 40  # a palette button's side, in the run view [px]
PALETTE_TITLE = 24  # a section's title, in the run view and the drawers [px]
HEX_SIZE = 40.0  # centre-to-corner size of a hex in the default view [px]
MIN_HEX, MAX_HEX = 20.0, 80.0  # zoom limits [px]
ZOOM_STEP = 1.25  # hex size factor per click

# Parts' groups, actuators before operators (D-069): the number keys follow this order; within a
# group, the parts in the table's order (D-202).
MENU_GROUPS: tuple[tuple[str, tuple[Kind, ...]], ...] = tuple(
    (title, tuple(kind for kind in Kind if kind.category is category))
    for title, category in (
        ("Sensors", Category.SENSOR),
        ("Actuators", Category.ACTUATOR),
        ("Operators", Category.OPERATOR),
    )
)


class Tool(Enum):
    ADD = "add"
    WIRE = "wire"
    MOVE = "move"
    DELETE = "delete"
    TURN_LEFT = "turn left"  # counter-clockwise, 60° a click
    TURN_RIGHT = "turn right"  # clockwise
    PAN = "pan"  # moves the view, not a component; the hand among the view buttons
    SWAP = "swap"  # the focused part for another of its group in Parts (D-068)
    LESS = "less"  # the Maker's: the focused light dimmer, the obstacle smaller (D-301)
    MORE = "more"  # ... brighter, bigger


PALETTE_TOOLS = (
    Tool.ADD,
    Tool.WIRE,
    Tool.MOVE,
    Tool.DELETE,
    Tool.TURN_LEFT,
    Tool.TURN_RIGHT,
    Tool.SWAP,
)
TURNS = {Tool.TURN_LEFT: 1, Tool.TURN_RIGHT: -1}  # hex directions run counter-clockwise


class Piece(Enum):  # Objects' rows: what the Maker puts on the plane (D-301)
    LIGHT = "light"
    OBSTACLE = "obstacle"
    MARK = "mark"  # a zone, which only the objectives read (D-306)
    START = "start"  # the swimmer's start: always one, moved and turned, never placed


class Brief(Enum):  # Brief's fields, in the Maker: what the level is called and asks (D-305)
    TITLE = "title"
    SPEC = "spec"


class EditButton(Enum):
    UNDO = "undo"
    REDO = "redo"


class GoalButton(Enum):  # Goals' last row, while the level asks fewer than two (D-308)
    ADD = "add"


class Shown(Enum):  # atop the editor's main screen (D-068)
    ACTION = "action"  # what the next click or Enter does, and its key; a click opens Tools


class Mode(Enum):  # what a click on the board does (D-068)
    WRITE = "write"  # a cell focused, its Wheel: place, turn, wire, move
    DELETE = "delete"  # the part clicked removed with its wires, or the wire clicked
    LOCK = "lock"  # the sandbox's: the part clicked made the level's, or freed (D-319)


class LevelButton(Enum):  # the accented switch at the bar's foot, to the other environment
    RUN = "run"  # in the editor: the board, swimming in its arena
    EDIT = "edit"  # in the run: back to the board as it was left


class FileButton(Enum):  # at Files' foot, under the wins (D-206)
    SAVE = "save"  # Copy a board: its text; the field to paste one is under it
    LEVEL = "level"  # the Maker's Files: Copy level, its JSON; a field under it (D-310)
    SHARE = "share"  # ... Share level: its JSON and its proof, once it is won (D-320)


class ViewButton(Enum):
    ZOOM_IN = "zoom in"
    ZOOM_OUT = "zoom out"
    PAN = "pan"
    CENTRE = "centre"  # bring cell (0, 0) back to the middle, at the same zoom
    RAYS = "rays"  # the run's only: the light's rays, shown or not
    MOTION = "motion"  # the run's only: the swimmer's velocity and spin, shown or not (D-076)
    STREAMS = "streams"  # the run's only: its flames and the light it draws in, shown or not


class Drawer(Enum):  # D-051
    TOOLS = "tools"  # Write and Delete; undo and redo; the Wheel (D-068, D-069)
    PARTS = "parts"  # the parts the level hands out, and what each does
    FILES = "files"  # this session's winning boards, to put one back (D-059)
    DIAGNOSTIC = "diagnostic"  # the level, small, with the probe the Run preview runs at (D-058)
    INSIDE = "inside"  # the run's: the swimmer's wiring, live; shown as Diagnostic (D-089)
    SCORE = "score"  # the run's: the level's wins this session
    NAVIGATOR = "navigator"  # zoom, hand, centre; the rays in the run
    HINTS = "hints"  # at the bar's foot: the level's hints, asked for in turn (D-078)
    SETTINGS = "settings"  # at the bar's foot: what the player sets (D-054)
    CHAPTERS = "chapters"  # at the bar's foot, over the switch: the levels and the sandbox
    OBJECTS = "objects"  # the Maker's: the plane's objects, undo and redo, the Wheel (D-301)
    TEXT = "text"  # the Maker's: the level's title and spec, its Brief (D-305; named so, D-318)
    GOALS = "goals"  # the Maker's: the time allowed and the goals, as sentences (D-308)


class MainView(Enum):  # what the editor's main screen shows, by the drawer open (D-058, D-069)
    DIAGRAM = "diagram"  # the board on its hex grid, to edit
    PREVIEW = "preview"  # the Run preview: the board as it runs, where the probe stands


class Env(Enum):  # the environments, each a tab over the main screen (D-051)
    EDITOR = "editor"
    RUN = "run"
    MAKER = "maker"  # the sandbox's own: its level, made (D-301)


DIAGNOSTIC_MAP: Rect = (  # the level, small, in Diagnostic, under its label: a square [px]
    BAR_WIDTH + MARGIN,
    DRAWER_TOP + TITLE_HEIGHT + 4,
    DRAWER_WIDTH - 2 * MARGIN,
    DRAWER_WIDTH - 2 * MARGIN,
)
DRAWERS = {  # each environment's drawers, in the bar's order from the top
    Env.EDITOR: (Drawer.TOOLS, Drawer.PARTS, Drawer.FILES, Drawer.DIAGNOSTIC, Drawer.NAVIGATOR),
    Env.RUN: (Drawer.INSIDE, Drawer.SCORE, Drawer.NAVIGATOR),  # the objectives under each
    Env.MAKER: (
        Drawer.OBJECTS,
        Drawer.PARTS,  # the Maker's: the board's size, the parts handed out (D-315)
        Drawer.GOALS,
        Drawer.TEXT,
        Drawer.FILES,
        Drawer.NAVIGATOR,
    ),
}
FOOT = (Drawer.HINTS, Drawer.SETTINGS, Drawer.CHAPTERS)  # the drawers whose icons sit at its foot
SWITCH_TO = {Env.EDITOR: LevelButton.RUN, Env.RUN: LevelButton.EDIT, Env.MAKER: LevelButton.RUN}


@dataclass(frozen=True)
class WinRow:
    """A row of Files: in its `group`, a level's, the win `index` this session, the fastest first
    (D-059, D-092)."""

    group: int
    index: int


@dataclass(frozen=True)
class HintRow:
    """A row of Hints: the level's hint `index`, the idea, the parts, then the shadow (D-078)."""

    index: int


@dataclass(frozen=True)
class Goal:
    """A row of Objectives: the level's objective `index`, or, for None, the time left."""

    index: int | None


@dataclass(frozen=True)
class MadeGoal:
    """A goal's name in the Maker's Goals, over its words: the level's objective `index`."""

    index: int


@dataclass(frozen=True)
class Word:
    """A word's button in Goals: objective `goal`'s verb, how many or target, `word` (D-308)."""

    goal: int
    word: Verb | Count | Target


@dataclass(frozen=True)
class Stepper:
    """A row of the Maker's Parts: how many of `kind` the level hands out, or, for None, its
    board's size; − and + at its right end (D-315)."""

    kind: Kind | None


@dataclass(frozen=True)
class Start:
    """A row of the Maker's Start from: the shipped level `index`, or, for None, a blank plane
    (D-310)."""

    index: int | None


@dataclass(frozen=True)
class Knob:
    """A slider of Goals: objective `goal`'s setting, or, for None, the time allowed."""

    goal: int | None


class Setting(Enum):  # the Settings drawer's rows (D-054)
    FAST = "fast"  # fast forward's speed
    HINTS = "hints"  # keys on the rows and in the tooltips
    TUTORIAL = "tutorial"  # Fear's tutorial again
    SOUND = "sound"  # locked: there is no sound yet
    MUSIC = "music"


# Shortcut keys, matched on the character typed (so they follow the keyboard layout) and shown
# in the tooltips. L and R turn left and right, here and in the arena view (D-025). Delete is on
# Backspace and Delete, matched on the physical key (D-069): its label, not a character.
TOOL_KEYS = {
    Tool.ADD: "A",
    Tool.WIRE: "W",
    Tool.MOVE: "M",
    Tool.DELETE: "Del",
    Tool.TURN_LEFT: "L",
    Tool.TURN_RIGHT: "R",
    Tool.SWAP: "S",
    Tool.LESS: "<",  # the Maker's (D-301); + and - zoom
    Tool.MORE: ">",
}
VIEW_KEYS = {
    ViewButton.ZOOM_IN: "+",
    ViewButton.ZOOM_OUT: "-",
    ViewButton.PAN: "H",
    ViewButton.CENTRE: "C",
    ViewButton.RAYS: "X",  # as in x-rays: L turns left (D-025)
    ViewButton.MOTION: "M",  # Move in the editor, where these three do not show (D-069)
    ViewButton.STREAMS: "W",  # as in wind, its icon; Wire in the editor
}
RUN_VIEWS = (ViewButton.RAYS, ViewButton.MOTION, ViewButton.STREAMS)  # Navigator's, in the run
MAKER_VIEWS = (ViewButton.RAYS,)  # ... in the Maker: the light, which the plane's shadows show
# With Ctrl (Cmd on a Mac), matched on the key code, which follows the layout; Ctrl+Y redoes too.
EDIT_KEYS = {EditButton.UNDO: "Ctrl+Z", EditButton.REDO: "Ctrl+Y"}
MODE_KEY = "E"  # Write and Delete in turn (as in erase); Esc goes back to Write
LOCK_KEY = "K"  # Lock and Write in turn, on the sandbox (D-319)
# On the physical key: Space runs, as the arena's play (D-021); from the run, Tab goes on to the
# next tab, the editor's, as it does from every tab, Shift+Tab back (D-304).
LEVEL_KEYS = {LevelButton.RUN: "Space", LevelButton.EDIT: "Tab"}
NEXT_TAB, LAST_TAB = "Tab", "Shift+Tab"  # what the tabs' tooltips show; F1 F2 F3 work too
# Each drawer's key, its initial (D-069): it opens the drawer, or folds it. A letter may mean
# something else in the other environment, F Fast forward in the run, S Swap in the editor, since
# the two never show together. Esc opens the levels, or folds them, once it has nothing left to
# back out of (D-304); the comma Settings, with Ctrl or Cmd too; the question mark Hints, H being
# the hand's (D-078).
PASSKEY_KEY = "P"  # with Chapters open, a passkey to type, not Parts (D-075)
DRAWER_KEYS = {
    Drawer.TOOLS: "T",
    Drawer.PARTS: "P",
    Drawer.FILES: "F",
    Drawer.DIAGNOSTIC: "D",
    Drawer.NAVIGATOR: "N",
    Drawer.INSIDE: "D",  # the run's Diagnostic (D-089)
    Drawer.SCORE: "S",
    Drawer.HINTS: "?",
    Drawer.SETTINGS: ",",
    Drawer.CHAPTERS: "Esc",
    Drawer.OBJECTS: "O",
    Drawer.TEXT: "T",  # Tools' key in the Editor, which the Maker has not
    Drawer.GOALS: "G",
}
KEY_ALIASES = {"=": "+", "_": "-"}  # the same keys, shift or not, on most layouts


@dataclass(frozen=True)
class Layout:
    env: Env  # the editor's frame, the run's or the Maker's
    maker: bool  # the sandbox: a third tab, the Maker, makes its level (D-301)
    kinds: frozenset[Kind]  # the parts the level hands out: the only ones Parts shows
    drawer: Drawer | None  # the drawer open, if one is
    chapter: int  # how many levels the chapter has: Chapters' rows, then the sandbox's
    bar_area: Rect
    drawer_buttons: tuple[tuple[Drawer, Rect], ...]  # the bar's icons, top down
    level_buttons: tuple[tuple[LevelButton, Rect], ...]  # at the bar's foot: Chapters, the switch
    drawer_area: Rect | None
    fold_handle: Rect | None  # the arrow on the drawer's edge
    drawer_title_at: tuple[int, int]
    section_titles: tuple[tuple[str, Rect], ...]  # Tools, Edit, File; View
    group_titles: tuple[tuple[str, Rect], ...]  # Parts, Files: a click folds or unfolds its group
    menu_items: tuple[tuple[Kind, Rect], ...]  # Parts' rows
    piece_rows: tuple[tuple[Piece, Rect], ...]  # Objects' rows, in the Maker (D-301)
    brief_fields: tuple[tuple[Brief, Rect], ...]  # Brief's: the title's, the spec's (D-305)
    goal_heads: tuple[tuple[MadeGoal, Rect], ...]  # Goals': each goal's name and bin (D-308)
    goal_words: tuple[tuple[Word, Rect], ...]  # ... under it, its words' buttons
    knobs: tuple[tuple[Knob, Rect], ...]  # ... the sliders: the time allowed, each setting
    goal_buttons: tuple[tuple[GoalButton, Rect], ...]  # ... Add a goal
    wheel_view: Rect | None  # Tools, Parts, Objects: the Wheel, what is focused large at its hub
    wheel_fold: Rect | None  # ... The Wheel's title; a click folds or unfolds it (D-069)
    list_area: Rect | None  # where the drawer's rows show, scrolled; they answer there (D-096)
    scroll: int  # how far the list is scrolled [px]
    scroll_max: int  # ... at most: how much of it does not fit [px]
    scroll_bar: Rect | None  # its track, while the rows do not fit
    mode_buttons: tuple[tuple[Mode, Rect], ...]  # Tools' rows: Write, Delete
    edit_buttons: tuple[tuple[EditButton, Rect], ...]  # ... then undo, redo; Objects' too
    action_at: Rect | None  # the editor's and the Maker's: what a click does, atop the main screen
    view_buttons: tuple[tuple[ViewButton, Rect], ...]  # Navigator's rows
    goal_rows: tuple[tuple[Goal, Rect], ...]  # in the run: each objective, the time left
    goal_area: Rect | None  # ... at the foot of the open drawer, whichever it is (D-065)
    win_rows: tuple[tuple[WinRow, Rect], ...]  # Files' rows: this session's wins, every level's
    setting_rows: tuple[tuple[Setting, Rect], ...]  # Settings' rows
    hint_rows: tuple[tuple[HintRow, Rect], ...]  # Hints' rows, if the level has hints (D-078)
    hint_texts: tuple[tuple[int, Rect], ...]  # ... under each taken one, its lines: its index
    shadow_picture: Rect | None  # ... under the shadow's, while it shows: the board, small
    shadow_line: Rect | None  # ... and under it, where to build it: Tools or Parts (D-088)
    chapter_rows: tuple[tuple[int, Rect], ...]  # Chapters' rows: a level's index; the sandbox last
    passkey_field: Rect | None  # Chapters' foot: a level's passkey typed there (D-075)
    file_buttons: tuple[tuple[FileButton, Rect], ...]  # Files' foot: Save (D-206)
    board_field: Rect | None  # ... under it, Load: a board's text pasted or typed there
    level_field: Rect | None  # the Maker's Files: a level's text pasted there (D-310)
    share_note: Rect | None  # ... under Share level, a line: won, or how to win it (D-320)
    start_rows: tuple[tuple[Start, Rect], ...]  # ... under it, Start from: a blank plane, a level
    steppers: tuple[tuple[Stepper, Rect], ...]  # the Maker's Parts: the zone, each part (D-315)
    info_buttons: tuple[tuple[object, Rect], ...]  # one per row: what its info box tells of
    tabs: tuple[tuple[str, Rect], ...]  # "run", "editor", and on the sandbox "maker"
    board_area: Rect  # the main screen: the board, or in the run the arena
    controls_area: Rect | None  # in the run, a strip under the arena: play, a step, the timeline
    overview: Rect | None  # Navigator's: the whole board, or level, small (D-060)
    zoom_buttons: tuple[tuple[ViewButton, Rect], ...]  # under it, out and in (D-065)
    zoom_bar: Rect | None  # between them: the zoom, from the farthest to the nearest
    caption_at: tuple[int, int]  # top-left corner of the level's title and spec, under the tabs
    status_at: tuple[int, int]  # top-left corner of the status line


@dataclass(frozen=True)
class View:
    """How the grid is seen: the size of a hex and where cell (0, 0) sits on screen."""

    size: float  # centre-to-corner [px]
    origin: tuple[float, float]  # pixel centre of cell (0, 0) [px]


def make_layout(
    drawer: Drawer | None = Drawer.PARTS,
    folded: frozenset[str] = frozenset(),
    kinds: frozenset[Kind] = frozenset(Kind),
    chapter: int = 0,
    env: Env = Env.EDITOR,
    goals: int = 0,
    files: tuple[tuple[str, int], ...] = (),
    wheel_folded: bool = False,
    scroll: int = 0,
    hint_lines: tuple[int, ...] | None = None,
    shadow: bool = False,
    maker: bool = False,
    made: tuple[bool, ...] = (),
    addable: bool = False,
    starts: int = 0,
) -> Layout:
    """The bar, the open drawer's rows and the main screen, for the editor or the run. folded:
    the groups shown closed, Parts' or Files'; kinds: the parts the level hands out, the only
    ones Parts shows (D-039); chapter: how many levels Chapters lists, before the sandbox; goals:
    how many objectives the level has, at the foot of each of the run's drawers, before the time
    left; files: Files' groups, each a level's title and how many of its wins it lists (D-092);
    wheel_folded: the picture of the cell folded, at the foot of Tools and of Parts; scroll: how
    far the open drawer's rows are scrolled, kept within what they need (D-069, D-096);
    hint_lines: how many lines each hint taken shows under its row, in Hints, or None for a
    level with none to take; shadow: the shadow shows, in a picture under its row (D-078);
    maker: the sandbox, whose tabs end with the Maker's (D-301); made: in Goals, each goal, by
    whether its verb takes a setting; addable: the level may ask one more (D-308); starts: in
    the Maker's Files, how many shipped levels it may start from, after a blank plane (D-310)."""
    width, height = SCREEN
    bar = (0, 0, BAR_WIDTH, height)
    side = (BAR_WIDTH - BAR_BUTTON) // 2
    top = DRAWERS[env]
    switch = ((BAR_WIDTH - SWITCH) // 2, height - SWITCH - 12, SWITCH, SWITCH)
    drawer_buttons = tuple(
        (d, (side, BAR_PITCH // 2 + 6 + k * BAR_PITCH - BAR_BUTTON // 2, BAR_BUTTON, BAR_BUTTON))
        for k, d in enumerate(top)
    ) + tuple(  # at the foot, over the switch, from the bottom up: Chapters, Settings, Hints
        (d, (side, switch[1] - (len(FOOT) - k) * BAR_PITCH, BAR_BUTTON, BAR_BUTTON))
        for k, d in enumerate(FOOT)
    )
    left = BAR_WIDTH + (DRAWER_WIDTH if drawer is not None else 0)  # the board's left edge
    # The drawer's rows end here: 8 px clear of the objectives in the run, at its foot otherwise.
    floor = _goals_top(height, goals) - 16 if env is Env.RUN else height - FOOT_MARGIN
    rows = _Rows()
    if drawer is Drawer.TOOLS:
        rows.tools(height, wheel_folded, scroll, maker)
    elif drawer is Drawer.PARTS and env is Env.MAKER:
        rows.maker_parts(folded)
        rows.scrolled(floor, scroll)  # D-096
    elif drawer is Drawer.PARTS:
        rows.parts(folded, kinds, height, wheel_folded, scroll)
    elif drawer is Drawer.OBJECTS:
        rows.objects(height, wheel_folded, scroll)
    elif drawer is Drawer.TEXT:
        rows.brief()
    elif drawer is Drawer.GOALS:
        rows.made_goals(made, addable)
        rows.scrolled(floor, scroll)  # D-096
    elif drawer is Drawer.DIAGNOSTIC:
        rows.label("The level")
    elif drawer is Drawer.FILES and env is Env.MAKER:
        rows.maker_files(starts)
        rows.scrolled(floor, scroll)  # D-096
    elif drawer is Drawer.FILES:
        rows.files(files, folded, height, scroll)
    elif drawer is Drawer.INSIDE:  # a drawing under its title, not rows
        rows.label("The swimmer's wiring")
    elif drawer is Drawer.SCORE:
        rows.label("Your wins")
    elif drawer in (Drawer.NAVIGATOR, Drawer.SETTINGS, Drawer.CHAPTERS) or (
        drawer is Drawer.HINTS and hint_lines is not None
    ):  # rows that scroll within the drawer if they do not fit (D-096)
        if drawer is Drawer.NAVIGATOR:
            rows.view(env)
        elif drawer is Drawer.HINTS:
            rows.hints(hint_lines, shadow, floor)
        elif drawer is Drawer.SETTINGS:
            rows.settings()
        else:
            rows.chapters(chapter)
        rows.scrolled(floor, scroll)
    goal_area = None
    if env is Env.RUN and drawer is not None:  # the objectives, at the foot of every drawer
        foot = _Rows()
        foot.y = _goals_top(height, goals)
        goal_area = (BAR_WIDTH, foot.y - 8, DRAWER_WIDTH, height - foot.y + 8)
        foot.label("Objectives")
        foot.goals(goals)
        rows.items += foot.items
        rows.sections += foot.sections
    tabs, x = [], left
    for name in MAKER_TABS if maker else TABS:
        tabs.append((name, (x, 0, TAB_WIDTHS[name], TABS_HEIGHT)))
        x += TAB_WIDTHS[name]
    open_ = drawer is not None
    centre = left + (width - left) // 2  # the main screen's
    main = height - STATUS_HEIGHT - (CONTROLS_HEIGHT if env is Env.RUN else 0)  # its foot
    return Layout(
        env=env,
        maker=maker,
        kinds=kinds,
        drawer=drawer,
        chapter=chapter,
        bar_area=bar,
        drawer_buttons=drawer_buttons,
        level_buttons=((SWITCH_TO[env], switch),),
        drawer_area=(BAR_WIDTH, 0, DRAWER_WIDTH, height) if open_ else None,
        fold_handle=(left - 1, height // 2 - HANDLE[1] // 2, *HANDLE) if open_ else None,
        drawer_title_at=(BAR_WIDTH + MARGIN, 9),
        section_titles=tuple(rows.sections),
        group_titles=tuple(rows.groups),
        menu_items=tuple(rows.of(Kind)),
        piece_rows=tuple(rows.of(Piece)),
        brief_fields=tuple(rows.fields),
        goal_heads=tuple(rows.heads),
        goal_words=tuple(rows.words),
        knobs=tuple(rows.knobs),
        goal_buttons=tuple(rows.of(GoalButton)),
        wheel_view=rows.wheel_view,
        wheel_fold=rows.wheel_fold,
        list_area=rows.list_area,
        scroll=rows.scroll,
        scroll_max=rows.scroll_max,
        scroll_bar=rows.scroll_bar,
        mode_buttons=tuple(rows.of(Mode)),
        edit_buttons=tuple(rows.of(EditButton)),
        action_at=(centre - ACTION_WIDTH // 2, TOP + 8, ACTION_WIDTH, ACTION_WIDTH)
        if env in (Env.EDITOR, Env.MAKER)  # the Maker's since D-314
        else None,
        view_buttons=tuple(rows.of(ViewButton)),
        goal_rows=tuple(rows.of(Goal)),
        goal_area=goal_area,
        win_rows=tuple(rows.of(WinRow)),
        setting_rows=tuple(rows.of(Setting)),
        hint_rows=tuple(rows.of(HintRow)),
        hint_texts=tuple(rows.hint_texts),
        shadow_picture=rows.picture,
        shadow_line=rows.line,
        chapter_rows=tuple(rows.of(int)),
        passkey_field=rows.passkey,
        file_buttons=tuple(rows.of(FileButton)),
        board_field=rows.board_field,
        level_field=rows.level_field,
        share_note=rows.share_note,
        start_rows=tuple(rows.of(Start)),
        steppers=tuple(rows.steppers),
        info_buttons=tuple((what, _info_disc(what, rect)) for what, rect in rows.items),
        tabs=tuple(tabs),
        board_area=(left, TOP, width - left, main - TOP),
        controls_area=(left, main, width - left, CONTROLS_HEIGHT) if env is Env.RUN else None,
        overview=rows.overview,
        zoom_buttons=tuple(rows.zoom_buttons),
        zoom_bar=rows.zoom_bar,
        caption_at=(left + MARGIN, TABS_HEIGHT + 5),
        status_at=(left + MARGIN, height - STATUS_HEIGHT + 6),
    )


def _goals_top(height: int, goals: int) -> int:
    """Where the run's objectives start, at the foot of its drawers: their label (D-065) [px]."""
    return (
        height - FOOT_MARGIN - TITLE_HEIGHT - (goals + 1) * (GOAL_HEIGHT + ROW_PITCH - ROW_HEIGHT)
    )


class _Rows:
    """A drawer's rows and titles, laid out from the top down."""

    def __init__(self) -> None:
        self.y = DRAWER_TOP
        self.wheel_view: Rect | None = None
        self.wheel_fold: Rect | None = None
        self.list_area: Rect | None = None
        self.scroll, self.scroll_max = 0, 0
        self.scroll_bar: Rect | None = None
        self.items: list[tuple[object, Rect]] = []
        self.sections: list[tuple[str, Rect]] = []
        self.groups: list[tuple[str, Rect]] = []
        self.overview: Rect | None = None
        self.zoom_buttons: list[tuple[ViewButton, Rect]] = []
        self.zoom_bar: Rect | None = None
        self.passkey: Rect | None = None
        self.board_field: Rect | None = None
        self.level_field: Rect | None = None
        self.share_note: Rect | None = None
        self.hint_texts: list[tuple[int, Rect]] = []
        self.fields: list[tuple[Brief, Rect]] = []
        self.heads: list[tuple[MadeGoal, Rect]] = []
        self.words: list[tuple[Word, Rect]] = []
        self.knobs: list[tuple[Knob, Rect]] = []
        self.steppers: list[tuple[Stepper, Rect]] = []
        self.picture: Rect | None = None
        self.line: Rect | None = None

    def of(self, kind: type) -> list:
        return [(what, rect) for what, rect in self.items if isinstance(what, kind)]

    def _title(self, title: str, into: list) -> None:
        into.append((title, (BAR_WIDTH + MARGIN, self.y, DRAWER_WIDTH - 2 * MARGIN, TITLE_HEIGHT)))
        self.y += TITLE_HEIGHT

    def _row(self, what: object, height: int = ROW_HEIGHT) -> None:
        width = DRAWER_WIDTH - 2 * ROW_INSET
        self.items.append((what, (BAR_WIDTH + ROW_INSET, self.y, width, height)))
        self.y += height + ROW_PITCH - ROW_HEIGHT

    def parts(
        self,
        folded: frozenset[str],
        kinds: frozenset[Kind],
        height: int,
        wheel_folded: bool,
        scroll: int,
    ) -> None:
        """The groups that fold, scrolled by `scroll` within the list's area; under it, down to
        the drawer's foot, the cell (D-069)."""
        bottom = self._wheel(height, wheel_folded) - SECTION_GAP
        groups = [
            (title, [kind for kind in group if kind in kinds]) for title, group in MENU_GROUPS
        ]
        self._folding(groups, folded, bottom, scroll)

    def files(
        self, files: tuple[tuple[str, int], ...], folded: frozenset[str], height: int, scroll: int
    ) -> None:
        """Under its label, each level's wins, a group that folds and scrolls as Parts' do
        (D-092); at the drawer's foot, Save/Load: Copy a board, then a field to paste one into
        (D-206)."""
        self.label("Wins this session")
        foot = height - FOOT_MARGIN - TITLE_HEIGHT - 2 * ROW_PITCH
        groups = [(title, [WinRow(g, k) for k in range(n)]) for g, (title, n) in enumerate(files)]
        self._folding(groups, folded, foot - SECTION_GAP, scroll)
        self.y = foot
        self.label("Save/Load")
        self._row(FileButton.SAVE)
        self.board_field = (BAR_WIDTH + ROW_INSET, self.y, DRAWER_WIDTH - 2 * ROW_INSET, ROW_HEIGHT)
        self.y += ROW_PITCH

    def maker_parts(self, folded: frozenset[str]) -> None:
        """The Maker's Parts (D-315): under Board, its size; then the parts in the Editor's
        groups, sensors, actuators, operators, each under a title that folds it (D-069); a row
        each, with − and + at its right end."""
        self._title("Board", self.sections)
        self._stepper(Stepper(None))
        self.y += SECTION_GAP
        for title, kinds in MENU_GROUPS:
            self._title(title, self.groups)
            for kind in () if title in folded else kinds:
                self._stepper(Stepper(kind))
            self.y += SECTION_GAP

    def _stepper(self, what: Stepper) -> None:
        width = DRAWER_WIDTH - 2 * ROW_INSET
        self.steppers.append((what, (BAR_WIDTH + ROW_INSET, self.y, width, ROW_HEIGHT)))
        self.y += ROW_PITCH

    def maker_files(self, starts: int) -> None:
        """The Maker's Files (D-310): under Save/Load, Copy level, Share level and a line under
        it (D-320), then a field to paste a level's text into, as the editor's Files has for a
        board (D-206); under Start from, a blank plane, then the `starts` shipped levels."""
        self._title("Save/Load", self.sections)
        self._row(FileButton.LEVEL)
        self._row(FileButton.SHARE)
        top, width = self.y - (ROW_PITCH - ROW_HEIGHT), DRAWER_WIDTH - 2 * ROW_INSET
        self.share_note = (BAR_WIDTH + ROW_INSET, top, width, HINT_LINE)
        self.y = top + HINT_LINE + ROW_PITCH - ROW_HEIGHT
        self.level_field = (BAR_WIDTH + ROW_INSET, self.y, DRAWER_WIDTH - 2 * ROW_INSET, ROW_HEIGHT)
        self.y += ROW_PITCH + SECTION_GAP
        self._title("Start from", self.sections)
        for index in (None, *range(starts)):
            self._row(Start(index))

    def _folding(
        self,
        groups: Sequence[tuple[str, Sequence[object]]],
        folded: frozenset[str],
        bottom: int,
        scroll: int,
    ) -> None:
        """Rows in groups under titles that fold, from here down to `bottom`, scrolled by `scroll`
        when they do not fit (D-069); a group with no row has no title."""
        top = self.y
        room = bottom - top
        self.list_area = (BAR_WIDTH, top, DRAWER_WIDTH, room)
        groups = [(title, shown) for title, shown in groups if shown]  # no title for nothing
        whole = sum(
            TITLE_HEIGHT + SECTION_GAP + (0 if title in folded else len(shown) * ROW_PITCH)
            for title, shown in groups
        )
        self.scroll_max = max(0, whole - room)
        self.scroll = min(max(scroll, 0), self.scroll_max)
        if self.scroll_max:  # between the rows' right ends and the drawer's edge
            x = BAR_WIDTH + DRAWER_WIDTH - (ROW_INSET + SCROLL_WIDTH) // 2
            self.scroll_bar = (x, top, SCROLL_WIDTH, room)
        self.y = top - self.scroll
        for title, shown in groups:
            self._title(title, self.groups)
            for what in () if title in folded else shown:
                self._row(what)
            self.y += SECTION_GAP

    def scrolled(self, bottom: int, scroll: int) -> None:
        """What was laid out from DRAWER_TOP shows down to `bottom`, the list's area; if it runs
        below, it is moved up by `scroll`, kept within what it needs, and a scroll bar shows
        (D-096). Parts and Files scroll their groups by `_folding` instead."""
        top = DRAWER_TOP
        self.list_area = (BAR_WIDTH, top, DRAWER_WIDTH, bottom - top)
        self.scroll_max = max(0, self.y - bottom)
        self.scroll = min(max(scroll, 0), self.scroll_max)
        if not self.scroll_max:
            return
        x = BAR_WIDTH + DRAWER_WIDTH - (ROW_INSET + SCROLL_WIDTH) // 2
        self.scroll_bar = (x, top, SCROLL_WIDTH, bottom - top)
        up = -self.scroll
        moving = (self.items, self.sections, self.groups, self.hint_texts, self.zoom_buttons)
        for listed in (*moving, self.heads, self.words, self.knobs, self.steppers):
            listed[:] = [(what, _moved(rect, up)) for what, rect in listed]
        self.picture, self.line = _moved(self.picture, up), _moved(self.line, up)
        self.passkey, self.overview = _moved(self.passkey, up), _moved(self.overview, up)
        self.zoom_bar, self.level_field = _moved(self.zoom_bar, up), _moved(self.level_field, up)
        self.share_note = _moved(self.share_note, up)

    def tools(self, height: int, wheel_folded: bool, scroll: int, maker: bool = False) -> None:
        """Write and Delete, and on the sandbox Lock (D-319), then undo and redo, as rows,
        scrolled above the Wheel if they do not fit; at the drawer's foot, the cell, as in Parts
        (D-068, D-069)."""
        modes = tuple(mode for mode in Mode if maker or mode is not Mode.LOCK)
        self._over_wheel((("Mode", modes), ("Edit", EditButton)), height, wheel_folded, scroll)

    def objects(self, height: int, wheel_folded: bool, scroll: int) -> None:
        """The Maker's objects under their title, then undo and redo, which need none, as rows,
        scrolled above the Wheel if they do not fit; at the drawer's foot, the Wheel round what
        is focused on the plane (D-301, D-306)."""
        self._over_wheel((("Plane", Piece), ("", EditButton)), height, wheel_folded, scroll)

    def brief(self) -> None:
        """The level's title, a field a row high, then its spec, a field SPEC_LINES high, each
        under its label (D-305)."""
        for label, field, lines in (("Title", Brief.TITLE, 1), ("Spec", Brief.SPEC, SPEC_LINES)):
            self._title(label, self.sections)
            height = ROW_HEIGHT if lines == 1 else lines * HINT_LINE + 2 * FIELD_PAD
            width = DRAWER_WIDTH - 2 * ROW_INSET
            self.fields.append((field, (BAR_WIDTH + ROW_INSET, self.y, width, height)))
            self.y += height + ROW_PITCH - ROW_HEIGHT + SECTION_GAP

    def made_goals(self, made: tuple[bool, ...], addable: bool) -> None:
        """The time allowed, a slider; each goal, its name over three rows of buttons, the verbs,
        how many and the targets, and a slider under them if its verb takes a setting; then Add
        a goal, while the level may ask one more (D-308). The names title the goals: the drawer's
        own title says Goals."""
        x, width = BAR_WIDTH + ROW_INSET, DRAWER_WIDTH - 2 * ROW_INSET
        self._title("Time allowed", self.sections)
        self._knob(Knob(None))
        self.y += SECTION_GAP
        for k, setting in enumerate(made):
            self.heads.append((MadeGoal(k), (x, self.y, width, HEAD_HEIGHT)))
            self.y += HEAD_HEIGHT
            for words in (Verb, Count, Target):  # side by side, filling the row, gaps between
                n, pitch = len(words), width + WORD_GAP
                for i, word in enumerate(words):
                    left, right = x + i * pitch // n, x + (i + 1) * pitch // n - WORD_GAP
                    self.words.append((Word(k, word), (left, self.y, right - left, WORD_HEIGHT)))
                self.y += WORD_HEIGHT + WORD_GAP
            if setting:
                self._knob(Knob(k))
            self.y += SECTION_GAP
        if addable:
            self._row(GoalButton.ADD)

    def _knob(self, knob: Knob) -> None:
        width = DRAWER_WIDTH - 2 * ROW_INSET
        self.knobs.append((knob, (BAR_WIDTH + ROW_INSET, self.y, width, SLIDER_HEIGHT)))
        self.y += SLIDER_HEIGHT + WORD_GAP

    def _over_wheel(self, sections: tuple, height: int, wheel_folded: bool, scroll: int) -> None:
        """Each section's title and rows, scrolled above the Wheel if they do not fit."""
        for title, rows in sections:
            if title:
                self._title(title, self.sections)
            for what in rows:
                self._row(what)
            self.y += SECTION_GAP
        self.scrolled(self._wheel(height, wheel_folded) - SECTION_GAP, scroll)

    def _wheel(self, height: int, folded: bool) -> int:
        """At the drawer's foot, The Wheel's title, which folds, then, unless folded, the Wheel:
        the focused cell drawn large, its icons round it (D-069); the title's top [px]."""
        width = DRAWER_WIDTH - 2 * MARGIN
        top = height - FOOT_MARGIN - TITLE_HEIGHT - (0 if folded else WHEEL_HEIGHT)
        self.wheel_fold = (BAR_WIDTH + MARGIN, top, width, TITLE_HEIGHT)
        if not folded:
            self.wheel_view = (BAR_WIDTH + MARGIN, top + TITLE_HEIGHT, width, WHEEL_HEIGHT)
        return top

    def view(self, env: Env) -> None:
        """The view's options as rows, in the run the rays, the swimmer's motion and its streams
        (D-076), in the Maker the rays; then the overview and, under it, the zoom: a bar between
        its two buttons (D-065)."""
        options = {Env.RUN: RUN_VIEWS, Env.MAKER: MAKER_VIEWS}.get(env, ())
        if options:
            self._title("View", self.sections)
            for button in options:
                self._row(button)
            self.y += SECTION_GAP
        self._title("Overview", self.sections)
        x, width = BAR_WIDTH + MARGIN, DRAWER_WIDTH - 2 * MARGIN
        self.overview = (x, self.y + 4, width, OVERVIEW_HEIGHT)
        top = self.y + 4 + OVERVIEW_HEIGHT + 10
        self.zoom_buttons = [
            (ViewButton.ZOOM_OUT, (x, top, ZOOM_BUTTON, ZOOM_BUTTON)),
            (ViewButton.ZOOM_IN, (x + width - ZOOM_BUTTON, top, ZOOM_BUTTON, ZOOM_BUTTON)),
        ]
        bar = width - 2 * (ZOOM_BUTTON + 8)
        self.zoom_bar = (x + ZOOM_BUTTON + 8, top + (ZOOM_BUTTON - 16) // 2, bar, 16)
        self.y = top + ZOOM_BUTTON + ROW_PITCH - ROW_HEIGHT  # where the drawer's rows end

    def label(self, title: str) -> None:
        self._title(title, self.sections)

    def goals(self, n: int) -> None:
        for k in [*range(n), None]:
            self._row(Goal(k), GOAL_HEIGHT)

    def settings(self) -> None:
        """Its rows one under the other, no titles (D-067)."""
        for what in Setting:
            self._row(what)

    def hints(self, lines: tuple[int, ...], shadow: bool, floor: int) -> None:
        """The hints' rows (D-078); under each taken one, its `lines`; under the shadow's, while
        it shows, its picture: a square as wide as the drawer allows, smaller if what is left
        above `floor`, the objectives in the run, is less, but not under SHADOW_LEAST, the drawer
        scrolling then (D-096); and under the picture, a line saying where to build it (D-088)."""
        x, width = BAR_WIDTH + MARGIN, DRAWER_WIDTH - 2 * MARGIN
        for k in range(HINT_ROWS):
            self._row(HintRow(k))
            if k < len(lines) and lines[k]:
                top = self.y - (ROW_PITCH - ROW_HEIGHT) + 2
                self.hint_texts.append((k, (x, top, width, lines[k] * HINT_LINE)))
                self.y = top + lines[k] * HINT_LINE + ROW_PITCH - ROW_HEIGHT
        if shadow:
            side = max(SHADOW_LEAST, min(width, floor - self.y - SHADOW_GAP - HINT_LINE))
            self.picture = (x + (width - side) // 2, self.y, side, side)
            self.line = (x, self.y + side + SHADOW_GAP, width, HINT_LINE)
            self.y += side + SHADOW_GAP + HINT_LINE + ROW_PITCH - ROW_HEIGHT

    def chapters(self, levels: int) -> None:
        self._title("Chapter 1: light", self.sections)
        for k in range(levels):
            self._row(k)
        self.y += SECTION_GAP
        self._title("Free play", self.sections)
        self._row(levels)  # the sandbox
        self.y += SECTION_GAP
        self._title("Passkey", self.sections)  # a level's word typed: it opens (D-075)
        self.passkey = (BAR_WIDTH + ROW_INSET, self.y, DRAWER_WIDTH - 2 * ROW_INSET, ROW_HEIGHT)
        self.y += ROW_PITCH


def _moved(rect: Rect | None, dy: int) -> Rect | None:
    """`rect` moved down by `dy` [px]; None stays None."""
    if rect is None:
        return None
    x, y, w, h = rect
    return (x, y + dy, w, h)


def _info_disc(what: object, row: Rect) -> Rect:
    """Where a row's info disc catches a click: INFO_AT into the row, on its middle; an
    objective's, whose count and bar run along its second line, at its first line's end."""
    x, y, w, h = row
    cx, cy = (x + w - 16, y + 14) if isinstance(what, Goal) else (x + INFO_AT, y + h // 2)
    return (cx - INFO_HIT // 2, cy - INFO_HIT // 2, INFO_HIT, INFO_HIT)


def win_row_at(layout: Layout, point: tuple[int, int]) -> WinRow | None:
    """The win whose row in Files is under `point`, where the list shows (D-092)."""
    if not _listed(layout, point):
        return None
    return next((w for w, rect in layout.win_rows if contains(rect, point)), None)


def goal_row_at(layout: Layout, point: tuple[int, int]) -> Goal | None:
    return next((g for g, rect in layout.goal_rows if contains(rect, point)), None)


def palette_target_at(layout: Layout, point: tuple[int, int]) -> Drawer | LevelButton | str | None:
    """What a tooltip would name under `point`: an icon of the bar, or another environment's
    tab, by its name (D-060)."""
    tab = tab_at(layout, point)
    return (
        drawer_button_at(layout, point)
        or level_button_at(layout, point)
        or (tab if tab is not None and tab != layout.env.value else None)
    )


def drawer_key(env: Env, typed: str) -> Drawer | None:
    """The drawer of `env`, in its bar or at its foot, whose key is `typed`, upper case (D-069)."""
    return next((d for d in (*DRAWERS[env], *FOOT) if DRAWER_KEYS[d] == typed), None)


def main_view_for(drawer: Drawer | None, last: MainView) -> MainView:
    """What the editor's main screen shows with `drawer` open (D-069): the Run preview in
    Diagnostic, what it showed before (`last`) in Navigator, which only moves the view; else the
    board."""
    if drawer is Drawer.DIAGNOSTIC:
        return MainView.PREVIEW
    return last if drawer is Drawer.NAVIGATOR else MainView.DIAGRAM


def drawer_button_at(layout: Layout, point: tuple[int, int]) -> Drawer | None:
    return next((d for d, rect in layout.drawer_buttons if contains(rect, point)), None)


def file_button_at(layout: Layout, point: tuple[int, int]) -> FileButton | None:
    return next((b for b, rect in layout.file_buttons if contains(rect, point)), None)


def level_field_at(layout: Layout, point: tuple[int, int]) -> bool:
    """Whether `point` is on the Maker's field for a level's text, in its Files (D-310)."""
    return (
        layout.level_field is not None
        and _listed(layout, point)
        and contains(layout.level_field, point)
    )


def step_buttons(row: Rect) -> tuple[Rect, Rect]:
    """A row of the Maker's Parts: its − and its +, at its right end, the count between them."""
    x, y, w, h = row
    top = y + (h - STEP_BUTTON) // 2
    plus = (x + w - STEP_BUTTON - 6, top, STEP_BUTTON, STEP_BUTTON)
    return (plus[0] - 2 * STEP_BUTTON, top, STEP_BUTTON, STEP_BUTTON), plus


def stepper_at(layout: Layout, point: tuple[int, int]) -> tuple[Stepper, int] | None:
    """The − or the + of the Maker's Parts under `point`: its row, and -1 or 1 (D-315)."""
    if not _listed(layout, point):
        return None
    for what, rect in layout.steppers:
        minus, plus = step_buttons(rect)
        if contains(minus, point) or contains(plus, point):
            return what, -1 if contains(minus, point) else 1
    return None


def start_row_at(layout: Layout, point: tuple[int, int]) -> Start | None:
    """The row of the Maker's Start from under `point`, where the drawer shows its rows."""
    return _row_at(layout, layout.start_rows, point)


def board_field_at(layout: Layout, point: tuple[int, int]) -> bool:
    """Whether `point` is on Load's field, at Files' foot (D-206)."""
    return layout.board_field is not None and contains(layout.board_field, point)


def passkey_at(layout: Layout, point: tuple[int, int]) -> bool:
    """Whether `point` is on Chapters' passkey field (D-075), where it shows."""
    field = layout.passkey_field
    return field is not None and contains(field, point) and _listed(layout, point)


def chapter_row_at(layout: Layout, point: tuple[int, int]) -> int | None:
    """The place whose row in Chapters is under `point`: a level's index, or the sandbox's."""
    return _row_at(layout, layout.chapter_rows, point)


def hint_row_at(layout: Layout, point: tuple[int, int]) -> HintRow | None:
    return _row_at(layout, layout.hint_rows, point)


def setting_row_at(layout: Layout, point: tuple[int, int]) -> Setting | None:
    return _row_at(layout, layout.setting_rows, point)


def overview_at(layout: Layout, point: tuple[int, int]) -> bool:
    """Whether `point` is on Navigator's overview, where it shows (D-060)."""
    shown = layout.overview is not None and contains(layout.overview, point)
    return shown and _listed(layout, point)


def tab_at(layout: Layout, point: tuple[int, int]) -> str | None:
    return next((name for name, rect in layout.tabs if contains(rect, point)), None)


def tab_beside(layout: Layout, back: bool = False) -> str:
    """The tab after the open one, from the last round to the first; or, `back`, before it."""
    names = [name for name, _ in layout.tabs]
    return names[(names.index(layout.env.value) + (-1 if back else 1)) % len(names)]


def tab_key_to(layout: Layout, name: str) -> str | None:
    """The key that goes to tab `name` from the open one, as its tooltip shows it: Tab to the
    next, Shift+Tab to the one before; None for the open one (D-304)."""
    if name == layout.env.value:
        return None
    return NEXT_TAB if name == tab_beside(layout) else LAST_TAB


def on_fold_handle(layout: Layout, point: tuple[int, int]) -> bool:
    return layout.fold_handle is not None and contains(layout.fold_handle, point)


def contains(rect: Rect, point: tuple[int, int]) -> bool:
    x, y, w, h = rect
    return x <= point[0] < x + w and y <= point[1] < y + h


def _listed(layout: Layout, point: tuple[int, int]) -> bool:
    """Whether `point` may fall on a row of the drawer: anywhere, unless its rows show within
    an area, where they scroll (D-069, D-092, D-096)."""
    return layout.list_area is None or contains(layout.list_area, point)


def _row_at(layout: Layout, rows: Sequence[tuple[object, Rect]], point: tuple[int, int]):
    """What the row under `point` is for, of `rows`, where the drawer shows its rows."""
    if not _listed(layout, point):
        return None
    return next((what for what, rect in rows if contains(rect, point)), None)


def group_at(layout: Layout, point: tuple[int, int]) -> str | None:
    if not _listed(layout, point):
        return None
    return next((title for title, rect in layout.group_titles if contains(rect, point)), None)


def info_at(layout: Layout, point: tuple[int, int]) -> object | None:
    """The row whose info disc is under `point`, if any: a part, a tool, a button, a win; an
    objective's, at the run's drawers' foot, and Save, at Files', which never scroll (D-065)."""
    listed = _listed(layout, point)
    return next(
        (
            what
            for what, rect in layout.info_buttons
            if contains(rect, point) and (listed or isinstance(what, (Goal, FileButton)))
        ),
        None,
    )


def menu_item_at(layout: Layout, point: tuple[int, int]) -> Kind | None:
    return _row_at(layout, layout.menu_items, point)


def brief_field_at(layout: Layout, point: tuple[int, int]) -> Brief | None:
    """Brief's field under `point`: the title's or the spec's (D-305)."""
    return next((f for f, rect in layout.brief_fields if contains(rect, point)), None)


def word_at(layout: Layout, point: tuple[int, int]) -> Word | None:
    """The word's button of Goals under `point`, where the drawer shows its rows (D-308)."""
    return _row_at(layout, layout.goal_words, point)


def bin_rect(head: Rect) -> Rect:
    """A goal's bin, at the right end of its name's row `head`."""
    x, y, w, h = head
    return (x + w - BIN, y + (h - BIN) // 2, BIN, BIN)


def bin_at(layout: Layout, point: tuple[int, int]) -> int | None:
    """The goal whose bin is under `point`: a click there takes it out."""
    bins = [(head.index, bin_rect(rect)) for head, rect in layout.goal_heads]
    return _row_at(layout, bins, point)


def goal_button_at(layout: Layout, point: tuple[int, int]) -> GoalButton | None:
    return _row_at(layout, layout.goal_buttons, point)


def slider_parts(rect: Rect) -> tuple[Rect, Rect, Rect]:
    """A slider's label, its track and its value's box, left to right, in its row `rect`."""
    x, y, w, h = rect
    label = (x, y, KNOB_LABEL, h)
    track = (x + KNOB_LABEL + 8, y, w - KNOB_LABEL - KNOB_VALUE - 16, h)
    value = (x + w - KNOB_VALUE, y + 3, KNOB_VALUE, h - 6)
    return label, track, value


def knob_at(layout: Layout, point: tuple[int, int]) -> tuple[Knob, bool] | None:
    """The slider of Goals under `point`, where the drawer shows its rows, and whether `point`
    is on its value's box rather than its label or its track (D-308)."""
    knob = _row_at(layout, layout.knobs, point)
    if knob is None:
        return None
    return knob, contains(slider_parts(dict(layout.knobs)[knob])[2], point)


def along(track: Rect, x: float) -> float:
    """How far along `track` the pixel column `x` is: 0 at its left end, 1 at its right."""
    left, _, width, _ = track
    return min(1.0, max(0.0, (x - left) / width))


def piece_row_at(layout: Layout, point: tuple[int, int]) -> Piece | None:
    """The row of Objects under `point`, where the drawer shows its rows (D-301)."""
    return _row_at(layout, layout.piece_rows, point)


def wheel_fold_at(layout: Layout, point: tuple[int, int]) -> bool:
    """Whether `point` is on The Wheel's title, which folds it (D-069)."""
    return layout.wheel_fold is not None and contains(layout.wheel_fold, point)


def scroll_bar_at(layout: Layout, point: tuple[int, int], grab: int = 4) -> bool:
    """Whether a press at `point` falls on the list's scroll bar, `grab` px either side of it."""
    if layout.scroll_bar is None:
        return False
    x, y, w, h = layout.scroll_bar
    return contains((x - grab, y, w + 2 * grab, h), point)


def scroll_thumb(layout: Layout) -> Rect | None:
    """The scroll bar's thumb: as long against its track as the list's area against the
    whole list, at least SCROLL_THUMB; as far down it as the list is scrolled."""
    if layout.scroll_bar is None:
        return None
    x, y, w, h = layout.scroll_bar
    length = max(SCROLL_THUMB, round(h * h / (h + layout.scroll_max)))
    return (x, y + round((h - length) * layout.scroll / layout.scroll_max), w, length)


def scroll_for(layout: Layout, y: int) -> int:
    """The scroll that puts the thumb's middle at height `y`: a press on the track, or a drag."""
    _, _, _, length = scroll_thumb(layout)
    _, track, _, h = layout.scroll_bar
    level = (y - length / 2 - track) / (h - length)
    return round(min(1.0, max(0.0, level)) * layout.scroll_max)


def view_button_at(layout: Layout, point: tuple[int, int]) -> ViewButton | None:
    return _row_at(layout, layout.view_buttons, point)


def edit_button_at(layout: Layout, point: tuple[int, int]) -> EditButton | None:
    return _row_at(layout, layout.edit_buttons, point)


def action_at(layout: Layout, point: tuple[int, int]) -> Shown | None:
    """The action shown atop the main screen, under `point`: a click on it opens Tools."""
    shown = layout.action_at is not None and contains(layout.action_at, point)
    return Shown.ACTION if shown else None


def mode_button_at(layout: Layout, point: tuple[int, int]) -> Mode | None:
    return _row_at(layout, layout.mode_buttons, point)


def level_button_at(layout: Layout, point: tuple[int, int]) -> LevelButton | None:
    return next((b for b, rect in layout.level_buttons if contains(rect, point)), None)


def zoom_button_at(layout: Layout, point: tuple[int, int]) -> ViewButton | None:
    return _row_at(layout, layout.zoom_buttons, point)


def zoom_bar_at(layout: Layout, point: tuple[int, int], grab: int = 6) -> float | None:
    """How far along the zoom bar a press at `point` falls, 0 the farthest, 1 the nearest;
    None off it, or where the drawer does not show it."""
    if layout.zoom_bar is None or not _listed(layout, point):
        return None
    x, y, w, h = layout.zoom_bar
    if not (x - grab <= point[0] <= x + w + grab and y - grab <= point[1] <= y + h + grab):
        return None
    return min(1.0, max(0.0, (point[0] - x) / w))


def level_of(value: float, low: float, high: float) -> float:
    """Where `value` sits between `low` and `high`, on a log scale: a zoom as the bar shows it."""
    return min(1.0, max(0.0, math.log(value / low) / math.log(high / low)))


def value_at(level: float, low: float, high: float) -> float:
    """The value at `level` between `low` and `high`, on a log scale: `level_of` undone."""
    return low * (high / low) ** min(1.0, max(0.0, level))


Bounds = tuple[float, float, float, float]  # x0, y0, x1, y1 [hex sizes], cell (0, 0) at 0
ROOM = 1.5  # the overview shows this many times the zone, each way (D-066)


def board_extent(layout: Layout, cells: Sequence[Cell]) -> Bounds:
    """What the overview shows of the board, and the most the main screen may (D-066): the zone,
    its hexes whole, ROOM times over, and at least what the main screen shows at HEX_SIZE,
    centred on cell (0, 0) and widened to the main screen's aspect."""
    _, _, w, h = layout.board_area
    points = [to_pixel(cell, 1.0, (0.0, 0.0)) for cell in cells] or [(0.0, 0.0)]
    reach = 1.0  # a hex's own half, and a little [hex sizes]
    half_w = max(ROOM * (max(abs(x) for x, _ in points) + reach), w / HEX_SIZE / 2)
    half_h = max(ROOM * (max(abs(y) for _, y in points) + reach), h / HEX_SIZE / 2)
    half_w, half_h = max(half_w, half_h * w / h), max(half_h, half_w * h / w)
    return (-half_w, -half_h, half_w, half_h)


def board_view_of(area: Rect, bounds: Bounds) -> View:
    """The view that shows `bounds` whole in `area`, centred."""
    x, y, w, h = area
    x0, y0, x1, y1 = bounds
    size = min(w / (x1 - x0), h / (y1 - y0))
    return View(size, (x + w / 2 - size * (x0 + x1) / 2, y + h / 2 - size * (y0 + y1) / 2))


def kept_on_board(layout: Layout, view: View, bounds: Bounds) -> View:
    """The view, zoomed in if it showed more than `bounds`, slid so that it shows nothing
    outside them: what the overview frames stays inside it (D-066)."""
    least = board_view_of(layout.board_area, bounds).size
    x, y, w, h = layout.board_area
    if view.size < least:
        k = least / view.size
        cx, cy = x + w / 2, y + h / 2
        view = View(least, (cx + k * (view.origin[0] - cx), cy + k * (view.origin[1] - cy)))
    x0, y0, x1, y1 = bounds
    s, (ox, oy) = view.size, view.origin
    left, right, top, bottom = (x - ox) / s, (x + w - ox) / s, (y - oy) / s, (y + h - oy) / s
    dx = (x0 - left) if left < x0 else (x1 - right) if right > x1 else 0.0
    dy = (y0 - top) if top < y0 else (y1 - bottom) if bottom > y1 else 0.0
    return View(s, (ox - dx * s, oy - dy * s))


def overview_view(layout: Layout, cells: Sequence[Cell]) -> View:
    """The board's extent seen small in Navigator's overview (D-060, D-066)."""
    return board_view_of(layout.overview, board_extent(layout, cells))


def shown_frame(layout: Layout, view: View, small: View) -> Rect:
    """What the main screen shows of the board, as a frame in the overview seen through
    `small`."""
    x, y, w, h = layout.board_area
    k = small.size / view.size
    left = small.origin[0] + k * (x - view.origin[0])
    top = small.origin[1] + k * (y - view.origin[1])
    return (round(left), round(top), round(k * w), round(k * h))


def centred_on(layout: Layout, view: View, small: View, point: tuple[int, int]) -> View:
    """The view, at its zoom, centred where a press at `point` falls in the overview."""
    px = (point[0] - small.origin[0]) / small.size
    py = (point[1] - small.origin[1]) / small.size
    x, y, w, h = layout.board_area
    return View(view.size, (x + w / 2 - view.size * px, y + h / 2 - view.size * py))


def centred_view(layout: Layout, size: float = HEX_SIZE) -> View:
    """Cell (0, 0) at the centre of the board area."""
    x, y, w, h = layout.board_area
    return View(size, (x + w / 2, y + h / 2))


def opening_view(layout: Layout, cells: Sequence[Cell]) -> View:
    """How the editor first shows a zone: cell (0, 0) at the centre, at HEX_SIZE, or smaller if
    the zone's hexes would reach under the action atop the board or past its sides (D-102)."""
    _, _, w, h = layout.board_area
    points = [to_pixel(cell, 1.0, (0.0, 0.0)) for cell in cells] or [(0.0, 0.0)]
    high = max(abs(y) for _, y in points) + 1.0  # to a hex's top corner [hex sizes]
    wide = max(abs(x) for x, _ in points) + SQRT3 / 2  # to its side
    size = min(HEX_SIZE, (h / 2 - ACTION_ROOM) / high, (w / 2 - MARGIN) / wide)
    return centred_view(layout, size)


def moved_view(view: View, before: Layout, after: Layout) -> View:
    """The same view, slid with the board's centre when a drawer opens or folds."""
    (x0, y0, w0, h0), (x1, y1, w1, h1) = before.board_area, after.board_area
    dx, dy = (x1 + w1 / 2) - (x0 + w0 / 2), (y1 + h1 / 2) - (y0 + h0 / 2)
    return pan(view, dx, dy)


def fitted_view(area: Rect, points: Sequence[tuple[float, float]], margin: float) -> View:
    """The biggest view (up to MAX_HEX) that shows `points` with `margin` to spare, centred.

    points: pixel positions at hex size 1 with cell (0, 0) at the origin; margin in hex sizes.
    """
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    x, y, w, h = area
    wide, high = max(xs) - min(xs) + 2 * margin, max(ys) - min(ys) + 2 * margin
    size = min(MAX_HEX, w / wide, h / high)
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    return View(size, (x + w / 2 - size * cx, y + h / 2 - size * cy))


def zoom(view: View, factor: float, about: tuple[float, float]) -> View:
    """Scale the grid by `factor` (within the limits), keeping the point `about` in place."""
    size = min(MAX_HEX, max(MIN_HEX, view.size * factor))
    k = size / view.size
    ox, oy = view.origin
    return View(size, (about[0] + k * (ox - about[0]), about[1] + k * (oy - about[1])))


def pan(view: View, dx: float, dy: float) -> View:
    """Slide the grid by (dx, dy) [px]."""
    return View(view.size, (view.origin[0] + dx, view.origin[1] + dy))


def cell_at(layout: Layout, view: View, point: tuple[int, int]) -> Cell | None:
    """The hex under `point`, or None outside the board area (the caller checks the zone)."""
    if not contains(layout.board_area, point):
        return None
    return from_pixel(point[0], point[1], view.size, view.origin)


def visible_cells(layout: Layout, view: View) -> list[Cell]:
    """Every cell whose hex shows, at least in part, in the board area; row by row."""
    x, y, w, h = layout.board_area
    s, (ox, oy) = view.size, view.origin
    rows = range(math.floor((y - s - oy) / (1.5 * s)), math.ceil((y + h + s - oy) / (1.5 * s)) + 1)
    cells = []
    for r in rows:
        # Cell (q, r) is centred at x = ox + sqrt(3) s (q + r / 2).
        q_min = math.floor((x - s - ox) / (SQRT3 * s) - r / 2)
        q_max = math.ceil((x + w + s - ox) / (SQRT3 * s) - r / 2)
        cells += [(q, r) for q in range(q_min, q_max + 1)]
    return cells
