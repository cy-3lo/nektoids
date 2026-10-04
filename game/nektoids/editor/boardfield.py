"""Load's field at Files' foot, and what loading a board's text does (D-206).

The field holds what is pasted or typed into it. On the web the page's own text field takes the
keys and the paste (`clipboard.py`); natively the editor hands it pygame's keys. Enter loads:
the text gives a board (D-205), which goes on the open level as a win of another level does
(`Board.adopt`, D-092), or the status line says why it does not. Pure Python, no pygame.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from nektoids.graph import boardtext
from nektoids.graph.board import Board

TAKEN = frozenset(boardtext.READ) | frozenset(boardtext.IGNORED)  # what the field accepts
LONGEST = 400  # characters, far more than any board's text


@dataclass
class BoardField:
    text: str = ""

    def type(self, name: str, char: str) -> str | None:
        """A key, by its pygame name and the character it types: one the field accepts is
        added, Backspace takes one back; "enter" or "escape" when the field is done, else None."""
        if name == "escape":
            return "escape"
        if name in ("return", "enter"):
            return "enter"
        if name == "backspace":
            self.text = self.text[:-1]
        elif len(char) == 1 and char in TAKEN:
            self.paste(char)
        return None

    def paste(self, text: str) -> None:
        """Text pasted in: what the field accepts of it, up to LONGEST characters in all."""
        self.text = (self.text + "".join(c for c in text if c in TAKEN))[:LONGEST]


def load(board: Board, text: str) -> tuple[bool, str]:
    """Put the board that `text` holds on `board`, the level's: (True, what the status line
    says) if it went on, (False, why not) if not, `board` unchanged. Parts of the text on the
    cells of the level's locked parts, as they are placed, are those parts."""
    if not text.strip():
        return False, "paste a board's text into the field first"
    try:
        read, corrected = boardtext.read(text)
    except ValueError as error:
        return False, str(error)
    locked = {(n.kind, n.cell, n.facing) for n in board.nodes.values() if n.locked}
    state = read.snapshot()
    nodes = tuple(replace(n, locked=(n.kind, n.cell, n.facing) in locked) for n in state.nodes)
    refused = board.adopt(replace(state, nodes=nodes))
    if refused is not None:
        return False, refused.reason
    parts, wires = len(state.nodes), len(state.wires)
    said = f"Loaded: {parts} part{'s' * (parts != 1)}, {wires} wire{'s' * (wires != 1)}"
    return True, said + (", one mistyped character put right." if corrected else ".")
