"""Beads on wires. beads.py imports no pygame, so this runs headless."""

import pytest

from nektoids.editor.beads import BEAD_SPEED, Beads

DT = 1 / 120


def run(beads, flux, seconds, dt=DT):
    for _ in range(round(seconds / dt)):
        beads.step([flux], dt)


def test_a_wire_sends_as_many_beads_as_its_flux_adds_up_to():
    beads = Beads([100.0])
    run(beads, 2.5, 8.0)
    assert abs(beads.spawned[0] - 20) <= 1
    assert beads.spawned[0] + beads.phase[0] == pytest.approx(20.0, abs=1e-6)


def test_beads_are_spaced_by_speed_over_flux():
    beads = Beads([100.0])
    run(beads, 2.0, 5.0)
    ordered = sorted(beads.positions[0])
    gaps = [b - a for a, b in zip(ordered, ordered[1:], strict=False)]
    assert gaps == pytest.approx([BEAD_SPEED / 2.0] * len(gaps), abs=1e-9)


def test_beads_move_along_the_wire_and_leave_at_its_end():
    beads = Beads([10.0], speed=7.0)
    beads.step([2.0], 0.5)  # one bead owed after half a second: sent 0 s ago
    assert beads.positions[0] == [0.0]
    before = beads.positions[0][0]
    beads.step([0.0], 1.0)
    assert beads.positions[0] == [pytest.approx(before + 7.0)]
    beads.step([0.0], 1.0)
    assert beads.positions[0] == []  # 14 > 10: gone


def test_no_flux_sends_no_beads():
    beads = Beads([10.0])
    run(beads, 0.0, 2.0)
    assert beads.spawned == [0] and beads.positions == [[]]


def test_a_step_longer_than_the_gap_sends_several_beads_at_distinct_places():
    beads = Beads([100.0], speed=7.0)
    beads.step([8.0], 1.0)  # eight beads in one step
    assert beads.spawned == [8]
    positions = sorted(beads.positions[0])
    assert positions == pytest.approx([7.0 * k / 8.0 for k in range(8)])


def test_a_rate_that_changes_changes_the_spacing_behind_it():
    beads = Beads([100.0], speed=7.0)
    run(beads, 4.0, 2.0)
    run(beads, 1.0, 2.0)
    positions = sorted(beads.positions[0])
    near, far = positions[:3], positions[-3:]
    assert near[1] - near[0] == pytest.approx(7.0, abs=1e-6)  # the new, slower rate
    assert far[1] - far[0] == pytest.approx(7.0 / 4.0, abs=1e-6)  # the old one, further on


def test_the_same_fluxes_give_the_same_beads():
    one, two = Beads([30.0, 12.0]), Beads([30.0, 12.0])
    for k in range(500):
        fluxes = [(k % 7) * 0.5, (k % 3) * 1.5]
        one.step(fluxes, DT)
        two.step(fluxes, DT)
    assert one.positions == two.positions and one.spawned == two.spawned


def test_reset_empties_every_wire():
    beads = Beads([30.0, 12.0])
    beads.step([5.0, 5.0], 1.0)
    beads.reset()
    assert beads.spawned == [0, 0] and beads.positions == [[], []] and beads.phase == [0.0, 0.0]
