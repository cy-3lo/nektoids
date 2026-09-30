# /// script
# dependencies = [
#   "numpy",
# ]
# ///
"""Nektoids entry point.

Runs natively (`python game/main.py`) and in the browser (`pygbag game`).
For now it shows the wiring editor; the Run button and the simulation view come next.
F2 switches to the developer view (D-016): the board as a running circuit, with equations.
"""

import asyncio

import pygame

from nektoids.editor.devdrive import SIM_HZ, TICKS_PER_FRAME
from nektoids.editor.draw import Fonts, draw
from nektoids.editor.layout import SCREEN, make_layout
from nektoids.editor.scene import EditorScene
from nektoids.editor.schematic import SchematicScene
from nektoids.editor.schematic_draw import draw_schematic
from nektoids.levels.sandbox import free_board
from nektoids.levels.scenarios import scenarios

FPS = 60
DEV_VIEW = True  # F2 opens the developer view; False hides it
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
    return SchematicScene([("Your board", board), *((s.title, s.board) for s in scenarios())])


async def main() -> None:
    running = True
    developer: SchematicScene | None = None  # the developer view, while F2 has it open
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif DEV_VIEW and event.type == pygame.KEYDOWN and event.key == pygame.K_F2:
                developer = None if developer is not None else open_developer_view()
            elif developer is not None:
                developer.handle_event(event)
            else:
                scene.handle_event(event)

        if developer is not None:
            developer.update()
            draw_schematic(screen, developer, fonts)
        else:
            scene.update()
            draw(screen, scene, fonts)
        pygame.display.flip()
        clock.tick(FPS)

        await asyncio.sleep(0)  # pygbag: hand control back to the browser, every frame


asyncio.run(main())
# Nothing below this line (pygbag).
