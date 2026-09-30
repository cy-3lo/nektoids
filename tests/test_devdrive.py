"""The developer view's clock, sliders and waveforms. devdrive.py imports no pygame."""

import pytest

from nektoids.editor.devdrive import (
    DT,
    PERIOD,
    SLIDER_GRAB,
    STEP_AT,
    TICKS_PER_FRAME,
    WAVES,
    Clock,
    knob_y,
    level_at,
    next_wave,
    on_track,
    track_for,
    waveform,
)
from nektoids.editor.layout import HEX_SIZE, MAX_HEX, View, fitted_view, make_layout
from nektoids.graph.evaluate import RATE_MAX
from nektoids.graph.hexgrid import to_pixel


def tick_at(seconds):
    return round(seconds / DT)


# Waveforms


def test_hold_and_step_waves():
    assert waveform("hold", 0.75, 0) == waveform("hold", 0.75, 999) == 0.75
    assert waveform("step", 0.75, tick_at(STEP_AT) - 1) == 0.0
    assert waveform("step", 0.75, tick_at(STEP_AT)) == 0.75


def test_sine_and_square_waves_stay_between_zero_and_the_level():
    for name in ("sine", "square"):
        values = [waveform(name, 0.5, k) for k in range(0, tick_at(2 * PERIOD), 7)]
        assert min(values) >= 0.0 and max(values) <= 0.5
    assert waveform("sine", 0.5, 0) == pytest.approx(0.0, abs=1e-12)
    assert waveform("sine", 0.5, tick_at(PERIOD / 2)) == pytest.approx(0.5)
    assert waveform("square", 0.5, tick_at(PERIOD / 4)) == 0.0
    assert waveform("square", 0.5, tick_at(3 * PERIOD / 4)) == 0.5


def test_waves_cycle_through_all_of_them_and_an_unknown_name_is_an_error():
    name, seen = WAVES[0], []
    for _ in WAVES:
        seen.append(name)
        name = next_wave(name)
    assert seen == list(WAVES) and name == WAVES[0]
    with pytest.raises(ValueError, match="unknown waveform"):
        waveform("saw", 1.0, 0)


# Clock


def test_a_running_clock_gives_two_ticks_a_frame_in_order():
    clock = Clock()
    assert list(clock.frame()) == [0, 1] and list(clock.frame()) == [2, 3]
    assert TICKS_PER_FRAME == 2 and clock.seconds == pytest.approx(4 * DT)


def test_a_paused_clock_gives_nothing_until_stepped_once():
    clock = Clock()
    clock.frame()
    clock.toggle_pause()
    assert list(clock.frame()) == []
    clock.step()
    assert list(clock.frame()) == [2, 3]
    assert list(clock.frame()) == []
    clock.toggle_pause()
    assert list(clock.frame()) == [4, 5]


def test_stepping_a_running_clock_does_not_skip_ahead_later():
    clock = Clock()
    clock.step()
    assert list(clock.frame()) == [0, 1]
    clock.toggle_pause()
    assert list(clock.frame()) == []


def test_reset_goes_back_to_tick_zero():
    clock = Clock()
    clock.frame()
    clock.reset()
    assert clock.tick == 0 and list(clock.frame()) == [0, 1]


# Sliders


def test_the_track_is_left_of_the_part_and_centred_on_it():
    track = track_for((300.0, 200.0), 40.0)
    assert track.x < 300.0 and (track.top + track.bottom) / 2 == pytest.approx(200.0)
    assert track.bottom - track.top == pytest.approx(1.6 * 40.0)


def test_level_and_knob_position_are_inverse_and_clamped():
    track = track_for((300.0, 200.0), 40.0)
    for level in (0.0, 0.125, 0.5, RATE_MAX):
        assert level_at(track, knob_y(track, level)) == pytest.approx(level)
    assert knob_y(track, 0.0) == track.bottom and knob_y(track, RATE_MAX) == track.top
    assert level_at(track, track.top - 50.0) == RATE_MAX
    assert level_at(track, track.bottom + 50.0) == 0.0


def test_a_press_grabs_the_knob_near_the_track_only():
    track = track_for((300.0, 200.0), 40.0)
    middle = (track.top + track.bottom) / 2
    assert on_track(track, (track.x, middle))
    assert on_track(track, (track.x + SLIDER_GRAB, track.bottom + SLIDER_GRAB))
    assert not on_track(track, (track.x + SLIDER_GRAB + 1, middle))
    assert not on_track(track, (track.x, track.top - SLIDER_GRAB - 1))


# Fitting the schematic to its area


def test_a_fitted_view_centres_the_points_and_keeps_them_inside_with_their_margin():
    area = (340, 0, 620, 608)
    points = [(0.0, 0.0), (10.0, 4.0)]
    view = fitted_view(area, points, margin=2.0)
    xs = [view.origin[0] + view.size * x for x, _ in points]
    ys = [view.origin[1] + view.size * y for _, y in points]
    assert (min(xs) + max(xs)) / 2 == pytest.approx(area[0] + area[2] / 2)
    assert (min(ys) + max(ys)) / 2 == pytest.approx(area[1] + area[3] / 2)
    assert min(xs) - 2.0 * view.size >= area[0] - 1e-9
    assert max(xs) + 2.0 * view.size <= area[0] + area[2] + 1e-9


def test_a_small_graph_is_not_blown_up_past_the_zoom_limit():
    view = fitted_view(make_layout().board_area, [(0.0, 0.0), (1.0, 0.0)], margin=1.0)
    assert view.size == MAX_HEX


def test_a_wide_graph_shrinks_the_view_to_fit():
    view = fitted_view((0, 0, 400, 400), [(0.0, 0.0), (30.0, 0.0)], margin=1.0)
    assert view.size == pytest.approx(400 / 32.0) and view.size < HEX_SIZE
    assert to_pixel((0, 0), view.size, view.origin)[0] >= 0.0
    assert isinstance(view, View)
