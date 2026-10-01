import math
from collections import deque

import numpy as np
import pytest

from nektoids.graph.board import Kind, Refused
from nektoids.graph.dynamics import TAU, initial_state
from nektoids.graph.network import Network
from nektoids.levels.arenas import arenas
from nektoids.levels.objectives import REACH, Outcome, outcome, reaching
from nektoids.levels.sandbox import tutorial_board
from nektoids.sim.arena import LIGHT_RADIUS
from nektoids.sim.motion import SPEED
from nektoids.sim.optics import eye_rates
from nektoids.sim.world import parts, state_hash, step

DT = 1.0 / 120.0
LEVELS = {level.title: level for level in arenas()}


def wired(*wires):
    """The tutorial board (eyes 0 upper, 1 lower; thrusters 2 upper, 3 lower), wired."""
    board = tutorial_board()
    for a, b in wires:
        assert not isinstance(board.connect(a, b), Refused)
    return Network.from_board(board)


CROSSED = wired((0, 3), (1, 2))  # Braitenberg's aggression: charges the light
UNCROSSED = wired((0, 2), (1, 3))  # ... and fear: turns away from it


def driven(*wires):
    """The tutorial board, wired, with a Source on both thrusters: a drive of its own."""
    board = tutorial_board()
    source = board.place(Kind.SOURCE, (0, 0), locked=True)
    for a, b in ((source.id, 2), (source.id, 3), *wires):
        assert not isinstance(board.connect(a, b), Refused)
    return Network.from_board(board)


DRIVEN = driven((0, 3), (1, 2))  # crossed, and driven: out of a shadow, then to the light


def run(net, title, seconds, start=None):
    """Swimmers of radius 1 running `net` in the level from rest; start (N, 3): x, y [u],
    heading [rad], the level's own if None. Yields (pos, heading, y) after each tick."""
    arena = LEVELS[title].arena
    if start is None:
        x, y, heading = LEVELS[title].start
        start = np.array([[x, y, math.radians(heading)]])
    pos, heading, radius = start[:, :2], start[:, 2], np.ones(len(start))
    y = initial_state(net, len(start))
    for _ in range(round(seconds / DT)):
        pos, heading, y = step(arena, net, pos, heading, radius, y, DT)
        yield pos, heading, y


def last(states):
    return deque(states, maxlen=1)[0]


def play(net, title):
    """Run the level until it is over, as the arena view does: (outcome, ticks, visited)."""
    level = LEVELS[title]
    visited = reaching(level.arena, np.array([level.start[:2]]), np.ones(1))
    for tick, (pos, _, _) in enumerate(run(net, title, level.time_limit), start=1):
        visited |= reaching(level.arena, pos, np.ones(1))
        ended = outcome(level, visited, tick, DT)
        if ended is not None:
            return ended, tick, visited
    raise AssertionError("the run outlived its time limit")


# Determinism (invariant 1)


CROWD = ((2.0, 2.0, 0.0), (38.0, 36.0, 2 * math.pi))  # where and how the crowd starts


def crowd_hash(seed, seconds=5.0, n_swimmers=50):
    title = "In the shadow"
    rng = np.random.default_rng(seed)
    start = rng.uniform(*CROWD, (n_swimmers, 3))
    pos, heading, y = last(run(CROSSED, title, seconds, start))
    return state_hash(pos, heading, np.ones(n_swimmers), y, round(seconds / DT))


def test_same_level_same_graph_same_starts_give_an_identical_run():
    assert crowd_hash(seed=0) == crowd_hash(seed=0)


def test_other_starts_give_another_run():
    assert crowd_hash(seed=0) != crowd_hash(seed=1)


# Behaviour


def test_crossed_wiring_charges_the_light_and_wins_within_twelve_seconds():
    ended, ticks, _ = play(CROSSED, "One light")
    assert ended is Outcome.WON and ticks * DT < 12.0
    assert play(CROSSED, "One light")[1] == ticks  # the same tick, every run


def test_uncrossed_wiring_turns_its_back_to_the_light_and_stops_in_the_dark():
    ended, _, visited = play(UNCROSSED, "One light")
    assert ended is Outcome.TIME_UP and not visited.any()
    light, touch = LEVELS["One light"].arena.light_xy[0], REACH * (LIGHT_RADIUS + 1.0)
    begun = np.hypot(*(np.array(LEVELS["One light"].start[:2]) - light)) - touch
    states = list(run(UNCROSSED, "One light", 12.0))
    nearest = min(np.hypot(*(pos[0] - light)) - touch for pos, _, _ in states)
    assert nearest > 0.8 * begun  # never a fifth of the way to reaching it
    _, _, y = states[-1]
    assert np.all(y[:, UNCROSSED.eyes] < 0.01)  # still fading: it slows as it darkens


def test_in_the_shadow_the_eyes_see_nothing_and_a_swimmer_without_a_drive_never_moves():
    level = LEVELS["In the shadow"]
    pos, _, y = last(run(CROSSED, "In the shadow", 5.0))
    assert pos.tolist() == [list(level.start[:2])]
    assert np.all(y[:, CROSSED.eyes] == 0.0)


def test_in_the_shadow_a_drive_gets_it_out_and_it_wins_with_time_and_room_to_spare():
    title = "In the shadow"
    ended, ticks, _ = play(DRIVEN, title)
    assert ended is Outcome.WON and ticks * DT < LEVELS[title].time_limit / 2
    assert play(DRIVEN, title)[1] == ticks  # the same tick, every run
    light = LEVELS[title].arena.light_xy[0]
    nearest = min(np.hypot(*(pos[0] - light)) for pos, _, _ in run(DRIVEN, title, ticks * DT + 2.0))
    assert nearest < 0.5 * (LIGHT_RADIUS + 1.0)  # deep in, not grazing it (D-004)


def test_after_a_tick_the_eyes_in_the_state_read_where_the_body_now_is():
    arena = LEVELS["One light"].arena
    for pos, heading, y in run(CROSSED, "One light", 2.0):
        seen = eye_rates(arena, pos, heading, np.ones(1), *parts(CROSSED, CROSSED.eyes))
        assert np.array_equal(y[:, CROSSED.eyes], seen)


def test_a_source_on_both_thrusters_drives_the_body_straight_on_at_full_speed_no_walls():
    net = Network.from_edges([Kind.SOURCE, Kind.THRUSTER, Kind.THRUSTER], [(0, 1), (0, 2)])
    pos, heading, _ = last(run(net, "One light", 15.0))  # from (9, 15), heading E
    lag = SPEED * TAU  # the thrusters take TAU to reach their rate (D-017)
    assert pos[0, 0] == pytest.approx(9.0 + SPEED * 15.0 - lag, abs=1e-9)  # far past x = 40
    assert pos[0, 1] == 15.0 and heading.tolist() == [0.0]
