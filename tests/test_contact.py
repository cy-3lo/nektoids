import numpy as np
import pytest

from nektoids.sim.arena import Arena, Disc
from nektoids.sim.contact import confine

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


# Walls


def test_a_body_driven_into_a_wall_stops_touching_it_and_slides_along_it():
    path = slide(Arena(20.0, 10.0), (5.0, 5.0), (1.0, 2.0), seconds=4.0)
    assert np.all(path[:, 1] <= 9.0)
    assert path[-1] == pytest.approx([9.0, 9.0])  # x kept its speed along the wall


def test_a_body_driven_into_a_corner_stays_in_it():
    path = slide(Arena(20.0, 10.0), (5.0, 5.0), (3.0, 3.0), seconds=10.0)
    assert path[-1].tolist() == [19.0, 9.0]


# Obstacles


def test_a_body_driven_head_on_at_an_obstacle_stops_touching_it():
    disc = Disc(10.0, 5.0)
    path = slide(Arena(20.0, 10.0, obstacles=(disc,)), (3.0, 5.0), (2.0, 0.0), seconds=6.0)
    assert path[-1].tolist() == [8.0, 5.0]
    assert np.all(gap(path, disc) >= 1.0 - 1e-9)


def test_a_body_driven_off_centre_at_an_obstacle_slides_round_it_and_leaves_it_at_its_top():
    disc = Disc(10.0, 5.0)
    path = slide(Arena(20.0, 10.0, obstacles=(disc,)), (3.0, 5.5), (2.0, 0.0), seconds=6.0)
    assert np.all(gap(path, disc) >= 1.0 - 1e-9)
    assert path[-1, 0] > 12.0  # past it, moving on along x
    assert path[-1, 1] == pytest.approx(7.0, abs=1e-4)  # touching height: R + r above its centre


def test_a_body_in_a_crevice_by_a_wall_stays_inside_and_out_of_the_obstacle():
    disc = Disc(10.0, 2.5)  # 1.5 u from the wall: too narrow for a body 2 u across
    path = slide(Arena(20.0, 10.0, obstacles=(disc,)), (3.0, 1.0), (2.0, 0.0), seconds=6.0)
    assert np.all(path[:, 1] >= 1.0)
    assert path[-1, 0] < 10.0 - 1.3  # held back where it touches both
    assert gap(path, disc).min() > 1.0 - 2.0 * DT  # overlaps by less than one tick's travel


def test_a_body_on_an_obstacles_centre_leaves_along_x():
    arena = Arena(20.0, 10.0, obstacles=(Disc(10.0, 5.0),))
    assert confine(arena, np.array([[10.0, 5.0]]), ONE).tolist() == [[12.0, 5.0]]


def test_a_body_clear_of_everything_is_left_where_it_is_and_the_input_is_not_changed():
    arena = Arena(20.0, 10.0, obstacles=(Disc(10.0, 5.0),))
    pos = np.array([[4.0, 6.0], [10.0, 6.5]])  # the second inside the obstacle's reach
    out = confine(arena, pos, np.ones(2))
    assert out[0].tolist() == [4.0, 6.0]
    assert out[1] == pytest.approx([10.0, 7.0])
    assert pos.tolist() == [[4.0, 6.0], [10.0, 6.5]]
