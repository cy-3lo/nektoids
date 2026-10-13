"""The flow drawn (D-608): tracers over the plane in view, carried by the flow, never the run's
state. flowfield.py imports no pygame."""

import numpy as np

from nektoids.editor.flowfield import CELL, LEVELS, Tracers
from nektoids.sim import flow
from nektoids.sim.arena import STIR_RADIUS, Arena, Disc, Light, Pump, Source

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


def _still(arena: Arena) -> flow.Swim:
    """A swimmer at POS, no thrust: only the pumps and sources stir."""
    return flow.swim(arena, POS[None], np.ones(1), np.zeros((1, 0, 2)), np.zeros((1, 0, 2)))


WIDE = (-15.0, -12.0, 15.0, 12.0)


def _run(arena: Arena, push: float = 0.0, frames: int = 300):
    """The tracers over WIDE, a swimmer from (-8, 0) pushed by two side thrusters at `push` [f]
    each, frames of 1/30 s: the count seeded, the counts frame by frame, and the tracers."""
    pos, tips = np.array([-8.0, 0.0]), np.array([[[0.0, 1.0], [0.0, -1.0]]])
    forces = np.array([[[push, 0.0], [push, 0.0]]])
    swum = flow.swim(arena, pos[None], np.ones(1), pos + tips, forces)
    tracers = Tracers()
    tracers.follow(arena, pos, 1.0, swum, WIDE, 0.0)
    seeded, counts = len(tracers.x), []
    for _ in range(frames):
        swum = flow.swim(arena, pos[None], np.ones(1), pos + tips, forces)
        tracers.follow(arena, pos, 1.0, swum, WIDE, 1 / 30)
        pos = pos + swum.velocity[0] / 30
        counts.append(len(tracers.x))
    return seeded, np.array(counts), tracers


def test_the_slab_keeps_the_tracers_as_many_round_a_pump_a_source_a_sink_and_a_swimmer():
    for arena, push in (  # D-704: without it, the count drifted and gaps opened
        (Arena(pumps=(Pump(4.0, 0.0, 0, 0.8),)), 0.0),
        (Arena(sources=(Source(5.0, 0.0, 100.0),)), 0.0),
        (Arena(sources=(Source(5.0, 0.0, -100.0),)), 0.0),
        (Arena((Light(6.0, 8.0, 4.0),)), 0.5),
    ):
        seeded, counts, tracers = _run(arena, push)
        assert np.all(np.abs(counts / seeded - 1.0) < 0.1), arena
        assert len(tracers.speed) == len(tracers.x)


def test_a_source_feeds_its_rim_as_densely_as_the_field_and_a_sink_swallows_what_reaches_it():
    _, _, fed = _run(Arena(sources=(Source(5.0, 0.0, 100.0),)))
    ring = np.hypot(*(fed.x - (5.0, 0.0)).T)
    expected = np.pi * (3.0**2 - 1.0**2) / CELL**2  # one a cell, between 1 and 3 u
    assert 0.6 * expected < np.sum((ring > 1.0) & (ring < 3.0)) < 1.4 * expected
    _, _, drained = _run(Arena(sources=(Source(5.0, 0.0, -100.0),)), frames=30)
    assert np.hypot(*(drained.x - (5.0, 0.0)).T).min() > STIR_RADIUS


def test_rise_leaves_still_fluid_alone_a_source_out_of_view_puts_out_none_and_runs_repeat():
    far = Arena(sources=(Source(50.0, 0.0, 100.0),))
    tracers = Tracers()
    tracers.follow(far, POS, 1.0, _still(far), RECT, 0.0)
    seeded = len(tracers.x)
    tracers.follow(far, POS, 1.0, _still(far), RECT, 0.2)
    assert len(tracers.x) == seeded  # its flow here rises too slowly to take one in 0.2 s
    runs = [_run(Arena(sources=(Source(5.0, 0.0, 100.0),)), frames=20)[2].x for _ in range(2)]
    assert np.array_equal(*runs)


def test_past_the_most_the_most_crowded_cells_lose_their_oldest_first():
    from nektoids.editor.flowfield import _thinned

    x = np.array([[0.1, 0.1], [0.2, 0.2], [0.3, 0.3], [2.1, 0.1], [2.2, 0.2], [4.1, 0.1]])
    rect = (0.0, 0.0, 9.0, 9.0)
    assert _thinned(x, rect, 0).all()
    assert _thinned(x, rect, 1).tolist() == [False, True, True, True, True, True]
    assert _thinned(x, rect, 3).tolist() == [False, False, True, False, True, True]
