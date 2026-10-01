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


def test_a_change_by_hand_cuts_off_what_came_after_and_a_win_found_after_it():
    run = Recording(0)
    for k in range(1, 6):
        run.add(k)
    run.won_at = 5
    run.cut(2, 20)
    assert run.frontier == 2 and run.at(2) == 20 and run.at(1) == 1
    assert run.won_at is None  # it may not be won there any more
    run.won_at = 2
    run.cut(2, 30)
    assert run.won_at == 2  # a win at the very tick changed by hand still stands
