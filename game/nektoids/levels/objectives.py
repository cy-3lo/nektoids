"""What a level asks of its swimmers, counted, and when a run is over (D-023, D-038, D-040).

An objective is a sentence (D-307): a verb, how many, and what. Reach: touch a light or an
obstacle (centres within REACH times the sum of their radii, a little short of touching, D-029),
or come into a mark, the swimmer's centre inside its circle. Leave: get out of a mark. Stay: be
inside a mark for `seconds` in a row. How many: all of the level's targets of that kind, one of
them, or none, which makes the sentence a ban: the run is lost the moment it happens (D-040).
Three verbs, three counts, three targets (D-312): leave and stay take marks alone, and stay
takes no "none". A mark is a zone only the objectives read (D-306); going round a light is
reaching the marks round it (D-312).

Each objective says what counts at a tick, `marks`, an array (N, K) for N swimmers and K targets,
or (N, 1) when the targets are taken together; the run keeps something for each objective, from
`start` and then `keep` at every tick: latched marks for reach and leave (once marked, always
marked), the time spent inside for stay. Each objective counts what it asks from what was kept,
so many met out of so many needed (brief section 1: countable win conditions), and may lose the
run. A run is lost as soon as an objective loses it, won when every objective is met, over when
its time is up. Pure numbers, no pygame.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np

from nektoids.levels.lattice import Range
from nektoids.sim.arena import LIGHT_RADIUS

REACH = 1.05  # a light counts as reached this many times its touching distance away (D-043)
EPS = 1e-9  # a timer this close to its seconds has reached them
SECONDS = Range(1.0, 60.0, 1.0, "s")  # how long a stay lasts (D-307)

if TYPE_CHECKING:
    from nektoids.levels.level import Level

Kept = tuple[np.ndarray, ...]  # what the run keeps for each objective, one array apiece


class Verb(Enum):
    REACH = "reach"
    LEAVE = "leave"
    STAY = "stay"


class Count(Enum):
    ALL = "all"
    ONE = "one"
    NONE = "none"  # a ban: the run is lost the moment it happens


class Target(Enum):
    LIGHT = "light"
    OBSTACLE = "obstacle"
    MARK = "mark"


class Outcome(Enum):
    WON = "won"
    TIME_UP = "time up"
    LOST = "lost"  # an objective lost the run: a light touched (D-040)


SETTING = {Verb.STAY: ("seconds", SECONDS, 5.0)}  # the setting a verb takes, its default
ON_MARKS = (Verb.LEAVE, Verb.STAY)  # the verbs that take marks alone
NO_NONE = (Verb.STAY,)  # the verbs that take no "none"
THING = {  # each target, as a sentence says it: one, many, one with its article
    Target.LIGHT: ("light", "lights", "a light"),
    Target.OBSTACLE: ("obstacle", "obstacles", "an obstacle"),
    Target.MARK: ("ring", "rings", "a ring"),  # a mark, as the player sees it
}
NAMES = {  # version 1's objectives, named as they were (D-038, D-040, D-097)
    (Verb.REACH, Count.ALL, Target.LIGHT): "Visit every light",
}
ALONE = {  # ... those that say "the", as true only where the level has one such target
    (Verb.REACH, Count.NONE, Target.LIGHT): "Don't touch the light",
    (Verb.LEAVE, Count.ALL, Target.MARK): "Leave the ring",
}
ICONS = {  # each verb's, by its name in `editor/icons.py`; a ban's is its own
    Verb.REACH: "location-dot",
    Verb.LEAVE: "right-from-bracket",
    Verb.STAY: "bullseye",
}


def sensible(verb: Verb, count: Count, target: Target) -> str | None:
    """Why a sentence says nothing a run can count, or None if it says something."""
    if verb in ON_MARKS and target is not Target.MARK:
        return f"one can {verb.value} a ring, not {THING[target][2]}"
    if verb in NO_NONE and count is Count.NONE:
        return f"no goal can be to {verb.value} none"
    return None


def reworded(goal: Goal, word: Verb | Count | Target) -> Goal:
    """The goal with `word` in its place, as the Maker's choosers put it (D-308), the other
    words moved as little as makes the sentence say something: a leave or a stay aims at marks,
    a stay at one or all, never none; a target or a "none" the verb cannot take puts the verb
    back to reach, which takes any. A setting stays with its verb; a new verb's is at
    its default."""
    verb, many, target = goal.verb, goal.many, goal.target
    if isinstance(word, Verb):
        verb = word
        target = Target.MARK if verb in ON_MARKS else target
        many = Count.ONE if verb in NO_NONE and many is Count.NONE else many
    else:
        many, target = (word, target) if isinstance(word, Count) else (many, word)
        verb = verb if sensible(verb, many, target) is None else Verb.REACH
    kept = {name: getattr(goal, name) for name, _ in settings(goal)} if verb is goal.verb else {}
    return Goal(verb, many, target, **kept)


@dataclass(frozen=True)
class Goal:
    """An objective, a sentence (D-307): `verb` `many` `target`, and the setting its verb takes:
    a stay's seconds."""

    verb: Verb
    many: Count  # how many of the targets: its data's "count"
    target: Target
    seconds: float | None = None  # a stay's: how long in a row, inside [s]

    def __post_init__(self) -> None:
        """ValueError for a sentence that says nothing (`sensible`), or a setting its verb does
        not take; the one it takes, if not given, at its default."""
        why = sensible(self.verb, self.many, self.target)
        if why is not None:
            raise ValueError(why)
        taken, _, default = SETTING.get(self.verb, (None, None, None))
        if taken is None and self.seconds is not None:
            raise ValueError(f"to {self.verb.value} takes no seconds")
        if taken is not None and self.seconds is None:
            object.__setattr__(self, taken, default)

    # How it reads: "the light" where the level has one, "a light" or "the lights" where more

    def name(self, level: Level) -> str:
        """The sentence, as the run's rows say it, in `level`."""
        words = (self.verb, self.many, self.target)
        alone = self._alone(level)
        known = NAMES.get(words) or (ALONE.get(words) if alone else None)
        if known is not None:
            return known
        one, many, a_one = THING[self.target]
        come, the = "Enter" if self.target is Target.MARK else "Reach", self._the(alone)
        return {
            (Verb.REACH, Count.ALL): f"{come} every {one}",
            (Verb.REACH, Count.ONE): f"{come} {a_one}",
            (Verb.REACH, Count.NONE): f"Keep out of {the}"
            if self.target is Target.MARK
            else f"Touch no {one}",
            (Verb.LEAVE, Count.ALL): f"Leave every {one}",
            (Verb.LEAVE, Count.ONE): f"Leave {a_one}",
            (Verb.LEAVE, Count.NONE): f"Stay inside {the}",
            (Verb.STAY, Count.ALL): f"Stay in every {one}",
            (Verb.STAY, Count.ONE): f"Stay in {a_one}",
        }[(self.verb, self.many)]

    def about(self, level: Level) -> str:
        """What its info box says, in `level`."""
        one, _, a_one = THING[self.target]
        alone = self._alone(level)
        if self.many is Count.NONE and self.verb is Verb.LEAVE:
            return f"Getting out of {self._the(alone)} loses the run at once."
        if self.many is Count.NONE:
            done = "Coming into" if self.target is Target.MARK else "Touching"
            return f"{done} {a_one} loses the run at once."
        come = {Target.LIGHT: "Reach", Target.OBSTACLE: "Touch", Target.MARK: "Come into"}
        each = self.many is Count.ALL
        if self.verb is Verb.REACH:
            return (
                f"{come[self.target]} every {one}, in any order."
                if each
                else (f"{come[self.target]} {a_one}: any one.")
            )
        if self.verb is Verb.LEAVE:
            return f"Get out of every {one} at once." if each else f"Get out of {a_one}: any one."
        inside = f"every {one} at once" if each else a_one
        return f"Stay inside {inside} for {self.seconds:g} s in a row."

    @property
    def icon(self) -> str:
        """Its row's icon in the run, by its name in `editor/icons.py`."""
        return "circle-xmark" if self.many is Count.NONE else ICONS[self.verb]

    def broken(self, level: Level) -> str:
        """What the run's end says if it loses the run, in `level`."""
        if self.many is not Count.NONE:
            return "Lost"
        alone = self._alone(level)
        if self.verb is Verb.LEAVE:
            return f"It got out of {self._the(alone)}"
        if self.target is Target.MARK:
            return "It went into a ring"
        if self.target is Target.LIGHT:
            return "It touched the light" if alone else "It touched a light"
        return "It touched an obstacle"

    def _alone(self, level: Level) -> bool:
        """Whether `level` has one target of the kind the goal aims at, and no more."""
        return len(targets(level, self.target)[1]) == 1

    def _the(self, alone: bool) -> str:
        """Its targets taken together: "the ring" if there is one, "the rings" if more."""
        one, many, _ = THING[self.target]
        return f"the {one}" if alone else f"the {many}"

    # How it counts

    def marks(self, level: Level, pos: np.ndarray, radius: np.ndarray) -> np.ndarray:
        """What counts now, for swimmers at pos (N, 2) [u] of radius (N,) [u]: (N, K) for each
        target, or (N, 1) for the targets together."""
        centres, size = targets(level, self.target)
        dx = centres[None, :, 0] - pos[:, None, 0]
        dy = centres[None, :, 1] - pos[:, None, 1]
        if self.verb is Verb.REACH:
            near = size[None, :] if self.target is Target.MARK else _touch(size, radius)
            now = dx * dx + dy * dy <= near * near  # (N, K)
            return now.any(axis=1)[:, None] if self.many is Count.ONE else now
        rim = size[None, :]
        if self.verb is Verb.LEAVE and self.many is not Count.NONE:
            out = dx * dx + dy * dy > rim * rim
            together = out.all(axis=1) if self.many is Count.ALL else out.any(axis=1)
            return together[:, None]
        inside = dx * dx + dy * dy <= rim * rim
        if self.verb is Verb.LEAVE:  # none: out of every one, out of the zone
            return ~inside.any(axis=1)[:, None]
        together = inside.all(axis=1) if self.many is Count.ALL else inside.any(axis=1)
        return together[:, None]

    def start(self, now: np.ndarray) -> np.ndarray:
        """What the run keeps for it at t = 0, from what counts then."""
        return np.zeros(now.shape) if self.verb is Verb.STAY else now

    def keep(self, kept: np.ndarray, now: np.ndarray, dt: float) -> np.ndarray:
        """What the run keeps after a tick of `dt` [s], from what it kept and what counts now:
        latched marks; a stay's time inside, back to 0 when out, kept once full."""
        if self.verb is Verb.STAY:
            full = kept >= self.seconds - EPS
            return np.where(full, kept, np.where(now, kept + dt, 0.0))
        return kept | now

    def count(self, kept: np.ndarray) -> tuple[int, int]:
        """How many are met, out of how many needed: for a ban, the swimmers it has not
        caught."""
        if self.many is Count.NONE:
            return int((~kept.any(axis=1)).sum()), int(kept.shape[0])
        if self.verb is Verb.STAY:
            return int((kept >= self.seconds - EPS).sum()), int(kept.size)
        return int(kept.sum()), int(kept.size)

    def progress(self, kept: np.ndarray) -> float:
        """How far along it is, from 0 to 1: its bar."""
        if self.verb is Verb.STAY:
            return float(min(1.0, kept.max() / self.seconds)) if kept.size else 0.0
        done, needed = self.count(kept)
        return done / needed if needed else 1.0

    def lost(self, kept: np.ndarray) -> bool:
        """Whether it has lost the run, whatever the rest: a ban, once broken."""
        return self.many is Count.NONE and bool(kept.any())


def _touch(size: np.ndarray, radius: np.ndarray) -> np.ndarray:
    """(N, K): how near each swimmer's centre comes to each light's or obstacle's when it
    touches it, a little short: REACH (R + r), 2.1 u for a base body and a light [u]."""
    return REACH * (size[None, :] + np.asarray(radius, dtype=np.float64)[:, None])


def targets(level: Level, target: Target) -> tuple[np.ndarray, np.ndarray]:
    """The level's targets of a kind: their centres (K, 2) [u] and their radii (K,) [u]."""
    arena = level.arena
    if target is Target.LIGHT:
        return arena.light_xy, np.full(len(arena.light_xy), LIGHT_RADIUS)
    if target is Target.OBSTACLE:
        return arena.disc_xy, arena.disc_radius
    marks = level.marks
    return np.array([m.at for m in marks]).reshape(-1, 2), np.array([m.value for m in marks])


def reaching(level: Level, pos: np.ndarray, radius: np.ndarray) -> np.ndarray:
    """(N, L): whether each swimmer reaches each light now, as reach and its ban count it."""
    return Goal(Verb.REACH, Count.ALL, Target.LIGHT).marks(level, pos, radius)


def begin(level: Level, pos: np.ndarray, radius: np.ndarray) -> Kept:
    """What the run keeps for each of the level's objectives at t = 0."""
    return tuple(o.start(o.marks(level, pos, radius)) for o in level.objectives)


def follow(level: Level, kept: Kept, pos: np.ndarray, radius: np.ndarray, dt: float) -> Kept:
    """What the run keeps after a tick of `dt` [s], the swimmers now at `pos`."""
    pairs = zip(level.objectives, kept, strict=True)
    return tuple(o.keep(k, o.marks(level, pos, radius), dt) for o, k in pairs)


def met(objective: Goal, kept: np.ndarray) -> bool:
    done, needed = objective.count(kept)
    return done >= needed


def outcome(level: Level, kept: Kept, tick: int, dt: float) -> Outcome | None:
    """How the run stands after `tick` ticks of `dt` [s]: lost as soon as an objective loses it,
    won when the level has objectives and every one is met, else over when its time is up, else
    still running (None)."""
    pairs = list(zip(level.objectives, kept, strict=True))
    if any(o.lost(k) for o, k in pairs):
        return Outcome.LOST
    if level.objectives and all(met(o, k) for o, k in pairs):
        return Outcome.WON
    if tick >= round(level.time_limit / dt):
        return Outcome.TIME_UP
    return None


def settings(goal: Goal) -> tuple[tuple[str, Range], ...]:
    """The setting a goal's verb takes, by name, with what it may be: none, or one."""
    taken, scale, _ = SETTING.get(goal.verb, (None, None, None))
    return () if taken is None else ((taken, scale),)


KEYS = ("verb", "count", "target", "seconds")  # what an objective's data may hold
GONE = "circling is gone: reach marks round the target instead (D-312)"


def objective_to_dict(goal: Goal) -> dict:
    """The sentence and its setting, as a level's data holds it."""
    data = {"verb": goal.verb.value, "count": goal.many.value, "target": goal.target.value}
    return data | {taken: getattr(goal, taken) for taken, _ in settings(goal)}


def objective_from_dict(data: Mapping) -> Goal:
    """ValueError for a key it does not know (D-201), a word no sentence has, or a sentence
    that says nothing."""
    if data.get("verb") == "circle" or "turns" in data:
        raise ValueError(GONE)
    unknown = [key for key in data if key not in KEYS]
    if unknown:
        raise ValueError(f"an objective takes no {', '.join(map(repr, unknown))}")
    try:
        words = (Verb(data["verb"]), Count(data["count"]), Target(data["target"]))
    except KeyError as missing:
        raise ValueError(f"an objective needs its {missing.args[0]}") from None
    return Goal(*words, seconds=data.get("seconds"))


V2_TAKES = {  # version 2's objectives, by kind, and the settings each took
    "visit lights": (),
    "keep off": (),
    "leave ring": ("radius",),
    "stay near": ("radius", "seconds"),
}
V2_DEFAULTS = {"leave ring": {"radius": 12.0}}
V2_DEFAULTS["stay near"] = {"radius": 6.0, "seconds": 5.0}


def upgraded(objectives: list, lights: list) -> tuple[list, list]:
    """Version 2's objectives as sentences (D-307), and the marks their rings become: a ring to
    leave or to stay in round every light, of its radius, is a mark on each light. ValueError
    for an objective version 2 had not, a setting it did not take, or rings of two sizes, which
    as marks would each count for the other's goal."""
    goals, rings = [], set()
    for old in objectives:
        kind = old.get("kind")
        if kind == "circle light":
            raise ValueError(GONE)
        if kind not in V2_TAKES:
            raise ValueError(f"no objective is called {kind!r}")
        unknown = [key for key in old if key not in ("kind", *V2_TAKES[kind])]
        if unknown:
            raise ValueError(f"{kind!r} takes no {', '.join(map(repr, unknown))}")
        given = V2_DEFAULTS.get(kind, {}) | {k: v for k, v in old.items() if k != "kind"}
        sentence = {
            "visit lights": {"verb": "reach", "count": "all", "target": "light"},
            "keep off": {"verb": "reach", "count": "none", "target": "light"},
            "leave ring": {"verb": "leave", "count": "all", "target": "mark"},
            "stay near": {"verb": "stay", "count": "one", "target": "mark"},
        }[kind]
        if "radius" in given:
            rings.add(float(given.pop("radius")))
        goals.append(sentence | given)
    if len(rings) > 1:
        raise ValueError("rings of two sizes: as marks, each would count for the other's goal")
    marks = [{"kind": "mark", "at": list(at), "radius": r} for r in rings for at in lights]
    return goals, marks
