import numpy as np
import pytest

from nektoids.sim.arena import Arena, Disc, Light
from nektoids.sim.contact import SPRING, SPRING_GIVE, collide, confine, drag
from nektoids.sim.motion import THRUST

DT = 1.0 / 120.0
ONE = np.ones(1)  # one body of radius 1


def slide(arena, start, velocity, seconds):
    """Positions (ticks + 1, 2) of one body of radius 1 moved at a constant world velocity and
    confined after every tick, as world.step does."""
    pos = np.array([start], dtype=np.float64)
    path = [pos[0]]
    for _ in range(round(seconds / DT)):
        pos = confine(arena, pos + DT * np.array([velocity]), ONE)
        path.append(pos[0])
    return np.array(path)


def gap(path, disc):
    """(ticks + 1,): distance from each centre on the path to the disc's rim."""
    return np.hypot(path[:, 0] - disc.x, path[:, 1] - disc.y) - disc.radius


# The open plane (D-028)


def test_a_body_with_nothing_in_its_way_goes_on_for_ever():
    path = slide(Arena(), (5.0, 5.0), (3.0, 3.0), seconds=10.0)
    assert path[-1] == pytest.approx([35.0, 35.0])


# Obstacles


def test_a_body_driven_head_on_at_an_obstacle_stops_touching_it():
    disc = Disc(10.0, 5.0)
    path = slide(Arena(obstacles=(disc,)), (3.0, 5.0), (2.0, 0.0), seconds=6.0)
    assert path[-1].tolist() == [8.0, 5.0]
    assert np.all(gap(path, disc) >= 1.0 - 1e-9)


def test_a_body_driven_off_centre_at_an_obstacle_slides_round_it_and_leaves_it_at_its_top():
    disc = Disc(10.0, 5.0)
    path = slide(Arena(obstacles=(disc,)), (3.0, 5.5), (2.0, 0.0), seconds=6.0)
    assert np.all(gap(path, disc) >= 1.0 - 1e-9)
    assert path[-1, 0] > 12.0  # past it, moving on along x
    assert path[-1, 1] == pytest.approx(7.0, abs=1e-4)  # touching height: R + r above its centre


def test_a_body_in_a_crevice_between_two_obstacles_is_held_back_out_of_both():
    discs = (Disc(10.0, 3.75), Disc(10.0, 6.25))  # 0.5 u apart: too narrow for a body 2 u across
    path = slide(Arena(obstacles=discs), (3.0, 5.0), (2.0, 0.0), seconds=6.0)
    assert path[-1, 0] < 10.0 - 1.3  # held back where it touches both
    assert path[-1, 1] == pytest.approx(5.0, abs=0.01)  # the middle, but for the obstacles
    # pushing it out one after the other: the second has the last word
    for disc in discs:
        assert gap(path, disc).min() > 1.0 - 2.0 * DT  # overlaps by less than one tick's travel


def test_a_body_on_an_obstacles_centre_leaves_along_x():
    arena = Arena(obstacles=(Disc(10.0, 5.0),))
    assert confine(arena, np.array([[10.0, 5.0]]), ONE).tolist() == [[12.0, 5.0]]


def test_a_body_clear_of_everything_is_left_where_it_is_and_the_input_is_not_changed():
    arena = Arena(obstacles=(Disc(10.0, 5.0),))
    pos = np.array([[4.0, 6.0], [10.0, 6.5]])  # the second inside the obstacle's reach
    out = confine(arena, pos, np.ones(2))
    assert out[0].tolist() == [4.0, 6.0]
    assert out[1] == pytest.approx([10.0, 7.0])
    assert pos.tolist() == [[4.0, 6.0], [10.0, 6.5]]


def test_a_light_is_solid_and_a_swimmer_driven_into_it_stops_touching_it():
    arena = Arena(lights=(Light(10.0, 0.0, 8.0),))  # D-424
    path = slide(arena, (0.0, 0.0), (3.0, 0.0), 5.0)
    assert path[-1, 0] == pytest.approx(10.0 - 2.0)  # against it, centres R + r apart
    assert np.all(path[:, 0] <= 8.0 + 1e-12)


def push_head_on(radius: float, force: float, seconds: float, release: float = 0.0):
    """One body pushed along +x with `force` [f] into an obstacle of `radius` at (radius + 1.5,
    0), for `seconds`, then taken away for `release`, the obstacle let go: its displacement
    along x [u], tick by tick, as world.step moves body and obstacle."""
    arena = Arena(obstacles=(Disc(radius + 1.5, 0.0, radius),))
    pos, offsets, along = np.array([[0.0, 0.0]]), arena.at_rest, []
    for tick in range(round((seconds + release) / DT)):
        pushing = tick < round(seconds / DT)
        speed = force / drag(np.ones(1))[0] if pushing else 0.0
        if tick == round(seconds / DT):
            pos = np.array([[0.0, 100.0]])  # away: the obstacle comes back alone
        pos, offsets = collide(arena, offsets, pos + DT * np.array([[speed, 0.0]]), ONE, DT)
        along.append(offsets[0, 0])
    return np.array(along)


def test_a_head_on_push_of_two_full_thrusters_moves_an_obstacle_spring_give_whatever_its_size():
    for radius in (1.0, 3.0, 8.0):  # D-424: k u = F at rest, a sphere's drag only sets how fast
        along = push_head_on(radius, 2.0 * THRUST, 4.0)
        assert along[-1] == pytest.approx(SPRING_GIVE, rel=1e-3)
        assert np.all(along >= 0.0) and np.all(along <= SPRING_GIVE * (1 + 1e-3))  # no overshoot
    small, large = (
        push_head_on(1.0, 2.0, 0.15),
        push_head_on(8.0, 2.0, 0.15),
    )  # it arrives at 0.08 s
    assert small[-1] > large[-1]  # a larger sphere gives as far, more slowly


def test_let_go_an_obstacle_comes_back_with_its_time_constant_and_never_rings():
    radius = 3.0
    along = push_head_on(radius, 2.0, 4.0, release=1.0)
    held = round(4.0 / DT) - 1
    tau = drag(np.array([radius]))[0] / SPRING  # ζ / k: a factor 1 - dt / τ a tick
    n = round(tau / DT)
    assert along[held + n] == pytest.approx(along[held] * (1 - DT / tau) ** n, rel=1e-6)
    assert along[held + n] == pytest.approx(
        along[held] * np.exp(-1.0), rel=0.1
    )  # τ, as Euler gives it
    assert np.all(np.diff(along[held:]) <= 0.0) and along[-1] >= 0.0  # back, never past rest


def test_a_pushed_obstacle_takes_its_part_of_an_overlap_as_the_drags_say():
    arena = Arena(obstacles=(Disc(3.0, 0.0, 1.0),))
    pos, offsets = collide(arena, arena.at_rest, np.array([[1.4, 0.0]]), ONE, 1e-9)
    assert pos[0, 0] == pytest.approx(1.0 - 0.3, abs=1e-6) or offsets[0, 0] > 0.0
    assert pos[0, 0] + 2.0 == pytest.approx(3.0 + offsets[0, 0])  # touching after
    assert offsets[0, 0] == pytest.approx(0.2)  # equal spheres: the 0.4 overlap halved
