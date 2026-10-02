"""The Settings drawer's choices (D-054). settings.py imports no pygame."""

from nektoids.editor.settings import FAST_CHOICES, Settings


def test_each_setting_steps_through_its_choices_and_comes_round_again():
    settings = Settings()
    assert (settings.fast, settings.key_hints, settings.tooltip_frames) == (4, True, 60)
    seen = []
    for _ in FAST_CHOICES:
        settings.next_fast()
        seen.append(settings.fast)
    assert sorted(seen) == sorted(FAST_CHOICES) and settings.fast == 4
    settings.toggle_hints()
    assert not settings.key_hints


def test_a_value_off_the_list_steps_to_the_first_choice():
    settings = Settings(fast=3)
    settings.next_fast()
    assert settings.fast == FAST_CHOICES[0]
