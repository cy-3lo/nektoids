"""The Board's buttons as keys (D-401): a hex the size of a cell, a bevel 3 px wide lit from the
top left, a shadow 2 px right and 3 px down; pressed in, the light falls on the far sides and
the shadow goes. `draw.py` puts the icon or the part on it, and the tags. The Editor's keys are
squares, lit and shadowed alike (D-410)."""

from __future__ import annotations

import math

import pygame

from nektoids.editor.palette import CLEAR, KEY_SHADOW, mix

BEVEL = 3  # [px]
SHADOW_AT = (2, 3)  # [px]
_layers: dict[tuple[int, int], pygame.Surface] = {}  # the shadows' layer, one per screen size


def hexagon(centre: tuple[float, float], radius: float) -> list[tuple[float, float]]:
    """A pointy-top hex, as the board's cells."""
    x, y = centre
    return [
        (
            x + radius * math.cos(math.radians(30 + 60 * k)),
            y + radius * math.sin(math.radians(30 + 60 * k)),
        )
        for k in range(6)
    ]


def shadows(screen: pygame.Surface, centres: list[tuple[float, float]], size: float) -> None:
    """The buttons' shadows, under them all, so that none falls on a neighbour."""
    layer = _layers.get(screen.get_size())
    if layer is None:
        layer = _layers[screen.get_size()] = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    layer.fill(CLEAR)
    for x, y in centres:
        pygame.draw.polygon(layer, KEY_SHADOW, hexagon((x + SHADOW_AT[0], y + SHADOW_AT[1]), size))
    screen.blit(layer, (0, 0))


def bevel(screen: pygame.Surface, centre, size: float, light, dark) -> None:
    """The rim, BEVEL px wide, each side shaded by how it faces a light at the top left."""
    outer = hexagon(centre, size)
    inner = hexagon(centre, size - BEVEL / math.cos(math.radians(30)))
    for k in range(6):
        facing = math.radians(60 + 60 * k)  # the side between corners k and k + 1, on screen
        towards = (-math.cos(facing) - math.sin(facing)) / math.sqrt(2)  # 1: facing the light
        quad = [outer[k], outer[(k + 1) % 6], inner[(k + 1) % 6], inner[k]]
        pygame.draw.polygon(screen, mix(dark, light, (towards + 1) / 2), quad)


def tag(screen: pygame.Surface, centre, text: pygame.Surface, fill, edge=None) -> None:
    """A label on a rounded tag centred on `centre`, at least as wide as it is tall."""
    rect = text.get_rect(center=centre).inflate(10, 2)
    rect.width = max(rect.width, rect.height + 4)
    rect.center = (round(centre[0]), round(centre[1]))
    pygame.draw.rect(screen, fill, rect, border_radius=5)
    if edge is not None:
        pygame.draw.rect(screen, edge, rect, 1, border_radius=5)
    screen.blit(text, text.get_rect(center=rect.center))


def square_shadows(screen: pygame.Surface, rects: list) -> None:
    """The square keys' shadows, under them all, as the hexes' (D-410)."""
    layer = _layers.get(screen.get_size())
    if layer is None:
        layer = _layers[screen.get_size()] = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    layer.fill(CLEAR)
    for x, y, w, h in rects:
        pygame.draw.rect(layer, KEY_SHADOW, (x + SHADOW_AT[0], y + SHADOW_AT[1], w, h))
    screen.blit(layer, (0, 0))


def square_bevel(screen: pygame.Surface, rect, light, dark) -> None:
    """A square key's rim, BEVEL px wide: the top lit, the bottom dark, the sides between."""
    r, b = pygame.Rect(rect), BEVEL
    inner = r.inflate(-2 * b, -2 * b)
    sides = (
        ([r.topleft, r.topright, inner.topright, inner.topleft], light),
        ([r.topleft, inner.topleft, inner.bottomleft, r.bottomleft], mix(light, dark, 0.35)),
        ([r.topright, r.bottomright, inner.bottomright, inner.topright], mix(light, dark, 0.65)),
        ([r.bottomleft, inner.bottomleft, inner.bottomright, r.bottomright], dark),
    )
    for quad, colour in sides:
        pygame.draw.polygon(screen, colour, quad)
