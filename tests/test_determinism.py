import math
from collections import deque

import numpy as np
import pytest

from nektoids.graph.board import Kind, Refused
from nektoids.graph.dynamics import TAU, initial_state
from nektoids.graph.hexgrid import NE, NW, SE, SW, E
from nektoids.graph.network import Network
from nektoids.levels.arenas import arenas
from nektoids.levels.objectives import REACH, Outcome, begin, follow, outcome
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
    """Run the level until it is over, as the arena view does: (outcome, ticks, kept), what its
    objectives keep, followed tick by tick (D-038, D-040)."""
    level = LEVELS[title]
    kept = begin(level, np.array([level.start[:2]]), np.ones(1))
    for tick, (pos, _, _) in enumerate(run(net, title, level.time_limit), start=1):
        kept = follow(level, kept, pos, np.ones(1), DT)
        ended = outcome(level, kept, tick, DT)
        if ended is not None:
            return ended, tick, kept
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
    ended, ticks, _ = play(CROSSED, "Aggression")
    assert ended is Outcome.WON and ticks * DT < 12.0
    assert play(CROSSED, "Aggression")[1] == ticks  # the same tick, every run


def test_uncrossed_wiring_turns_its_back_to_the_light_and_stops_in_the_dark():
    ended, _, (visited,) = play(UNCROSSED, "Aggression")
    assert ended is Outcome.TIME_UP and not visited.any()
    light, touch = LEVELS["Aggression"].arena.light_xy[0], REACH * (LIGHT_RADIUS + 1.0)
    begun = np.hypot(*(np.array(LEVELS["Aggression"].start[:2]) - light)) - touch
    states = list(run(UNCROSSED, "Aggression", 12.0))
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


def fear(upper, lower, crossed=False):
    """The fear tutorial's board (D-039): the eyes at the front, turned to `upper` and `lower`,
    the thrusters at the back corners, pushing forward, each eye wired to its own side."""
    board = LEVELS["Fear"].new_board()
    eyes = [
        board.place(Kind.EYE, cell, facing=f) for cell, f in (((2, -1), upper), ((1, 1), lower))
    ]
    thrusters = [board.place(Kind.THRUSTER, cell) for cell in ((1, -2), (-1, 2))]
    for eye, thruster in zip(eyes, reversed(thrusters) if crossed else thrusters, strict=True):
        assert not isinstance(board.connect(eye.id, thruster.id), Refused)
    return Network.from_board(board)


def test_fear_flees_the_light_with_its_eyes_looking_back_and_leaves_the_ring_in_time():
    ended, ticks, _ = play(fear(NW, SW), "Fear")
    assert ended is Outcome.WON and ticks * DT < LEVELS["Fear"].time_limit / 2
    assert play(fear(NW, SW), "Fear")[1] == ticks  # the same tick, every run


def test_fear_fails_crossed_or_with_its_eyes_looking_forward():
    assert play(fear(NW, SW, crossed=True), "Fear")[0] is Outcome.TIME_UP  # it closes in
    assert play(fear(NE, SE), "Fear")[0] is Outcome.TIME_UP  # it turns away, then stops
    assert play(fear(E, E), "Fear")[0] is Outcome.TIME_UP  # as placed, before any turn


def love(upper, lower, wiring="love"):
    """The love board (D-040): the eyes and thrusters where fear has them, the eyes turned to
    `upper` and `lower`. "love": each eye takes from a Source's 1 in a Diff, which drives the
    thruster on the eye's own side; "aggression": each eye drives the other side; "fear": its
    own; "drive": a Source on each thruster, the eyes unwired."""
    board = LEVELS["Love"].new_board()
    eyes = [
        board.place(Kind.EYE, cell, facing=f) for cell, f in (((2, -1), upper), ((1, 1), lower))
    ]
    thrusters = [board.place(Kind.THRUSTER, cell) for cell in ((1, -2), (-1, 2))]
    sources = []
    if wiring in ("love", "drive"):
        sources = [board.place(Kind.SOURCE, cell) for cell in ((0, -1), (-1, 1))]
    if wiring == "love":
        diffs = [board.place(Kind.DIFFERENCE, cell) for cell in ((1, -1), (0, 0))]
        wires = [
            pair
            for source, eye, diff, thruster in zip(sources, eyes, diffs, thrusters, strict=True)
            for pair in ((source, diff), (eye, diff), (diff, thruster))
        ]
    else:
        drives = {"aggression": eyes[::-1], "fear": eyes, "drive": sources}[wiring]
        wires = list(zip(drives, thrusters, strict=True))
    for a, b in wires:
        assert not isinstance(board.connect(a.id, b.id), Refused)
    return Network.from_board(board)


def love_on_the_axis():
    """The smallest love (D-044): one eye at the front looking ahead, a Diff of a Source and the
    eye, one thruster at the back, all on the body's axis."""
    board = LEVELS["Love"].new_board()
    eye = board.place(Kind.EYE, (2, 0), facing=E)
    source = board.place(Kind.SOURCE, (0, -1))
    diff = board.place(Kind.DIFFERENCE, (1, 0))
    thruster = board.place(Kind.THRUSTER, (-2, 0))
    for a, b in ((source, diff), (eye, diff), (diff, thruster)):
        assert not isinstance(board.connect(a.id, b.id), Refused)
    return Network.from_board(board)


def nearest_and_last(net):
    """How near Love's light the swimmer comes, and where it rests when the time is up [u]."""
    light = LEVELS["Love"].arena.light_xy[0]
    far = [np.hypot(*(pos[0] - light)) for pos, _, _ in run(net, "Love", 20.0)]
    return min(far), far[-1]


LOVE_RING = LEVELS["Love"].objectives[0].radius  # the swimmer's centre stays within it [u]
TOUCH = REACH * (LIGHT_RADIUS + 1.0)  # a base body reaches the light this near [u]


def test_love_comes_to_the_light_stops_short_of_it_and_stays_with_time_and_room_to_spare():
    ended, ticks, _ = play(love(E, E), "Love")
    assert ended is Outcome.WON and ticks * DT < LEVELS["Love"].time_limit / 2
    assert play(love(E, E), "Love")[1] == ticks  # the same tick, every run
    nearest, last = nearest_and_last(love(E, E))
    assert nearest > TOUCH + 1.0  # a unit clear of touching (D-004)
    assert last + 1.0 < LOVE_RING  # its whole body inside the dashed ring


def test_love_with_one_eye_one_diff_and_one_thruster_on_the_axis_wins_too():
    ended, ticks, _ = play(love_on_the_axis(), "Love")
    assert ended is Outcome.WON and ticks * DT < 0.6 * LEVELS["Love"].time_limit
    nearest, last = nearest_and_last(love_on_the_axis())
    assert nearest > TOUCH + 1.0 and last + 1.0 < LOVE_RING  # it rests 4.5 u out


def test_love_with_its_eyes_turned_out_loses_sight_of_the_light_and_touches_it():
    assert play(love(NE, SE), "Love")[0] is Outcome.LOST  # the light ends behind their faces


def test_without_a_diff_the_swimmer_touches_the_light_and_loses():
    for wiring, upper, lower in (
        ("aggression", E, E),
        ("aggression", NE, SE),
        ("fear", E, E),
        ("drive", E, E),
    ):
        assert play(love(upper, lower, wiring), "Love")[0] is Outcome.LOST, wiring


def test_after_a_tick_the_eyes_in_the_state_read_where_the_body_now_is():
    arena = LEVELS["Aggression"].arena
    for pos, heading, y in run(CROSSED, "Aggression", 2.0):
        seen = eye_rates(arena, pos, heading, np.ones(1), *parts(CROSSED, CROSSED.eyes))
        assert np.array_equal(y[:, CROSSED.eyes], seen)


def test_a_source_on_both_thrusters_drives_the_body_straight_on_at_full_speed_no_walls():
    net = Network.from_edges([Kind.SOURCE, Kind.THRUSTER, Kind.THRUSTER], [(0, 1), (0, 2)])
    pos, heading, _ = last(run(net, "Aggression", 15.0))  # from (9, 15), heading E
    lag = SPEED * TAU  # the thrusters take TAU to reach their rate (D-017)
    assert pos[0, 0] == pytest.approx(9.0 + SPEED * 15.0 - lag, abs=1e-9)  # far past x = 40
    assert pos[0, 1] == 15.0 and heading.tolist() == [0.0]
