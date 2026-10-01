# /// script
# dependencies = [
#   "numpy",
# ]
# ///
"""Nektoids entry point.

Runs natively (`python game/main.py`) and in the browser (`pygbag game`).
It opens on the first level's board in the editor. Run (Space) runs it in its arena; Edit (Esc)
comes back to the board as it was left; once a level is won, Next level (Enter) opens the next
one's board (`editor/router.py`).
Developer tools, while DEV_VIEW is on:
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
from nektoids.editor.layout import SCREEN, make_layout
from nektoids.editor.router import Router
from nektoids.editor.scene import EditorScene
from nektoids.editor.schematic import SchematicScene
from nektoids.editor.schematic_draw import draw_schematic
from nektoids.levels.arenas import arenas
from nektoids.levels.scenarios import Scenario, scenarios

FPS = 60
DEV_VIEW = True  # F2 opens the developer view, F3 the arena view, F4 prints the board
assert SIM_HZ == FPS * TICKS_PER_FRAME  # the developer view runs a whole number of ticks a frame

pygame.init()
screen = pygame.display.set_mode(SCREEN)
pygame.display.set_caption("Nektoids")
clock = pygame.time.Clock()
fonts = Fonts.load()
levels = arenas()  # read from their files once, at startup (web.md: no file I/O in the loop)
router = Router(levels)
editors: dict[int, EditorScene] = {}  # each level's editor, and its undo history with it


def editor() -> EditorScene:
    """The current level's editor, made the first time the level opens."""
    if router.index not in editors:
        level = router.level
        caption = (f"{router.label}. {level.title}", level.spec)
        editors[router.index] = EditorScene(router.board, make_layout(), caption)
    return editors[router.index]


def play() -> ArenaScene:
    """The player's run of the current level, on its board as it stands."""
    return ArenaScene(
        router.board, [router.level], developer=False, has_next=router.has_next, label=router.label
    )


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
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif (
                DEV_VIEW
                and event.type == pygame.KEYDOWN
                and event.key in (pygame.K_F2, pygame.K_F3)
            ):
                developer = toggle(developer, event.key)
            elif DEV_VIEW and event.type == pygame.KEYDOWN and event.key == pygame.K_F4:
                print(json.dumps(router.board.to_dict(), separators=(",", ":")), flush=True)
            elif developer is not None:
                developer.handle_event(event)
            elif playing is not None:
                playing.handle_event(event)
            else:
                editor().handle_event(event)

        # What the scenes asked for this frame.
        if isinstance(developer, ArenaScene) and developer.request == "edit":
            developer = None
        if playing is not None and playing.request is not None:
            if playing.request == "next":
                router.next()
            else:
                router.edit()
            playing = None
        if editor().request == "run":
            editor().request = None
            router.run()
            playing = play()

        if isinstance(developer, SchematicScene):
            developer.update()
            draw_schematic(screen, developer, fonts)
        elif isinstance(developer, ArenaScene):
            developer.update()
            draw_arena(screen, developer, fonts)
        elif playing is not None:
            playing.update()
            draw_arena(screen, playing, fonts)
        else:
            editor().update()
            draw(screen, editor(), fonts)
        pygame.display.flip()
        clock.tick(FPS)

        await asyncio.sleep(0)  # pygbag: hand control back to the browser, every frame


asyncio.run(main())
# Nothing below this line (pygbag).
