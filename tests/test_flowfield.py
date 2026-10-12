"""The flow drawn (D-608): tracers over the plane in view, carried by the flow, never the run's
state. flowfield.py imports no pygame."""

import numpy as np

from nektoids.editor.flowfield import CELL, LEVELS, Tracers
from nektoids.sim import flow
from nektoids.sim.arena import Arena, Disc, Light

ARENA = Arena(lights=(Light(6.0, 0.0, 4.0),), obstacles=(Disc(-5.0, 4.0, 2.0),))
RECT = (-10.0, -8.0, 10.0, 8.0)
POS = np.array([0.0, 0.0])


def _swum(push: float) -> flow.Swim:
    """A swimmer at POS pushed ahead by two side thrusters at `push` [f] each."""
    tips = np.array([[[0.0, 1.0], [0.0, -1.0]]])
    return flow.swim(ARENA, POS[None], np.ones(1), tips, np.array([[[push, 0.0], [push, 0.0]]]))


def test_one_tracer_a_cell_none_in_a_light_an_obstacle_or_the_swimmer_the_same_each_time():
    tracers = Tracers()
    tracers.follow(ARENA, POS, 1.0, _swum(0.0), RECT, 0.0)
    cells = (20.0 / CELL) * (16.0 / CELL)
    assert 0.8 * cells < len(tracers.x) <= cells
    for centre, reach in ((POS, 1.0), ((6.0, 0.0), 1.0), ((-5.0, 4.0), 2.0)):
        assert np.hypot(*(tracers.x - centre).T).min() >= reach
    again = Tracers()
    again.follow(ARENA, POS, 1.0, _swum(0.0), RECT, 0.0)
    assert np.array_equal(again.x, tracers.x) and tracers.seeded == 1


def test_still_fluid_moves_nothing_and_a_swimmer_moves_them_within_the_view():
    tracers = Tracers()
    tracers.follow(ARENA, POS, 1.0, _swum(0.0), RECT, 0.0)
    before = tracers.x.copy()
    tracers.follow(ARENA, POS, 1.0, _swum(0.0), RECT, 1.0)
    assert np.allclose(tracers.x, before, atol=1e-12) and tracers.levels().max() == 0
    tracers.follow(ARENA, POS, 1.0, _swum(1.0), RECT, 1.0)
    assert not np.array_equal(tracers.x, before) and tracers.levels().max() == LEVELS - 1
    left, bottom, right, top = RECT
    assert np.all((tracers.x[:, 0] >= left) & (tracers.x[:, 0] < right))
    assert np.all((tracers.x[:, 1] >= bottom) & (tracers.x[:, 1] < top))


def test_another_view_or_a_clear_seeds_them_again():
    tracers = Tracers()
    tracers.follow(ARENA, POS, 1.0, _swum(1.0), RECT, 0.0)
    tracers.follow(ARENA, POS, 1.0, _swum(1.0), (-5.0, -5.0, 5.0, 5.0), 0.0)
    tracers.clear()
    tracers.follow(ARENA, POS, 1.0, _swum(1.0), (-5.0, -5.0, 5.0, 5.0), 0.0)
    assert tracers.seeded == 3
