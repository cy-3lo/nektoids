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
the chapter's levels and the sandbox (`editor/router.py`, D-030, D-054). A level opened from it
or by Next level comes up under its card, which says what it asks (D-042). A level's tutorial or
hints show over the editor and the run, and follow what the player does (`editor/tutorial.py`,
D-039).
Developer tools, while DEV_VIEW is on:
F1 goes to the editor of the open level, from any view or screen.
F2 switches to the developer view (D-016): the board as a running circuit, with equations.
F3 switches to the arena view (D-019, D-022): the board in every arena, with the tools.
F4 prints the board as one line of JSON (D-024): in the terminal natively, in pygbag's
terminal on the page in the browser. Nothing is written to a file.
"""

import asyncio
import json

import pygame

from nektoids.editor.arena import ArenaScene
from nektoids.editor.arena_draw import draw_arena
from nektoids.editor.devdrive import SIM_HZ, TICKS_PER_FRAME
from nektoids.editor.draw import Fonts, draw
from nektoids.editor.layout import DRAWERS, FOOT, SCREEN, Drawer, MainView, contains, make_layout
from nektoids.editor.preview_draw import draw_preview
from nektoids.editor.router import Router, Screen
from nektoids.editor.scene import EditorScene
from nektoids.editor.schematic import SchematicScene
from nektoids.editor.schematic_draw import draw_schematic
from nektoids.editor.settings import Settings
from nektoids.editor.shell import bottom_button
from nektoids.editor.shell_draw import draw_end, draw_level_card, draw_title_card
from nektoids.editor.tutorial import (
    Context,
    Tutorial,
    allows,
    answer,
    box_rect,
    drawer_for,
    guided,
    panels,
    target_rects,
    target_spots,
)
from nektoids.editor.tutorial_draw import draw_tutorial
from nektoids.graph.board import Kind
from nektoids.levels.arenas import arenas, sandbox
from nektoids.levels.objectives import Outcome
from nektoids.levels.scenarios import Scenario, scenarios
from nektoids.levels.score import Score

FPS = 60
DEV_VIEW = True  # F1 the editor, F2 the developer view, F3 the arena view, F4 prints the board
assert SIM_HZ == FPS * TICKS_PER_FRAME  # the developer view runs a whole number of ticks a frame

pygame.init()
screen = pygame.display.set_mode(SCREEN)
pygame.display.set_caption("Nektoids")
clock = pygame.time.Clock()
fonts = Fonts.load()
levels = arenas()  # read from their files once, at startup (web.md: no file I/O in the loop)
router = Router(levels, sandbox())
editors: dict[int, EditorScene] = {}  # each level's editor, and its undo history with it
tutorials: dict[int, Tutorial] = {}  # each level's tutorial or hints, where it has got to
opened_for: dict[int, int] = {}  # the step whose drawer each level's editor last opened
settings = Settings()  # what the player sets, for the session (D-054)


def tutorial() -> Tutorial | None:
    """The open level's tutorial while a step remains, or None (the sandbox has none)."""
    data = None if router.in_sandbox else router.level.tutorial
    if data is not None and router.index not in tutorials:
        tutorials[router.index] = Tutorial.from_dict(data)
    guide = tutorials.get(router.index)
    return guide if guide is not None and guide.step is not None else None


def tutorial_box(guide: Tutorial, scene: EditorScene | ArenaScene) -> tuple:
    """Where the step's target and its box are, on the screen now open: `scene`'s."""
    spots = target_spots(guide.step.show, router.screen, scene.layout, scene.view)
    done = guide.before  # the work just done, which the box keeps clear of too (D-048)
    before = (
        [] if done is None else target_rects(done.show, router.screen, scene.layout, scene.view)
    )
    beside = scene.layout.board_area  # the board, or the arena
    return spots, box_rect([rect for rect, _ in spots], len(guide.step.say), beside, before)


def choose_place(index: int) -> None:
    """A place picked in Chapters, under its card. A guided level starts afresh, its board, its
    undo history and its tutorial; the others keep their boards, and their hints start again
    (D-048, D-050, D-054). The editor left goes back to Parts, as an editor opens."""
    if router.index in editors:
        editors[router.index].open_drawer(Drawer.PARTS)
    for index_, level in enumerate(levels):
        if guided(level.tutorial):
            router.reset(index_)
            editors.pop(index_, None)
            tutorials.pop(index_, None)
            opened_for.pop(index_, None)
    for guide in tutorials.values():
        guide.restart()
    router.open(index)


def tutorial_press(guide: Tutorial, event: pygame.event.Event, scene) -> str | None:
    """ "next" or "skip" if this key or click is the tutorial's (`tutorial.answer`), else None."""
    if event.type == pygame.KEYDOWN:
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
        layout = make_layout(kinds=handed_out, chapter=len(levels))
        editors[router.index] = EditorScene(board, layout, caption, settings, level)
    return editors[router.index]


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
        chapter=len(levels),
    )


def shell_event(event: pygame.event.Event) -> None:
    """The cards and the end take the event (D-035, D-042)."""
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
    """F2 opens or closes the developer view, F3 the arena view; either replaces the other."""
    if key == pygame.K_F2:
        return None if isinstance(open_view, SchematicScene) else open_developer_view()
    if isinstance(open_view, ArenaScene):
        return None
    return ArenaScene(router.board, levels, settings=settings, chapter=len(levels))


async def main() -> None:
    running = True
    developer: SchematicScene | ArenaScene | None = None  # the F2 or F3 view, while open
    playing: ArenaScene | None = None  # the player's run, while it shows
    run_drawer: Drawer | None = Drawer.OBJECTIVES  # the run's open drawer, from one run to the next

    def on_screen() -> EditorScene | ArenaScene:
        """The scene the player sees: the run, or the open level's editor."""
        return playing if playing is not None else editor()

    pointer = (0, 0)  # where the mouse is, for the end's button [px]
    while running:
        for event in pygame.event.get():
            if event.type == pygame.MOUSEMOTION:
                pointer = event.pos
            if event.type == pygame.QUIT:
                running = False
            elif (
                DEV_VIEW
                and event.type == pygame.KEYDOWN
                and event.key in (pygame.K_F2, pygame.K_F3)
            ):
                developer = toggle(developer, event.key)
            elif DEV_VIEW and event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
                developer, playing = None, None  # straight to the editor, from anywhere
                router.edit()
            elif DEV_VIEW and event.type == pygame.KEYDOWN and event.key == pygame.K_F4:
                print(json.dumps(router.board.to_dict(), separators=(",", ":")), flush=True)
            elif developer is not None:
                developer.handle_event(event)
            elif (
                (guide := tutorial()) is not None
                and router.screen in (Screen.EDIT, Screen.RUN)
                and (button := tutorial_press(guide, event, on_screen())) is not None
            ):
                if button == "next":
                    guide.next()  # and nothing else
                else:
                    guide.skip()
                editor().message = ""  # a refusal from the step before no longer holds
            elif router.screen in (Screen.TITLE, Screen.SPEC, Screen.END):
                shell_event(event)
            elif playing is not None:
                playing.handle_event(event)
            else:
                editor().handle_event(event)

        # What the scenes asked for this frame.
        if isinstance(developer, ArenaScene) and developer.request == "edit":
            developer = None
        if playing is not None:
            if playing.outcome is Outcome.WON and playing.ended_at is not None:
                router.mark_won()  # the next level opens in Chapters
                router.record(Score(playing.parts, playing.ended_at))  # once: a set
            playing.scores = router.scores
            if playing.request == "next" and router.has_next:
                router.next()
            elif playing.request == "next":
                router.finish()
            elif playing.request == "edit":
                router.edit()
            elif playing.request == "tutorial":  # Settings: Fear's tutorial again
                choose_place(0)
            if playing.chosen is not None:  # a place picked in Chapters
                choose_place(playing.chosen)
            if playing.request is not None or playing.chosen is not None:
                run_drawer, playing = playing.layout.drawer, None
        if router.screen is Screen.EDIT:
            asked, editor().request = editor().request, None
            if asked == "run":
                router.run()
                playing = play(run_drawer)
            elif asked == "tutorial":  # Settings: Fear's tutorial again
                choose_place(0)
            chosen, editor().chosen = editor().chosen, None
            if chosen is not None:
                choose_place(chosen)

        guide = tutorial()
        if guide is not None:  # on past what the player has done
            ended = playing.outcome if playing is not None else None
            guide.follow(Context(router.board, editor().tool, router.screen, ended))
            guide = tutorial()
        editor().ghosts = guide.ghosts if guide is not None else ()
        editor().chapters = router.rows()  # what Chapters shows
        if playing is not None:
            playing.chapters = router.rows()
        scene = on_screen()
        wanted = drawer_for(guide.step) if guide is not None else None
        here = (*DRAWERS[scene.layout.env], *FOOT)  # a step opens a drawer of the screen it is on
        if wanted in here and opened_for.get(router.index) != guide.index:
            opened_for[router.index] = guide.index  # once a step: then the player's to change
            if scene.layout.drawer is not wanted:
                scene.open_drawer(wanted)
        gate = None if guide is None else lambda action, g=guide: allows(g.step, action)
        editor().gate = gate  # only what the step asks goes through (D-048)
        editor().lit = panels(guide)  # the panels a step explains, titles lit (D-050)
        if playing is not None:
            playing.gate = gate
            playing.lit = panels(guide)
            if guide is not None and guide.explains:
                playing.clock.paused = True  # an explaining step holds the run still (D-050)

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
        else:
            editor().update()
            preview = editor().main is MainView.PREVIEW  # the Run preview, not the board (D-058)
            draw(screen, editor(), fonts, draw_preview if preview else None)
            if router.screen is Screen.TITLE:
                draw_title_card(screen, fonts)
            elif router.screen is Screen.SPEC:
                draw_level_card(screen, router, fonts)
        if developer is None and guide is not None and router.screen in (Screen.EDIT, Screen.RUN):
            draw_tutorial(screen, fonts, guide, *tutorial_box(guide, on_screen()), pointer)
        pygame.display.flip()
        clock.tick(FPS)

        await asyncio.sleep(0)  # pygbag: hand control back to the browser, every frame


asyncio.run(main())
# Nothing below this line (pygbag).
