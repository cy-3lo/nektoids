"""Every colour the game draws, named by its job, and the palette they all come from (D-047, D-049).

A palette is ten neutrals and two accents, built in OKLCH, where lightness L, chroma C and hue h
are separate. The neutrals sit at fixed lightness steps, deep to bright. Their tint is
`tint_chroma` at the dark end and fades to a third of it at the bright end; its hue is
`tint_hue` in the darks and, if `light_hue` is given, turns to it in the lights, along the
shorter way round, between LIGHT_TURN's two lightnesses. Each accent comes in three levels: dark
for fills under light text, mid for marks on parts, bright for outlines and highlights over dark
ground. `accent1` marks what the player works with: the faces of eyes and thrusters, the tool in
hand, the tutorial's highlight, the swimmer in the run. `accent2` marks what goes wrong: a
refusal, a lost run, a warning; and, darker, the thrust: a thruster's flames (D-076). Change
`PALETTE` and the whole game follows: no other module holds a colour. Pure Python, no pygame.
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
LIGHT_TURN = (0.30, 0.75)  # the tint's hue turns from `tint_hue` to `light_hue` between these L
ACCENT_L = (0.43, 0.68, 0.85)  # dark, mid, bright
ACCENT_C = (0.085, 0.14, 0.11)  # their chroma, before the gamut trims it


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
    accent1: (
        Accent  # what the player works with: faces, the tool in hand, the tutorial, the swimmer
    )
    accent2: Accent  # what goes wrong: a refusal, a lost run, a warning


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


def tint(
    lightness: float, tint_hue: float, tint_chroma: float, light_hue: float | None = None
) -> tuple[float, float]:
    """The chroma and hue [degrees] of the neutral at `lightness`: the chroma fading from the dark
    end to the bright, the hue turning from `tint_hue` to `light_hue` the shorter way round."""
    span = NEUTRAL_L[-1] - NEUTRAL_L[0]
    chroma = tint_chroma * (1 - (1 - BRIGHT_END_TINT) * (lightness - NEUTRAL_L[0]) / span)
    if light_hue is None:
        return chroma, tint_hue % 360
    low, high = LIGHT_TURN
    t = min(1.0, max(0.0, (lightness - low) / (high - low)))
    turn = t * t * (3 - 2 * t)  # smoothstep: no kink where the turn starts or ends
    way = (light_hue - tint_hue + 180) % 360 - 180  # the shorter way, signed [degrees]
    return chroma, (tint_hue + turn * way) % 360


def make_palette(
    tint_hue: float,
    tint_chroma: float,
    accent1_hue: float,
    accent2_hue: float,
    light_hue: float | None = None,
) -> Palette:
    """Ten neutrals tinted `tint_hue` [degrees], `tint_chroma` at the dark end, turning to
    `light_hue` in the lights if given; and the two accents, of hues `accent1_hue` and
    `accent2_hue` [degrees]."""
    neutrals = {
        name: oklch(L, *tint(L, tint_hue, tint_chroma, light_hue))
        for name, L in zip(NEUTRALS, NEUTRAL_L, strict=True)
    }
    return Palette(**neutrals, accent1=accent(accent1_hue), accent2=accent(accent2_hue))


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


# The game's palette: Slate and evergreen, with a red. This line alone changes every colour.
PALETTE = make_palette(
    tint_hue=273.0, tint_chroma=0.022, accent1_hue=187.0, accent2_hue=25.0, light_hue=85.0
)
P = PALETTE

# Every view
BACKGROUND = P.base
BAR = P.deep  # the activity bar, the status line (D-051)
TAB_STRIP = P.surface  # the strip of tabs, the shut ones on it: a shade over the open one's
DARK = P.base  # icons on parts, text on bright buttons
PANEL = P.surface
TOOLTIP_BG = mix(P.surface, P.raised, 0.5)
BUTTON = P.raised
HOVER = mix(P.raised, P.line, 0.5)
ACTIVE = P.accent1.dark  # the tool in hand, the menu row picked, a toggle that is on
# The Board's buttons, keys in a bevel lit from the top left (D-401)
KEY_LIGHT = P.dim  # a button's bevel, the sides facing the light
KEY_DARK = P.deep  # ... the sides away from it
KEY_GREYED = mix(P.deep, P.dim, 0.4)  # a greyed button's light sides: the bevel dimmed
KEY_SHADOW = (0, 0, 0, 150)  # under a button, 2 px right and 3 px down
GREYED_FACE = P.accent1.dark  # an eye's face, a thruster's back, on a greyed button
RULE = P.line  # separators between columns and between sets of buttons
SCROLL_THUMB = P.dim  # a scroll bar's thumb, over its track in RULE (D-069)
SWATCH_OFF = P.raised  # colour picker, not active yet
TEXT = P.text
DIM_TEXT = P.dim
HEADING = mix(P.dim, P.text, 0.5)  # a drawer's headings, between its title and rows (D-420)
GREYED = P.muted
TO_BEAT = P.muted  # the score of a level's proof, a cross in Score (D-330)
PLOT_FRAME = mix(P.line, P.dim, 0.75)  # Score's box and ticks, a shade over a rule (D-340)
PLOT_TEXT = mix(P.dim, P.text, 0.6)  # ... its numbers and its axes' names
REFUSED = P.accent2.bright  # a refusal, a lost run, a run out of time
FLASH = P.accent2.dark  # the flash on a refused move
VEIL = (0, 0, 0, 150)  # over a level's board under its card; over all but a tutorial's targets
CLEAR = (0, 0, 0, 0)  # a hole in a veil
LIT = P.accent1.bright  # a tutorial's target, drawn in it, and its box while it leads
PULSE_FRAMES = 72  # a tutorial's target pulses, bright to medium and back: 1.2 s (D-337)
PULSE_FILL_TOP = 0.5  # a lit button's fill: accent1's dark at most so far to its medium, its
# white icon 3.3:1 over it at the brightest, 3:1 the least for a graphic (D-350)

# The board
ZONE = P.surface  # cells of the level's zone
OUTSIDE = P.deep  # cells outside it
OUTSIDE_LINE = mix(P.deep, P.line, 0.3)
GRID_LINE = mix(
    P.line, P.dim, 0.5
)  # the zone's cells: lighter than the buttons' ground, not to mix with them
BODY_OUTLINE = P.raised  # the swimmer's symbol behind the board, a shade under the grid
COMPONENT = P.parts
LOCK_RING = mix(P.parts, P.bright, 0.4)
PIN_RING = P.accent1.mid  # a part the player locked: theirs, in the accent (D-406)
EYE_FACE = P.accent1.mid  # the flat face an eye reads the light through (D-020)
THRUSTER_BACK = P.accent1.mid  # the back a thruster pushes from
WIRE = mix(P.dim, P.parts, 0.4)
WIRING = P.bright  # the wire being drawn, where it would run: white, apart from the shadows
WIRING_OK = P.accent1.bright  # ... and it may connect there (D-087)
GHOST_OK = P.bright  # a tutorial's part outlined where it should face
FOCUS_TINT = 0.5  # a cell a tutorial's step acts on: so much of its pulse over the zone (D-337)
GHOST_FILL = P.line  # a tutorial's ghost part or wire, a shadow: darker than a wire, no outline
DOOMED = P.muted  # what a Delete click would remove
ICON_EDGE = mix(P.muted, P.dim, 0.5)  # the edge of an icon of the Wheel, and of a pile's (D-068)

# The circuit: rates and beads, in the developer view and the run's column
FULL = P.bright  # a rate at RATE_MAX: the developer's sliders, the timeline
METER = P.accent1.mid  # a part's level meter in a circuit: the colour of its face (D-052)
BEAD = P.bright  # a bead on a wire, whatever it carries: its spacing shows the rate
VALUE = P.text  # the live numbers in the developer view's panel
WARN = P.accent2.mid  # the developer view's warnings

# The arena
SHADOW = P.deep  # the open plane, and a reading of 0 on the light map
LIGHT = P.bright  # a light, and a reading of RATE_MAX
RAY = mix(P.deep, P.line, 0.75)  # every ray, whatever its light, a shade lighter (D-342)
OBSTACLE = mix(P.line, P.muted, 0.5)
BODY = P.accent1.bright  # the selected swimmer
BODY_UNSELECTED = P.dim
RUN_SO_FAR = mix(P.dim, P.line, 0.3)  # the timeline's part already run, ahead of the playhead
EYE_SHADES = (P.bright, P.dim)  # one per eye in the polar plot, in turn
WIN = P.accent1.bright  # a win on Score's plot that no other beats: the Pareto front

# The Editor's plane (D-301): its grid, under the rays
PLANE_DOT = mix(P.deep, P.dim, 0.35)  # where a position may fall, every whole u (D-311)
PLANE_LINE = mix(P.deep, P.line, 0.6)  # a line every 5 u
MARK = mix(P.muted, P.dim, 0.5)  # a mark, an empty circle and its centre, in every view (D-306)

# The swimmer at work (D-076): its flames and the light it draws in, of one lightness (OKLab L
# 0.56), dimmer than the swimmer
FLAME = mix(P.accent2.dark, P.accent2.mid, 0.5)  # a thruster's flames, specks drifting out
INTAKE = mix(P.muted, P.dim, 0.6)  # the light an eye draws in, specks drifting to its face
SELECTED = mix(P.accent1.dark, BUTTON, 0.4)  # the text selected in a field, behind it (D-418)
FLAME_FAINT = mix(FLAME, PANEL, 0.3)  # ... on Diagnostic's circuit, behind it (D-415)
INTAKE_FAINT = mix(INTAKE, PANEL, 0.3)
PART_OUTLINE = P.dim  # a part's outline on the swimmer; its face keeps EYE_FACE, THRUSTER_BACK
MOTION = P.accent1.bright  # its velocity and its spin, in the swimmer's own colour


def pulse(frame: int) -> Colour:
    """A tutorial's target's colour at `frame`, drawing only: accent1, bright to medium and back
    every PULSE_FRAMES, a cosine's smoothness, in place of the sparks (D-337)."""
    return mix(P.accent1.mid, P.accent1.bright, _swing(frame))


def pulse_fill(frame: int) -> Colour:
    """A tutorial's target's fill at `frame`, where the target is a button filled in the accent,
    the switch: from its own fill, accent1's dark, toward its medium and back, in step with
    `pulse`; its icon stays as it is (D-350)."""
    return mix(P.accent1.dark, P.accent1.mid, PULSE_FILL_TOP * _swing(frame))


def _swing(frame: int) -> float:
    """1 at frame 0, 0 half a pulse on, 1 again every PULSE_FRAMES: a cosine's smoothness."""
    return 0.5 + 0.5 * math.cos(2 * math.pi * frame / PULSE_FRAMES)
