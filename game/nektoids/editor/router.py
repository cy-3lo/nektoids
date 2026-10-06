"""Where the player is: the title card, a level being built or watched, the end.

The loop of the brief (§1): the spec and the board in the editor, Run, watch the run, back to
the editor to change the mechanism, or on to the next level once won (D-030). Around it (D-035,
D-054): the game opens on the first level under a title card; the Chapters drawer lists the
levels by chapter, one route through them all (D-325), and the sandbox, each level opening once
the one before it is won; after the last level comes the end. A level opened from Chapters or by
Next level comes up under its card, which says what it asks, then on its run, paused, the board
as it stands (D-069). On the sandbox, a third screen, the Maker, makes its level, which the
editor and the run try (D-301). Each level keeps its board for the session, so going back finds
it as it was left, and the scores of its wins (D-028); nothing is kept after it. Pure Python, no
pygame: `main.py` turns the state into scenes.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from nektoids.graph.board import Board, BoardState
from nektoids.levels.arenas import CHAPTERS, locate
from nektoids.levels.level import Level
from nektoids.levels.score import Score, front


def level_number(index: int) -> str:
    """The number of the route's level at `index`: its chapter's, then its place there, "2.1"
    (D-325)."""
    chapter, k = locate(index)
    return f"{chapter.number}.{k + 1}"


def level_label(index: int) -> str:
    """How the route's level at `index` is named on screen, before its title (D-034)."""
    return f"LEVEL {level_number(index)}"


@dataclass(frozen=True)
class ChapterRow:
    """A place as the Chapters drawer shows it (D-054)."""

    index: int
    label: str  # "1.2", or "" for the sandbox
    title: str
    spec: str  # what it asks, for its info box
    state: str  # "won", "open", "locked", "sandbox"
    best: Score | None  # the fastest win this session
    current: bool  # the place open now
    passkey: str = ""  # won: the word its win gave, which opens the next level (D-075)


@dataclass(frozen=True)
class Won:
    """A win of a level this session, as Files shows it (D-059): its score, the board that won
    it, and whether no other win beats it."""

    score: Score
    board: BoardState
    best: bool


@dataclass(frozen=True)
class WinGroup:
    """A level's wins this session, under its title in Files, a group that folds (D-092)."""

    index: int  # the level's place on the route
    title: str  # "1.2 Aggression"
    wins: tuple[Won, ...]  # as `Router.wins` orders them


class Screen(Enum):
    TITLE = "title"  # the card over the first level, gone at the first click
    SPEC = "spec"  # a level's card: its name and what it asks, gone at the first click
    EDIT = "edit"  # a level's board in the editor
    RUN = "run"  # the level's board swimming in its arena
    MAKE = "make"  # the sandbox's level, made in the Maker (D-301)
    END = "end"  # after the route's last level


class Router:
    def __init__(self, levels: Sequence[Level], sandbox: Level | None = None) -> None:
        self.levels = list(levels)  # the route, every chapter's levels in order
        self.sandbox = sandbox  # no objective; always open
        self.index = 0  # the open place: a level on the route, or `sandbox_index`
        self.screen = Screen.TITLE
        self.won: set[int] = set()  # the levels won this session
        self.opened: set[int] = set()  # the levels a passkey opened this session (D-075)
        self.folded = self._all_but(0)  # Chapters' chapters shown closed, by title (D-326)
        self._boards: dict[int, Board] = {}
        self._scores: dict[int, set[Score]] = {}
        self._won_with: dict[int, dict[Score, BoardState]] = {}  # each score's first board

    @property
    def sandbox_index(self) -> int:
        return len(self.levels)

    @property
    def in_sandbox(self) -> bool:
        return self.index == self.sandbox_index

    @property
    def level(self) -> Level:
        return self.sandbox if self.in_sandbox else self.levels[self.index]

    @property
    def board(self) -> Board:
        """The open level's board: its own, fresh the first time, then as the player left it."""
        if self.index not in self._boards:
            self._boards[self.index] = self.level.new_board()
        return self._boards[self.index]

    @property
    def label(self) -> str:
        return "SANDBOX" if self.in_sandbox else level_label(self.index)

    @property
    def has_next(self) -> bool:
        """A level comes after the open one on the route."""
        return not self.in_sandbox and self.index + 1 < len(self.levels)

    @property
    def is_last(self) -> bool:
        """The open level is the route's last: winning it leads to the end."""
        return not self.in_sandbox and self.index + 1 == len(self.levels)

    @property
    def scores(self) -> frozenset[Score]:
        """The open level's wins this session, each score once; none for the sandbox."""
        return frozenset(self._scores.get(self.index, ()))

    def best(self, index: int) -> Score | None:
        """The fastest of a level's wins this session, if it has any (D-054)."""
        scores = self._scores.get(index, ())
        return min(scores, key=lambda s: (s.ticks, s.parts)) if scores else None

    def state(self, index: int) -> str:
        """How Chapters shows a place: "won", "open", "locked", or "sandbox"."""
        if index == self.sandbox_index:
            return "sandbox"
        if index in self.won:
            return "won"
        return "open" if self.unlocked(index) else "locked"

    def rows(self) -> tuple[ChapterRow, ...]:
        """What Chapters shows: the levels, then the sandbox."""
        places = [*self.levels, self.sandbox] if self.sandbox is not None else list(self.levels)
        return tuple(
            ChapterRow(
                k,
                "" if k == self.sandbox_index else level_number(k),
                place.title,
                place.spec,
                self.state(k),
                self.best(k),
                k == self.index,
                self._word_won(k),
            )
            for k, place in enumerate(places)
        )

    def _word_won(self, index: int) -> str:
        """A level's word, once won, if it opens a next level: Chapters shows it (D-075)."""
        if index not in self.won or not self._word_opens(index):
            return ""
        return self.levels[index].passkey

    def _word_opens(self, index: int) -> bool:
        """Whether the word of the level at `index` opens the level after it: not the last's,
        nor a chapter's last, whose next level opens a chapter, open from the start (D-325)."""
        last = index + 1 >= len(self.levels)
        return bool(self.levels[index].passkey) and not last and locate(index + 1)[1] > 0

    def _all_but(self, index: int) -> set[str]:
        """Every chapter's title but that of the route's level at `index`: Chapters as it opens
        on a chapter (D-326)."""
        return {chapter.heading for chapter in CHAPTERS} - {locate(index)[0].heading}

    def fold(self, title: str) -> None:
        """A chapter's title clicked in Chapters: its levels fold away, or show again."""
        self.folded ^= {title}

    def _go(self, index: int) -> None:
        """The place at `index` is the open one. A level whose chapter Chapters shows closed
        folds every other chapter instead, so that the open level's row always shows; one whose
        chapter shows keeps the player's folds, as the sandbox does (D-326)."""
        if index != self.sandbox_index and locate(index)[0].heading in self.folded:
            self.folded = self._all_but(index)
        self.index = index

    def unlocked(self, index: int) -> bool:
        """Each chapter's first level, any level after one won, any a passkey opened, and the
        sandbox are open (D-075, D-325)."""
        first = index == self.sandbox_index or locate(index)[1] == 0
        return first or index - 1 in self.won or index in self.opened

    def unlock(self, word: str) -> int | None:
        """A passkey typed (D-075): the level after the one whose win gives `word`, in any case,
        opens, with every level before it, none of them won; that level's index, or None if no
        level's word opens one (the last level's opens nothing yet)."""
        word = word.strip().upper()
        for k, level in enumerate(self.levels[:-1]):
            if level.passkey == word:
                self.opened |= set(range(k + 2))
                self.folded -= {locate(k + 1)[0].heading}  # it shows, open, in Chapters
                return k + 1
        return None

    def next_passkey(self) -> tuple[str, str] | None:
        """The open level's word and the label of the level it opens, for its win card (D-075);
        None in the sandbox, or with no word that opens a level."""
        if self.in_sandbox or not self._word_opens(self.index):
            return None
        return self.level.passkey, level_label(self.index + 1)

    # Moving about

    def begin(self) -> None:
        """The card goes, the title card or a level's; the level opens on its run, paused
        (D-069)."""
        self.screen = Screen.RUN

    def open(self, index: int) -> None:
        """A place from Chapters, under its card; ValueError if it is still locked."""
        if not self.unlocked(index):
            raise ValueError(f"{level_label(index)} opens once the level before it is won")
        self._go(index)
        self.screen = Screen.SPEC

    def run(self) -> None:
        self.screen = Screen.RUN

    def edit(self) -> None:
        self.screen = Screen.EDIT

    def make(self) -> None:
        """The Maker, the sandbox's alone (D-301); ValueError on a level of the route."""
        if not self.in_sandbox:
            raise ValueError("only the sandbox's level is made in the Maker")
        self.screen = Screen.MAKE

    def revise(self, level: Level) -> None:
        """The sandbox's level as the Maker leaves it (D-301), for the editor and the next run;
        its board stays as the player left it. ValueError on a level of the route."""
        if not self.in_sandbox:
            raise ValueError("only the sandbox's level is made in the Maker")
        self.sandbox = level

    def reset(self, index: int) -> None:
        """The level at `index` back to its fresh board, the next time it opens (D-050)."""
        self._boards.pop(index, None)

    def mark_won(self) -> None:
        """The open level was won: the next one opens."""
        if not self.in_sandbox:
            self.won.add(self.index)

    def record(self, score: Score, board: BoardState | None = None) -> None:
        """A win of the open level, scored, and the board that won it, the first one to score
        so; the sandbox, with no objective, keeps none."""
        if not self.in_sandbox:
            self._scores.setdefault(self.index, set()).add(score)
            if board is not None:
                self._won_with.setdefault(self.index, {}).setdefault(score, board)

    def wins(self, index: int) -> tuple[Won, ...]:
        """A level's wins this session with their boards: those no other beats first, then the
        rest, each the fastest first (D-059)."""
        boards = self._won_with.get(index, {})
        best = front(frozenset(boards))
        order = sorted(boards, key=lambda s: (s not in best, s.ticks, s.parts))
        return tuple(Won(score, boards[score], score in best) for score in order)

    def files(self) -> tuple[WinGroup, ...]:
        """What Files lists (D-092): the open level's wins, then each other level's, in the
        route's order; a level with none has no group, nor has the sandbox."""
        order = sorted(range(len(self.levels)), key=lambda k: k != self.index)
        groups = (
            WinGroup(k, f"{level_number(k)} {self.levels[k].title}", self.wins(k)) for k in order
        )
        return tuple(group for group in groups if group.wins)

    def next(self) -> None:
        """On to the next level, under its card; ValueError after the last one."""
        if not self.has_next:
            raise ValueError("that was the last level")
        self.mark_won()
        self._go(self.index + 1)
        self.screen = Screen.SPEC

    def finish(self) -> None:
        """After the last level: the end."""
        self.mark_won()
        self.screen = Screen.END
