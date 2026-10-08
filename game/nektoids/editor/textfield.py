"""A field of text typed or pasted in (D-206, D-305): Paste a board at Files' foot, the Editor's
title and spec in Text (D-318).

It holds its text and a caret, where the next character goes. Natively the scene hands it
pygame's keys: a character it takes goes in at the caret; Backspace and Delete take one out
either side of it; the arrows, Home and End move it; Enter and Esc end the field. On the web the
page's own text field takes the keys and the paste (`clipboard.py`), and the field takes what the
page holds once a frame (`take`). Each field says what it takes, a set of characters or any
printable one, and how long it may grow. `wrapped` lays its text out in lines that fit, for a
field taller than a line. Pure Python, no pygame.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

LONGEST = 400  # characters, unless a field says otherwise


@dataclass
class TextField:
    text: str = ""
    taken: frozenset[str] | None = None  # the characters it takes; None: any printable one
    longest: int = LONGEST
    caret: int = -1  # where the next character goes, 0 to len(text); -1: after the text

    def __post_init__(self) -> None:
        self.text = self._kept(self.text)
        self.caret = len(self.text) if self.caret < 0 else min(self.caret, len(self.text))

    def takes(self, char: str) -> bool:
        return char in self.taken if self.taken is not None else char.isprintable()

    def type(self, name: str, char: str) -> str | None:
        """A key, by its pygame name and the character it types: "enter" or "escape" when the
        field is done, else None, the key done in the field."""
        if name == "escape":
            return "escape"
        if name in ("return", "enter"):
            return "enter"
        if name == "backspace" and self.caret > 0:
            self.text = self.text[: self.caret - 1] + self.text[self.caret :]
            self.caret -= 1
        elif name == "delete":
            self.text = self.text[: self.caret] + self.text[self.caret + 1 :]
        elif name in ("left", "right"):
            self.caret = min(len(self.text), max(0, self.caret + (1 if name == "right" else -1)))
        elif name in ("home", "end"):
            self.caret = 0 if name == "home" else len(self.text)
        elif len(char) == 1 and self.takes(char):
            self.paste(char)
        return None

    def paste(self, text: str) -> None:
        """Text pasted in at the caret: what the field takes of it, as far as it may grow."""
        room = self.longest - len(self.text)
        added = self._kept(text)[: max(0, room)]
        self.text = self.text[: self.caret] + added + self.text[self.caret :]
        self.caret += len(added)

    def take(self, text: str, caret: int) -> None:
        """What the page's own field holds, and its caret (web): the characters this one does
        not take left out, the caret moved back by those before it."""
        self.caret = len(self._kept(text[:caret]))
        self.text = self._kept(text)
        self.caret = min(self.caret, len(self.text))

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
