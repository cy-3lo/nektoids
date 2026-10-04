"""The table of kinds (D-202): one entry per kind, each whole. kinds.py imports no pygame."""

from nektoids.editor.devdrive import DT
from nektoids.editor.geometry import SHAPES
from nektoids.editor.glyphs import GLYPH, POINTS_TO
from nektoids.editor.layout import Tool
from nektoids.graph.board import Kind
from nektoids.graph.kinds import SPEC, Category
from nektoids.sim.world import ACTIONS, SENSES


def test_every_kind_has_one_entry_in_the_order_kinds_are_listed():
    assert list(SPEC) == list(Kind)
    for kind in Kind:
        assert kind.spec is SPEC[kind] and kind.spec.name and kind.spec.what, kind


def test_a_sensors_rate_is_given_every_other_part_follows_a_law():
    for kind in Kind:
        law = kind.spec.law
        if kind.category is Category.SENSOR:
            assert law is None and not kind.receives, kind  # no law: no rate held at 0 by mistake
        else:
            assert law is not None and law.slope > 0.0, kind


def test_every_law_is_stable_for_the_tick_of_the_run():
    assert all(DT <= kind.spec.law.max_dt for kind in Kind if kind.spec.law), DT


def test_letters_and_names_tell_the_kinds_apart():
    letters = [kind.spec.letter for kind in Kind]
    assert all(len(letter) == 1 and letter.isupper() for letter in letters)
    assert len(set(letters)) == len(letters)
    assert len({kind.spec.name for kind in Kind}) == len(Kind)


def test_limits_on_wires_are_counts_and_only_parts_that_turn_have_a_facing():
    for kind in Kind:
        assert kind.max_inputs is None or kind.max_inputs > 0, kind
        assert kind.max_outputs is None or kind.max_outputs > 0, kind
        assert kind.default_facing is None or kind.category is not Category.OPERATOR, kind


def test_no_kind_is_spelled_as_a_tool():
    # A tutorial's data names parts and tools alike (`editor/tutorial.py`): never the same word.
    assert not {kind.value for kind in Kind} & {tool.value for tool in Tool}


def test_every_part_is_drawn_with_an_outline_and_an_icon_the_font_has():
    for kind in Kind:
        assert kind.spec.shape in SHAPES, kind
        assert kind.spec.icon is None or kind.spec.icon in GLYPH, kind
        if kind.spec.icon in POINTS_TO:  # an icon that points must belong to a part that turns
            assert kind.default_facing is not None, kind


def test_every_sensor_has_a_sense_and_every_actuator_an_action_the_simulation_knows():
    for kind in Kind:  # a sensor without its sense would read 0; an actuator would do nothing
        sensor, actuator = kind.category is Category.SENSOR, kind.category is Category.ACTUATOR
        assert (kind.spec.sense in SENSES) if sensor else kind.spec.sense is None, kind
        assert (kind.spec.action in ACTIONS) if actuator else kind.spec.action is None, kind
