import numpy as np

from nektoids.sim.world import make_world, state_hash, step

DT = 1.0 / 120.0


def run(seed: int, n_steps: int = 2000, n_agents: int = 50) -> str:
    world = make_world(seed=seed, n_agents=n_agents, width=960.0, height=640.0)
    force = np.zeros_like(world.pos)
    for _ in range(n_steps):
        step(world, force, DT)
    return state_hash(world)


def test_same_seed_gives_identical_run():
    assert run(seed=0) == run(seed=0)


def test_different_seeds_give_different_runs():
    assert run(seed=0) != run(seed=1)


def test_free_agent_decelerates_under_drag():
    world = make_world(seed=0, n_agents=10, width=960.0, height=640.0)
    speed_before = np.linalg.norm(world.vel, axis=1)
    for _ in range(100):
        step(world, np.zeros_like(world.pos), DT)
    speed_after = np.linalg.norm(world.vel, axis=1)
    assert np.all(speed_after < speed_before)
