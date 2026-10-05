"""The Run preview's engine (D-058). probe.py imports no pygame."""

import math

import numpy as np
import pytest

from nektoids.editor.layout import View
from nektoids.editor.probe import Probe
from nektoids.graph.board import Kind
from nektoids.graph.dynamics import RATE_MAX
from nektoids.graph.hexgrid import to_pixel
from nektoids.levels.arenas import arenas
from nektoids.sim.arena import BASE_RADIUS

LEVELS = {level.title: level for level in arenas()}
VIEW = View(34.0, (628.0, 335.0))  # as the editor shows the board


def wired(level):
    """An eye wired straight to a thruster, on the level's own board."""
    board = level.new_board()
    eye = board.place(Kind.EYE, (2, -1))
    thruster = board.place(Kind.THRUSTER, (1, -2))
    board.connect(eye.id, thruster.id)
    return board


def seeing(level):
    """A probe on the level, turned until its eye sees the light."""
    probe = Probe(wired(level), level, VIEW)
    for _ in range(12):
        if probe.eyes()[0] > 0.0:
            return probe
        probe.turn(math.pi / 6)
    raise AssertionError("the eye never sees the light")


def test_the_eyes_read_the_light_where_the_probe_stands_and_the_circuit_follows():
    assert Probe(wired(LEVELS["Fear"]), LEVELS["Fear"], VIEW).pose[:2] == LEVELS["Fear"].start[:2]
    probe = seeing(LEVELS["Fear"])
    (sent,) = probe.eyes()
    assert 0.0 < sent <= RATE_MAX
    for _ in range(400):
        probe.tick()
    (thruster,) = probe.net.thrusters
    assert probe.y[thruster] == pytest.approx(sent, abs=1e-3)  # settled: it passes the eye on


def test_an_eye_held_at_a_level_sends_it_until_the_probe_moves_or_turns():
    probe = seeing(LEVELS["Fear"])
    (eye,) = probe.net.eyes
    light = probe.eyes().copy()
    probe.hold(int(eye), 5.0)
    assert probe.eyes()[0] == RATE_MAX  # clamped
    probe.hold(int(eye), 0.2)
    assert probe.eyes()[0] == 0.2
    probe.turn(math.pi)
    assert not probe.held and probe.eyes()[0] != light[0]  # back to the light, now behind it
    probe.hold(int(eye), 0.2)
    probe.place(*probe.pose[:2])
    assert not probe.held


def test_the_probe_stays_out_of_the_obstacles():
    level = LEVELS["Shadows"]
    probe = Probe(level.new_board(), level, VIEW)
    disc = level.arena.obstacles[0]
    probe.place(disc.x, disc.y)
    gap = math.hypot(probe.pose.x - disc.x, probe.pose.y - disc.y)
    assert gap >= disc.radius + BASE_RADIUS - 1e-9


def test_an_eyes_meter_is_a_handle_from_nothing_at_its_foot_to_full_at_its_top():
    probe = Probe(wired(LEVELS["Fear"]), LEVELS["Fear"], VIEW)
    (eye,) = probe.net.eyes
    track = probe.track(int(eye))
    assert probe.handle_at((track.x, (track.top + track.bottom) / 2)) == int(eye)
    assert probe.handle_at(probe.circuit.centre(int(eye))) is None  # the eye itself
    assert probe.level_at(int(eye), track.top) == RATE_MAX
    assert probe.level_at(int(eye), track.bottom + 50) == 0.0


def test_the_preview_draws_the_board_where_the_editor_does_and_follows_its_view():
    board = wired(LEVELS["Fear"])
    probe = Probe(board, LEVELS["Fear"], VIEW)
    (eye,) = probe.net.eyes
    cell = board.nodes[probe.net.ids[int(eye)]].cell
    assert probe.circuit.centre(int(eye)) == to_pixel(cell, VIEW.size, VIEW.origin)  # D-060
    for _ in range(50):
        probe.tick()
    before = probe.y.copy()
    zoomed = View(51.0, (400.0, 300.0))
    probe.see(zoomed)
    assert probe.circuit.centre(int(eye)) == to_pixel(cell, zoomed.size, zoomed.origin)
    assert np.array_equal(probe.y, before)
    rings = [[m.value for m in LEVELS[t].marks] for t in ("Fear", "Love")]  # marks (D-307)
    assert rings == [[12.0], [6.0]]


def test_diagnostics_map_shows_the_whole_level_where_the_swimmer_starts():
    from nektoids.editor.layout import DIAGNOSTIC_MAP, contains
    from nektoids.editor.probe import level_view

    for level in LEVELS.values():
        view = level_view(level, DIAGNOSTIC_MAP)
        x, y, _ = level.start
        assert contains(DIAGNOSTIC_MAP, tuple(round(v) for v in view.to_screen(x, y)))
        for lx, ly in level.arena.light_xy:
            assert contains(DIAGNOSTIC_MAP, tuple(round(v) for v in view.to_screen(lx, ly)))
