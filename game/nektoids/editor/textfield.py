"""A field of text typed or pasted in (D-206, D-305): Paste a board at Files' foot, the Editor's
title and spec in Text (D-318).

It holds its text, a caret, where the next character goes, and an anchor, the selection's other
end, when some text is selected (D-418). Natively the scene hands it pygame's keys: a character
it takes replaces the selection, or goes in at the caret; Backspace and Delete take out the
selection, else one character either side of the caret; the arrows, Home and End move the
caret, and with Shift they select; Ctrl or Cmd+A selects it all; a click places the caret and a
drag selects (`place`). On the web the page's own text field takes the keys and the paste
(`clipboard.py`), and the field takes what the page holds once a frame, its selection too
(`take`). Each field says what it takes, a set of characters or any printable one, and how long
it may grow. `wrapped` lays its text out in lines that fit, for a field taller than a line.
Pure Python, no pygame.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

LONGEST = 400  # characters, unless a field says otherwise
MOVES = ("left", "right", "home", "end")


@dataclass
class TextField:
    text: str = ""
    taken: frozenset[str] | None = None  # the characters it takes; None: any printable one
    longest: int = LONGEST
    caret: int = -1  # where the next character goes, 0 to len(text); -1: after the text
    anchor: int | None = None  # the selection's other end; None: nothing selected

    def __post_init__(self) -> None:
        self.text = self._kept(self.text)
        self.caret = len(self.text) if self.caret < 0 else min(self.caret, len(self.text))

    def takes(self, char: str) -> bool:
        return char in self.taken if self.taken is not None else char.isprintable()

    @property
    def selection(self) -> tuple[int, int] | None:
        """The selected text's ends, the first before the last; None if none is selected."""
        if self.anchor is None or self.anchor == self.caret:
            return None
        return min(self.anchor, self.caret), max(self.anchor, self.caret)

    def selected(self) -> str:
        span = self.selection
        return "" if span is None else self.text[span[0] : span[1]]

    def type(self, name: str, char: str, shift: bool = False, command: bool = False) -> str | None:
        """A key, by its pygame name and the character it types, Shift or Ctrl/Cmd held:
        "enter" or "escape" when the field is done, else None, the key done in the field."""
        if name == "escape":
            return "escape"
        if name in ("return", "enter"):
            return "enter"
        if command:
            if name == "a":
                self.anchor, self.caret = 0, len(self.text)
            return None
        if name in MOVES:
            self._move(name, shift)
        elif name in ("backspace", "delete"):
            if not self.cut():
                at = self.caret - (name == "backspace")
                if 0 <= at < len(self.text):
                    self.text = self.text[:at] + self.text[at + 1 :]
                    self.caret = at
        elif len(char) == 1 and self.takes(char):
            self.paste(char)
        return None

    def _move(self, name: str, shift: bool) -> None:
        """The caret moved; with Shift the selection grows from where it was; without, a
        selection collapses to its end that way."""
        span = self.selection
        if shift and self.anchor is None:
            self.anchor = self.caret
        if not shift and span is not None and name in ("left", "right"):
            self.caret, self.anchor = (span[0] if name == "left" else span[1]), None
            return
        if name in ("left", "right"):
            self.caret = min(len(self.text), max(0, self.caret + (1 if name == "right" else -1)))
        else:
            self.caret = 0 if name == "home" else len(self.text)
        if not shift:
            self.anchor = None

    def cut(self) -> str:
        """The selected text taken out, the caret where it was; what was taken."""
        span = self.selection
        self.anchor = None
        if span is None:
            return ""
        taken = self.text[span[0] : span[1]]
        self.text, self.caret = self.text[: span[0]] + self.text[span[1] :], span[0]
        return taken

    def paste(self, text: str) -> None:
        """Text pasted in place of the selection, or at the caret: what the field takes of it,
        as far as it may grow."""
        self.cut()
        room = self.longest - len(self.text)
        added = self._kept(text)[: max(0, room)]
        self.text = self.text[: self.caret] + added + self.text[self.caret :]
        self.caret += len(added)

    def place(self, at: int, extend: bool = False) -> None:
        """The caret put at `at`, a click; with `extend`, a drag, the selection from where the
        press put it."""
        at = min(max(0, at), len(self.text))
        if extend and self.anchor is None:
            self.anchor = self.caret
        self.caret = at
        if not extend:
            self.anchor = None

    def take(self, text: str, caret: int, anchor: int | None = None) -> None:
        """What the page's own field holds, its caret and the selection's other end (web): the
        characters this one does not take left out, the ends moved back by those before them."""
        self.caret = min(len(self._kept(text[:caret])), len(self._kept(text)))
        kept = None if anchor is None else len(self._kept(text[:anchor]))
        self.text = self._kept(text)
        self.anchor = None if kept is None or kept == self.caret else min(kept, len(self.text))

    def _kept(self, text: str) -> str:
        """What the field takes of `text`, a line break a space if it takes no line break, so
        lines pasted run on as words do (D-413)."""
        spaced = (" " if c in "\r\n" and not self.takes(c) else c for c in text)
        return "".join(c for c in spaced if self.takes(c))[: self.longest]


def wrapped(text: str, fits: Callable[[str], bool]) -> list[tuple[int, str]]:
    """`text` in lines that each `fits`, broken after a space where one may be, else anywhere:
    each line with where it starts in `text`, so a caret finds its line. The spaces stay, at the
    ends of the lines they break; a text with nothing is one empty line."""
    lines: list[tuple[int, str]] = []
    start = 0
    while start < len(text):
        end = start + 1
        while end < len(text) and fits(text[start : end + 1]):
            end += 1
        if end < len(text):  # back to the last space that fits, if there is one
            space = text.rfind(" ", start, end)
            end = space + 1 if space >= start else end
        lines.append((start, text[start:end]))
        start = end
    return lines or [(0, "")]


def caret_at(lines: list[tuple[int, str]], caret: int) -> tuple[int, int]:
    """The line the caret is on, and how far along it: (line, characters)."""
    k = max(i for i, (start, _) in enumerate(lines) if start <= caret)
    return k, caret - lines[k][0]


def shown_from(text: str, caret: int | None, fits: Callable[[str], bool]) -> int:
    """The first character a field of one line shows: the text slides left as far as the
    caret needs to show."""
    start = 0
    while caret is not None and start < caret and not fits(text[start:caret]):
        start += 1
    return start


def index_at(text: str, start: int, advance: float, dx: float) -> int:
    """The place between two characters nearest `dx` [px] from where the text is shown from
    `start`, each character `advance` wide."""
    return min(len(text), max(0, start + round(dx / advance)))


def index_in_lines(lines: list[tuple[int, str]], row: int, advance: float, dx: float) -> int:
    """The same in a field of `wrapped` lines: on line `row`, clamped to the lines there are,
    no farther than its last character but the space that breaks it."""
    row = min(max(0, row), len(lines) - 1)
    start, words = lines[row]
    end = len(words.rstrip(" ")) if row < len(lines) - 1 else len(words)
    return start + min(end, max(0, round(dx / advance)))
