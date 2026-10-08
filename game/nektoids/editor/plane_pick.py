"""What is picked on the Editor's plane (D-410), as the Board picks its parts (D-402, D-406): an
object is an item, by its index in the level, or the swimmer's start. A click picks the one
object clicked, and a click on the only one picked drops it; with the add key, Shift or Cmd, it
adds the object or drops it. A click on the open plane drops the pick. A drag from the open
plane draws a rectangle, which picks the objects whose centres lie inside it. When items go,
the pick keeps the others, their indices moved up. Pure Python, no pygame.
"""

from __future__ import annotations

from collections.abc import Iterable

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


def boxed(
    pick: Pick,
    centres: dict[Object, tuple[float, float]],
    corner: tuple[float, float],
    other: tuple[float, float],
    add: bool = False,
) -> Pick:
    """The pick of a rectangle dragged from `corner` to `other` on the screen: the objects whose
    `centres` [px] lie inside it, in their order; with `add`, after what was picked (D-410)."""
    (x0, y0), (x1, y1) = corner, other
    left, right, top, bottom = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
    inside = [o for o, (x, y) in centres.items() if left <= x <= right and top <= y <= bottom]
    return tuple(dict.fromkeys((*(pick if add else ()), *inside)))


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
