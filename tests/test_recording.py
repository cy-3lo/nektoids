"""The run's recording, behind the timeline (D-033). recording.py imports no pygame."""

import pytest

from nektoids.editor.recording import Recording


def test_a_recording_keeps_every_tick_from_the_start_to_the_frontier():
    run = Recording("t0")
    for k in range(1, 4):
        run.add(f"t{k}")
    assert run.frontier == 3
    assert [run.at(k) for k in range(4)] == ["t0", "t1", "t2", "t3"]
    with pytest.raises(IndexError, match="not recorded"):
        run.at(4)


def test_a_change_by_hand_cuts_off_what_came_after():
    run = Recording(0)
    for k in range(1, 6):
        run.add(k)
    run.cut(2, 20)
    assert run.frontier == 2 and run.at(2) == 20 and run.at(1) == 1
