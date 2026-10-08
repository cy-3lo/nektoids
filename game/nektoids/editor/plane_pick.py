"""What is picked on the Editor's plane (D-410), as the Board picks its parts (D-402, D-406): an
object is an item, by its index in the level, or the swimmer's start. A click picks the one
object clicked, and a click on the only one picked drops it; with the add key, Shift or Cmd, it
adds the object or drops it. A click on the open plane drops the pick. A drag from the open
plane picks the objects it crosses; going back onto one already crossed cuts the path back to
it, however far. When items go, the pick keeps the others, their indices moved up. Pure Python,
no pygame.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from nektoids.editor.layout import Piece

Object = int | Piece  # an item, by its index in the level; Piece.START, the swimmer's start
Pick = tuple[Object, ...]  # in the order picked

NOTHING: Pick = ()


def clicked(pick: Pick, target: Object | None, add: bool = False) -> Pick:
    """The pick after a click with Select on `target`, None on the open plane."""
    if target is None:
        return pick if add else NOTHING
    if not add:
        return NOTHING if pick == (target,) else (target,)
    if target in pick:
        return tuple(o for o in pick if o != target)
    return (*pick, target)


@dataclass(frozen=True)
class Sweep:
    """A drag picking the objects it crosses; `base`, what was picked before, kept with the add
    key."""

    path: Pick = ()
    base: Pick = ()

    @property
    def pick(self) -> Pick:
        return tuple(dict.fromkeys((*self.base, *self.path)))


def begun(pick: Pick, add: bool = False) -> Sweep:
    return Sweep((), pick if add else NOTHING)


def crossed(sweep: Sweep, target: Object | None) -> Sweep:
    """The sweep as the mouse comes over `target`: an object of its path cuts the path back to
    it; another is added; the open plane leaves it."""
    if target is None:
        return sweep
    if target in sweep.path:
        return Sweep(sweep.path[: sweep.path.index(target) + 1], sweep.base)
    return Sweep((*sweep.path, target), sweep.base)


def items(pick: Pick) -> list[int]:
    """The items picked, by index, without the swimmer's start."""
    return [o for o in pick if isinstance(o, int)]


def after_removal(pick: Pick, gone: Iterable[int]) -> Pick:
    """The pick once items `gone` are out of the level: theirs dropped, the others' indices moved
    up past each one gone before them."""
    gone = sorted(set(gone))
    kept = []
    for o in pick:
        if isinstance(o, int):
            if o in gone:
                continue
            o -= sum(1 for g in gone if g < o)
        kept.append(o)
    return tuple(kept)
