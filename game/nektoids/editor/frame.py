"""What the editor and the run share (D-051): the activity bar, one drawer at a time, the tabs
and the switch between them, the rows' info discs, Hints, Chapters and Settings, the bar's
tooltips, and the scrolling of a drawer whose rows do not fit (D-096).

A scene inherits `Frame`, calls `_start_frame` once, `frame_track` as the mouse moves,
`frame_press` first on a click, `frame_release` when it is let go, `frame_wheel` first on a turn
of the mouse wheel, and `frame_update` once a frame; it gives `_relayout` (its layout with
another drawer open, scrolled as `scrolls` says), and may give `_slid` (what follows the main
screen when a drawer opens or folds), `_cancel` (a gesture under way ends) and `_refuse` (says
why not).
What the player asks of `main.py` is left in `request` ("run", "edit", "make", "tutorial"), `chosen`
(a place picked in Chapters), `asked_fold` (a chapter's title clicked there) or `asked_hint` (a
row of Hints), which `main.py` clears. Pure Python, no pygame.
"""

from __future__ import annotations

from collections.abc import Callable

from nektoids.editor.entry import Entry
from nektoids.editor.hints import HintView
from nektoids.editor.layout import (
    PASSKEY_KEY,
    SCROLL_STEP,
    TAB_KEYS,
    Drawer,
    Layout,
    Setting,
    chapter_row_at,
    contains,
    drawer_button_at,
    group_at,
    hint_row_at,
    info_at,
    level_button_at,
    on_fold_handle,
    palette_target_at,
    passkey_at,
    scroll_bar_at,
    scroll_for,
    setting_row_at,
    tab_at,
    tab_beside,
)
from nektoids.editor.router import ChapterRow
from nektoids.editor.settings import Settings
from nektoids.editor.tutorial import REFUSAL, Action
from nektoids.graph.board import Kind
from nektoids.levels.level import PASSKEY_LENGTH

LEAVE = {"editor": "edit", "run": "run", "maker": "make"}  # what a tab asks for: its screen
WARM_FRAMES = 18  # after a tooltip, the next one shows at once for this long: 0.3 s [frames]


class Frame:
    layout: Layout

    def _start_frame(self, layout: Layout, settings: Settings | None) -> None:
        self.layout = layout
        self.settings = settings if settings is not None else Settings()  # the session's
        self.request: str | None = None  # "run", "edit", "make", "tutorial": main.py's to clear
        self.chosen: int | None = None  # a place picked in Chapters: main.py's to clear
        self.chapters: tuple[ChapterRow, ...] = ()  # what Chapters shows; main.py's
        self.shut: frozenset[str] = frozenset()  # ... the chapters it shows closed; main.py's
        self.asked_fold: str | None = None  # a chapter's title clicked: main.py's to fold and clear
        self.info: object | None = None  # the row whose info box is open: a part, a tool...
        self.entry: Entry | None = None  # ... a part's, at work in its own circuit (D-082)
        self.tip_target: object | None = None  # the bar's icon, or another tab, under the mouse
        self.tip_frames = 0  # how long it has been there
        self.tip_warm = 0  # a tooltip showed lately: the next shows at once, for so long [frames]
        self.message = ""  # the last refusal, until something succeeds
        self.lit: frozenset[str] = frozenset()  # what a tutorial step explains (D-050); main.py's
        self.gate: Callable[[Action], bool] | None = None  # what it lets through; main.py's
        self.typing: str | None = None  # a passkey being typed in Chapters; None: not (D-075)
        self.asked_passkey: str | None = None  # a passkey typed: main.py's to try and clear
        self.said = ""  # what that passkey opened, in the status line until the next click
        self.hints: HintView | None = None  # what Hints shows; None, the level has none; main.py's
        self.tutored = (
            False  # the open level has a tutorial, Settings' to replay (D-334); main.py's
        )
        self.asked_hint: int | None = None  # a row of Hints clicked: main.py's to take and clear
        self.scrolls: dict[Drawer, int] = {}  # how far each drawer's rows are scrolled [px]
        self.scrolling = False  # a drawer's scroll bar held: its rows follow the mouse

    @property
    def tooltip(self) -> object | None:
        """What a tooltip names now, once the mouse has rested on it long enough: an icon of the
        bar, another tab, or what the scene adds (`_tip_target`)."""
        return self.tip_target if self.tip_frames >= self.settings.tooltip_frames else None

    def frame_update(self) -> None:
        """Once a frame: the tooltip's rest, and a part's entry at work while its box is open."""
        if not isinstance(self.info, Kind):
            self.entry = None
        elif self.entry is None or self.entry.kind is not self.info:
            self.entry = Entry(self.info)
        else:
            self.entry.tick()
        if self.tip_target is not None:
            self.tip_frames += 1
        self.tip_warm = WARM_FRAMES if self.tooltip is not None else max(0, self.tip_warm - 1)

    def frame_track(self, pos: tuple[int, int]) -> None:
        """The tooltip follows the mouse: after a rest on a new target; at once if one showed a
        moment ago, as the mouse goes from icon to icon across the gaps between them (D-069)."""
        target = self._tip_target(pos)
        if target != self.tip_target:
            warm = target is not None and self.tip_warm > 0
            self.tip_target = target
            self.tip_frames = self.settings.tooltip_frames if warm else 0
        if self.scrolling:
            self._scroll_to(scroll_for(self.layout, pos[1]))

    def frame_release(self) -> None:
        """The mouse let go: a scroll bar held is let go too."""
        self.scrolling = False

    def frame_wheel(self, pos: tuple[int, int], notches: int) -> bool:
        """A turn of the mouse wheel at `pos`, taken if it is on the open drawer's rows and they
        do not fit: up, they come down (D-069, D-096). False if it is not, for the scene."""
        area = self.layout.list_area
        if area is None or not contains(area, pos) or not self.layout.scroll_max:
            return False
        self._scroll_to(self.layout.scroll - notches * SCROLL_STEP)
        return True

    def frame_press(self, pos: tuple[int, int]) -> bool:
        """A click on the frame, taken: the fold arrow, a scroll bar, the bar, a tab, an info
        disc, a row of Hints, Chapters or Settings, the passkey field. False if it fell
        elsewhere, for the scene to take. A passkey being typed is given up by a click anywhere
        but on its field."""
        self.said, self.typing = "", None
        if passkey_at(self.layout, pos):
            self.typing = ""  # a word to type (D-075)
            return True
        if on_fold_handle(self.layout, pos):
            self.open_drawer(None)
            return True
        if scroll_bar_at(self.layout, pos):  # held, the rows follow the mouse (D-096)
            self.scrolling = True
            self._scroll_to(scroll_for(self.layout, pos[1]))
            return True
        drawer = drawer_button_at(self.layout, pos)
        if drawer is not None:  # the open drawer's icon folds it (D-051)
            self.open_drawer(None if drawer is self.layout.drawer else drawer)
            return True
        tab = tab_at(self.layout, pos)
        if tab is not None:
            if tab != self.layout.env.value:
                self._ask(LEAVE[tab])
            return True
        level = level_button_at(self.layout, pos)
        if level is not None:
            self._ask(level.value)  # "run" or "edit": the switch
            return True
        what = info_at(self.layout, pos)  # inside its row: before the row's own action
        if what is not None:
            self.info = what
            return True
        hint = hint_row_at(self.layout, pos)
        if hint is not None:
            self._take_hint(hint.index)
            return True
        title = group_at(self.layout, pos) if self.layout.drawer is Drawer.CHAPTERS else None
        if title is not None:  # a chapter folds or shows again, in every tab (D-326)
            self.asked_fold = title
            return True
        place = chapter_row_at(self.layout, pos)
        if place is not None:
            self._choose_place(place)
            return True
        setting = setting_row_at(self.layout, pos)
        if setting is not None:
            self._set(setting)
            return True
        return False

    def tab_key(self, name: str) -> bool:
        """F1, F2 or F3, by pygame's name for the key: its tab, Run, Editor or the Maker, as a
        click on it (D-303); off the sandbox, F3 says where the Maker is. False for any other."""
        tab = next((tab for tab, key in TAB_KEYS.items() if key.lower() == name), None)
        if tab is None:
            return False
        if tab not in dict(self.layout.tabs):
            self._refuse("the Maker is Free play's: open it in Chapters")
        elif tab != self.layout.env.value:
            self._ask(LEAVE[tab])
        return True

    def next_tab(self, back: bool = False) -> None:
        """Tab: the next tab, Run, Editor, then the Maker on the sandbox, round to the first;
        Shift+Tab, the one before (D-304). As a click on it, so a tutorial's step may hold it."""
        self._ask(LEAVE[tab_beside(self.layout, back)])

    def start_passkey(self, typed: str) -> bool:
        """P with Chapters open: a passkey to type, not Parts (D-075); False for any other key."""
        if self.layout.drawer is not Drawer.CHAPTERS or typed.upper() != PASSKEY_KEY:
            return False
        self.typing, self.said = "", ""
        return True

    def type_key(self, name: str, char: str) -> None:
        """A key while a passkey is typed, by its pygame name and the character it types: A to Z
        added, up to PASSKEY_LENGTH; Backspace takes one back; Enter asks main.py to try the word;
        Esc gives it up (D-075)."""
        if name == "escape":
            self.typing = None
        elif name == "backspace":
            self.typing = self.typing[:-1]
        elif name in ("return", "enter"):
            word, self.typing = self.typing, None
            self.asked_passkey = word or None
        elif len(char) == 1 and "A" <= char.upper() <= "Z" and len(self.typing) < PASSKEY_LENGTH:
            self.typing += char.upper()

    def toggle_drawer(self, drawer: Drawer) -> None:
        """A drawer's key: it opens, or folds if it is open (D-054, D-069)."""
        self.open_drawer(None if self.layout.drawer is drawer else drawer)

    def open_drawer(self, drawer: Drawer | None) -> None:
        """Open a drawer, or fold the open one (None); what the main screen shows slides with it."""
        before = self.layout
        self.layout = self._relayout(drawer)
        self._slid(before, self.layout)
        self.info = None

    def _scroll_to(self, scroll: int) -> None:
        """The open drawer's rows scrolled to `scroll`, as far as they go; an info box open on a
        row closes, as it would move."""
        drawer = self.layout.drawer
        self.scrolls[drawer] = scroll
        self.layout = self._relayout(drawer)
        self.scrolls[drawer], self.info = self.layout.scroll, None

    def set_hints(self, hints: HintView | None) -> None:
        """What Hints shows of the level's hints (D-078); the drawer is laid out again if that
        changed."""
        if hints != self.hints:
            self.hints = hints
            self.layout = self._relayout(self.layout.drawer)

    def set_chapters(self, rows: tuple[ChapterRow, ...], shut: frozenset[str]) -> None:
        """What Chapters shows, and the chapters it shows closed (D-326); the drawer is laid out
        again if those changed."""
        self.chapters = rows
        if shut != self.shut:
            self.shut = shut
            self.layout = self._relayout(self.layout.drawer)

    def _folded(self, drawer: Drawer | None, own: set[str] | None = None) -> frozenset[str]:
        """The groups `drawer` shows closed: in Chapters, the chapters, as main.py says; in any
        other, the scene's `own`."""
        return self.shut if drawer is Drawer.CHAPTERS else frozenset(own or ())

    def _hint_layout(self) -> dict:
        """What `make_layout` needs of the hints shown: the lines under each row, the picture."""
        if self.hints is None:
            return {}
        return {"hint_lines": tuple(map(len, self.hints.lines)), "shadow": self.hints.shadow}

    def _take_hint(self, index: int) -> None:
        """A row of Hints: main.py takes it, unless the level's tutorial leads (D-078)."""
        if self.hints is not None and self.hints.locked:
            self._refuse("skip or finish the tutorial for hints")
        elif self.hints is not None:
            self.asked_hint = index

    def _choose_place(self, index: int) -> None:
        """A level or the sandbox, picked in Chapters, if it is open and the tutorial lets it."""
        state = next((row.state for row in self.chapters if row.index == index), "open")
        if state == "locked":
            self._refuse("it opens once the level before it is won")
        elif self._allowed(Action("map")):
            self._cancel()
            self.chosen = index

    def _set(self, setting: Setting) -> None:
        """A row of Settings: each choice in turn, or the open level's tutorial again (D-054,
        D-334)."""
        if setting is Setting.FAST:
            self.settings.next_fast()
        elif setting is Setting.HINTS:
            self.settings.toggle_hints()
        elif setting is Setting.TUTORIAL and self.tutored:
            self._ask("tutorial")
        elif setting is Setting.TUTORIAL:
            self._refuse("this level has no tutorial")
        else:
            self._refuse("there is no sound yet")

    def _ask(self, request: str) -> None:
        """A request for main.py, if the tutorial lets it through."""
        if self._allowed(Action(request)):
            self._cancel()
            self.request = request

    def _allowed(self, action: Action) -> bool:
        """Whether the tutorial's step lets `action` through (D-048); if not, say so."""
        if self.gate is None or self.gate(action):
            return True
        self._refuse(REFUSAL)
        return False

    # A scene's own

    def _relayout(self, drawer: Drawer | None) -> Layout:
        raise NotImplementedError

    def _tip_target(self, pos: tuple[int, int]) -> object | None:
        """What a tooltip would name under `pos`: the bar's icon, another tab; a scene may add
        its own, as the editor adds the Wheel's icons (D-069)."""
        return palette_target_at(self.layout, pos)

    def _slid(self, before: Layout, after: Layout) -> None:
        """What follows the main screen when it moves; nothing by default."""

    def _cancel(self) -> None:
        """A gesture under way ends; the last refusal goes."""
        self.message = ""

    def _refuse(self, reason: str) -> None:
        self.message = reason
