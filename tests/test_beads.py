"""Beads on wires. beads.py imports no pygame, so this runs headless."""

import math

import pytest

from nektoids.editor.beads import BEAD_RATE_AT_FULL, BEAD_SPEED, Beads, Travelling

DT = 1 / 120


def run(beads, flux, seconds, dt=DT):
    for _ in range(round(seconds / dt)):
        beads.step([flux], dt)


def test_the_phase_is_the_running_total_of_the_flux_modulo_one():
    beads = Beads([100.0])
    run(beads, 2.5, 1.0)  # 2.5 beads released
    assert beads.phase[0] == pytest.approx(0.5, abs=1e-9)
    run(beads, 0.0, 3.0)  # nothing more: the phase is remembered, not reset
    assert beads.phase[0] == pytest.approx(0.5, abs=1e-9)


def test_beads_are_spaced_by_speed_over_flux_along_the_whole_wire():
    beads = Beads([100.0])
    run(beads, 2.0, 1.3)
    found = beads.positions(0, 2.0)
    gaps = [b - a for a, b in zip(found, found[1:], strict=False)]
    assert gaps == pytest.approx([BEAD_SPEED / 2.0] * len(gaps), abs=1e-9)
    assert found[0] == pytest.approx(beads.phase[0] * BEAD_SPEED / 2.0)
    assert len(found) == pytest.approx(100.0 * 2.0 / BEAD_SPEED, abs=1.0)


def test_at_a_steady_flux_every_bead_moves_at_the_bead_speed():
    beads = Beads([100.0])
    run(beads, 3.0, 0.5)
    before = beads.positions(0, 3.0)
    beads.step([3.0], 0.01)
    after = beads.positions(0, 3.0)
    moved = [b - a for a, b in zip(before, after, strict=False)]
    assert moved == pytest.approx([BEAD_SPEED * 0.01] * len(moved), abs=1e-9)


def test_a_new_bead_leaves_the_source_when_the_phase_wraps_and_nothing_jumps():
    beads = Beads([100.0])
    beads.phase[0] = 0.999
    before = beads.positions(0, 4.0)
    beads.step([4.0], 0.001)  # 0.004 of a bead: the phase wraps
    after = beads.positions(0, 4.0)
    assert beads.phase[0] == pytest.approx(0.003, abs=1e-9)
    assert after[0] < 0.1  # the new one, just off the source
    assert after[1:] == pytest.approx([x + BEAD_SPEED * 0.001 for x in before], abs=1e-9)
    assert len(after) == len(before) + 1


def test_a_change_of_flux_rescales_the_lattice_about_the_source_without_moving_the_phase():
    beads = Beads([100.0])
    run(beads, 3.0, 0.7)
    slow = beads.positions(0, 3.0)
    phase = beads.phase[0]
    fast = beads.positions(0, 6.0)  # the same phase, the flux doubles: twice as many beads
    assert beads.phase[0] == phase
    assert fast[: len(slow)] == pytest.approx([x / 2.0 for x in slow])
    assert len(fast) >= 2 * len(slow) - 1


def worst_step(belt, period, low=0.25, high=BEAD_RATE_AT_FULL):
    """Largest move of any one bead in one tick, flux swinging between low and high [beads/s].

    Bead j is the j-th released; the phase wrapping is what releases one, so count the wraps.
    """
    beads, wraps, last, previous, worst = Beads([30.0]), 0, 0.0, {}, 0.0
    for tick in range(int(2 * period / DT)):
        flux = (high + low) / 2 + (high - low) / 2 * math.sin(2 * math.pi * tick * DT / period)
        beads.step([flux], DT)
        wraps += beads.phase[0] < last
        last = beads.phase[0]
        now = {wraps - k: x for k, x in enumerate(beads.positions(0, flux, belt=belt))}
        for j in now.keys() & previous.keys():
            worst = max(worst, abs(now[j] - previous[j]))
        previous = now
    return worst


def test_a_belt_moves_each_bead_continuously_whatever_the_flux_does():
    # Even a flux that swings from nearly nothing to the full rate ten times a second.
    assert worst_step(belt=True, period=0.1) <= BEAD_SPEED * DT + 1e-9
    assert worst_step(belt=True, period=2.0) <= BEAD_SPEED * DT + 1e-9


def test_the_spacing_style_whips_when_a_low_flux_changes_fast_and_the_belt_does_not():
    whip = worst_step(belt=False, period=2.0)
    assert whip > 10 * BEAD_SPEED * DT  # tens of times the steady step, for a 2 s swing
    assert worst_step(belt=True, period=2.0) <= BEAD_SPEED * DT + 1e-9


def test_a_belt_has_a_fixed_gap_and_its_beads_move_in_proportion_to_the_flux():
    beads = Beads([100.0])
    beads.phase[0] = 0.3
    for flux in (1.0, 4.0, 8.0):
        found = beads.positions(0, flux, belt=True)
        gaps = [b - a for a, b in zip(found, found[1:], strict=False)]
        assert gaps == pytest.approx([BEAD_SPEED / BEAD_RATE_AT_FULL] * len(gaps))
    run(beads, 4.0, 0.0)
    before = beads.positions(0, 4.0, belt=True)
    beads.step([4.0], 0.01)
    after = beads.positions(0, 4.0, belt=True)
    assert after[0] - before[0] == pytest.approx(BEAD_SPEED * 4.0 / BEAD_RATE_AT_FULL * 0.01)


def test_no_flux_shows_no_beads_and_keeps_the_phase():
    beads = Beads([10.0])
    run(beads, 1.25, 1.0)
    assert beads.positions(0, 0.0) == []
    assert beads.phase[0] == pytest.approx(0.25, abs=1e-9)


def test_a_bead_leaves_the_wire_at_its_end():
    beads = Beads([4.0])
    beads.phase[0] = 0.9
    assert all(x < 4.0 for x in beads.positions(0, 1.0))
    assert beads.positions(0, 1.0) == [pytest.approx(0.9 * BEAD_SPEED)]  # the next one is at 6.65


def test_the_same_fluxes_give_the_same_beads():
    one, two = Beads([30.0, 12.0]), Beads([30.0, 12.0])
    for k in range(500):
        fluxes = [(k % 7) * 0.5, (k % 3) * 1.5]
        one.step(fluxes, DT)
        two.step(fluxes, DT)
    assert one.phase == two.phase
    assert one.positions(0, 3.0) == two.positions(0, 3.0)


def test_reset_forgets_every_phase():
    beads = Beads([30.0, 12.0])
    beads.step([5.0, 5.0], 0.3)
    beads.reset()
    assert beads.phase == [0.0, 0.0]


def test_travelling_beads_sit_where_beads_would_on_a_steady_wire():
    steady, travelling = Beads([10.0]), Travelling([10.0])
    travelling.fill([2.0])
    for _ in range(100):
        steady.step([2.0], DT)
        travelling.step([2.0], DT)
        assert travelling.positions(0, 2.0) == pytest.approx(steady.positions(0, 2.0))


def test_travelling_beads_never_go_backwards_as_the_rate_rises():
    beads = Travelling([10.0])  # D-082: Beads whip back as the rate climbs, these do not
    beads.fill([0.5])
    before = beads.positions(0, 0.5)
    for k in range(240):
        flux = 0.5 + 3.0 * k / 240  # a fast rise, from 0.5 to 3.5 beads/s in 2 s
        beads.step([flux], DT)
        now = beads.positions(0, flux)
        assert now == sorted(now) and all(0.0 <= x < 10.0 for x in now)
        for x in before:  # every bead moved on at its speed, or left the wire at its end
            on = x + BEAD_SPEED * DT
            assert on >= 10.0 or any(abs(y - on) < 1e-9 for y in now)
        before = now
