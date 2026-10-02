"""Every colour the game draws, named by its job, and the palette they all come from (D-047).

A palette is ten neutrals and two accents, built in OKLCH, where lightness L, chroma C and hue h
are separate. The neutrals sit at fixed lightness steps, deep to bright, all of one hue; the tint
is `tint_chroma` at the dark end and fades to a third of it at the bright end. Each accent comes
in three levels: dark for fills under light text, mid for marks on parts, bright for outlines and
highlights over dark ground. `sense` is the eyes' and the tutorial's, `act` the thrusters' and
the swimmer's. Change `PALETTE` and the whole game follows: no other module holds a colour.
Pure Python, no pygame.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

Colour = tuple[int, int, int]

NEUTRALS = ("deep", "base", "surface", "raised", "line", "muted", "dim", "parts", "text", "bright")
# OKLab lightness of each neutral: the greys the game was drawn in before D-047, measured, so
# every contrast between them stays as it was.
NEUTRAL_L = (0.156, 0.193, 0.233, 0.295, 0.343, 0.447, 0.622, 0.777, 0.901, 0.949)
BRIGHT_END_TINT = 1 / 3  # the bright end keeps this much of the tint's chroma
ACCENT_L = (0.43, 0.68, 0.85)  # dark, mid, bright
ACCENT_C = (0.085, 0.14, 0.11)  # their chroma, before the gamut trims it
RED_HUE, AMBER_HUE = 22.0, 77.0  # the signals' hues [degrees], as before D-047


@dataclass(frozen=True)
class Accent:
    dark: Colour  # fills, under light text or icons
    mid: Colour  # marks on parts, half over the board
    bright: Colour  # outlines and highlights over dark ground


@dataclass(frozen=True)
class Palette:
    deep: Colour  # outside the zone; shadow in the arena
    base: Colour  # behind everything
    surface: Colour  # panels, the zone's cells
    raised: Colour  # buttons
    line: Colour  # the grid, rules, outlines
    muted: Colour  # what is disabled or barely there
    dim: Colour  # secondary text, wires, rings
    parts: Colour  # every part's fill
    text: Colour
    bright: Colour  # the light, beads at full rate
    sense: Accent  # the eyes' faces, the tool in hand, the tutorial's highlight
    act: Accent  # the thrusters' backs, the swimmer
    refused: Colour  # a refusal, a lost run
    refused_dark: Colour  # the flash on a refused move
    warn: Colour  # the developer view's warnings


def oklch(lightness: float, chroma: float, hue: float) -> Colour:
    """sRGB, 0-255, of an OKLCH colour (Ottosson 2020), its chroma trimmed until it fits."""
    for _ in range(80):
        a = chroma * math.cos(math.radians(hue))
        b = chroma * math.sin(math.radians(hue))
        linear = _oklab_to_linear(lightness, a, b)
        if all(-1e-9 <= v <= 1 + 1e-9 for v in linear):
            break
        chroma *= 0.95
    return tuple(round(255 * _encode(min(1.0, max(0.0, v)))) for v in linear)


def mix(a: Colour, b: Colour, t: float) -> Colour:
    """`t` of the way from `a` to `b`."""
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b, strict=True))


def accent(hue: float) -> Accent:
    return Accent(*(oklch(L, C, hue) for L, C in zip(ACCENT_L, ACCENT_C, strict=True)))


def make_palette(tint_hue: float, tint_chroma: float, sense_hue: float, act_hue: float) -> Palette:
    """Ten neutrals of hue `tint_hue` [degrees], tinted `tint_chroma` at the dark end, and the
    accents `sense` and `act` of hues `sense_hue` and `act_hue` [degrees]."""
    span = NEUTRAL_L[-1] - NEUTRAL_L[0]
    neutrals = {
        name: oklch(
            L, tint_chroma * (1 - (1 - BRIGHT_END_TINT) * (L - NEUTRAL_L[0]) / span), tint_hue
        )
        for name, L in zip(NEUTRALS, NEUTRAL_L, strict=True)
    }
    return Palette(
        **neutrals,
        sense=accent(sense_hue),
        act=accent(act_hue),
        refused=oklch(0.70, 0.16, RED_HUE),
        refused_dark=oklch(0.47, 0.13, RED_HUE),
        warn=oklch(0.82, 0.12, AMBER_HUE),
    )


def _oklab_to_linear(lightness: float, a: float, b: float) -> tuple[float, float, float]:
    long_ = lightness + 0.3963377774 * a + 0.2158037573 * b
    medium_ = lightness - 0.1055613458 * a - 0.0638541728 * b
    short_ = lightness - 0.0894841775 * a - 1.2914855480 * b
    lo, me, sh = long_**3, medium_**3, short_**3  # the cone responses, LMS
    return (
        4.0767416621 * lo - 3.3077115913 * me + 0.2309699292 * sh,
        -1.2684380046 * lo + 2.6097574011 * me - 0.3413193965 * sh,
        -0.0041960863 * lo - 0.7034186147 * me + 1.7076147010 * sh,
    )


def _encode(v: float) -> float:
    """Linear light to the sRGB curve."""
    return 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055


# The game's palette: Forest, violet and sky. This line alone changes every colour.
PALETTE = make_palette(tint_hue=150.0, tint_chroma=0.028, sense_hue=315.0, act_hue=235.0)
P = PALETTE

# Every view
BACKGROUND = P.base
DARK = P.base  # icons on parts, text on bright buttons
PANEL = P.surface
TOOLTIP_BG = mix(P.surface, P.raised, 0.5)
BUTTON = P.raised
HOVER = mix(P.raised, P.line, 0.5)
ACTIVE = P.sense.dark  # the tool in hand, the menu row picked, a toggle that is on
RULE = P.line  # separators between columns and between sets of buttons
SWATCH_OFF = P.raised  # colour picker, not active yet
TEXT = P.text
DIM_TEXT = P.dim
GREYED = P.muted
REFUSED = P.refused
FLASH = P.refused_dark
VEIL = (0, 0, 0, 150)  # over a level's board under its card; over all but a tutorial's targets
CLEAR = (0, 0, 0, 0)  # a hole in a veil
LIT = P.sense.bright  # a tutorial's target outlined, and its box while it leads

# The board
ZONE = P.surface  # cells of the level's zone
OUTSIDE = P.deep  # cells outside it
OUTSIDE_LINE = mix(P.deep, P.line, 0.3)
GRID_LINE = P.line
BODY_OUTLINE = P.line  # the swimmer's symbol behind the board: which way is forward
COMPONENT = P.parts
LOCK_RING = mix(P.parts, P.bright, 0.4)
EYE_FACE = P.sense.mid  # the flat face an eye reads the light through (D-020)
THRUSTER_BACK = P.act.mid  # the back a thruster pushes from
WIRE = mix(P.dim, P.parts, 0.4)
GHOST = P.muted  # where a wire would run
GHOST_OK = P.bright  # ... and it may connect there
GHOST_FILL = P.raised  # a tutorial's ghost part, under the real one
DOOMED = P.muted  # what a Delete click would remove

# The circuit: rates and beads, in the developer view and the run's column
IDLE = mix(P.muted, P.dim, 0.5)  # a part at rate 0
FULL = P.bright  # a part at RATE_MAX
WIRE_OFF = P.line  # a wire that carries nothing
BEAD = P.bright  # a bead on a wire at RATE_MAX
BEAD_OFF = P.muted  # ... and on a wire that barely carries anything
VALUE = P.text  # the live numbers in the developer view's panel
WARN = P.warn

# The arena
SHADOW = P.deep  # the open plane, and a reading of 0 on the light map
LIGHT = P.bright  # a light, and a reading of RATE_MAX
RAY = mix(P.deep, P.line, 0.45)  # every ray, whatever its light
OBSTACLE = mix(P.line, P.muted, 0.5)
BODY = P.act.bright  # the selected swimmer
BODY_UNSELECTED = P.dim
RING = P.dim  # a ring to leave or to stay in, until that is done
RUN_SO_FAR = mix(P.dim, P.line, 0.3)  # the timeline's part already run, ahead of the playhead
EYE_SHADES = (P.bright, P.dim)  # one per eye in the polar plot, in turn
