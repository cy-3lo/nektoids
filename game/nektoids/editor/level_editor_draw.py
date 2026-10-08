"""Drawing the Editor (D-301). Reads the scene; never changes it.

The plane at large, as the run shows it, over its grid: a dot wherever a position may fall,
every whole u, 2 px wide, none where they would crowd (`dot_step`); a line every 5 u, no
coordinate: the grid is enough (D-311). Over the grid the light's rays, as they stand when the
run starts, the obstacles, the lights, and the swimmer where it starts, its wedge where it
heads; the focus lit, a ring round its object or a cross on its point; what is in hand, where a
click would put it; atop it, as on the Board, what the next click or Enter does, or what is
focused, its name and key beside it, a line under it (D-314). Round it, the frame (`draw.py`):
the tabs and the level's caption, the bar, the open drawer, the status line. Objects as Parts
draws its rows and its Wheel (D-068, D-069): each object and how many are on the plane, undo and
redo, then the Wheel round the focus, the focus large at its hub, the line under it saying what
it is. Parts: the board's size and each part handed out, − and + either side of the count,
greyed at the ends (D-315). Goals: each goal's name and bin over its words' buttons, the words
it says lit, those that would aim at nothing dimmed; the sliders, the time allowed's and each
setting's (D-308). Text: the title in a field, the spec in a taller one, wrapped (D-305).
Files: Copy level, then the field a level's text is pasted into, then the levels to start from,
a blank plane first, the chapter's under their numbers, the sandbox's last (D-310). Navigator:
its rays' row, its overview and zoom.
"""

from __future__ import annotations

from collections import Counter

import numpy as np
import pygame

from nektoids.editor.arena_draw import (
    draw_items,
    draw_light,
    draw_mark,
    draw_marks,
    draw_overview,
    draw_rays,
)
from nektoids.editor.arena_view import LINE_STEP, dot_step, lattice, shown
from nektoids.editor.buttons import State
from nektoids.editor.buttons_draw import square_bevel, square_shadows, tag
from nektoids.editor.devdrive import DT
from nektoids.editor.draw import (
    MENU_ANGLE,
    ROW_NAME,
    TIP,
    Fonts,
    cached_text,
    draw_bar,
    draw_drawer,
    draw_field,
    draw_heading,
    draw_info,
    draw_part,
    draw_row,
    draw_status_line,
    draw_symbol,
    draw_tabs,
    draw_tip,
    draw_tooltip,
    draw_track,
    swimmer_width,
)
from nektoids.editor.editor_keys import Key, confirm_box, key_at, places, tip
from nektoids.editor.icons import EDIT_ICON, PIECE_ICON, VIEW_ICON
from nektoids.editor.layout import (
    FIELD_PAD,
    HINT_LINE,
    SPEC_LINES,
    VIEW_KEYS,
    Brief,
    EditButton,
    FileButton,
    Knob,
    Piece,
    Start,
    ViewButton,
    bin_rect,
    contains,
    slider_parts,
    step_buttons,
)
from nektoids.editor.level_editor import EditorScene, Paste
from nektoids.editor.objects import (
    NAMES,
    PLACED,
    reach,
    where,
)
from nektoids.editor.palette import (
    ACTIVE,
    BACKGROUND,
    BAR,
    BODY,
    BUTTON,
    DARK,
    DIM_TEXT,
    DIVIDER,
    GREYED,
    ICON_EDGE,
    KEY_DARK,
    KEY_GREYED,
    KEY_LIGHT,
    LIT,
    OBSTACLE,
    OUTSIDE,
    PANEL,
    PLANE_DOT,
    PLANE_LINE,
    REFUSED,
    RULE,
    SELECTED,
    SHADOW,
    TEXT,
    TOOLTIP_BG,
)
from nektoids.editor.parts import NAME as PART_NAME
from nektoids.editor.textfield import caret_at, wrapped
from nektoids.levels.lattice import snapped
from nektoids.levels.level import ItemKind
from nektoids.levels.making import BLANK_TIME, NEW, ZONES, lacks
from nektoids.levels.objectives import Count, Outcome, Target, Verb, at_start, settings
from nektoids.sim.arena import LIGHT_RADIUS

FOCUS_GAP = 4  # from an object's rim to the ring round it when focused [px]
FOCUS_DOT = 5  # a focused point's circle; its cross's arms reach 6 px past it [px]
DOT_SIZE = 2  # a dot of the grid, square [px] (D-311)
PIECE_ABOUT = {  # what Objects' rows' info boxes say
    Piece.LIGHT: "Click it, then the plane, or drag it there. Its power, 1 to 8, is how much"
    " light it gives: what an eye reads of it falls as 1/r.",
    Piece.OBSTACLE: "Click it, then the plane, or drag it there. A disc the swimmer slides round"
    " and the light does not cross: it casts a shadow. Its radius, 1 to 8.",
    Piece.MARK: "Click it, then the plane, or drag it there. A ring only the goals read: the"
    " swimmer neither sees nor touches it. Its radius, 1 to 8.",
    Piece.START: "Where the swimmer starts, and which way it heads. Drag it, or turn it with L"
    " and R, or the mouse wheel on it.",
}

WORD_NAME = {  # Goals' buttons (D-308), the targets as Objects names them
    Verb.REACH: "Reach",
    Verb.LEAVE: "Leave",
    Verb.STAY: "Stay",
    Count.ALL: "All",
    Count.ONE: "One",
    Count.NONE: "None",
    Target.LIGHT: "Lights",
    Target.OBSTACLE: "Obstacles",
    Target.MARK: "Marks",
}

KEPT = "Its plane, goals and time replace the level's. The board stays as it is."  # D-310
UNJUDGED = {  # the status line, while the level is decided where its swimmer starts (D-349)
    Outcome.WON: "Won where the swimmer starts: move the start or change a goal.",
    Outcome.LOST: "Lost where the swimmer starts: move the start or change a goal.",
}
SHARED = (  # Share level's box, once it has copied (D-346)
    "Copied: your level and its proof",
    (
        "To share it with the community, paste it into a comment on the itch.io page,"
        " cy-3lo.itch.io/nektoids, or send it to contact@nektoids.com.",
    ),
)

_dots_cache: dict[str, object] = {"key": None, "surface": None}


def draw_level_editor(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    screen.fill(BACKGROUND)
    screen.set_clip(scene.arena_area)
    _draw_grid(screen, scene)
    if scene.show_rays:  # as they stand at the run's start
        view, area = scene.view, scene.arena_area
        draw_rays(screen, view, area, scene.arena, scene.rays, 0.0, scene.pos, scene.radius)
    draw_marks(screen, scene.view, scene.level.marks)
    draw_items(screen, fonts, scene.view, scene.arena)
    if not scene.start_off:  # cut off the plane, until its key places it again (D-410)
        centre = scene.view.to_screen(*scene.pos[0])
        radius = float(scene.radius[0]) * scene.view.scale
        width = swimmer_width(radius)  # in proportion (D-410)
        draw_symbol(screen, DARK, centre, radius + 1, scene.heading, width + 2)
        draw_symbol(screen, BODY, centre, radius, scene.heading, width)
    _draw_pick(screen, scene)
    _draw_box(screen, scene)
    _draw_in_hand(screen, scene, fonts)
    _draw_count(screen, scene, fonts)
    screen.set_clip(None)
    _draw_keys(screen, scene, fonts)
    draw_tabs(screen, scene, fonts)
    _draw_status(screen, scene, fonts)
    draw_bar(screen, scene, fonts)
    draw_drawer(screen, scene, fonts, _draw_rows, _draw_foot)
    draw_tooltip(screen, scene, fonts)
    _draw_key_tip(screen, scene, fonts)
    draw_info(screen, scene, fonts, _about)
    _draw_confirm(screen, scene, fonts)


KEY_ICON = {  # the Editor's keys (D-410); an object's is its own (PIECE_ICON)
    Key.SELECT: "arrow-pointer",
    Key.HAND: "hand",
    Key.BIGGER: "caret-up",
    Key.SMALLER: "caret-down",
    Key.ZOOM_IN: VIEW_ICON[ViewButton.ZOOM_IN],
    Key.ZOOM_OUT: VIEW_ICON[ViewButton.ZOOM_OUT],
    Key.UNDO: EDIT_ICON[EditButton.UNDO],
    Key.REDO: EDIT_ICON[EditButton.REDO],
    Key.COPY: "copy",
    Key.PASTE: "paste",
    Key.CUT: "scissors",
    Key.ERASE: "eraser",
}
KEY_ICON_SIZE = 0.6  # an icon on its key, over the key's side
BOX_CROSS = 7  # the half-length of a rectangle's + at its corners [px]
COUNT_BELOW = 14  # a value's tag under its object's rim [px]


def _draw_keys(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """The keys round the plane, floating over it (D-410), as the Board's buttons look (D-401):
    chosen, pressed in; lit, a teal bevel; greyed, dimmed."""
    looks, found = scene.key_states(), places(scene.arena_area)
    square_shadows(screen, [r for k, r in found.items() if looks[k] is not State.CHOSEN])
    for key, rect in found.items():
        look = looks[key]
        pygame.draw.rect(screen, ACTIVE if look is State.CHOSEN else OUTSIDE, rect)
        light, dark = {
            State.PLAIN: (KEY_LIGHT, KEY_DARK),
            State.LIT: (LIT, ACTIVE),
            State.CHOSEN: (KEY_DARK, LIT),  # pressed in: the light falls on the far sides
            State.GREYED: (KEY_GREYED, KEY_DARK),
        }[look]
        square_bevel(screen, rect, light, dark)
        x, y, w, h = rect
        at = (x + w // 2 + (look is State.CHOSEN), y + h // 2 + (look is State.CHOSEN))
        ink = GREYED if look is State.GREYED else TEXT
        if key is Piece.START:  # the swimmer's own shape (D-410)
            draw_swimmer_icon(screen, at, KEY_ICON_SIZE * w / 2, ink)
            continue
        icon = PIECE_ICON[key] if isinstance(key, Piece) else KEY_ICON[key]
        fonts.icons.draw(screen, icon, at, round(KEY_ICON_SIZE * w), ink)


def _draw_key_tip(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """A key's tooltip beside it, once the mouse has rested there: its name and key (D-410)."""
    target = scene.tooltip
    found = places(scene.arena_area)
    if target not in found:
        return
    x, y, w, h = found[target]
    text = tip(target, scene.settings.key_hints)
    if isinstance(target, Piece):  # the objects at the right: the tip to their left
        draw_tip(screen, fonts, text, midright=(x - 14, y + h // 2))
    else:
        draw_tip(screen, fonts, text, midleft=(x + w + 14, y + h // 2))


def draw_swimmer_icon(screen: pygame.Surface, centre, radius: float, colour) -> None:
    """The swimmer's symbol as an icon, pointing right: a circle round a wedge (D-410)."""
    draw_symbol(screen, colour, centre, radius, 0.0, swimmer_width(radius))


def _draw_box(screen: pygame.Surface, scene: EditorScene) -> None:
    """A rectangle dragged from the open plane: its outline, a + at the corner it started from
    and at the mouse (D-410)."""
    if scene.box_from is None or scene.box_to is None:
        return
    (x0, y0), (x1, y1) = scene.box_from, scene.box_to
    box = pygame.Rect(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))
    pygame.draw.rect(screen, LIT, box, 1)
    for cx, cy in (scene.box_from, scene.box_to):
        pygame.draw.line(screen, LIT, (cx - BOX_CROSS, cy), (cx + BOX_CROSS, cy), 2)
        pygame.draw.line(screen, LIT, (cx, cy - BOX_CROSS), (cx, cy + BOX_CROSS), 2)


def _draw_pick(screen: pygame.Surface, scene: EditorScene) -> None:
    """A ring round each object picked (D-410)."""
    for obj in scene.pick:
        cx, cy = scene.view.to_screen(*where(scene.level, obj))
        ring = reach(scene.level, obj) * scene.view.scale + FOCUS_GAP
        pygame.draw.circle(screen, LIT, (cx, cy), ring, 2)


def _draw_count(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """An object's value a moment under it, once placed or set, as the Board's count of parts
    left (D-401, D-410): a light's power, an obstacle's or a mark's radius, the swimmer's
    heading."""
    obj = scene.counted
    if scene.count_frames <= 0 or obj is None:
        return
    if isinstance(obj, int) and obj >= len(scene.level.items):
        return
    cx, cy = scene.view.to_screen(*where(scene.level, obj))
    below = cy + reach(scene.level, obj) * scene.view.scale + COUNT_BELOW
    if obj is Piece.START:
        value = f"{scene.level.start[2]:g}°"
    else:
        value = f"{scene.level.items[obj].value:g}"
    tag(screen, (cx, below), fonts.small.render(value, True, TEXT), BAR, DIM_TEXT)


def _draw_confirm(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """Erase all's box over the plane: the question, then Cancel, the default, lit, and Erase
    all, which alone erases (D-410)."""
    if not scene.confirming:
        return
    box, cancel, erase = (pygame.Rect(r) for r in confirm_box(scene.arena_area))
    pygame.draw.rect(screen, TOOLTIP_BG, box, border_radius=8)
    pygame.draw.rect(screen, RULE, box, 1, border_radius=8)
    for k, line in enumerate(("Are you sure you want to erase", "all the objects?")):
        shown = fonts.text.render(line, True, TEXT)
        screen.blit(shown, shown.get_rect(midtop=(box.centerx, box.top + 16 + 24 * k)))
    for rect, label, default in ((cancel, "Cancel", True), (erase, "Erase all", False)):
        pygame.draw.rect(screen, ACTIVE if default else BUTTON, rect, border_radius=6)
        pygame.draw.rect(screen, LIT if default else ICON_EDGE, rect, 2, border_radius=6)
        shown = fonts.text.render(label, True, TEXT if default else REFUSED)
        screen.blit(shown, shown.get_rect(center=rect.center))


def _draw_in_hand(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """An object's key held, or carried: the object where a click would put it, under the
    mouse (D-410)."""
    piece = scene.carrying or scene.held
    if not isinstance(piece, Piece) or piece is Piece.START:
        return
    if not contains(scene.arena_area, scene.pointer) or places_hit(scene, scene.pointer):
        return
    kind = PLACED[piece]
    centre = scene.view.to_screen(*snapped(scene.view.to_world(*scene.pointer)))
    radius = (LIGHT_RADIUS if kind is ItemKind.LIGHT else NEW[kind]) * scene.view.scale
    _draw_object(screen, fonts, kind, centre, radius)
    pygame.draw.circle(screen, LIT, centre, radius + FOCUS_GAP, 2)


def places_hit(scene: EditorScene, point) -> bool:
    return key_at(scene.arena_area, point) is not None


def _draw_object(screen: pygame.Surface, fonts: Fonts, kind: ItemKind, centre, radius) -> None:
    """A light, an obstacle or a mark of `radius` [px], as the plane draws them."""
    if kind is ItemKind.LIGHT:
        draw_light(screen, fonts, centre, radius)
    elif kind is ItemKind.MARK:
        draw_mark(screen, centre, radius)
    else:
        pygame.draw.circle(screen, OBSTACLE, centre, radius)


def _draw_grid(screen: pygame.Surface, scene: EditorScene) -> None:
    """The plane as far as it shows: its dots, if they do not crowd, and a line every 5 u."""
    view, area = scene.view, pygame.Rect(scene.arena_area)
    dots = dot_step(view.scale)
    if dots is None:
        pygame.draw.rect(screen, SHADOW, area)
    else:
        screen.blit(_dotted(scene, area, dots), area.topleft)
    left, bottom, right, top = shown(view, tuple(area))
    for x in lattice(left, right, LINE_STEP):
        px = round(view.to_screen(x, 0.0)[0])
        pygame.draw.line(screen, PLANE_LINE, (px, area.top), (px, area.bottom))
    for y in lattice(bottom, top, LINE_STEP):
        py = round(view.to_screen(0.0, y)[1])
        pygame.draw.line(screen, PLANE_LINE, (area.left, py), (area.right, py))


def _dotted(scene: EditorScene, area: pygame.Rect, step: float) -> pygame.Surface:
    """The plane's ground with a dot every `step` [u], as `area` shows it; made again only when
    the view or the area changes."""
    view = scene.view
    key = (view, tuple(area), step)
    if _dots_cache["key"] != key:
        left, bottom, right, top = shown(view, tuple(area))
        xs = np.round(view.origin[0] + view.scale * lattice(left, right, step)).astype(int)
        ys = np.round(view.origin[1] - view.scale * lattice(bottom, top, step)).astype(int)
        xs, ys = xs - area.x, ys - area.y
        xs, ys = xs[(xs >= 0) & (xs < area.w)], ys[(ys >= 0) & (ys < area.h)]
        pixels = np.empty((area.h, area.w, 3), dtype=np.uint8)
        pixels[...] = SHADOW
        for dy in range(DOT_SIZE):  # a square of DOT_SIZE pixels, from the point down and right
            for dx in range(DOT_SIZE):
                rows, cols = ys + dy, xs + dx
                pixels[np.ix_(rows[rows < area.h], cols[cols < area.w])] = PLANE_DOT
        flat = pygame.image.frombuffer(pixels.tobytes(), area.size, "RGB")
        _dots_cache["surface"], _dots_cache["key"] = flat.copy(), key  # its own pixels
    return _dots_cache["surface"]


def _draw_rows(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """The Editor's own drawers: Objects' rows, each object and how many are on the plane, lit if
    in hand or picked (D-410); Goals'; Brief's fields; Files'; Navigator's rays, overview and
    zoom."""
    layout, level = scene.layout, scene.level
    counts = Counter(item.kind for item in level.items)
    for piece, rect in layout.piece_rows:
        count = ("count", str(1 if piece is Piece.START else counts[PLACED[piece]]))
        active = piece is scene.held or (piece is Piece.START and Piece.START in scene.pick)
        if piece is Piece.START:  # the swimmer's own shape, as on its key (D-410)
            count = ("count", "0" if scene.start_off else "1")
            draw_row(screen, scene, fonts, rect, piece, NAMES[piece], count, active)
            x, y, _, h = rect
            draw_swimmer_icon(screen, (x + 20, y + h // 2), 8, TEXT)
        else:
            icon = PIECE_ICON[piece]
            draw_row(screen, scene, fonts, rect, piece, NAMES[piece], count, active, icon=icon)
    for field, rect in layout.brief_fields:
        writing = scene.writing is field
        author = (level.author or "").removeprefix("@")  # its "@" outside the field (D-341)
        said = {Brief.TITLE: level.title, Brief.SPEC: level.spec}.get(field, author)
        field_now = scene.field if writing else None
        text, caret = (field_now.text, field_now.caret) if field_now else (said, None)
        anchor = field_now.anchor if field_now else None
        if field is Brief.AUTHOR:  # the "@", fixed, before the field (D-341)
            at = fonts.text.render("@", True, TEXT)
            screen.blit(at, at.get_rect(midright=(rect[0] - 4, rect[1] + rect[3] // 2)))
        if field is not Brief.SPEC:  # the title's, the author's (D-331)
            hint = "Title" if field is Brief.TITLE else ""  # dimmed, while it has none (D-419)
            draw_field(screen, fonts, rect, text, caret, hint=hint, anchor=anchor)
        else:
            _draw_spec(screen, fonts, rect, text, caret, anchor)
    _draw_goals(screen, scene, fonts)
    _draw_parts(screen, scene, fonts)
    for start, rect in layout.start_rows:  # under the rule, scrolled (D-322)
        label, level = scene.starts[start.index] if start.index is not None else ("", None)
        name, icon = ("Blank level", "file") if level is None else (level.title, None)
        draw_row(
            screen, scene, fonts, rect, start, name, ("none", ""), icon=icon, badge=label or None
        )
    for button, rect in scene.layout.view_buttons:
        key = ("key", VIEW_KEYS[button])
        icon = VIEW_ICON[button]
        draw_row(
            screen, scene, fonts, rect, button, ROW_NAME[button], key, scene.show_rays, icon=icon
        )
    if scene.layout.overview is not None:
        draw_overview(screen, scene, fonts, (*scene.pos[0], scene.heading))


def _share_says(scene: EditorScene) -> str:
    """The line under Share level (D-320): its score, once won as it stands; else how to win."""
    if scene.checking is not None:
        return f"Checking its proof: {round(100 * scene.checking[0].progress)}%"
    if at_start(scene.level) is not None:  # D-349
        return "Decided at its start: not judged"
    if scene.shareable:
        return f"Won in {scene.proof.ticks * DT:.2f} s, {scene.proof.parts} parts"
    return "Win it in Run first"  # D-321


def _draw_parts(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """Parts (D-315): the board's cells, then each part, its icon and name, then − and + either
    side of how many, the infinity sign for unlimited, greyed at the ends of what it may be."""
    board = scene.level.board
    for what, rect in scene.layout.steppers:
        box = pygame.Rect(rect)
        pygame.draw.rect(screen, BUTTON, box, border_radius=6)
        slot = (box.left + 20, box.centery)
        if what.kind is None:
            fonts.icons.draw(screen, "border-all", slot, 16, TEXT)
            zone = board["zone"]
            name, value = "Cells", zone if isinstance(zone, int) else len(zone)
            low, high = value <= ZONES[0], value >= ZONES[-1]
        else:
            draw_part(screen, fonts, what.kind, MENU_ANGLE.get(what.kind), slot, 24, False)
            name, value = PART_NAME[what.kind], board["stock"].get(what.kind.value, 0)
            low, high = value == 0, value is None
        shown = cached_text(fonts.name, name, TEXT)
        screen.blit(shown, (box.left + 42, box.centery - shown.get_height() // 2))
        minus, plus = step_buttons(rect)
        for button, icon, end in ((minus, "minus", low), (plus, "plus", high)):
            centre, radius = pygame.Rect(button).center, button[2] // 2
            pygame.draw.circle(screen, PANEL, centre, radius)
            pygame.draw.circle(screen, RULE if end else ICON_EDGE, centre, radius, 1)
            fonts.icons.draw(screen, icon, centre, 12, GREYED if end else TEXT)
        middle = ((minus[0] + minus[2] + plus[0]) // 2, box.centery)
        if value is None:
            fonts.icons.draw(screen, "infinity", middle, 14, TEXT)
        else:
            count = cached_text(fonts.small, str(value), TEXT)
            screen.blit(count, count.get_rect(center=middle))


def _draw_goals(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """Goals (D-308): each goal's name, as the run will say it, its bin at the right; under it,
    its words' buttons, those it says lit, those that would aim at nothing dimmed; the sliders;
    Add a goal."""
    layout, level = scene.layout, scene.level
    for head, rect in layout.goal_heads:
        x, y, _, h = rect
        shown = cached_text(fonts.name, level.objectives[head.index].name(level), TEXT)
        screen.blit(shown, (x + 2, y + (h - shown.get_height()) // 2))
        fonts.icons.draw(screen, "trash-can", pygame.Rect(bin_rect(rect)).center, 14, DIM_TEXT)
    for word, rect in layout.goal_words:
        goal = level.objectives[word.goal]
        said = word.word in (goal.verb, goal.many, goal.target)
        dimmed = not said and lacks(level, word.goal, word.word) is not None
        box = pygame.Rect(rect)
        pygame.draw.rect(screen, ACTIVE if said else BUTTON, box, border_radius=6)
        if said:
            pygame.draw.rect(screen, LIT, box, 2, border_radius=6)
        shown = cached_text(fonts.label, WORD_NAME[word.word], GREYED if dimmed else TEXT)
        screen.blit(shown, shown.get_rect(center=box.center))
    for knob, rect in layout.knobs:
        _draw_knob(screen, scene, fonts, knob, rect)
    for button, rect in layout.goal_buttons:
        draw_row(screen, scene, fonts, rect, button, ROW_NAME[button], ("none", ""), icon="plus")


def _draw_knob(screen: pygame.Surface, scene: EditorScene, fonts: Fonts, knob: Knob, rect) -> None:
    """A slider of Goals: what it sets, at its left; its track, as Navigator's zoom; its value,
    in a box at its right, a field with a caret while it is typed in."""
    now, scale = scene.value(knob), scene.scale(knob)
    name = "Time" if knob.goal is None else settings(scene.level.objectives[knob.goal])[0][0]
    label, track, value = slider_parts(rect)
    shown = cached_text(fonts.label, name.capitalize(), DIM_TEXT)
    screen.blit(shown, (label[0], label[1] + (label[3] - shown.get_height()) // 2))
    level = (min(max(now, scale.lo), scale.hi) - scale.lo) / (scale.hi - scale.lo)
    draw_track(screen, track, level, held=scene.sliding == knob)
    if scene.writing == knob:
        field = scene.field
        draw_field(screen, fonts, value, field.text, field.caret, anchor=field.anchor)
        return
    box = pygame.Rect(value)
    pygame.draw.rect(screen, BUTTON, box, border_radius=6)
    shown = cached_text(fonts.small, f"{now:g} {scale.unit}".strip(), TEXT)
    screen.blit(shown, shown.get_rect(center=box.center))


def _draw_spec(
    screen: pygame.Surface, fonts: Fonts, rect, text: str, caret: int | None, anchor=None
) -> None:
    """Brief's spec (D-305): its text wrapped to the box, SPEC_LINES lines of it, those round the
    caret while it is typed in, the caret a bar, the selection lit behind it (D-418); the box
    outlined in the accent then."""
    box = pygame.Rect(rect)
    pygame.draw.rect(screen, BUTTON, box, border_radius=6)
    if caret is not None:
        pygame.draw.rect(screen, LIT, box, 2, border_radius=6)
    font, left, room = fonts.small, box.left + 12, box.width - 24
    lines = wrapped(text, lambda line: font.size(line.rstrip())[0] <= room)
    line, along = caret_at(lines, caret) if caret is not None else (0, 0)
    first = max(0, line - SPEC_LINES + 1)
    span = None if caret is None or anchor in (None, caret) else sorted((anchor, caret))
    for n, (start, words) in enumerate(lines[first : first + SPEC_LINES]):
        top = box.top + FIELD_PAD + n * HINT_LINE
        if span is not None and span[0] < start + len(words) and span[1] > start:
            lo, hi = max(span[0], start) - start, min(span[1], start + len(words)) - start
            x0, x1 = left + font.size(words[:lo])[0], left + font.size(words[:hi])[0]
            pygame.draw.rect(screen, SELECTED, (x0, top + 1, x1 - x0, HINT_LINE - 2))
        screen.blit(font.render(words, True, TEXT), (left, top + 1))
    if caret is not None:
        x = left + font.size(lines[line][1][:along])[0]
        top = box.top + FIELD_PAD + (line - first) * HINT_LINE
        pygame.draw.line(screen, LIT, (x, top + 2), (x, top + HINT_LINE - 2), 2)


def _draw_foot(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """What the drawer's scrolled rows do not clip: atop Files, Save/Load, over its rule."""
    if scene.layout.files_rule is not None:
        _draw_save_load(screen, scene, fonts)


def _draw_save_load(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """Files' Save/Load (D-310, D-320): its title; Copy level, the field to paste a level into,
    Share level, greyed until it is won, and the line under it; the rule over the levels to
    start from, which scroll under it (D-322)."""
    layout = scene.layout
    for title, rect in layout.section_titles:
        if title == "Save/Load":
            draw_heading(screen, fonts, title, rect)
    for button, rect in layout.file_buttons:
        share = button is FileButton.SHARE  # greyed until the level is won (D-320)
        icon, shut = ("share", not scene.shareable) if share else ("copy", False)
        name = ROW_NAME[button]
        draw_row(screen, scene, fonts, rect, button, name, ("none", ""), greyed=shut, icon=icon)
    x, y, _, h = layout.share_note
    note = cached_text(fonts.small, _share_says(scene), LIT if scene.shareable else DIM_TEXT)
    screen.blit(note, (x + 4, y + (h - note.get_height()) // 2))
    pasting = scene.writing is Paste.LEVEL
    field = scene.field if pasting else None
    text, caret, anchor = (field.text, field.caret, field.anchor) if field else ("", None, None)
    hint = "Paste a level"
    draw_field(
        screen, fonts, layout.level_field, text, caret, "paste", hint, row=True, anchor=anchor
    )
    x, y, w, _ = layout.files_rule
    pygame.draw.line(screen, DIVIDER, (x, y), (x + w, y), 2)  # the bar that divides (D-422)


def _about(scene: EditorScene, what: object) -> tuple[str, tuple[str, ...]]:
    """What the Editor's info boxes say: an object's row, undo and redo, a view's button, a row
    of Start from; Share level's, once it has copied, how to share the level (D-346)."""
    if what is FileButton.SHARE and scene.shared:
        return SHARED
    if isinstance(what, Piece):
        return NAMES[what], (PIECE_ABOUT[what],)
    if isinstance(what, Start) and what.index is None:
        blank = f"No item, the swimmer at the origin, no goal, {BLANK_TIME:g} s, two of each part."
        return "Blank level", (blank, KEPT)
    if isinstance(what, Start):
        level = scene.starts[what.index][1]
        return level.title, (level.spec, KEPT)
    return ROW_NAME[what], (TIP[what],)


def _draw_status(screen: pygame.Surface, scene: EditorScene, fonts: Fonts) -> None:
    """What a click or a key does now; why something was refused; that the level is decided
    where its swimmer starts, while it is (D-349); what a passkey opened."""
    text, colour = scene.hint(), DIM_TEXT
    start = at_start(scene.level)
    if scene.message:
        text, colour = scene.message, REFUSED
    elif start is not None:
        text, colour = UNJUDGED[start], REFUSED
    elif scene.said:
        text, colour = scene.said, LIT
    draw_status_line(screen, scene, fonts, text, colour)
