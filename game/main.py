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
levels and the sandbox (`editor/router.py`, D-030, D-035).
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
from nektoids.editor.layout import SCREEN, contains, make_layout
from nektoids.editor.router import Router, Screen
from nektoids.editor.scene import EditorScene
from nektoids.editor.schematic import SchematicScene
from nektoids.editor.schematic_draw import draw_schematic
from nektoids.editor.shell import bottom_button, map_row_at
from nektoids.editor.shell_draw import draw_end, draw_map, draw_title_card
from nektoids.levels.arenas import arenas, sandbox
from nektoids.levels.objectives import Outcome
from nektoids.levels.scenarios import Scenario, scenarios

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


def editor() -> EditorScene:
    """The open level's editor, made the first time the level opens."""
    if router.index not in editors:
        level = router.level
        caption = (f"{router.label}. {level.title}", level.spec)
        editors[router.index] = EditorScene(router.board, make_layout(), caption)
    return editors[router.index]


def play() -> ArenaScene:
    """The player's run of the open level, on its board as it stands."""
    after = "Next level" if router.has_next else "The end" if router.is_last else None
    return ArenaScene(
        router.board, [router.level], developer=False, next_label=after, label=router.label
    )


def shell_event(event: pygame.event.Event) -> None:
    """The title card, the map and the end take the event (D-035)."""
    clicked = event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
    escape = event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
    if router.screen is Screen.TITLE:
        if clicked or event.type == pygame.KEYDOWN:
            router.begin()
    elif router.screen is Screen.MAP:
        place = map_row_at(len(levels), event.pos) if clicked else None
        if place is not None and router.unlocked(place):
            router.open(place)
        elif escape or (clicked and contains(bottom_button(), event.pos)):
            router.edit()
    elif escape or (clicked and contains(bottom_button(), event.pos)):  # the end
        router.open_map()


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
            elif router.screen in (Screen.TITLE, Screen.MAP, Screen.END):
                shell_event(event)
            elif playing is not None:
                playing.handle_event(event)
            else:
                editor().handle_event(event)

        # What the scenes asked for this frame.
        if isinstance(developer, ArenaScene) and developer.request == "edit":
            developer = None
        if playing is not None:
            if playing.outcome is Outcome.WON:
                router.mark_won()  # the next level opens on the map
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
                router.open_map()

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
        pygame.display.flip()
        clock.tick(FPS)

        await asyncio.sleep(0)  # pygbag: hand control back to the browser, every frame


asyncio.run(main())
# Nothing below this line (pygbag).
