"""A part's entry at work (D-082). entry.py imports no pygame."""

import pytest

from nektoids.editor.devdrive import TICKS_PER_FRAME
from nektoids.editor.entry import (
    DEMOS,
    ENTRY_AREA,
    EYE_HIGH,
    EYE_LOW,
    EYE_PERIOD,
    KEEP_TIME,
    OUTWARDS,
    Entry,
)
from nektoids.editor.layout import contains
from nektoids.graph.board import Kind

FPS = 60  # frames a second: a tick of the entry


@pytest.mark.parametrize("kind", list(Kind))
def test_every_part_has_its_own_circuit_built_whole_and_seen_whole(kind):
    entry, demo = Entry(kind), DEMOS[kind]
    board = entry.circuit.board
    assert len(board.nodes) == len(demo.parts) and len(board.wires) == len(demo.wires)
    assert kind in {node.kind for node in board.nodes.values()}
    for i in range(entry.circuit.net.n):  # every part inside the box's area
        assert contains(ENTRY_AREA, tuple(map(int, entry.circuit.centre(i))))


@pytest.mark.parametrize(
    "kind, out",
    [
        (Kind.SOURCE, 1.0),
        (Kind.DOUBLE, 0.6),  # 0.3 in
        (Kind.HALVE, 0.4),  # 0.8 in
        (Kind.SUM, 0.7),  # 0.3 and 0.4
        (Kind.DIFFERENCE, 0.4),  # |0.7 - 0.3|
        (Kind.THRUSTER, 0.7),  # 0.3 and 0.4, added
    ],
)
def test_it_opens_at_its_steady_rates_and_the_part_does_what_its_entry_says(kind, out):
    entry = Entry(kind)
    net = entry.circuit.net
    thruster = int(net.thrusters[0])
    assert entry.y[thruster] == pytest.approx(out, abs=1e-6)
    for _ in range(30):
        entry.tick()
    assert entry.y[thruster] == pytest.approx(out, abs=1e-6)  # steady


def test_only_the_eyes_own_reading_rises_and_falls():
    entry = Entry(Kind.EYE)
    seen = []
    for _ in range(round(EYE_PERIOD * FPS)):
        entry.tick()
        seen.append(float(entry.eyes()[0]))
    assert min(seen) == pytest.approx(EYE_LOW, abs=0.01)
    assert max(seen) == pytest.approx(EYE_HIGH, abs=0.01)
    double = Entry(Kind.DOUBLE)
    double.tick()
    assert list(double.eyes()) == [0.3]


@pytest.mark.parametrize("kind", list(KEEP_TIME))
def test_double_gives_two_beads_for_one_and_halve_one_for_two_in_time(kind):
    entry = Entry(kind)
    beads, ratio = entry.circuit.beads, KEEP_TIME[kind]
    flux = entry.circuit.flux
    assert flux[1] == pytest.approx(ratio * flux[0])
    arrives = beads.lengths[0] * 4.0 * float(flux[0]) / beads.speed  # BEAD_RATE_AT_FULL
    every = min(1.0, ratio)  # ÷2: a bead leaves with every other arrival, either of the two
    for _ in range(3 * FPS):  # a bead leaves as one arrives, frame after frame
        entry.tick()
        lag = (beads.phase[1] - ratio * (beads.phase[0] - arrives)) % every
        assert min(lag, every - lag) < 1e-6
    assert TICKS_PER_FRAME * FPS == 120


@pytest.mark.parametrize("kind", list(Kind))
def test_eyes_and_thrusters_face_out_the_light_comes_in_and_the_flames_go_out(kind):
    entry = Entry(kind)  # D-082: the eye's face on the left, the thruster's back on the right
    for _ in range(20):
        entry.tick()
    net = entry.circuit.net
    turned = [net.facing[i] for i in (*net.eyes, *net.thrusters)]
    assert turned and all(facing == OUTWARDS for facing in turned)
    eyes = [entry.circuit.centre(int(i))[0] for i in net.eyes]
    thrusters = [entry.circuit.centre(int(i))[0] for i in net.thrusters]
    light, flames = entry.light(), entry.flames()
    assert all(x < max(eyes) for x, _ in light)  # coming in from the left
    assert flames and all(x > min(thrusters) for x, _ in flames)  # going out to the right
    for x, y in (*light, *flames):
        assert contains(ENTRY_AREA, (int(x), int(y)))


def test_every_entry_is_drawn_at_the_same_scale():
    assert len({Entry(kind).circuit.view.size for kind in Kind}) == 1


def test_the_light_and_the_flames_are_as_many_as_the_rates():
    double = Entry(Kind.DOUBLE)  # 0.3 in, 0.6 out
    seen, out = 0, 0
    for _ in range(600):
        double.tick()
        seen, out = seen + len(double.light()), out + len(double.flames())
    assert 12 * 0.3 * 0.8 < seen / 600 < 12 * 0.3 * 1.2  # INTAKE_SPECKS at the eye's reading
    assert 12 * 0.6 * 0.8 < out / 600 < 12 * 0.6 * 1.2  # FLAME_SPECKS at the thruster's rate
