"""The mouse wheel turning a part (D-402, D-405): notches, and a trackpad's small scrolls."""

from nektoids.editor.notches import REST, Notches


def test_each_notch_of_a_wheel_is_a_turn_at_once():
    notches = Notches()
    assert [notches.feed(d) for d in (1, 1, -1, 2)] == [1, 1, -1, 2]


def test_small_scrolls_add_up_to_a_turn_then_rest_so_a_flick_turns_once():
    notches = Notches()
    assert [notches.feed(0.3) for _ in range(3)] == [0, 0, 0]  # 0.9: not yet
    assert notches.feed(0.3) == 1  # 1.2: a turn, the rest let go
    assert [notches.feed(0.5) for _ in range(5)] == [0] * 5  # the flick goes on: resting
    for _ in range(REST):
        notches.tick()
    assert [notches.feed(-0.6), notches.feed(-0.6)] == [0, -1]  # the other way, after the rest
    assert notches.feed(0) == 0
