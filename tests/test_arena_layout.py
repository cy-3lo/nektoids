"""The run's own places in the frame (D-057). arena_layout.py imports no pygame."""

import pytest

from nektoids.editor.arena_layout import (
    BUTTON_KEYS,
    CONTROLS,
    DRAWER_BODY,
    KEY_BUTTONS,
    MAP_KEY,
    POLAR_KEY,
    TIME_TICKS,
    TURN_KEYS,
    VIEW_BUTTON,
    ArenaButton,
    banner_button_at,
    banner_rect,
    banner_rects,
    control_at,
    control_rects,
    polar_box,
    summary_at,
    time_ticks,
    timeline_at,
    timeline_rect,
    timeline_x,
)
from nektoids.editor.layout import (
    SCREEN,
    TOOL_KEYS,
    VIEW_KEYS,
    Drawer,
    Env,
    Tool,
    ViewButton,
    contains,
    make_layout,
)

RUN = make_layout(Drawer.INSIDE, env=Env.RUN, goals=2)
FOLDED = make_layout(None, env=Env.RUN, goals=2)


def centre(rect):
    x, y, w, h = rect
    return (x + w // 2, y + h // 2)


def test_the_controls_sit_side_by_side_in_the_strip_then_the_timeline_then_the_time():
    for layout in (RUN, FOLDED):
        strip, rects = layout.controls_area, control_rects(layout)
        assert [b for b, _ in rects] == list(CONTROLS)
        for (_, (x, y, w, h)), (_, (x2, _, _, _)) in zip(rects, rects[1:], strict=False):
            assert x + w < x2 and contains(strip, (x, y)) and contains(strip, (x + w, y + h))
        line = timeline_rect(layout)
        last = rects[-1][1]
        assert last[0] + last[2] < line[0] and line[0] + line[2] < summary_at(layout)[0]
        assert contains(strip, line[:2]) and summary_at(layout)[0] <= strip[0] + strip[2]
        for button, rect in rects:
            assert control_at(layout, centre(rect)) is button
        assert control_at(layout, centre(layout.board_area)) is None  # the arena


def test_the_timeline_runs_from_zero_to_the_limit_and_finds_a_time():
    x, y, w, h = timeline_rect(RUN)
    assert timeline_x(RUN, 0.0, 20.0) == x and timeline_x(RUN, 20.0, 20.0) == x + w
    assert timeline_x(RUN, 30.0, 20.0) == x + w  # past the limit: at the end
    assert timeline_at(RUN, (x + w // 2, y + h // 2), 20.0) == pytest.approx(10.0, abs=0.1)
    assert timeline_at(RUN, (x + w // 2, y - 1), 20.0) is None


def test_the_banner_holds_its_buttons_side_by_side_at_the_arenas_top_and_finds_them():
    both = (ArenaButton.NEXT, ArenaButton.EDIT)
    (_, (x1, y1, w1, h1)), (_, (x2, y2, _, _)) = banner_rects(RUN, both)
    bx, by, bw, bh = banner_rect(RUN)
    assert y1 == y2 and x1 + w1 < x2 and bx < x1 and x2 + w1 < bx + bw and y1 + h1 < by + bh
    assert banner_button_at(RUN, both, (x1 + 5, y1 + 5)) is ArenaButton.NEXT
    assert banner_button_at(RUN, (ArenaButton.EDIT,), (x1 + 5, y1 + 5)) is None  # centred
    arena = RUN.board_area
    assert contains(arena, (bx, by)) and contains(arena, (bx + bw, by + bh))
    assert contains(arena, polar_box(RUN)[:2])


def test_inside_and_score_draw_in_the_drawer_under_its_title():
    x, y, w, h = DRAWER_BODY
    dx, dy, dw, dh = RUN.drawer_area
    assert (x, w) == (dx, dw) and y > dy and y + h <= SCREEN[1]


def test_a_key_means_the_same_here_as_in_the_editor():
    for view, button in VIEW_BUTTON.items():  # Navigator's rows press the run's buttons
        assert BUTTON_KEYS[button] == VIEW_KEYS[view]
    assert set(VIEW_BUTTON) == set(ViewButton)
    # Turning the swimmer left and right, as the editor turns a part (D-025).
    assert TURN_KEYS == (TOOL_KEYS[Tool.TURN_LEFT], TOOL_KEYS[Tool.TURN_RIGHT])
    others = {*BUTTON_KEYS.values(), MAP_KEY, POLAR_KEY}
    # Motion and Streams take Move's and Wire's letters, as the editor never shows them (D-069,
    # D-076); nothing else means an editor tool here (D-021)
    shared = {BUTTON_KEYS[ArenaButton.MOTION], BUTTON_KEYS[ArenaButton.STREAMS]}
    assert (
        others & set(TOOL_KEYS.values()) == shared == {TOOL_KEYS[Tool.MOVE], TOOL_KEYS[Tool.WIRE]}
    )
    ours = others | set(TURN_KEYS)
    assert len(ours) == len(BUTTON_KEYS) + len(TURN_KEYS) + 2  # and no key twice here


def test_every_button_has_a_key_and_typed_ones_find_their_button():
    assert set(BUTTON_KEYS) == set(ArenaButton)
    for key, button in KEY_BUTTONS.items():
        assert BUTTON_KEYS[button] == key and len(key) == 1


@pytest.mark.parametrize(
    ("limit", "ticks"),
    [
        (4, [0, 1, 2, 3, 4]),
        (10, [0, 2, 4, 6, 8, 10]),
        (15, [0, 5, 10, 15]),
        (20, [0, 5, 10, 15, 20]),
        (45, [0, 10, 20, 30, 40]),
        (120, [0, 30, 60, 90, 120]),
    ],
)
def test_scores_time_axis_is_ticked_in_round_seconds_a_few_times(limit, ticks):
    assert time_ticks(limit) == ticks and len(ticks) <= TIME_TICKS  # D-340
