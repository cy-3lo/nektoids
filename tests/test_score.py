"""A level's score: time to win against parts, and the Pareto front (D-028, D-045)."""

from nektoids.levels.score import Score, front


def test_a_score_beats_another_only_if_no_worse_on_both_axes_and_not_the_same():
    fast_big, slow_small = Score(parts=8, ticks=900), Score(parts=4, ticks=1200)
    assert not fast_big.beats(slow_small) and not slow_small.beats(fast_big)  # they pull apart
    assert Score(4, 900).beats(fast_big) and Score(4, 900).beats(slow_small)
    assert not Score(4, 900).beats(Score(4, 900))


def test_the_front_keeps_the_scores_no_other_beats_each_once_by_parts():
    scores = [Score(8, 900), Score(4, 1200), Score(6, 1300), Score(4, 1200), Score(10, 900)]
    assert front(scores) == (Score(4, 1200), Score(8, 900))
    assert front([]) == ()
