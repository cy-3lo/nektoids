"""A button held down (D-412): it acts again after a moment, then at a steady pace."""

from nektoids.editor.hold import EVERY, HOLD, Hold


def _acting(hold: Hold, frames: int) -> list[int]:
    """The frames, counted from 1, on which what is held acts again."""
    return [frame for frame in range(1, frames + 1) if hold.tick()]


def test_a_held_button_acts_again_after_a_moment_then_at_a_steady_pace():
    hold = Hold()
    hold.press("plus")
    assert _acting(hold, HOLD + 2 * EVERY) == [HOLD, HOLD + EVERY, HOLD + 2 * EVERY]


def test_nothing_held_or_let_go_never_acts():
    hold = Hold()
    assert _acting(hold, 2 * HOLD) == []
    hold.press("plus")
    _acting(hold, HOLD - 1)
    hold.release()
    assert hold.target is None
    assert _acting(hold, 2 * HOLD) == []


def test_a_new_press_waits_its_moment_again():
    hold = Hold()
    hold.press("plus")
    _acting(hold, HOLD + EVERY // 2)
    hold.press("minus")
    assert _acting(hold, HOLD) == [HOLD]
    assert hold.target == "minus"
