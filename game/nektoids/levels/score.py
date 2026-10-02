"""A level's score (D-028, D-045): the time a run took to win and the number of parts its board
holds. The two pull apart (brief §1: several incompatible axes), so one run beats another only
if it is no slower and no bigger, and better on one of the two. The session's wins of a level
are points in that plane; those no other beats are its Pareto front. Nothing is kept after the
session. Pure Python, no pygame.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Score:
    parts: int  # complexity(board) (D-045)
    ticks: int  # the tick the run was won at: exact, where seconds would not be

    def beats(self, other: Score) -> bool:
        """No more parts and no slower than `other`, and not the same score."""
        return self.parts <= other.parts and self.ticks <= other.ticks and self != other


def front(scores: Iterable[Score]) -> tuple[Score, ...]:
    """The scores no other beats, each once, by parts: fewer parts, then slower."""
    unique = sorted(set(scores))
    return tuple(s for s in unique if not any(o.beats(s) for o in unique))
