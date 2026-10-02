# /// script
# dependencies = [
#   "numpy",
# ]
# ///
"""Nektoids entry point.

Runs natively (`python game/main.py`) and in the browser (`pygbag game`).
It opens on the first level's board in the editor, under the title card. Run (Space) runs it in
its arena; Edit (Esc) comes back to the board as it was left; once a level is won, Next level
(Enter) opens the next one's board, and after the last, the end. Map (Tab) lists the chapter's
levels and the sandbox (`editor/router.py`, D-030, D-035). A level opened from the map or by Next
level comes up under its card, which says what it asks (D-042). A level's tutorial or hints show
over the editor and the run, and follow what the player does (`editor/tutorial.py`, D-039).
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
from nektoids.editor.arena_layout import ARENA_AREA
from nektoids.editor.devdrive import SIM_HZ, TICKS_PER_FRAME
from nektoids.editor.draw import Fonts, draw
from nektoids.editor.layout import SCREEN, contains, make_layout
from nektoids.editor.router import Router, Screen
from nektoids.editor.scene import EditorScene
from nektoids.editor.schematic import SchematicScene
from nektoids.editor.schematic_draw import draw_schematic
from nektoids.editor.shell import bottom_button, map_row_at
from nektoids.editor.shell_draw import draw_end, draw_level_card, draw_map, draw_title_card
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


def tutorial() -> Tutorial | None:
    """The open level's tutorial while a step remains, or None (the sandbox has none)."""
    data = None if router.in_sandbox else router.level.tutorial
    if data is not None and router.index not in tutorials:
        tutorials[router.index] = Tutorial.from_dict(data)
    guide = tutorials.get(router.index)
    return guide if guide is not None and guide.step is not None else None


def tutorial_box(guide: Tutorial) -> tuple:
    """Where the step's target and its box are, on the screen now open."""
    scene = editor()
    spots = target_spots(guide.step.show, router.screen, scene.layout, scene.view)
    done = guide.before  # the work just done, which the box keeps clear of too (D-048)
    before = (
        [] if done is None else target_rects(done.show, router.screen, scene.layout, scene.view)
    )
    beside = ARENA_AREA if router.screen is Screen.RUN else scene.layout.board_area
    return spots, box_rect([rect for rect, _ in spots], len(guide.step.say), beside, before)


def open_map() -> None:
    """To the map. A guided level starts afresh, its board, its undo history and its tutorial;
    the others keep their boards, and their hints start again (D-048, D-050)."""
    router.open_map()
    for index, level in enumerate(levels):
        if guided(level.tutorial):
            router.reset(index)
            editors.pop(index, None)
            tutorials.pop(index, None)
            opened_for.pop(index, None)
    for guide in tutorials.values():
        guide.restart()


def tutorial_press(guide: Tutorial, event: pygame.event.Event) -> str | None:
    """ "next" or "skip" if this key or click is the tutorial's (`tutorial.answer`), else None."""
    if event.type == pygame.KEYDOWN:
        return answer(guide, tutorial_box(guide)[1], None)
    if event.type == pygame.MOUSEBUTTONDOWN and 1 <= event.button <= 3:  # not the wheel
        return answer(guide, tutorial_box(guide)[1], event.pos)
    return None


def editor() -> EditorScene:
    """The open level's editor, made the first time the level opens."""
    if router.index not in editors:
        level = router.level
        caption = (f"{router.label}. {level.title}", level.spec)
        board = router.board
        handed_out = frozenset(kind for kind in Kind if board.total(kind) != 0)
        editors[router.index] = EditorScene(board, make_layout(kinds=handed_out), caption)
    return editors[router.index]


def play() -> ArenaScene:
    """The player's run of the open level, on its board as it stands."""
    after = "Next level" if router.has_next else "The end" if router.is_last else None
    return ArenaScene(
        router.board, [router.level], developer=False, next_label=after, label=router.label
    )


def shell_event(event: pygame.event.Event) -> None:
    """The cards, the map and the end take the event (D-035, D-042)."""
    clicked = event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
    escape = event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
    if router.screen in (Screen.TITLE, Screen.SPEC):
        if clicked or event.type == pygame.KEYDOWN:
            router.begin()
    elif router.screen is Screen.MAP:
        place = map_row_at(len(levels), event.pos) if clicked else None
        if place is not None and router.unlocked(place):
            router.open(place)
        elif escape or (clicked and contains(bottom_button(), event.pos)):
            router.edit()
    elif escape or (clicked and contains(bottom_button(), event.pos)):  # the end
        open_map()


def open_developer_view() -> SchematicScene:
    """Your board first, then the examples."""
    return SchematicScene([Scenario("Your board", router.board), *scenarios()])


def toggle(
    open_view: SchematicScene | ArenaScene | None, key: int
) -> SchematicScene | ArenaScene | None:
    """F2 opens or closes the developer view, F3 the arena view; either replaces the other."""
    if key == pygame.K_F2:
        return None if isinstance(open_view, SchematicScene) else open_developer_view()
    return None if isinstance(open_view, ArenaScene) else ArenaScene(router.board, levels)


async def main() -> None:
    running = True
    developer: SchematicScene | ArenaScene | None = None  # the F2 or F3 view, while open
    playing: ArenaScene | None = None  # the player's run, while it shows
    pointer = (0, 0)  # where the mouse is, for the map's and the end's buttons [px]
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
                and (button := tutorial_press(guide, event)) is not None
            ):
                if button == "next":
                    guide.next()  # and nothing else
                else:
                    guide.skip()
                editor().message = ""  # a refusal from the step before no longer holds
            elif router.screen in (Screen.TITLE, Screen.SPEC, Screen.MAP, Screen.END):
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
                router.mark_won()  # the next level opens on the map
                router.record(Score(playing.parts, playing.ended_at))  # once: a set
            playing.scores = router.scores
            if playing.request == "next" and router.has_next:
                router.next()
            elif playing.request == "next":
                router.finish()
            elif playing.request == "edit":
                router.edit()
            if playing.request is not None:
                playing = None
        if router.screen is Screen.EDIT:
            asked, editor().request = editor().request, None
            if asked == "run":
                router.run()
                playing = play()
            elif asked == "map":
                open_map()

        guide = tutorial()
        if guide is not None:  # on past what the player has done
            ended = playing.outcome if playing is not None else None
            guide.follow(Context(router.board, editor().tool, router.screen, ended))
            guide = tutorial()
        editor().ghosts = guide.ghosts if guide is not None else ()
        wanted = drawer_for(guide.step) if guide is not None else None
        if wanted is not None and opened_for.get(router.index) != guide.index:
            opened_for[router.index] = guide.index  # once a step: then the player's to change
            if editor().layout.drawer is not wanted:
                editor().open_drawer(wanted)
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
        elif router.screen is Screen.MAP:
            draw_map(screen, router, fonts, pointer)
        elif router.screen is Screen.END:
            draw_end(screen, fonts, pointer)
        elif playing is not None:
            playing.update()
            draw_arena(screen, playing, fonts)
        else:
            editor().update()
            draw(screen, editor(), fonts)
            if router.screen is Screen.TITLE:
                draw_title_card(screen, fonts)
            elif router.screen is Screen.SPEC:
                draw_level_card(screen, router, fonts)
        if developer is None and guide is not None and router.screen in (Screen.EDIT, Screen.RUN):
            draw_tutorial(screen, fonts, guide, *tutorial_box(guide), pointer)
        pygame.display.flip()
        clock.tick(FPS)

        await asyncio.sleep(0)  # pygbag: hand control back to the browser, every frame


asyncio.run(main())
# Nothing below this line (pygbag).
