# /// script
# dependencies = [
#   "numpy",
# ]
# ///
"""Nektoids entry point.

Runs natively (`python game/main.py`) and in the browser (`pygbag game`).
For now it only proves the pipeline end to end: numpy + pygame-ce, native and WASM.
"""

import asyncio

import numpy as np
import pygame

from nektoids.sim.world import make_world, step

WIDTH, HEIGHT = 960, 640
FPS = 60
# The simulation advances a fixed number of steps per frame, never by wall-clock time.
STEPS_PER_FRAME = 2
DT = 1.0 / (FPS * STEPS_PER_FRAME)  # [s]
AGENT_RADIUS = 6  # [px]
BACKGROUND = (18, 20, 28)
AGENT_COLOUR = (240, 200, 90)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Nektoids")
clock = pygame.time.Clock()
world = make_world(seed=0, n_agents=1, width=WIDTH, height=HEIGHT)
no_force = np.zeros_like(world.pos)


async def main() -> None:
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        for _ in range(STEPS_PER_FRAME):
            step(world, no_force, DT)

        screen.fill(BACKGROUND)
        for x, y in world.pos:
            pygame.draw.circle(screen, AGENT_COLOUR, (int(x), int(y)), AGENT_RADIUS)
        pygame.display.flip()
        clock.tick(FPS)

        await asyncio.sleep(0)  # pygbag: hand control back to the browser, every frame


asyncio.run(main())
# Nothing below this line (pygbag).
