"""The lattice a made level's values sit on (D-301). lattice.py imports no pygame."""

from nektoids.levels.lattice import HEADING, POSITION, Range, snap, snapped


def test_positions_snap_to_whole_units_and_headings_to_fifteen_degrees_never_to_minus_zero():
    assert (POSITION, HEADING) == (1.0, 15.0)  # D-311
    assert snapped((10.2, 13.9)) == (10.0, 14.0)
    assert snapped((-0.2, 0.6)) == (0.0, 1.0) and str(snapped((-0.2, 0.0))[0]) == "0.0"
    assert snap(35.0, HEADING) == 30.0 and snap(-7.6, HEADING) == -15.0


def test_a_range_keeps_a_setting_on_its_steps_and_within_its_ends():
    power = Range(1.0, 16.0, 1.0)
    assert power.clamp(4.4) == 4.0 and power.clamp(0.0) == 1.0 and power.clamp(99.0) == 16.0
    assert power.stepped(4.0, 2) == 6.0 and power.stepped(16.0, 1) == 16.0
    assert power.stepped(4.4, -1) == 3.0  # from the lattice point nearest it
    radius = Range(0.5, 5.0, 0.5, "u")
    assert radius.stepped(1.0, -1) == 0.5 and radius.stepped(0.5, -1) == 0.5
    assert radius.unit == "u"
