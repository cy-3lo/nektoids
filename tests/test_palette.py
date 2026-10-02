"""The palette (D-047): OKLCH to sRGB, ten neutrals rising in lightness, two accents apart in
hue, and the contrasts that keep text and marks legible (invariant 6). palette.py has no pygame."""

import math

import pytest

from nektoids.editor import palette
from nektoids.editor.palette import NEUTRAL_L, PALETTE, make_palette, oklch, tint


def oklab(rgb):
    """sRGB 0-255 to OKLab, the forward transform (Ottosson 2020), to check `oklch` against."""
    lin = [
        (c / 255 / 12.92) if c / 255 <= 0.04045 else ((c / 255 + 0.055) / 1.055) ** 2.4 for c in rgb
    ]
    r, g, b = lin
    lms = (
        0.4122214708 * r + 0.5363015887 * g + 0.0514459929 * b,
        0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b,
        0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b,
    )
    lo, me, sh = (math.copysign(abs(v) ** (1 / 3), v) for v in lms)
    return (
        0.2104542553 * lo + 0.7936177850 * me - 0.0040720468 * sh,
        1.9779984951 * lo - 2.4285922050 * me + 0.4505937099 * sh,
        0.0259040371 * lo + 0.7827717662 * me - 0.8086757660 * sh,
    )


def hue(rgb):
    _, a, b = oklab(rgb)
    return math.degrees(math.atan2(b, a)) % 360


def luminance(rgb):
    """WCAG relative luminance."""
    lin = [
        (c / 255 / 12.92) if c / 255 <= 0.04045 else ((c / 255 + 0.055) / 1.055) ** 2.4 for c in rgb
    ]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    """WCAG contrast ratio, 1 to 21."""
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_oklch_inverts_the_forward_transform_inside_the_gamut():
    for rgb in [(18, 20, 28), (128, 128, 128), (89, 131, 146), (233, 196, 106), (184, 124, 211)]:
        L, a, b = oklab(rgb)
        back = oklch(L, math.hypot(a, b), math.degrees(math.atan2(b, a)))
        assert all(abs(x - y) <= 1 for x, y in zip(back, rgb, strict=True)), (rgb, back)
    assert oklch(1.0, 0.0, 0.0) == (255, 255, 255) and oklch(0.0, 0.0, 0.0) == (0, 0, 0)


def test_a_colour_outside_the_gamut_keeps_its_hue_and_loses_chroma():
    vivid = oklch(0.7, 0.4, 145.0)  # far more chroma than sRGB holds at this lightness
    assert all(0 <= c <= 255 for c in vivid)
    assert hue(vivid) == pytest.approx(145.0, abs=2.0)


def test_the_ten_neutrals_rise_in_lightness_and_each_accent_from_dark_to_bright():
    neutrals = [getattr(PALETTE, name) for name in palette.NEUTRALS]
    assert all(luminance(a) < luminance(b) for a, b in zip(neutrals, neutrals[1:], strict=False))
    for accent in (PALETTE.accent1, PALETTE.accent2):
        assert luminance(accent.dark) < luminance(accent.mid) < luminance(accent.bright)


def test_the_two_accents_differ_in_hue():
    gap = abs(hue(PALETTE.accent1.mid) - hue(PALETTE.accent2.mid)) % 360
    assert min(gap, 360 - gap) >= 45.0


@pytest.mark.parametrize("ramp", [(150.0, 0.028), (255.0, 0.03), (65.0, 0.025), (273.0, 0.022)])
def test_text_and_marks_stay_legible_whatever_the_tint(ramp):
    p = make_palette(*ramp, accent1_hue=187.0, accent2_hue=25.0)
    assert contrast(p.text, p.base) >= 7.0  # WCAG AAA
    assert contrast(p.dim, p.surface) >= 4.5  # WCAG AA: secondary text on panels
    assert contrast(p.parts, p.surface) >= 4.5  # a part on its cell
    assert contrast(p.text, p.accent1.dark) >= 4.5  # an icon on the tool in hand
    assert contrast(p.accent1.mid, p.surface) >= 3.0  # a part's face against the board
    assert contrast(p.accent2.bright, p.base) >= 4.5  # a refusal, read as text


def test_the_tint_turns_to_the_light_hue_the_shorter_way_and_only_in_the_lights():
    darks, lights = NEUTRAL_L[:4], NEUTRAL_L[-3:]
    assert all(tint(L, 273.0, 0.022, 85.0)[1] == pytest.approx(273.0) for L in darks)
    assert all(tint(L, 273.0, 0.022, 85.0)[1] == pytest.approx(85.0) for L in lights)
    midway = tint(0.525, 273.0, 0.022, 85.0)[1]  # halfway through the turn
    assert midway == pytest.approx((273.0 + 86.0) % 360, abs=1.0)  # through 359, not through 179
    assert tint(0.6, 150.0, 0.028)[1] == 150.0  # no light hue: one hue all along
    chromas = [tint(L, 273.0, 0.022)[0] for L in NEUTRAL_L]
    assert chromas[0] == pytest.approx(0.022) and chromas[-1] == pytest.approx(0.022 / 3)
