# /// script
# dependencies = [
#   "numpy",
# ]
# ///
"""Nektoids entry point.

Runs natively (`python game/main.py`) and in the browser (`pygbag game`).
It opens on the first level's board in the editor, under the title card. Run (Space) runs it in
its arena; Edit (Esc) comes back to the board as it was left; once a level is won, Next level
(Enter) opens the next one's board, and after the last, the end. Chapters (Tab), a drawer, lists
the chapter's levels and the sandbox (`editor/router.py`, D-030, D-054); on the sandbox, the
Maker tab makes its level (`editor/maker.py`, D-301). A level opened from it
or by Next level comes up under its card, which says what it asks (D-042). A level's tutorial
shows over the editor and the run, and follows what the player does (`editor/tutorial.py`,
D-039); its hints are asked for in the Hints drawer, in turn (`editor/hints.py`, D-078).
Developer tools, while DEV_VIEW is on:
F1, F2 and F3 are the tabs, Run, Editor and the Maker (D-303), so these moved four keys on:
F5 goes to the editor of the open level, from any view or screen.
F6 switches to the developer view (D-016): the board as a running circuit, with equations.
F7 switches to the arena view (D-019, D-022): the board in every arena, with the tools.
F8 prints the board as one line of JSON (D-024): in the terminal natively, in pygbag's
terminal on the page in the browser. Nothing is written to a file.
"""

import asyncio
import json

import pygame

from nektoids.editor import clipboard
from nektoids.editor.arena import ArenaScene
from nektoids.editor.arena_draw import draw_arena
from nektoids.editor.devdrive import DT, SIM_HZ, TICKS_PER_FRAME
from nektoids.editor.draw import Fonts, draw
from nektoids.editor.hints import Hints, Taken, hint_view
from nektoids.editor.layout import DRAWERS, FOOT, SCREEN, Drawer, MainView, contains, make_layout
from nektoids.editor.maker import MakerScene
from nektoids.editor.maker_draw import draw_maker
from nektoids.editor.palette import pulse
from nektoids.editor.preview_draw import draw_preview
from nektoids.editor.router import Router, Screen, level_label, level_number
from nektoids.editor.scene import EditorScene
from nektoids.editor.schematic import SchematicScene
from nektoids.editor.schematic_draw import draw_schematic
from nektoids.editor.settings import Settings
from nektoids.editor.shell import bottom_button
from nektoids.editor.shell_draw import draw_end, draw_level_card, draw_title_card
from nektoids.editor.tutorial import (
    Context,
    Live,
    Tutorial,
    allows,
    answer,
    box_rect,
    drawer_for,
    focus_cells,
    panels,
    shows_wheel,
    target_rects,
    target_spots,
)
from nektoids.editor.tutorial_draw import draw_tutorial
from nektoids.graph.board import Board, Kind
from nektoids.levels.arenas import CHAPTERS, arenas, sandbox
from nektoids.levels.objectives import Outcome
from nektoids.levels.scenarios import Scenario, scenarios
from nektoids.levels.score import Score

FPS = 60
DEV_VIEW = False  # True: F5 the editor, F6 the developer view, F7 the arena view, F8 prints
assert SIM_HZ == FPS * TICKS_PER_FRAME  # the developer view runs a whole number of ticks a frame

pygame.init()
screen = pygame.display.set_mode(SCREEN)
pygame.display.set_caption("Nektoids")
clock = pygame.time.Clock()
fonts = Fonts.load()
clipboard.install()  # the page's side of Save and Load, once (D-206)
levels = arenas()  # read from their files once, at startup (web.md: no file I/O in the loop)
free = sandbox()  # Free play's level as shipped: the Maker may start from it again (D-310)
router = Router(levels, free)
chapters = tuple((chapter.heading, len(chapter.names)) for chapter in CHAPTERS)  # D-326
editors: dict[int, EditorScene] = {}  # each level's editor, and its undo history with it
makers: dict[int, MakerScene] = {}  # the sandbox's Maker, made when first opened (D-301)
tutorials: dict[int, Tutorial] = {}  # each level's tutorial, where it has got to
shadows: dict[int, tuple[Hints, Board]] = {}  # each level's hints, read, and its shadow built
taken: dict[int, Taken] = {}  # what the player has taken of each level's hints (D-078)
opened_for: dict[int, int] = {}  # the step whose drawer each level's editor last opened
settings = Settings()  # what the player sets, for the session (D-054)


def tutorial() -> Tutorial | None:
    """The open level's tutorial while a step remains, or None (the sandbox has none)."""
    data = None if router.in_sandbox else router.level.tutorial
    if data is not None and router.index not in tutorials:
        tutorials[router.index] = Tutorial.from_dict(data)
    guide = tutorials.get(router.index)
    return guide if guide is not None and guide.step is not None else None


def tutorial_start() -> Drawer | None:
    """The editor's drawer the open level's tutorial begins in, while it has not begun; None:
    the level opens on its run (D-069, D-103)."""
    guide = tutorial()
    return guide.starts_in if guide is not None and guide.index == 0 else None


def hints() -> tuple[Hints, Board, Taken] | None:
    """The open level's hints, its shadow built once, and what of them is taken this session;
    None in the sandbox, which has none (D-078)."""
    if router.in_sandbox or router.level.hints is None:
        return None
    if router.index not in shadows:
        read = Hints.of(router.level)
        shadows[router.index] = (read, read.board)
    return (*shadows[router.index], taken.setdefault(router.index, Taken()))


def tutorial_box(guide: Tutorial, scene: EditorScene | ArenaScene) -> tuple:
    """Where the step's target and its box are, on the screen now open: `scene`'s; in the
    editor, the Wheel's icons round the focused cell are targets too (D-070)."""
    if isinstance(scene, EditorScene):
        live = Live(wheel=tuple(scene.wheel()), focused=scene.focused)
    else:  # the run: the swimmer, which Fear's first step outlines (D-071)
        live = Live(swimmer=scene.swimmer_box())
    where = (router.screen, scene.layout, scene.view, live)
    spots = target_spots(guide.step.show, *where)
    done = guide.before  # the work just done, which the box keeps clear of too (D-048)
    before = [] if done is None else target_rects(done.show, *where)
    beside = scene.layout.board_area  # the board, or the arena
    parts = []  # what the box must not hide: the parts on the editor's board (D-103)
    if isinstance(scene, EditorScene):
        parts = target_rects([{"cell": list(n.cell)} for n in scene.board.nodes.values()], *where)
    lines = len(guide.step.lines)
    return spots, box_rect([rect for rect, _ in spots], lines, beside, before, parts)


def choose_place(index: int) -> None:
    """A place picked in Chapters, under its card. Every level keeps its board, its undo history,
    the hints taken (D-078) and where its tutorial has got to: Fear's shows once a session
    (D-079). The editor left goes back to Parts, as an editor opens, and the run to Diagnostic
    (D-068, D-321)."""
    if router.index in editors:
        editors[router.index].open_drawer(Drawer.PARTS)
    router.open(index)


def replay_tutorial() -> None:
    """Settings' Tutorial: the open level's tutorial again, from its first step, on its board as
    the player left it, under its card (D-079, D-334)."""
    index = router.index
    tutorials.pop(index, None)
    opened_for.pop(index, None)
    choose_place(index)


MODIFIERS = {  # alone, they close no card: Cmd+Tab to another window, Shift before a letter
    pygame.K_LSHIFT,
    pygame.K_RSHIFT,
    pygame.K_LCTRL,
    pygame.K_RCTRL,
    pygame.K_LALT,
    pygame.K_RALT,
    pygame.K_LMETA,
    pygame.K_RMETA,
    pygame.K_CAPSLOCK,
}


def tutorial_press(guide: Tutorial, event: pygame.event.Event, scene) -> str | None:
    """ "next" or "skip" if this key or click is the tutorial's (`tutorial.answer`), else None."""
    if event.type == pygame.KEYDOWN and event.key not in MODIFIERS:
        return answer(guide, tutorial_box(guide, scene)[1], None)
    if event.type == pygame.MOUSEBUTTONDOWN and 1 <= event.button <= 3:  # not the wheel
        return answer(guide, tutorial_box(guide, scene)[1], event.pos)
    return None


def editor() -> EditorScene:
    """The open level's editor, made the first time the level opens."""
    if router.index not in editors:
        level = router.level
        caption = (f"{router.label}. {level.title}", level.spec)
        board = router.board
        handed_out = frozenset(kind for kind in Kind if board.total(kind) != 0)
        maker = router.in_sandbox  # its tabs end with the Maker's (D-301)
        layout = make_layout(Drawer.PARTS, kinds=handed_out, chapters=chapters, maker=maker)
        editors[router.index] = EditorScene(board, layout, caption, settings, level)
    return editors[router.index]


def maker() -> MakerScene:
    """The sandbox's Maker, made the first time it opens (D-301)."""
    if router.index not in makers:
        starts = (*((level_number(k), level) for k, level in enumerate(levels)), ("", free))
        makers[router.index] = MakerScene(
            router.level, router.label, settings, chapters, starts=starts, board=router.board
        )
        makers[router.index].open_blank()  # a blank plane to make (D-317)
    return makers[router.index]


def play(drawer: Drawer | None) -> ArenaScene:
    """The player's run of the open level, on its board as it stands, `drawer` open."""
    after = "Next level" if router.has_next else "The end" if router.is_last else None
    return ArenaScene(
        router.board,
        [router.level],
        developer=False,
        next_label=after,
        label=router.label,
        settings=settings,
        drawer=drawer,
        chapters=chapters,
        passkey=router.next_passkey(),  # on the win card (D-075)
        maker=router.in_sandbox,  # the Maker's tab (D-301)
    )


def shell_event(event: pygame.event.Event) -> None:
    """The cards and the end take the event (D-035, D-042): a card goes, and the run under it
    shows (D-069); the end's button goes back to the last level."""
    clicked = event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
    escape = event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
    if router.screen in (Screen.TITLE, Screen.SPEC):
        if clicked or event.type == pygame.KEYDOWN:
            router.begin()
    elif escape or (clicked and contains(bottom_button(), event.pos)):  # the end
        router.edit()  # back to the last level, Chapters open (D-054)
        editor().open_drawer(Drawer.CHAPTERS)


def open_developer_view() -> SchematicScene:
    """Your board first, then the examples."""
    return SchematicScene([Scenario("Your board", router.board), *scenarios()])


def toggle(
    open_view: SchematicScene | ArenaScene | None, key: int
) -> SchematicScene | ArenaScene | None:
    """F6 opens or closes the developer view, F7 the arena view; either replaces the other."""
    if key == pygame.K_F6:
        return None if isinstance(open_view, SchematicScene) else open_developer_view()
    if isinstance(open_view, ArenaScene):
        return None
    return ArenaScene(router.board, levels, settings=settings, chapters=chapters)


async def main() -> None:
    running = True
    developer: SchematicScene | ArenaScene | None = None  # the F6 or F7 view, while open
    playing: ArenaScene | None = None  # the player's run, while it shows
    run_drawer: Drawer | None = Drawer.INSIDE  # the run's open drawer, from one run to the next
    held: ArenaScene | None = None  # the run an explaining step paused while it played (D-071)

    def on_screen() -> EditorScene | ArenaScene | MakerScene:
        """The scene the player sees: the run, the sandbox's Maker, or the open level's editor."""
        if playing is not None:
            return playing
        return maker() if router.screen is Screen.MAKE else editor()

    pointer = (0, 0)  # where the mouse is, for the end's button [px]
    frame = 0  # frames drawn: what a tutorial's target pulses by (D-337), drawing only
    while running:
        frame += 1
        for event in pygame.event.get():
            if event.type == pygame.MOUSEMOTION:
                pointer = event.pos
            if event.type == pygame.QUIT:
                running = False
            elif (
                DEV_VIEW
                and event.type == pygame.KEYDOWN
                and event.key in (pygame.K_F6, pygame.K_F7)
            ):
                developer = toggle(developer, event.key)
            elif DEV_VIEW and event.type == pygame.KEYDOWN and event.key == pygame.K_F5:
                developer, playing = None, None  # straight to the editor, from anywhere
                router.edit()
            elif DEV_VIEW and event.type == pygame.KEYDOWN and event.key == pygame.K_F8:
                print(json.dumps(router.board.to_dict(), separators=(",", ":")), flush=True)
            elif developer is not None:
                developer.handle_event(event)
            elif (
                (guide := tutorial()) is not None
                and router.screen in (Screen.EDIT, Screen.RUN)
                and (button := tutorial_press(guide, event, on_screen())) is not None
            ):
                if button == "next":
                    last = guide.index == len(guide.steps) - 1
                    guide.next()  # and nothing else, but on the last step: a click there
                    if last and event.type == pygame.MOUSEBUTTONDOWN:  # does what it does too
                        on_screen().handle_event(event)  # Hints opens by its icon (D-079)
                else:
                    guide.skip()
                editor().message = ""  # a refusal from the step before no longer holds
            elif router.screen in (Screen.TITLE, Screen.SPEC, Screen.END):
                shell_event(event)
                if router.screen is Screen.RUN and (start := tutorial_start()) is not None:
                    router.edit()  # the card gives way to the editor, not the run (D-103)
                    editor().open_drawer(start)
                    if playing is not None:
                        run_drawer, playing = playing.layout.drawer, None
            elif playing is not None:
                playing.handle_event(event)
            elif router.screen is Screen.MAKE:
                maker().handle_event(event)
            else:
                editor().handle_event(event)

        # What the scenes asked for this frame.
        if isinstance(developer, ArenaScene) and developer.request == "edit":
            developer = None
        if playing is not None:
            if playing.outcome is Outcome.WON and playing.ended_at is not None:
                router.mark_won()  # the next level opens in Chapters
                score = Score(playing.parts, playing.ended_at)  # once: a set
                router.record(score, router.board.snapshot())  # the board that won, for Files
                made = makers.get(router.index)
                if router.in_sandbox and made is not None:  # the level made, won: its proof
                    made.won(playing.level, router.board, score)  # (D-320)
            playing.scores = router.scores
            if playing.request == "next" and router.has_next:
                router.next()
            elif playing.request == "next":
                router.finish()
            elif playing.request == "edit":
                router.edit()
            elif playing.request == "make":
                router.make()
            elif playing.request == "tutorial":  # Settings: the level's tutorial again
                replay_tutorial()
            if playing.chosen is not None:  # a place picked in Chapters
                choose_place(playing.chosen)
            if playing.request is not None or playing.chosen is not None:
                kept = playing.layout.drawer if playing.chosen is None else Drawer.INSIDE  # D-321
                run_drawer, playing = kept, None
        if router.screen is Screen.EDIT:
            asked, editor().request = editor().request, None
            if asked == "run":
                router.run()
                playing = play(run_drawer)
            elif asked == "make":
                router.make()
            elif asked == "tutorial":  # Settings: the level's tutorial again
                replay_tutorial()
            chosen, editor().chosen = editor().chosen, None
            if chosen is not None:
                choose_place(chosen)
                run_drawer = Drawer.INSIDE  # a place's run opens on Diagnostic (D-321)
        made = makers.get(router.index)
        if made is not None:  # the parts locked on the Editor's board, the level's (D-319)
            made.follow_board()
        if made is not None and made.level is not router.level:  # changed in the Maker (D-301)
            router.revise(made.level)
            if router.index in editors:
                editors[router.index].revise(made.level, made.caption)
        if router.screen is Screen.MAKE:
            asked, maker().request = maker().request, None
            if asked == "run":
                router.run()
                playing = play(run_drawer)
            elif asked == "edit":
                router.edit()
            elif asked == "tutorial":
                replay_tutorial()
            chosen, maker().chosen = maker().chosen, None
            if chosen is not None:
                choose_place(chosen)
                run_drawer = Drawer.INSIDE
        if router.screen in (Screen.TITLE, Screen.SPEC) and playing is None:
            playing = play(run_drawer)  # the run it opens on, paused, under its card (D-069)

        frames = (editor(), playing, makers.get(router.index))  # the scenes open on this place
        for scene in frames:  # a chapter's title clicked in Chapters (D-326)
            if scene is not None and scene.asked_fold is not None:
                router.fold(scene.asked_fold)
                scene.asked_fold = None
        for scene in frames:  # a passkey typed in Chapters (D-075)
            if scene is not None and scene.asked_passkey is not None:
                word, scene.asked_passkey = scene.asked_passkey, None
                opened = router.unlock(word)
                if opened is None:
                    scene.message = "no level has that word"
                else:
                    title = router.levels[opened].title
                    scene.said = (
                        f"{word} opens {level_label(opened)}, {title}: it is open in Chapters"
                    )

        given, built, took = hints() or (None, None, None)  # the level's, its shadow, the taken
        for scene in frames:  # a row of Hints clicked (D-078)
            if scene is not None and scene.asked_hint is not None:
                index, scene.asked_hint = scene.asked_hint, None
                refused = took.take(index) if took is not None else None
                if refused is not None:
                    scene.message = refused

        guide = tutorial()
        if guide is not None:  # on past what the player has done
            ended = playing.outcome if playing is not None else None
            time = playing.clock.tick * DT if playing is not None else 0.0  # the run's [s]
            drawer = on_screen().layout.drawer  # one a step may wait for (D-074)
            guide.follow(Context(router.board, editor().tool, router.screen, ended, time, drawer))
            guide = tutorial()
        hinted = None if given is None else hint_view(given, took, guide is not None, built)
        for scene in frames:  # what Hints shows; locked while a tutorial leads
            if scene is not None:
                scene.set_hints(hinted)
        shadow = given if took is not None and took.shown else None
        model = guide if guide is not None else shadow  # the tutorial's, else the hint's shadow
        editor().ghosts = model.ghosts if model is not None else ()
        editor().ghost_wires = model.ghost_wires if model is not None else ()  # D-074
        editor().set_wins(router.files())  # what Files shows: every level's wins (D-092)
        for scene in frames:  # what Chapters shows, in every tab, and the chapters it folds
            if scene is not None:
                scene.set_chapters(router.rows(), frozenset(router.folded))
                scene.tutored = not router.in_sandbox and router.level.tutorial is not None
        scene = on_screen()
        wanted = drawer_for(guide.step, scene.layout.drawer) if guide is not None else None
        here = (*DRAWERS[scene.layout.env], *FOOT)  # a step opens a drawer of the screen it is on
        if wanted in here and opened_for.get(router.index) != guide.index:
            opened_for[router.index] = guide.index  # once a step: then the player's to change
            if scene.layout.drawer is not wanted:
                scene.open_drawer(wanted)
            if shows_wheel(guide.step) and isinstance(scene, EditorScene):
                scene.unfold_wheel()  # its icon must show (D-070)
        gate = None if guide is None else lambda action, g=guide: allows(g.step, action)
        editor().gate = gate  # only what the step asks goes through (D-048)
        editor().lit = panels(guide)  # the panels a step explains, titles lit (D-050)
        editor().lit_ink = pulse(frame)  # ... in the accent, pulsing (D-337)
        editor().guide_cells = focus_cells(guide)  # the cells a step acts on, lit (D-063)
        if playing is not None:
            playing.gate = gate
            playing.lit = panels(guide)
            playing.lit_ink = pulse(frame)
            explaining = guide is not None and guide.explains
            if explaining and not playing.clock.paused:  # it holds the run still (D-050)
                playing.clock.paused, held = True, playing
            elif not explaining and held is playing:  # and lets it go on once explained (D-071)
                playing.clock.paused, held = False, None

        if isinstance(developer, SchematicScene):
            developer.update()
            draw_schematic(screen, developer, fonts)
        elif isinstance(developer, ArenaScene):
            developer.update()
            draw_arena(screen, developer, fonts)
        elif router.screen is Screen.END:
            draw_end(screen, fonts, pointer)
        elif playing is not None:
            playing.update()
            draw_arena(screen, playing, fonts)
        elif router.screen is Screen.MAKE:
            maker().update()
            draw_maker(screen, maker(), fonts)
        else:
            editor().update()
            preview = editor().main is MainView.PREVIEW  # the Run preview, not the board (D-058)
            draw(screen, editor(), fonts, draw_preview if preview else None)
        if developer is None and router.screen is Screen.TITLE:  # over the run (D-069)
            draw_title_card(screen, fonts)
        elif developer is None and router.screen is Screen.SPEC:
            draw_level_card(screen, router, fonts)
        if developer is None and guide is not None and router.screen in (Screen.EDIT, Screen.RUN):
            draw_tutorial(screen, fonts, guide, tutorial_box(guide, on_screen())[1], pointer)
        pygame.display.flip()
        clock.tick(FPS)

        await asyncio.sleep(0)  # pygbag: hand control back to the browser, every frame


asyncio.run(main())
# Nothing below this line (pygbag).
