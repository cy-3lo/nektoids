"""Diagnostic's engine on the Board (D-058, D-407). probe.py imports no pygame."""

import math

import pytest

from nektoids.editor.layout import DIAGNOSTIC_BODY, contains
from nektoids.editor.probe import Probe
from nektoids.graph.board import Kind
from nektoids.graph.dynamics import RATE_MAX
from nektoids.levels.arenas import arenas
from nektoids.sim.arena import BASE_RADIUS

LEVELS = {level.title: level for level in arenas()}
AREA = DIAGNOSTIC_BODY  # the board at work, at Diagnostic's top


def wired(level):
    """An eye wired straight to a thruster, on the level's own board."""
    board = level.new_board()
    eye = board.place(Kind.EYE, (2, -1))
    thruster = board.node_at((1, -2)) or board.place(Kind.THRUSTER, (1, -2))  # Fear's (D-354)
    board.connect(eye.id, thruster.id)
    return board


def seeing(level):
    """A probe on the level, turned until its eye sees the light."""
    probe = Probe(wired(level), level, AREA)
    for _ in range(12):
        if probe.eyes()[0, 0] > 0.0:  # amber, of the level's white light (D-506)
            return probe
        probe.turn(math.pi / 6)
    raise AssertionError("the eye never sees the light")


def test_the_eyes_read_the_light_where_the_probe_stands_and_the_circuit_follows():
    assert Probe(wired(LEVELS["Fear"]), LEVELS["Fear"], AREA).pose[:2] == LEVELS["Fear"].start_at
    probe = seeing(LEVELS["Fear"])
    (sent,) = probe.eyes()[:, 0]  # its eye amber: it sends the amber channel
    assert 0.0 < sent <= RATE_MAX
    for _ in range(400):
        probe.tick()
    driven = max(probe.y[t] for t in probe.net.thrusters)  # Fear's other thruster, locked, is
    assert driven == pytest.approx(sent, abs=1e-3)  # unwired (D-354); settled: it passes it on


def test_the_probe_stays_out_of_the_obstacles():
    level = LEVELS["Shadows"]
    probe = Probe(level.new_board(), level, AREA)
    disc = level.arena.obstacles[0]
    probe.place(disc.x, disc.y)
    gap = math.hypot(probe.pose.x - disc.x, probe.pose.y - disc.y)
    assert gap >= disc.radius + BASE_RADIUS - 1e-9


def test_the_board_at_work_is_drawn_whole_in_diagnostics_top_its_beads_running():
    probe = seeing(LEVELS["Fear"])  # D-407: fitted with its body, as Run's Diagnostic (D-089)
    for i in range(len(probe.net.ids)):
        assert contains(AREA, tuple(round(v) for v in probe.circuit.centre(i)))
    for _ in range(50):
        probe.tick()
    assert probe.y.any()  # the circuit runs where the probe stands
    rings = [[m.value for m in LEVELS[t].marks] for t in ("Fear", "Love")]  # marks (D-307)
    assert rings == [[8.0], [7.0]]  # Fear's ring, Love's (D-317, D-318)


def test_diagnostics_map_shows_the_whole_level_where_the_swimmer_starts():
    from nektoids.editor.layout import DIAGNOSTIC_MAP, contains
    from nektoids.editor.probe import level_view

    for level in LEVELS.values():
        view = level_view(level, DIAGNOSTIC_MAP)
        x, y, _ = level.start
        assert contains(DIAGNOSTIC_MAP, tuple(round(v) for v in view.to_screen(x, y)))
        for lx, ly in level.arena.light_xy:
            assert contains(DIAGNOSTIC_MAP, tuple(round(v) for v in view.to_screen(lx, ly)))
