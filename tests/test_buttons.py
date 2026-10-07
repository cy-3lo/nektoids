"""The Board's buttons (D-401): their places round the board, the same on every level."""

from nektoids.editor.buttons import FRAME, PLACES, Button
from nektoids.graph.board import Kind
from nektoids.graph.hexgrid import hex_disc, hex_distance, to_pixel


def test_every_button_and_part_has_a_place_of_its_own_off_the_largest_zone():
    assert set(PLACES) == {*Button, *Kind}
    assert len(set(PLACES.values())) == len(PLACES)
    zone = set(hex_disc(3))
    assert all(cell not in zone for cell in PLACES.values())
    assert all(hex_distance(cell, (0, 0)) in (4, 5) for cell in PLACES.values())  # round it
    assert set(FRAME) == zone | set(PLACES.values())


def test_the_tools_sit_at_n_and_s_in_rows_and_the_pairs_side_by_side():
    n = [Button.SELECT, Button.MOVE, Button.LOCK]
    s = [Button.UNDO, Button.REDO, Button.DELETE]
    for row, r in ((n, -4), (s, 4)):
        cells = [PLACES[b] for b in row]
        assert all(cell[1] == r for cell in cells)
        assert [q for q, _ in cells] == list(range(cells[0][0], cells[0][0] + len(cells)))
    xs = [to_pixel(PLACES[b], 1.0, (0.0, 0.0))[0] for b in s]
    assert sum(xs) / len(xs) == 0.0  # S centred under the board
    pairs = (
        (Button.TURN_LEFT, Button.TURN_RIGHT),
        (Kind.DOUBLE, Kind.HALVE),
        (Kind.SUM, Kind.DIFFERENCE),
        (Button.UNDO, Button.REDO),
    )
    for left, right in pairs:  # side by side in a row, the first on the left
        (q0, r0), (q1, r1) = PLACES[left], PLACES[right]
        assert r0 == r1 and q1 == q0 + 1
    assert all(PLACES[k][0] > 0 for k in Kind)  # the parts at E
    assert all(PLACES[b][0] < 0 for b in (Button.TURN_LEFT, Button.TURN_RIGHT, Button.WIRE))
