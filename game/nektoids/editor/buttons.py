"""The Board's buttons (D-401): hexes as the cells are, in the cells round the board, at the same
places on every level, so that the hand learns them.

The board's centre is cell (0, 0), r down. At N, Select, Move and Lock, Lock on the board reached
from the Editor only (D-319); at S, Undo, Redo and Delete; at W, Turn left and Turn right side by
side, Wire under them; at E, the parts: Eye, Source and Thruster, then Double and Halve side by
side over Sum and Difference. A kind the level does not hand out leaves its place empty. The
board shows at one size, centred, so that the largest zone and every button fit beside a drawer.

Each button looks chosen, lit, greyed or plain. Chosen is the one in hand. Lit and greyed say
what a press would do to what is picked (D-402): lit, it acts on it at once; greyed, it cannot.
With nothing picked, greyed is what nothing on the board could take: Turn with no part to turn,
Redo with nothing undone, a part none of which is left; plain, the button is chosen for the
clicks on the board.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum

from nektoids.editor.layout import EDIT_KEYS, LOCK_KEY, MENU_GROUPS, TOOL_KEYS, EditButton, Tool
from nektoids.editor.picking import Pick, Picked, parts
from nektoids.graph.board import Board, Kind
from nektoids.graph.hexgrid import Cell, from_pixel, hex_disc


class Button(Enum):
    SELECT = "select"
    MOVE = "move"
    LOCK = "lock"
    UNDO = "undo"
    REDO = "redo"
    DELETE = "delete"
    TURN_LEFT = "turn left"
    TURN_RIGHT = "turn right"
    WIRE = "wire"


PLACES: dict[Button | Kind, Cell] = {
    Button.SELECT: (1, -4),
    Button.MOVE: (2, -4),
    Button.LOCK: (3, -4),
    Button.UNDO: (-3, 4),
    Button.REDO: (-2, 4),
    Button.DELETE: (-1, 4),
    Button.TURN_LEFT: (-3, -2),
    Button.TURN_RIGHT: (-2, -2),
    Button.WIRE: (-3, -1),
    Kind.EYE: (4, -3),
    Kind.SOURCE: (4, -2),
    Kind.THRUSTER: (4, -1),
    Kind.DOUBLE: (2, 2),
    Kind.HALVE: (3, 2),
    Kind.SUM: (1, 3),
    Kind.DIFFERENCE: (2, 3),
}
LARGEST_ZONE = 3  # the sandbox's, 37 cells (D-102, D-313)
FRAME: tuple[Cell, ...] = (*hex_disc(LARGEST_ZONE), *PLACES.values())  # what the view shows whole
PART_SMALLER = 2.0  # a part on its button, against its darker ground making it look larger [px]
ICON_ON_BUTTON = 0.75  # a tool's icon, over the hex size: about a part's reach
TAG_INWARD = 6  # a key's tag and a count's, from the corner towards the centre [px]
COUNT_FRAMES = 90  # a part's count shows on its button this long after one is placed: 1.5 s


class State(Enum):
    PLAIN = "plain"
    CHOSEN = "chosen"
    LIT = "lit"
    GREYED = "greyed"


KEYS = {  # each button's key; a part's is its number among those handed out (`key_of`)
    Button.SELECT: "Esc",
    Button.MOVE: TOOL_KEYS[Tool.MOVE],
    Button.LOCK: LOCK_KEY,
    Button.UNDO: EDIT_KEYS[EditButton.UNDO],
    Button.REDO: EDIT_KEYS[EditButton.REDO],
    Button.DELETE: TOOL_KEYS[Tool.DELETE],
    Button.TURN_LEFT: TOOL_KEYS[Tool.TURN_LEFT],
    Button.TURN_RIGHT: TOOL_KEYS[Tool.TURN_RIGHT],
    Button.WIRE: TOOL_KEYS[Tool.WIRE],
}


def part_key(kind: Kind, kinds: frozenset[Kind]) -> str:
    """A part's number key: its place among the parts the level hands out, as in Parts."""
    ordered = [k for _, group in MENU_GROUPS for k in group if k in kinds]
    return str(ordered.index(kind) + 1)


def swaps(board: Board, cell, kinds: frozenset[Kind]) -> tuple[Kind, ...]:
    """What the part on `cell` may be swapped for (D-068): the other parts of its group in Parts
    that the level still hands out, in Parts' order."""
    node = board.node_at(cell)
    if node is None or node.locked:
        return ()
    ordered = [k for _, group in MENU_GROUPS for k in group if k in kinds]
    return tuple(
        k
        for k in ordered
        if k.category is node.kind.category and k is not node.kind and board.remaining(k) != 0
    )


def shown(kinds: frozenset[Kind], editor: bool) -> tuple[Button | Kind, ...]:
    """The buttons a level shows, in PLACES' order: Lock on the board reached from the Editor
    only; the parts the level hands out."""
    return tuple(
        b
        for b in PLACES
        if (b is not Button.LOCK or editor) and (not isinstance(b, Kind) or b in kinds)
    )


def button_at(
    buttons: Sequence[Button | Kind], size: float, origin: tuple[float, float], point
) -> Button | Kind | None:
    """The button under `point`, among those shown, at the view's `size` and `origin`."""
    cell = from_pixel(point[0], point[1], size, origin)
    return next((b for b in buttons if PLACES[b] == cell), None)


def key_of(button: Button | Kind, kinds: frozenset[Kind]) -> str:
    return part_key(button, kinds) if isinstance(button, Kind) else KEYS[button]


def tip(button: Button | Kind, board: Board, kinds: frozenset[Kind], key_hints: bool = True) -> str:
    """What a tooltip says over a button: its name and its key if Settings shows keys; a part's
    also how many are left, if the level counts them."""
    if isinstance(button, Kind):
        text = button.spec.name
    else:
        text = button.value.capitalize()
    if key_hints:
        text += f" ({key_of(button, kinds)})"
    if isinstance(button, Kind) and board.total(button) is not None:
        text += f", {board.remaining(button)} left"
    return text


def states(
    board: Board,
    buttons: Sequence[Button | Kind],
    chosen: Button | Kind,
    pick: Pick,
    can_undo: bool,
    can_redo: bool,
    kinds: frozenset[Kind],
) -> dict[Button | Kind, State]:
    """How each button looks, as the module's docstring says."""
    picked = parts(pick, board)
    cells = bool(pick) and pick.what is Picked.CELLS
    nodes = list(board.nodes.values())
    free = [n for n in nodes if not n.locked]

    def acts(b: Button | Kind) -> bool | None:
        """True: it acts on the pick; False: it cannot act now; None: it may, on the board."""
        if b is Button.UNDO:
            return None if can_undo else False
        if b is Button.REDO:
            return None if can_redo else False
        if b is Button.SELECT:
            return None
        if isinstance(b, Kind):
            if any(b in swaps(board, n.cell, kinds) for n in picked):
                return True  # a part picked becomes one
            if board.remaining(b) == 0:
                return False
            return True if cells else None  # into the cells picked; else picked for the clicks
        if cells:
            return False  # empty cells: nothing to move, turn, wire, delete or lock
        if picked:
            loose = [n for n in picked if not n.locked]
            return {
                Button.MOVE: len(loose) == len(picked),  # the level's stay: all go, or none
                Button.DELETE: bool(loose),
                Button.LOCK: True,
                Button.TURN_LEFT: any(n.facing is not None for n in loose),
                Button.TURN_RIGHT: any(n.facing is not None for n in loose),
                Button.WIRE: len(nodes) > 1,
            }[b]
        able = {
            Button.MOVE: bool(free),
            Button.DELETE: bool(free),
            Button.LOCK: bool(nodes),
            Button.TURN_LEFT: any(n.facing is not None for n in free),
            Button.TURN_RIGHT: any(n.facing is not None for n in free),
            Button.WIRE: len(nodes) > 1,
        }[b]
        return None if able else False

    looks = {}
    for b in buttons:
        if b == chosen:
            looks[b] = State.CHOSEN
            continue
        verdict = acts(b)
        looks[b] = State.PLAIN if verdict is None else State.LIT if verdict else State.GREYED
    return looks
