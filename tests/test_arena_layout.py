import pytest

from nektoids.editor.arena_layout import (
    ARENA_AREA,
    BANNER,
    BUTTON_KEYS,
    CIRCUIT_AREA,
    KEY_BUTTONS,
    MAP_KEY,
    PANEL_LEFT,
    PLAYER,
    POLAR_KEY,
    RULES,
    SCORE_AREA,
    TIMELINE,
    TURN_KEYS,
    VIEW,
    ArenaButton,
    banner_button_at,
    banner_rects,
    button_at,
    button_rects,
    timeline_at,
    timeline_x,
)
from nektoids.editor.layout import SCREEN, TOOL_KEYS, VIEW_KEYS, Tool, ViewButton


def test_the_palettes_sit_on_two_rows_in_the_column_without_overlapping():
    rects = dict(button_rects())
    assert list(rects) == [*PLAYER, *VIEW] and len(PLAYER) == len(VIEW) == 5  # equal rows
    for palette in (PLAYER, VIEW):
        row = [rects[b] for b in palette]
        assert len({y for _, y, _, _ in row}) == 1
        for (x, _, w, _), (x2, _, _, _) in zip(row, row[1:], strict=False):
            assert x + w < x2
    player_y, view_y = rects[PLAYER[0]][1], rects[VIEW[0]][1]
    assert player_y + rects[PLAYER[0]][3] < view_y
    for x, y, w, h in rects.values():
        assert PANEL_LEFT < x and x + w < SCREEN[0] and y + h < RULES[0]


def test_a_press_finds_the_button_under_it_and_nothing_between_them():
    for button, (x, y, w, h) in button_rects():
        assert button_at((x + w // 2, y + h // 2)) is button
    x, y, w, h = dict(button_rects())[ArenaButton.STEP]
    assert button_at((x + w + 2, y + h // 2)) is None
    assert button_at((10, 10)) is None  # the arena


def test_the_column_runs_palettes_then_objectives_then_wiring_and_the_arena_fills_the_left():
    assert RULES[0] < SCORE_AREA[1] and SCORE_AREA[1] + SCORE_AREA[3] <= RULES[1]
    assert RULES[1] < CIRCUIT_AREA[1] and CIRCUIT_AREA[1] + CIRCUIT_AREA[3] == SCREEN[1]
    assert ARENA_AREA[0] + ARENA_AREA[2] == PANEL_LEFT


def test_a_key_means_the_same_here_as_in_the_editor():
    same = {
        ArenaButton.ZOOM_IN: ViewButton.ZOOM_IN,
        ArenaButton.ZOOM_OUT: ViewButton.ZOOM_OUT,
        ArenaButton.HAND: ViewButton.PAN,
        ArenaButton.CENTRE: ViewButton.CENTRE,
    }
    for here, there in same.items():
        assert BUTTON_KEYS[here] == VIEW_KEYS[there]
    # Turning the swimmer left and right, as the editor turns a part (D-025).
    assert TURN_KEYS == (TOOL_KEYS[Tool.TURN_LEFT], TOOL_KEYS[Tool.TURN_RIGHT])
    others = {*BUTTON_KEYS.values(), MAP_KEY, POLAR_KEY}
    assert not others & set(TOOL_KEYS.values())  # nothing else means an editor tool here
    ours = others | set(TURN_KEYS)
    assert len(ours) == len(BUTTON_KEYS) + len(TURN_KEYS) + 2  # and no key twice here


def test_every_button_has_a_key_and_typed_ones_find_their_button():
    assert set(BUTTON_KEYS) == set(ArenaButton)
    for key, button in KEY_BUTTONS.items():
        assert BUTTON_KEYS[button] == key and len(key) == 1


def test_the_banner_holds_its_buttons_side_by_side_and_finds_them():
    both = (ArenaButton.NEXT, ArenaButton.EDIT)
    (_, (x1, y1, w1, h1)), (_, (x2, y2, _, _)) = banner_rects(both)
    bx, by, bw, bh = BANNER
    assert y1 == y2 and x1 + w1 < x2 and bx < x1 and x2 + w1 < bx + bw and y1 + h1 < by + bh
    assert banner_button_at(both, (x1 + 5, y1 + 5)) is ArenaButton.NEXT
    assert banner_button_at((ArenaButton.EDIT,), (x1 + 5, y1 + 5)) is None  # one button: centred
    assert ARENA_AREA[0] <= bx and bx + bw <= ARENA_AREA[0] + ARENA_AREA[2]


def test_the_timeline_runs_from_zero_to_the_limit_under_the_buttons_and_finds_a_time():
    x, y, w, h = TIMELINE
    lowest = max(by + bh for _, (_, by, _, bh) in button_rects())
    assert lowest < y and y + h <= RULES[0] and PANEL_LEFT < x and x + w < PANEL_LEFT + 320
    assert timeline_x(0.0, 20.0) == x and timeline_x(20.0, 20.0) == x + w
    assert timeline_x(30.0, 20.0) == x + w  # past the limit: at the end
    assert timeline_at((x + w // 2, y + h // 2), 20.0) == pytest.approx(10.0, abs=0.1)
    assert timeline_at((x + w // 2, y - 1), 20.0) is None
