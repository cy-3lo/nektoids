# /// script
# dependencies = [
#   "numpy",
# ]
# ///
"""Nektoids entry point.

Runs natively (`python game/main.py`) and in the browser (`pygbag game`).
For now it shows the wiring editor; the Run button and the simulation view come next.
"""

import asyncio

import pygame

from nektoids.editor.draw import Fonts, draw
from nektoids.editor.layout import SCREEN, make_layout
from nektoids.editor.scene import EditorScene
from nektoids.levels.sandbox import free_board

FPS = 60

pygame.init()
screen = pygame.display.set_mode(SCREEN)
pygame.display.set_caption("Nektoids")
clock = pygame.time.Clock()
fonts = Fonts.load()
board = free_board()  # tutorial_board() for pre-placed, locked eyes and thrusters
scene = EditorScene(board, make_layout())


async def main() -> None:
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                scene.handle_event(event)

        scene.update()
        draw(screen, scene, fonts)
        pygame.display.flip()
        clock.tick(FPS)

        await asyncio.sleep(0)  # pygbag: hand control back to the browser, every frame


asyncio.run(main())
# Nothing below this line (pygbag).
