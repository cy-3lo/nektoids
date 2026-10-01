from nektoids.editor.arena_layout import (
    ARENA_AREA,
    BUTTON_KEYS,
    CIRCUIT_AREA,
    KEY_BUTTONS,
    MAP_KEY,
    PANEL_LEFT,
    PLAYER,
    POLAR_KEY,
    RULES,
    SCORE_AREA,
    TURN_KEYS,
    VIEW,
    ArenaButton,
    button_at,
    button_rects,
)
from nektoids.editor.layout import SCREEN, TOOL_KEYS, VIEW_KEYS, Tool, ViewButton


def test_the_palettes_sit_on_two_rows_in_the_column_without_overlapping():
    rects = dict(button_rects())
    assert list(rects) == [*PLAYER, *VIEW] and len(rects) == 10
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
