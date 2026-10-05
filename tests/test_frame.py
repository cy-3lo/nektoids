"""The frame the editor and the run share (D-051, D-054). frame.py imports no pygame."""

from nektoids.editor.frame import LEAVE, WARM_FRAMES, Frame
from nektoids.editor.layout import (
    SCROLL_STEP,
    Drawer,
    Env,
    Layout,
    LevelButton,
    Setting,
    make_layout,
)
from nektoids.editor.router import ChapterRow
from nektoids.editor.tutorial import REFUSAL
from nektoids.graph.board import Kind


class Scene(Frame):
    """A frame and nothing else, as a scene would hold it."""

    def __init__(
        self,
        drawer: Drawer | None = Drawer.PARTS,
        env: Env = Env.EDITOR,
        chapter: int = 3,
        goals: int = 0,
        maker: bool = False,
    ):
        self.goals = goals  # the level's objectives, under the run's drawers
        layout = make_layout(drawer, chapter=chapter, env=env, goals=goals, maker=maker)
        self._start_frame(layout, None)
        self.slid: list[tuple[Drawer | None, Drawer | None]] = []

    def _relayout(self, drawer: Drawer | None) -> Layout:
        return make_layout(
            drawer,
            chapter=self.layout.chapter,
            env=self.layout.env,
            goals=self.goals,
            scroll=self.scrolls.get(drawer, 0),
            maker=self.layout.maker,
        )

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


def test_chapters_ends_with_a_passkey_field_typed_in_by_a_click_or_p():
    scene = Scene(Drawer.CHAPTERS)  # D-075
    field = scene.layout.passkey_field
    last = max(rect[1] + rect[3] for _, rect in scene.layout.chapter_rows)
    assert field is not None and field[1] > last  # under the sandbox
    assert Scene(Drawer.PARTS).layout.passkey_field is None
    assert scene.frame_press(centre(field)) and scene.typing == ""
    for name, char in (("s", "s"), ("w", "w"), ("1", "1"), ("o", "o"), ("backspace", "")):
        scene.type_key(name, char)
    assert scene.typing == "SW"  # letters only, upper case; Backspace takes one back
    scene.type_key("return", "\r")
    assert scene.asked_passkey == "SW" and scene.typing is None  # main.py tries it
    assert not Scene(Drawer.PARTS).start_passkey("p")  # P is Parts elsewhere
    assert scene.start_passkey("p") and scene.typing == ""
    scene.type_key("escape", "")
    assert scene.typing is None
    scene.start_passkey("P")
    scene.frame_press(centre(scene.layout.board_area))  # a click elsewhere gives it up
    assert scene.typing is None
    scene.start_passkey("P")
    for _ in range(12):
        scene.type_key("a", "a")
    assert scene.typing == "A" * 10  # at most PASSKEY_LENGTH


def test_a_parts_entry_runs_its_own_circuit_while_its_box_is_open():
    scene = Scene()
    scene.frame_update()
    assert scene.entry is None  # no box open
    scene.info = Kind.DOUBLE  # its info disc clicked
    scene.frame_update()
    entry = scene.entry
    assert entry is not None and entry.kind is Kind.DOUBLE
    before = list(entry.circuit.beads.phase)
    scene.frame_update()
    assert scene.entry is entry and entry.circuit.beads.phase != before  # it runs
    scene.info = Kind.SUM
    scene.frame_update()
    assert scene.entry.kind is Kind.SUM
    scene.info = Setting.FAST  # a row's box, not a part's
    scene.frame_update()
    assert scene.entry is None


def test_the_mouse_wheel_scrolls_a_drawer_whose_rows_do_not_fit_in_the_run_too():
    scene = Scene(Drawer.CHAPTERS, Env.RUN, chapter=7, goals=3)  # D-096
    inside = centre(scene.layout.list_area)
    assert scene.layout.scroll_max > 0 and scene.layout.scroll == 0
    scene.info = 0  # a row's info box: it closes, as its row moves
    assert scene.frame_wheel(inside, -2)  # down: the rows go up
    assert scene.layout.scroll == 2 * SCROLL_STEP and scene.info is None
    assert scene.frame_wheel(inside, 99) and scene.layout.scroll == 0  # no farther than the top
    assert not scene.frame_wheel(centre(scene.layout.board_area), -1)  # the scene's to take
    scene.toggle_drawer(Drawer.SETTINGS)  # its rows fit: nothing to scroll
    assert not scene.frame_wheel(centre(scene.layout.list_area), -1)
    scene.toggle_drawer(Drawer.CHAPTERS)
    assert scene.layout.scroll == 0  # each drawer keeps its own scroll


def test_the_scroll_bar_held_drags_the_rows_until_it_is_let_go():
    scene = Scene(Drawer.CHAPTERS, Env.RUN, chapter=7, goals=3)
    x, y, w, h = scene.layout.scroll_bar
    assert scene.frame_press((x + w // 2, y + h // 2)) and scene.scrolling
    scene.frame_track((x, y + h))
    assert scene.layout.scroll == scene.layout.scroll_max
    scene.frame_release()
    scene.frame_track((x, y))
    assert not scene.scrolling and scene.layout.scroll == scene.layout.scroll_max


def test_on_the_sandbox_each_tab_asks_for_its_own_screen_and_shows_its_tooltip():
    for env, here in ((Env.EDITOR, "editor"), (Env.RUN, "run"), (Env.MAKER, "maker")):  # D-301
        scene = Scene(None, env=env, maker=True)
        tabs = dict(scene.layout.tabs)
        for name, asked in (("run", "run"), ("editor", "edit"), ("maker", "make")):
            scene.request = None
            assert scene.frame_press(centre(tabs[name]))
            assert scene.request == (None if name == here else asked)
            scene.frame_track(centre(tabs[name]))
            assert scene.tip_target == (None if name == here else name)


def test_f1_f2_f3_ask_for_run_editor_and_the_maker_as_their_tabs_and_f3_off_the_sandbox_says_why():
    for env, here in ((Env.EDITOR, "editor"), (Env.RUN, "run"), (Env.MAKER, "maker")):  # D-303
        scene = Scene(None, env=env, maker=True)
        for key, asked in (("f1", "run"), ("f2", "edit"), ("f3", "make")):
            scene.request = None
            assert scene.tab_key(key)
            assert scene.request == (None if LEAVE[here] == asked else asked)
    scene = Scene(None, env=Env.RUN)  # a level of the chapter: two tabs
    assert scene.tab_key("f3") and scene.request is None and "Chapters" in scene.message
    assert not scene.tab_key("f4") and not scene.tab_key("space")
    scene.gate = lambda action: action.verb != "edit"  # a tutorial's step holds it
    assert scene.tab_key("f2") and scene.request is None and scene.message == REFUSAL
