"""The frame the editor and the run share (D-051, D-054). frame.py imports no pygame."""

from nektoids.editor.frame import WARM_FRAMES, Frame
from nektoids.editor.layout import Drawer, Layout, LevelButton, Setting, make_layout
from nektoids.editor.router import ChapterRow
from nektoids.editor.tutorial import REFUSAL


class Scene(Frame):
    """A frame and nothing else, as a scene would hold it."""

    def __init__(self, drawer: Drawer | None = Drawer.PARTS):
        self._start_frame(make_layout(drawer, chapter=3), None)
        self.slid: list[tuple[Drawer | None, Drawer | None]] = []

    def _relayout(self, drawer: Drawer | None) -> Layout:
        return make_layout(drawer, chapter=self.layout.chapter, env=self.layout.env)

    def _slid(self, before: Layout, after: Layout) -> None:
        self.slid.append((before.drawer, after.drawer))


def centre(rect):
    x, y, w, h = rect
    return (x + w // 2, y + h // 2)


def icon(scene: Scene, drawer: Drawer) -> tuple[int, int]:
    return centre(dict(scene.layout.drawer_buttons)[drawer])


def test_an_icon_opens_its_drawer_and_folds_it_again_and_the_main_screen_follows():
    scene = Scene()
    assert scene.frame_press(icon(scene, Drawer.FILES)) and scene.layout.drawer is Drawer.FILES
    assert scene.frame_press(icon(scene, Drawer.FILES)) and scene.layout.drawer is None
    scene.frame_press(icon(scene, Drawer.PARTS))
    assert scene.frame_press(centre(scene.layout.fold_handle)) and scene.layout.drawer is None
    assert scene.slid == [(Drawer.PARTS, Drawer.FILES), (Drawer.FILES, None)] + [
        (None, Drawer.PARTS),
        (Drawer.PARTS, None),
    ]
    scene.toggle_drawer(Drawer.CHAPTERS)
    assert scene.layout.drawer is Drawer.CHAPTERS
    scene.toggle_drawer(Drawer.CHAPTERS)
    assert scene.layout.drawer is None
    assert not scene.frame_press(centre(scene.layout.board_area))  # the scene's to take


def test_the_other_tab_and_the_switch_ask_for_the_run_unless_the_tutorial_holds_them():
    scene = Scene()
    tabs = dict(scene.layout.tabs)
    assert scene.frame_press(centre(tabs["editor"])) and scene.request is None  # already there
    assert scene.frame_press(centre(tabs["run"])) and scene.request == "run"
    scene.request = None
    switch = dict(scene.layout.level_buttons)[LevelButton.RUN]
    scene.gate = lambda action: action.verb != "run"
    assert scene.frame_press(centre(switch)) and scene.request is None
    assert scene.message == REFUSAL


def test_chapters_opens_a_place_that_is_open_and_says_why_one_is_locked():
    scene = Scene(Drawer.CHAPTERS)
    scene.chapters = (
        ChapterRow(0, "1.1", "Fear", "", "won", None, False),
        ChapterRow(1, "1.2", "Aggression", "", "open", None, True),
        ChapterRow(2, "1.3", "Love", "", "locked", None, False),
    )
    rows = dict(scene.layout.chapter_rows)
    scene.frame_press(centre(rows[2]))
    assert scene.chosen is None and "won" in scene.message
    scene.frame_press(centre(rows[0]))
    assert scene.chosen == 0 and scene.message == ""
    info = dict(scene.layout.info_buttons)[1]
    assert scene.frame_press(centre(info)) and scene.info == 1


def test_settings_step_through_their_choices_and_the_tutorial_is_asked_for():
    scene = Scene(Drawer.SETTINGS)
    rows = dict(scene.layout.setting_rows)
    scene.frame_press(centre(rows[Setting.FAST]))
    scene.frame_press(centre(rows[Setting.HINTS]))
    assert (scene.settings.fast, scene.settings.key_hints) == (8, False)
    scene.frame_press(centre(rows[Setting.SOUND]))
    assert scene.message == "there is no sound yet"
    scene.frame_press(centre(rows[Setting.TUTORIAL]))
    assert scene.request == "tutorial"


def test_an_icons_tooltip_shows_once_the_mouse_has_rested_on_it():
    scene = Scene()
    scene.frame_track(icon(scene, Drawer.NAVIGATOR))
    for _ in range(scene.settings.tooltip_frames - 1):
        scene.frame_update()
    assert scene.tooltip is None
    scene.frame_update()
    assert scene.tooltip is Drawer.NAVIGATOR
    scene.frame_track(centre(scene.layout.board_area))
    assert scene.tooltip is None and scene.tip_frames == 0


def test_once_a_tooltip_shows_the_next_icons_shows_at_once_across_the_gap_between_them():
    scene = Scene()  # D-069
    scene.frame_track(icon(scene, Drawer.NAVIGATOR))
    for _ in range(scene.settings.tooltip_frames):
        scene.frame_update()
    assert scene.tooltip is Drawer.NAVIGATOR
    x, y = icon(scene, Drawer.NAVIGATOR)
    scene.frame_track((x, y - 23))  # between two icons: nothing under the mouse
    scene.frame_update()
    scene.frame_track(icon(scene, Drawer.DIAGNOSTIC))
    assert scene.tooltip is Drawer.DIAGNOSTIC  # at once
    scene.frame_track(centre(scene.layout.board_area))
    for _ in range(WARM_FRAMES):
        scene.frame_update()
    scene.frame_track(icon(scene, Drawer.FILES))
    assert scene.tooltip is None  # rested long enough off the bar: the wait again


def test_a_scenes_own_tooltip_waits_as_the_bars_do():
    class Wheel(Scene):  # a scene adding a target of its own, as the editor adds its Wheel's icons
        def _tip_target(self, pos):
            return super()._tip_target(pos) or ("icon" if pos == (600, 600) else None)

    scene = Wheel()  # D-069
    scene.frame_track((600, 600))
    for _ in range(scene.settings.tooltip_frames - 1):
        scene.frame_update()
    assert scene.tooltip is None  # the same rest as the bar's
    scene.frame_update()
    assert scene.tooltip == "icon"
    scene.frame_track(icon(scene, Drawer.FILES))
    assert scene.tooltip is Drawer.FILES  # and the same warmth, from it to the bar


def test_the_other_tab_says_what_the_switch_says_and_this_one_nothing():
    scene = Scene()
    tabs = dict(scene.layout.tabs)
    scene.frame_track(centre(tabs["run"]))
    for _ in range(scene.settings.tooltip_frames):
        scene.frame_update()
    assert scene.tooltip == "run"  # drawn as the switch's: "Run (Space)" (D-060)
    scene.frame_track(centre(tabs["editor"]))
    assert scene.tip_target is None
