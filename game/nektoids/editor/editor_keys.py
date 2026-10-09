"""The Editor's buttons (D-410): square keys fixed on the screen, floating over the plane at its
edges, whatever the drawer and however the plane is panned or zoomed. At the left, two columns
of tools in pairs: Select and Hand, Bigger and Smaller, Zoom in and out, Undo and Redo, Copy and
Paste, Cut and Erase all; at the right, the objects: the Swimmer, a white, an amber and a violet
light (D-506), Obstacle and Mark.

Each key looks as the Board's buttons do (D-401): chosen, the one in hand; lit, it acts on what
is picked at once; greyed, it cannot act now: Bigger, Smaller, Cut and Copy with no item picked,
Paste with nothing copied, Undo or Redo with nothing to go back to, Erase all on an empty plane,
the Swimmer while it is on the plane: a level has one.
Pure numbers, no pygame.
"""

from __future__ import annotations

from enum import Enum

from nektoids.editor.buttons import State
from nektoids.editor.layout import Piece, Rect, contains
from nektoids.editor.plane_pick import Pick, items
from nektoids.levels.level import Level


class Key(Enum):
    SELECT = "select"
    HAND = "hand"
    BIGGER = "bigger"
    SMALLER = "smaller"
    ZOOM_IN = "zoom in"
    ZOOM_OUT = "zoom out"
    UNDO = "undo"
    REDO = "redo"
    COPY = "copy"
    PASTE = "paste"
    CUT = "cut"
    ERASE = "erase all"


LEFT = (
    (Key.SELECT, Key.HAND),
    (Key.BIGGER, Key.SMALLER),
    (Key.ZOOM_IN, Key.ZOOM_OUT),
    (Key.UNDO, Key.REDO),
    (Key.COPY, Key.PASTE),
    (Key.CUT, Key.ERASE),
)
RIGHT = tuple(Piece)  # the swimmer first, key 0; the lights, white, amber, violet (D-506)
SIZE = 36  # a key's side: its icon as big as the bar's, 22 px [px]
GAP = 4  # between two keys of a pair [px]
ROW_GAP = 8  # between two rows [px]
EDGE = 20  # from the plane's edge, clear of the drawer's handle [px]

KEYS = {  # what the tooltips name; an object's is its number
    Key.SELECT: "S",
    Key.HAND: "H",
    Key.BIGGER: ">",
    Key.SMALLER: "<",
    Key.ZOOM_IN: "+",
    Key.ZOOM_OUT: "-",
    Key.UNDO: "Ctrl+Z",
    Key.REDO: "Ctrl+Y",
    Key.COPY: "Ctrl+C",
    Key.PASTE: "Ctrl+V",
    Key.CUT: "Del",
    **{p: str(k) for k, p in enumerate(RIGHT)},  # 0 the swimmer, 1 to 5 the items
}
NAMES = {
    **{k: k.value.capitalize() for k in Key},
    Piece.LIGHT: "White light",
    Piece.AMBER_LIGHT: "Amber light",
    Piece.VIOLET_LIGHT: "Violet light",
    Piece.OBSTACLE: "Obstacle",
    Piece.MARK: "Mark",
    Piece.START: "Swimmer",
}
ACTS_ON_ITEMS = (Key.BIGGER, Key.SMALLER, Key.COPY, Key.CUT)


def places(area: Rect) -> dict[Key | Piece, Rect]:
    """Each key's square on the screen, by the plane's `area`: the tools at its left, the objects
    at its right, both centred up and down."""
    x, y, w, h = area
    rows = len(LEFT)
    top = y + (h - (rows * SIZE + (rows - 1) * ROW_GAP)) // 2
    found: dict[Key | Piece, Rect] = {}
    for r, pair in enumerate(LEFT):
        for c, key in enumerate(pair):
            found[key] = (x + EDGE + c * (SIZE + GAP), top + r * (SIZE + ROW_GAP), SIZE, SIZE)
    top = y + (h - (len(RIGHT) * SIZE + (len(RIGHT) - 1) * GAP)) // 2
    for r, piece in enumerate(RIGHT):
        found[piece] = (x + w - EDGE - SIZE, top + r * (SIZE + GAP), SIZE, SIZE)
    return found


def key_at(area: Rect, point: tuple[int, int]) -> Key | Piece | None:
    """The key under `point`, if any."""
    return next((k for k, rect in places(area).items() if contains(rect, point)), None)


def tip(key: Key | Piece, key_hints: bool = True) -> str:
    """What a key's tooltip says: its name, and its key if Settings shows keys."""
    shown = KEYS.get(key, "")
    return NAMES[key] + (f" ({shown})" if key_hints and shown else "")


def states(
    level: Level,
    held: Key | Piece,
    pick: Pick,
    can_undo: bool,
    can_redo: bool,
    copied: bool,
    start_off: bool = False,
) -> dict[Key | Piece, State]:
    """How each key looks, as the module's docstring says."""
    picked = bool(items(pick))
    looks: dict[Key | Piece, State] = {}
    for key in (*[k for pair in LEFT for k in pair], *RIGHT):
        if key == held:
            looks[key] = State.CHOSEN
        elif key is Key.CUT:  # the items, and the swimmer, picked (D-410)
            swimmer = Piece.START in pick and not start_off
            looks[key] = State.LIT if picked or swimmer else State.GREYED
        elif key in ACTS_ON_ITEMS:
            looks[key] = State.LIT if picked else State.GREYED
        elif key is Key.PASTE:
            looks[key] = State.PLAIN if copied else State.GREYED
        elif key is Key.UNDO:
            looks[key] = State.PLAIN if can_undo else State.GREYED
        elif key is Key.REDO:
            looks[key] = State.PLAIN if can_redo else State.GREYED
        elif key is Key.ERASE:
            looks[key] = State.PLAIN if level.items or level.objectives else State.GREYED
        elif key is Piece.START:  # one swimmer: its key, once it is off the plane (D-410)
            looks[key] = State.PLAIN if start_off else State.GREYED
        else:
            looks[key] = State.PLAIN
    return looks


CONFIRM = (380, 124)  # Erase all's box, centred on the plane [px]
CONFIRM_BUTTON = (120, 34)  # its two buttons: Cancel, the default, and Erase all [px]


def confirm_box(area: Rect) -> tuple[Rect, Rect, Rect]:
    """Erase all's box on the plane `area`, its Cancel button and its Erase all button, side by
    side at its foot, Cancel first (D-410)."""
    x, y, w, h = area
    bw, bh = CONFIRM
    box = (x + (w - bw) // 2, y + (h - bh) // 2, bw, bh)
    cw, ch = CONFIRM_BUTTON
    top = box[1] + bh - ch - 16
    cancel = (box[0] + bw // 2 - cw - 8, top, cw, ch)
    erase = (box[0] + bw // 2 + 8, top, cw, ch)
    return box, cancel, erase
