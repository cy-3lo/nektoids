"""The laws of the parts (D-202): each a state equation and an output. laws.py imports no pygame."""

import numpy as np
import pytest

from nektoids.graph.laws import RATE_MAX, TAU, Difference, Relax, Scaled


def rates(*values):
    """x (1, 1, K): one agent, one node, its K input slots."""
    return np.array(values, dtype=float).reshape(1, 1, -1)


def test_a_relaxing_law_steps_a_weighted_mean_of_its_state_and_its_target():
    law, y = Relax(Scaled(2.0)), np.array([[0.2]])
    x = rates(0.1, 0.15)  # asks for 2 * 0.25 = 0.5
    assert law.step(x, y, TAU / 2)[0, 0] == pytest.approx(0.35)
    assert law.step(x, y, TAU)[0, 0] == pytest.approx(0.5)  # dt = tau: straight to F
    assert law.step(rates(0.4, 0.4), y, TAU)[0, 0] == RATE_MAX  # capped
    assert law.output(y) is y and law.max_dt == TAU


def test_a_difference_is_either_way_round_and_a_lone_input_passes():
    assert Difference()(rates(0.2, 0.7))[0, 0] == pytest.approx(0.5)
    assert Difference()(rates(0.7, 0.2))[0, 0] == pytest.approx(0.5)
    assert Difference()(rates(0.3))[0, 0] == 0.3


def test_a_slow_relaxing_node_is_a_tank_that_keeps_what_has_not_left():
    # T dh/dt = in - h (ideas.md, stage 2): fed 0.5 for T from empty, it holds 0.5 (1 - 1/e),
    # and T h is what came in less what went out.
    tank, dt, inflow = Relax(Scaled(1.0), tau=4.0), 1 / 120, 0.5
    h, left = np.zeros((1, 1)), 0.0
    for _ in range(480):
        left += dt * h[0, 0]  # it sends out its level
        h = tank.step(rates(inflow), h, dt)
    assert h[0, 0] == pytest.approx(inflow * (1 - np.exp(-1.0)), rel=2e-3)  # Euler, dt/T = 1/480
    assert tank.tau * h[0, 0] == pytest.approx(480 * dt * inflow - left)
    assert tank.equation("K0", ["E0"]) == "4 s * dK0/dt = -K0 + min(R, E0)"
