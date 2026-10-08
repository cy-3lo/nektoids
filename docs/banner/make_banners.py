"""The banners, drawn by the game's own code (todo §14): GitHub's social preview and README
banner, and itch.io's cover and page banner. Each has the title, the studio and the phrase, the
swimmer under them at the run's scale, its velocity and spin shown, and its board at work on the
right, at the same moment of the same run, on its body, its streams in the run's colours. The
light the swimmer swims to is never seen: its rays fade out before it.

    PYTHONPATH=game python docs/banner/make_banners.py            # writes docs/banner/*.png
    PYTHONPATH=game python docs/banner/make_banners.py --guides   # ... the safe zone outlined

Run it again when the game's look changes. Not part of the game.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["SDL_VIDEODRIVER"] = "dummy"  # headless
import numpy as np  # noqa: E402
import pygame  # noqa: E402

pygame.init()
from nektoids.editor.layout import SCREEN  # noqa: E402

pygame.display.set_mode(SCREEN)  # the fonts and icons need a display
from nektoids.editor import arena_draw, streams  # noqa: E402
from nektoids.editor.arena import ArenaScene  # noqa: E402
from nektoids.editor.arena_view import ArenaView  # noqa: E402
from nektoids.editor.circuit import Circuit  # noqa: E402
from nektoids.editor.devdrive import DT, TICKS_PER_FRAME  # noqa: E402
from nektoids.editor.draw import TEXT_FONT_FILE, Fonts, draw_body, draw_circuit  # noqa: E402
from nektoids.editor.palette import DIM_TEXT, FLAME, INTAKE, REFUSED, SHADOW, TEXT  # noqa: E402
from nektoids.editor.settings import Settings  # noqa: E402
from nektoids.graph.board import Board, Kind  # noqa: E402
from nektoids.graph.hexgrid import NE, SE, E, hex_disc  # noqa: E402
from nektoids.levels.level import Item, ItemKind, Level  # noqa: E402

HERE = Path(__file__).parent
FORMATS = {  # size, safe border, title size, words' size, swimmer at, rays gone by, diagram
    "github": ((1280, 640), 40, 132, 20, (300, 450), 500, (660, 40, 580, 560)),
    "itch-cover": ((630, 500), 24, 92, 15, (150, 400), 330, (300, 190, 310, 290)),
    "itch-banner": ((960, 300), 20, 104, 15, (330, 240), 540, (640, 10, 300, 280)),
}
SCALE = 16.0  # the run's opening scale [px / u]
SECONDS = 1.0  # the moment of the run shown
LIGHT = (22.0, 6.0, 8.0)  # x, y [u], power: ahead and to the left, so that both eyes read
FADE = 220.0  # the rays fade out over this width [px]
REACH = 1.8  # the diagram's streams, as a part's entry draws them [hex sizes]
PHRASE = ("You don't control the swimmer.", "You wire its control board, press run, and watch.")


class _Shot(ArenaScene):
    """A run drawn on a whole image, not in the run's area."""

    size = (0, 0)

    @property
    def arena_area(self):
        return (0, 0, *self.size)


def board() -> Board:
    """Two eyes ahead, two thrusters at the tail, wired without crossing: the left eye doubled to
    the left thruster; the right eye taken from a Source to the right thruster."""
    b = Board(hex_disc(2))
    eye_left = b.place(Kind.EYE, (2, -2), facing=NE)
    eye_right = b.place(Kind.EYE, (0, 2), facing=SE)
    thr_left = b.place(Kind.THRUSTER, (-1, -1), facing=E)
    thr_right = b.place(Kind.THRUSTER, (-2, 1), facing=E)
    source = b.place(Kind.SOURCE, (-1, 2))
    diff = b.place(Kind.DIFFERENCE, (-1, 1))
    double = b.place(Kind.DOUBLE, (1, -1))
    wires = ((eye_left, double), (double, thr_left), (source, diff), (eye_right, diff))
    for a, c in (*wires, (diff, thr_right)):
        b.connect(a.id, c.id)
    return b


def run(b: Board, size: tuple[int, int]) -> _Shot:
    """The board run from the origin, heading along x, to SECONDS."""
    plane = {"zone": 19, "stock": {}, "parts": [], "wires": []}
    level = Level(
        "Banner", "-", (0.0, 0.0, 0.0), (Item(ItemKind.LIGHT, LIGHT[:2], LIGHT[2]),), plane, 60.0
    )
    _Shot.size = size
    shot = _Shot(b, [level], developer=False, settings=Settings(), drawer=None)
    shot.seek(SECONDS)
    while shot.seek_to is not None:
        shot.update()
    return shot


def banner(name: str, fonts: Fonts, guides: bool) -> pygame.Surface:
    (w, h), safe, title_size, words_size, swimmer_at, gone_by, diagram = FORMATS[name]
    b = board()
    shot = run(b, (w, h))
    x, y = shot.pos[0]
    shot.view = ArenaView(SCALE, (swimmer_at[0] - SCALE * x, swimmer_at[1] + SCALE * y))

    plane = pygame.Surface((w, h))  # the rays, fading out to the right
    arena_draw._draw_field(plane, shot, fonts)
    ground = np.array(SHADOW, dtype=float)
    pixels = pygame.surfarray.array3d(plane).astype(float)
    fade = np.clip((gone_by - np.arange(w)[:, None, None]) / FADE, 0.0, 1.0) ** 1.5
    image = pygame.surfarray.make_surface((ground + (pixels - ground) * fade).astype(np.uint8))
    arena_draw._draw_swimmers(image, shot)

    title = pygame.font.Font(None, title_size).render("NEKTOIDS", True, TEXT)
    image.blit(title, (safe + 24 * title_size // 132, safe + 20 * title_size // 132))
    left = safe + 30 * title_size // 132
    top = safe + 20 * title_size // 132 + title.get_height()
    words = pygame.font.Font(TEXT_FONT_FILE, words_size)
    image.blit(words.render("a game by Cy-3LO", True, DIM_TEXT), (left, top + 6))
    for k, line in enumerate(PHRASE):
        image.blit(words.render(line, True, TEXT), (left, top + 2.5 * words_size * (1 + 0.6 * k)))

    area = pygame.Rect(diagram)  # the board at work, at the swimmer's moment
    circuit = Circuit(b, tuple(area), 1.7, body=True)
    for _ in range(240):  # the beads spread along the wires at these rates
        circuit.advance(shot.y, DT)
    draw_body(image, circuit.board.cells, circuit.view.size, circuit.view.origin)
    frame = shot.clock.tick // TICKS_PER_FRAME
    speck = max(3, round(6 * area.height / 560))  # as large as the diagram is
    for f in range(frame - 2, frame + 1):  # three frames: the streams read on a still
        light = streams.light(circuit, shot.y, f, REACH, 0)
        flames = streams.flames(circuit, shot.y, f, REACH, 0)
        for points, colour in ((light, INTAKE), (flames, FLAME)):
            for sx, sy in points:
                image.fill(colour, (sx // speck * speck, sy // speck * speck, speck, speck))
    draw_circuit(image, circuit, shot.y, fonts, plain=True, meters=False)

    if guides:
        pygame.draw.rect(image, REFUSED, (safe, safe, w - 2 * safe, h - 2 * safe), 1)
    return image


def main() -> None:
    guides = "--guides" in sys.argv
    fonts = Fonts.load()
    for name in FORMATS:
        path = HERE / f"{name}{'-guides' if guides else ''}.png"
        pygame.image.save(banner(name, fonts, guides), path)
        print(path)


if __name__ == "__main__":
    main()
