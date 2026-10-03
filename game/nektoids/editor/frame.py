"""What the editor and the run share (D-051): the activity bar, one drawer at a time, the tabs
and the switch between them, the rows' info discs, Chapters and Settings, the bar's tooltips.

A scene inherits `Frame`, calls `_start_frame` once, `frame_track` as the mouse moves,
`frame_press` first on a click, and `frame_update` once a frame; it gives `_relayout` (its
layout with another drawer open), and may give `_slid` (what follows the main screen when a
drawer opens or folds), `_cancel` (a gesture under way ends) and `_refuse` (says why not).
What the player asks of `main.py` is left in `request` ("run", "edit", "tutorial") or `chosen`
(a place picked in Chapters), which `main.py` clears. Pure Python, no pygame.
"""

from __future__ import annotations

from collections.abc import Callable

from nektoids.editor.layout import (
    Drawer,
    Layout,
    Setting,
    chapter_row_at,
    drawer_button_at,
    info_at,
    level_button_at,
    on_fold_handle,
    palette_target_at,
    setting_row_at,
    tab_at,
)
from nektoids.editor.router import ChapterRow
from nektoids.editor.settings import Settings
from nektoids.editor.tutorial import REFUSAL, Action

LEAVE = {"editor": "edit", "run": "run"}  # what a tab asks for: the screen it names
WARM_FRAMES = 18  # after a tooltip, the next one shows at once for this long: 0.3 s [frames]


class Frame:
    layout: Layout

    def _start_frame(self, layout: Layout, settings: Settings | None) -> None:
        self.layout = layout
        self.settings = settings if settings is not None else Settings()  # the session's
        self.request: str | None = None  # "run", "edit" or "tutorial": main.py's to clear
        self.chosen: int | None = None  # a place picked in Chapters: main.py's to clear
        self.chapters: tuple[ChapterRow, ...] = ()  # what Chapters shows; main.py's
        self.info: object | None = None  # the row whose info box is open: a part, a tool...
        self.tip_target: object | None = None  # the bar's icon, or the other tab, under the mouse
        self.tip_frames = 0  # how long it has been there
        self.tip_warm = 0  # a tooltip showed lately: the next shows at once, for so long [frames]
        self.message = ""  # the last refusal, until something succeeds
        self.lit: frozenset[str] = frozenset()  # what a tutorial step explains (D-050); main.py's
        self.gate: Callable[[Action], bool] | None = None  # what it lets through; main.py's

    @property
    def tooltip(self) -> object | None:
        """What a tooltip names now, once the mouse has rested on it long enough: an icon of the
        bar, the other tab, or what the scene adds (`_tip_target`)."""
        return self.tip_target if self.tip_frames >= self.settings.tooltip_frames else None

    def frame_update(self) -> None:
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

    def frame_press(self, pos: tuple[int, int]) -> bool:
        """A click on the frame, taken: the fold arrow, the bar, a tab, an info disc, a row of
        Chapters or of Settings. False if it fell elsewhere, for the scene to take."""
        if on_fold_handle(self.layout, pos):
            self.open_drawer(None)
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
        place = chapter_row_at(self.layout, pos)
        if place is not None:
            self._choose_place(place)
            return True
        setting = setting_row_at(self.layout, pos)
        if setting is not None:
            self._set(setting)
            return True
        return False

    def toggle_drawer(self, drawer: Drawer) -> None:
        """A drawer's key: it opens, or folds if it is open (D-054, D-069)."""
        self.open_drawer(None if self.layout.drawer is drawer else drawer)

    def open_drawer(self, drawer: Drawer | None) -> None:
        """Open a drawer, or fold the open one (None); what the main screen shows slides with it."""
        before = self.layout
        self.layout = self._relayout(drawer)
        self._slid(before, self.layout)
        self.info = None

    def _choose_place(self, index: int) -> None:
        """A level or the sandbox, picked in Chapters, if it is open and the tutorial lets it."""
        state = next((row.state for row in self.chapters if row.index == index), "open")
        if state == "locked":
            self._refuse("it opens once the level before it is won")
        elif self._allowed(Action("map")):
            self._cancel()
            self.chosen = index

    def _set(self, setting: Setting) -> None:
        """A row of Settings: each choice in turn, or Fear's tutorial again (D-054)."""
        if setting is Setting.FAST:
            self.settings.next_fast()
        elif setting is Setting.HINTS:
            self.settings.toggle_hints()
        elif setting is Setting.TUTORIAL:
            self._ask("tutorial")
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
        """What a tooltip would name under `pos`: the bar's icon, the other tab; a scene may add
        its own, as the editor adds the Wheel's icons (D-069)."""
        return palette_target_at(self.layout, pos)

    def _slid(self, before: Layout, after: Layout) -> None:
        """What follows the main screen when it moves; nothing by default."""

    def _cancel(self) -> None:
        """A gesture under way ends; the last refusal goes."""
        self.message = ""

    def _refuse(self, reason: str) -> None:
        self.message = reason
