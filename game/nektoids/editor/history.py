"""Undo and redo for the editor (D-027): whole board states, not the edits that led to them.

Routes depend on the order the wires were drawn and never move (D-007), so replaying edits could
route a wire differently; putting a saved state back cannot. A board holds a few dozen frozen
parts and wires, so keeping a hundred of them costs nothing. Pure Python, no pygame.
"""

from __future__ import annotations

from nektoids.graph.board import BoardState

LIMIT = 100  # states kept for undo; the oldest go first


class History:
    def __init__(self, limit: int = LIMIT) -> None:
        self.limit = limit
        self._undo: list[BoardState] = []  # oldest first
        self._redo: list[BoardState] = []  # the next one to redo last

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def record(self, before: BoardState) -> None:
        """An edit was made from `before`: it can be undone, and what was undone can no longer
        be redone."""
        self._undo.append(before)
        del self._undo[: -self.limit]
        self._redo.clear()

    def undo(self, now: BoardState) -> BoardState | None:
        """The state before the last edit, `now` kept for redo; None if there is nothing to undo."""
        if not self._undo:
            return None
        self._redo.append(now)
        return self._undo.pop()

    def redo(self, now: BoardState) -> BoardState | None:
        """The state the last undo left, `now` kept for undo; None if there is nothing to redo."""
        if not self._redo:
            return None
        self._undo.append(now)
        return self._redo.pop()
