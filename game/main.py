# /// script
# dependencies = [
#   "numpy",
# ]
# ///
"""Nektoids entry point.

Runs natively (`python game/main.py`) and in the browser (`pygbag game`).
For now it shows the wiring editor; the Run button comes with the swimmer's dynamics.
F2 switches to the developer view (D-016): the board as a running circuit, with equations.
F3 switches to the arena view (D-019, D-022): a swimmer running the board in a lit arena.
F4 prints the editor's board as one line of JSON (D-024): in the terminal natively, in pygbag's
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
from nektoids.editor.scene import EditorScene
from nektoids.editor.schematic import SchematicScene
from nektoids.editor.schematic_draw import draw_schematic
from nektoids.levels.arenas import arenas
from nektoids.levels.sandbox import free_board
from nektoids.levels.scenarios import Scenario, scenarios

FPS = 60
DEV_VIEW = True  # F2 opens the developer view, F3 the arena view, F4 prints the board
assert SIM_HZ == FPS * TICKS_PER_FRAME  # the developer view runs a whole number of ticks a frame

pygame.init()
screen = pygame.display.set_mode(SCREEN)
pygame.display.set_caption("Nektoids")
clock = pygame.time.Clock()
fonts = Fonts.load()
board = free_board()  # tutorial_board() for pre-placed, locked eyes and thrusters
scene = EditorScene(board, make_layout())


def open_developer_view() -> SchematicScene:
    """Your board first, then the examples."""
    return SchematicScene([Scenario("Your board", board), *scenarios()])


def toggle(
    open_view: SchematicScene | ArenaScene | None, key: int
) -> SchematicScene | ArenaScene | None:
    """F2 opens or closes the developer view, F3 the arena view; either replaces the other."""
    if key == pygame.K_F2:
        return None if isinstance(open_view, SchematicScene) else open_developer_view()
    return None if isinstance(open_view, ArenaScene) else ArenaScene(board, arenas())


async def main() -> None:
    running = True
    developer: SchematicScene | ArenaScene | None = None  # the F2 or F3 view, while open
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
                print(json.dumps(board.to_dict(), separators=(",", ":")), flush=True)
            elif developer is not None:
                developer.handle_event(event)
            else:
                scene.handle_event(event)

        if isinstance(developer, SchematicScene):
            developer.update()
            draw_schematic(screen, developer, fonts)
        elif isinstance(developer, ArenaScene):
            developer.update()
            draw_arena(screen, developer, fonts)
        else:
            scene.update()
            draw(screen, scene, fonts)
        pygame.display.flip()
        clock.tick(FPS)

        await asyncio.sleep(0)  # pygbag: hand control back to the browser, every frame


asyncio.run(main())
# Nothing below this line (pygbag).
