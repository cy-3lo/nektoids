"""The Board's buttons (D-401): hexes as the cells are, in the cells round the board, at the same
places on every level, so that the hand learns them.

The board's centre is cell (0, 0), r down. At N, Select, Move and Lock, Lock on the board reached
from the Editor only (D-319); at S, Undo, Redo and Delete; at W, Turn left and Turn right side by
side, Wire under them and the Brush under Wire, and under the Brush the colour operators, Tint over
Filter and Swap (D-507); at E, the parts: Eye, Source and Thruster, then the
Tank over Double and Halve side by side, over Sum and Difference (D-501). A kind the level does
not hand out leaves its place empty. The board shows at one size, centred, so that the largest
zone and every button fit beside a drawer.

Each button looks chosen, lit, greyed or plain. Chosen is the one in hand. Lit and greyed say
what a press would do to what is picked (D-402): lit, it acts on it at once; greyed, it cannot.
With nothing picked, greyed is what nothing on the board could take: Turn with no part to turn,
Redo with nothing undone, a part none of which is left; plain, the button is chosen for the
clicks on the board.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum

from nektoids.editor.layout import (
    BOARD_HEX,
    EDIT_KEYS,
    GROUP_OF,
    LOCK_KEY,
    MENU_GROUPS,
    TOOL_KEYS,
    EditButton,
    Layout,
    Tool,
    View,
)
from nektoids.editor.picking import Pick, Picked, crossing, parts
from nektoids.graph.board import Board, Kind
from nektoids.graph.hexgrid import Cell, from_pixel, hex_disc, to_pixel


class Button(Enum):
    SELECT = "select"
    LOCK = "lock"
    UNDO = "undo"
    REDO = "redo"
    DELETE = "delete"
    TURN_LEFT = "turn left"
    TURN_RIGHT = "turn right"
    WIRE = "wire"
    BRUSH = "brush"  # paints eyes, Sources, thrusters, Tints, Filters (D-503, D-508)


PLACES: dict[Button | Kind, Cell] = {
    Button.SELECT: (1, -4),
    Button.LOCK: (2, -4),
    Button.DELETE: (3, -4),
    Button.UNDO: (-5, 3),
    Button.REDO: (-4, 3),
    Button.TURN_LEFT: (-3, -2),
    Button.TURN_RIGHT: (-2, -2),
    Button.WIRE: (-3, -1),
    Button.BRUSH: (-4, 0),  # under Wire, inside the frame: no other button moves (D-501)
    Kind.EYE: (4, -3),  # the groups a row each (D-508): Eye and Source,
    Kind.SOURCE: (5, -3),
    Kind.THRUSTER: (4, -2),  # the Thruster, the Tank,
    Kind.DOUBLE: (2, 2),
    Kind.HALVE: (3, 2),
    Kind.SUM: (1, 3),
    Kind.DIFFERENCE: (2, 3),
    Kind.TANK: (4, -1),  # then the math, Double and Halve over Sum and Difference
    Kind.TINT: (-4, 1),  # the colour corner, under Paint: Tint, then Filter and Swap (D-507)
    Kind.FILTER: (-5, 2),
    Kind.SWAP: (-4, 2),
}
LARGEST_ZONE = 3  # the sandbox's, 37 cells (D-102, D-313)
FRAME: tuple[Cell, ...] = (*hex_disc(LARGEST_ZONE), *PLACES.values())  # what the view shows whole
BUTTON_INSET = 2  # a button inside its cell, clear of the grid's 2 px line [px]
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
    Button.SELECT: "S",
    Button.LOCK: LOCK_KEY,
    Button.UNDO: EDIT_KEYS[EditButton.UNDO],
    Button.REDO: EDIT_KEYS[EditButton.REDO],
    Button.DELETE: TOOL_KEYS[Tool.DELETE],
    Button.TURN_LEFT: TOOL_KEYS[Tool.TURN_LEFT],
    Button.TURN_RIGHT: TOOL_KEYS[Tool.TURN_RIGHT],
    Button.WIRE: TOOL_KEYS[Tool.WIRE],
    Button.BRUSH: "B",  # its first letter, as every tool's (D-508)
}


def board_view(layout: Layout) -> View:
    """The Board's one view (D-401): BOARD_HEX, the largest zone and every button centred in the
    board area, with a drawer open or not; nothing zooms or pans it."""
    xs, ys = zip(*(to_pixel(cell, BOARD_HEX, (0.0, 0.0)) for cell in FRAME), strict=True)
    x, y, w, h = layout.board_area
    return View(
        BOARD_HEX, (round(x + (w - min(xs) - max(xs)) / 2), round(y + (h - min(ys) - max(ys)) / 2))
    )


def part_key(kind: Kind, kinds: frozenset[Kind]) -> str:
    """A part's number key: its group's, the same on every level (D-508)."""
    return str(GROUP_OF[kind] + 1)


def swaps(board: Board, cell, kinds: frozenset[Kind]) -> tuple[Kind, ...]:
    """What the part on `cell` may be swapped for (D-068): the other parts of its group in Parts
    (D-508) that the level still hands out, in Parts' order."""
    node = board.node_at(cell)
    if node is None or node.fixed:
        return ()
    ordered = [k for _, group in MENU_GROUPS for k in group if k in kinds]
    return tuple(
        k
        for k in ordered
        if GROUP_OF[k] == GROUP_OF[node.kind] and k is not node.kind and board.remaining(k) != 0
    )


def shown(kinds: frozenset[Kind], editor: bool) -> tuple[Button | Kind, ...]:
    """The buttons a level shows, in PLACES' order: every tool, Lock the player's on every board
    (D-406); the parts the level hands out. `editor`, the sandbox's, changes no button."""
    return tuple(b for b in PLACES if not isinstance(b, Kind) or b in kinds)


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
    editor: bool = False,
) -> dict[Button | Kind, State]:
    """How each button looks, as the module's docstring says."""
    picked = parts(pick, board)
    cells = bool(pick) and pick.what is Picked.CELLS
    nodes = list(board.nodes.values())
    free = [n for n in nodes if not n.fixed]
    mine = [n for n in nodes if not n.locked]

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
        if cells and b is Button.DELETE and crossing(pick, board):
            return True  # empty cells: Delete takes the wires through them (D-431)
        if cells and b not in (Button.WIRE, Button.DELETE):
            return False  # nothing to turn or lock; Wire and Delete are held, the pick dropped
        if picked:
            loose = [n for n in picked if not n.fixed]
            return {
                Button.BRUSH: any(n.kind.paintable for n in loose),
                Button.DELETE: bool(loose),
                Button.LOCK: editor or any(not n.locked for n in picked),
                Button.TURN_LEFT: any(n.facing is not None for n in loose),
                Button.TURN_RIGHT: any(n.facing is not None for n in loose),
                Button.WIRE: len(nodes) > 1,
            }[b]
        able = {
            Button.BRUSH: True,  # with nothing picked, it switches its colour (D-503)
            Button.DELETE: bool(free),
            Button.LOCK: bool(nodes) if editor else bool(mine),
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
