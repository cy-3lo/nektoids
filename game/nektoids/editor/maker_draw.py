"""Drawing the Maker (D-301). Reads the scene; never changes it.

The plane at large, as the run shows it, over its grid: a dot wherever a position may fall,
every whole u, 2 px wide, none where they would crowd (`dot_step`); a line every 5 u, no
coordinate: the grid is enough (D-311). Over the grid the light's rays, as they stand when the
run starts, the obstacles, the lights, and the swimmer where it starts, its wedge where it
heads; the focus lit, a ring round its object or a cross on its point; what is in hand, where a
click would put it; atop it, as in the Editor, what the next click or Enter does, or what is
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
    SYMBOL_WIDTH,
    draw_items,
    draw_light,
    draw_mark,
    draw_marks,
    draw_overview,
    draw_rays,
)
from nektoids.editor.arena_view import LINE_STEP, dot_step, lattice, shown
from nektoids.editor.devdrive import DT
from nektoids.editor.draw import (
    MENU_ANGLE,
    ROW_NAME,
    TIP,
    Fonts,
    cached_text,
    draw_bar,
    draw_disc,
    draw_drawer,
    draw_field,
    draw_info,
    draw_part,
    draw_row,
    draw_status_line,
    draw_symbol,
    draw_tabs,
    draw_tip,
    draw_tooltip,
    draw_track,
)
from nektoids.editor.icons import EDIT_ICON, PIECE_ICON, VIEW_ICON
from nektoids.editor.layout import (
    ACTION_WIDTH,
    BAR_WIDTH,
    EDIT_KEYS,
    FIELD_PAD,
    HINT_LINE,
    SPEC_LINES,
    VIEW_KEYS,
    WHEEL_TITLE,
    Brief,
    EditButton,
    FileButton,
    Knob,
    Piece,
    Start,
    Tool,
    bin_rect,
    contains,
    slider_parts,
    step_buttons,
)
from nektoids.editor.maker import MakerScene, Paste
from nektoids.editor.objects import (
    KEYS,
    NAMES,
    PLACED,
    Point,
    name,
    offer,
    piece_of,
    reach,
    says,
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
    GREYED,
    HOVER,
    ICON_EDGE,
    LIT,
    OBSTACLE,
    PANEL,
    PLANE_DOT,
    PLANE_LINE,
    REFUSED,
    RULE,
    SHADOW,
    TEXT,
)
from nektoids.editor.parts import NAME as PART_NAME
from nektoids.editor.textfield import caret_at, wrapped
from nektoids.editor.wheel import ICON, LINE_BELOW, WHEEL_HEX, centre_in
from nektoids.levels.lattice import snapped
from nektoids.levels.level import ItemKind
from nektoids.levels.making import BLANK_TIME, NEW, ZONES, lacks
from nektoids.levels.objectives import Count, Target, Verb, settings
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

KEPT = "Its plane, goals and time replace the level's; the board stays as it is."  # D-310

_dots_cache: dict[str, object] = {"key": None, "surface": None}


def draw_maker(screen: pygame.Surface, scene: MakerScene, fonts: Fonts) -> None:
    screen.fill(BACKGROUND)
    screen.set_clip(scene.arena_area)
    _draw_grid(screen, scene)
    if scene.show_rays:  # as they stand at the run's start
        view, area = scene.view, scene.arena_area
        draw_rays(screen, view, area, scene.arena, scene.rays, 0.0, scene.pos, scene.radius)
    draw_marks(screen, scene.view, scene.level.marks)
    draw_items(screen, fonts, scene.view, scene.arena)
    centre, radius = scene.view.to_screen(*scene.pos[0]), float(scene.radius[0]) * scene.view.scale
    draw_symbol(screen, DARK, centre, radius + 1, scene.heading, SYMBOL_WIDTH + 2)
    draw_symbol(screen, BODY, centre, radius, scene.heading, SYMBOL_WIDTH)
    _draw_focus(screen, scene)
    _draw_in_hand(screen, scene, fonts)
    screen.set_clip(None)
    _draw_action(screen, scene, fonts)
    draw_tabs(screen, scene, fonts)
    _draw_status(screen, scene, fonts)
    draw_bar(screen, scene, fonts)
    draw_drawer(screen, scene, fonts, _draw_rows, _draw_foot)
    draw_tooltip(screen, scene, fonts)
    _draw_wheel_tip(screen, scene, fonts)
    draw_info(screen, scene, fonts, _about)


def _draw_action(screen: pygame.Surface, scene: MakerScene, fonts: Fonts) -> None:
    """Atop the plane, as atop the Editor's board (D-068, D-314): what the next click or Enter
    does, a lit disc, its name and key beside it, a line under it saying what it does; with no
    action, the object focused, plain; nothing with nothing focused."""
    if scene.layout.action_at is None:
        return
    action = scene.action()
    what = action if action is not None else piece_of(scene.level, scene.focus)
    if what is None:
        return
    box = pygame.Rect(scene.layout.action_at)
    fill, edge = (ACTIVE, LIT) if action is not None else (BUTTON, ICON_EDGE)
    draw_disc(screen, fonts, box.center, what, fill, edge, ACTION_WIDTH / 2)  # as the Wheel's
    key = KEYS.get(action) if scene.settings.key_hints else None  # an action's, not an object's
    named = name(scene.level, scene.focus, what) + (f" ({key})" if key else "")
    shown = fonts.text.render(named, True, LIT if action is not None else TEXT)
    at = shown.get_rect(midleft=(box.right + 10, box.centery))
    pygame.draw.rect(screen, BAR, at.inflate(14, 6), border_radius=5)  # legible over the grid
    screen.blit(shown, at)
    line = _action_says(scene, action) if action is not None else says(scene.level, scene.focus)
    under = fonts.small.render(line, True, TEXT)
    at = under.get_rect(midtop=(box.centerx, box.bottom + 8))
    pygame.draw.rect(screen, BAR, at.inflate(14, 6), border_radius=5)
    screen.blit(under, at)


def _action_says(scene: MakerScene, action) -> str:
    """What the action atop the plane does, in a short line (D-314, D-318)."""
    if isinstance(action, Piece) and scene.picked is action:
        return "Click the plane: place it"
    if isinstance(action, Piece):
        return "Enter: place it here"
    if action is Tool.MOVE:
        return "Click or arrows: move. Enter: done"
    if action is Tool.DELETE:
        return "Enter: remove it"
    if action in (Tool.TURN_LEFT, Tool.TURN_RIGHT):
        return f"Enter: turn 15° {'left' if action is Tool.TURN_LEFT else 'right'}"
    return f"Enter: {name(scene.level, scene.focus, action).lower()}"


def _draw_focus(screen: pygame.Surface, scene: MakerScene) -> None:
    """The focus lit on the plane: a ring round its object, or a cross on its point."""
    focus = scene.focus
    if focus is None:
        return
    cx, cy = scene.view.to_screen(*where(scene.level, focus))
    if isinstance(focus, Point):
        pygame.draw.circle(screen, LIT, (cx, cy), FOCUS_DOT, 2)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            near, far = FOCUS_DOT + 2, FOCUS_DOT + 8
            start, end = (cx + dx * near, cy + dy * near), (cx + dx * far, cy + dy * far)
            pygame.draw.line(screen, LIT, start, end, 2)
        return
    ring = reach(scene.level, focus) * scene.view.scale + FOCUS_GAP
    pygame.draw.circle(screen, LIT, (cx, cy), ring, 2)


def _draw_in_hand(screen: pygame.Surface, scene: MakerScene, fonts: Fonts) -> None:
    """A row of Objects picked: its object where a click would put it, under the mouse."""
    if scene.picked is None or not contains(scene.arena_area, scene.pointer):
        return
    kind = PLACED[scene.picked]
    centre = scene.view.to_screen(*snapped(scene.view.to_world(*scene.pointer)))
    radius = (LIGHT_RADIUS if kind is ItemKind.LIGHT else NEW[kind]) * scene.view.scale
    _draw_object(screen, fonts, kind, centre, radius)
    pygame.draw.circle(screen, LIT, centre, radius + FOCUS_GAP, 2)


def _draw_object(screen: pygame.Surface, fonts: Fonts, kind: ItemKind, centre, radius) -> None:
    """A light, an obstacle or a mark of `radius` [px], as the plane draws them."""
    if kind is ItemKind.LIGHT:
        draw_light(screen, fonts, centre, radius)
    elif kind is ItemKind.MARK:
        draw_mark(screen, centre, radius)
    else:
        pygame.draw.circle(screen, OBSTACLE, centre, radius)


def _draw_grid(screen: pygame.Surface, scene: MakerScene) -> None:
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


def _dotted(scene: MakerScene, area: pygame.Rect, step: float) -> pygame.Surface:
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


def _draw_rows(screen: pygame.Surface, scene: MakerScene, fonts: Fonts) -> None:
    """The Maker's own drawers: Objects' rows, each object and how many are on the plane, lit if
    in hand or focused, then undo and redo; Goals'; Brief's fields; Files'; Navigator's rays,
    overview and zoom."""
    layout, level = scene.layout, scene.level
    counts = Counter(item.kind for item in level.items)
    for piece, rect in layout.piece_rows:
        count = ("count", str(1 if piece is Piece.START else counts[PLACED[piece]]))
        active = piece is scene.picked or (piece is Piece.START and scene.focus is Piece.START)
        icon = PIECE_ICON[piece]
        draw_row(screen, scene, fonts, rect, piece, NAMES[piece], count, active, icon=icon)
    can = {EditButton.UNDO: scene.history.can_undo, EditButton.REDO: scene.history.can_redo}
    for button, rect in layout.edit_buttons:
        key = ("key", EDIT_KEYS[button].replace("+", " "))
        name_ = ROW_NAME[button]
        draw_row(
            screen,
            scene,
            fonts,
            rect,
            button,
            name_,
            key,
            False,
            not can[button],
            EDIT_ICON[button],
        )
    for field, rect in layout.brief_fields:
        writing = scene.writing is field
        author = (level.author or "").removeprefix("@")  # its "@" outside the field (D-341)
        said = {Brief.TITLE: level.title, Brief.SPEC: level.spec}.get(field, author)
        text, caret = (scene.field.text, scene.field.caret) if writing else (said, None)
        if field is Brief.AUTHOR:  # the "@", fixed, before the field (D-341)
            at = fonts.text.render("@", True, TEXT)
            screen.blit(at, at.get_rect(midright=(rect[0] - 4, rect[1] + rect[3] // 2)))
        if field is not Brief.SPEC:  # the title's, the author's (D-331)
            draw_field(screen, fonts, rect, text, caret)
        else:
            _draw_spec(screen, fonts, rect, text, caret)
    _draw_goals(screen, scene, fonts)
    _draw_parts(screen, scene, fonts)
    for start, rect in layout.start_rows:  # under the rule, scrolled (D-322)
        label, level = scene.starts[start.index] if start.index is not None else ("", None)
        name, icon = ("Blank level", "file") if level is None else (level.title, "border-all")
        if label:
            name, icon = level.title, None
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


def _share_says(scene: MakerScene) -> str:
    """The line under Share level (D-320): its score, once won as it stands; else how to win."""
    if scene.checking is not None:
        return f"Checking its proof: {round(100 * scene.checking[0].progress)}%"
    if scene.shareable:
        return f"Won in {scene.proof.ticks * DT:.2f} s, {scene.proof.parts} parts"
    return "Win it in Run first"  # D-321


def _draw_parts(screen: pygame.Surface, scene: MakerScene, fonts: Fonts) -> None:
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


def _draw_goals(screen: pygame.Surface, scene: MakerScene, fonts: Fonts) -> None:
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


def _draw_knob(screen: pygame.Surface, scene: MakerScene, fonts: Fonts, knob: Knob, rect) -> None:
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
        draw_field(screen, fonts, value, scene.field.text, scene.field.caret)
        return
    box = pygame.Rect(value)
    pygame.draw.rect(screen, BUTTON, box, border_radius=6)
    shown = cached_text(fonts.small, f"{now:g} {scale.unit}".strip(), TEXT)
    screen.blit(shown, shown.get_rect(center=box.center))


def _draw_spec(screen: pygame.Surface, fonts: Fonts, rect, text: str, caret: int | None) -> None:
    """Brief's spec (D-305): its text wrapped to the box, SPEC_LINES lines of it, those round the
    caret while it is typed in, the caret a bar; the box outlined in the accent then."""
    box = pygame.Rect(rect)
    pygame.draw.rect(screen, BUTTON, box, border_radius=6)
    if caret is not None:
        pygame.draw.rect(screen, LIT, box, 2, border_radius=6)
    font, left, room = fonts.small, box.left + 12, box.width - 24
    lines = wrapped(text, lambda line: font.size(line.rstrip())[0] <= room)
    line, along = caret_at(lines, caret) if caret is not None else (0, 0)
    first = max(0, line - SPEC_LINES + 1)
    for n, (_, words) in enumerate(lines[first : first + SPEC_LINES]):
        top = box.top + FIELD_PAD + n * HINT_LINE
        screen.blit(font.render(words, True, TEXT), (left, top + 1))
    if caret is not None:
        x = left + font.size(lines[line][1][:along])[0]
        top = box.top + FIELD_PAD + (line - first) * HINT_LINE
        pygame.draw.line(screen, LIT, (x, top + 2), (x, top + HINT_LINE - 2), 2)


def _draw_foot(screen: pygame.Surface, scene: MakerScene, fonts: Fonts) -> None:
    """What the drawer's scrolled rows do not clip: at the foot of Objects, the Wheel; atop
    Files, Save/Load, over its rule."""
    if scene.layout.wheel_fold is not None:
        _draw_wheel(screen, scene, fonts)
    if scene.layout.files_rule is not None:
        _draw_save_load(screen, scene, fonts)


def _draw_save_load(screen: pygame.Surface, scene: MakerScene, fonts: Fonts) -> None:
    """Files' Save/Load (D-310, D-320): its title; Copy level, the field to paste a level into,
    Share level, greyed until it is won, and the line under it; the rule over the levels to
    start from, which scroll under it (D-322)."""
    layout = scene.layout
    for title, (x, y, _, h) in layout.section_titles:
        if title == "Save/Load":
            shown = cached_text(fonts.label, title.upper(), DIM_TEXT)
            screen.blit(shown, (x, y + (h - shown.get_height()) // 2))
    for button, rect in layout.file_buttons:
        share = button is FileButton.SHARE  # greyed until the level is won (D-320)
        icon, shut = ("share", not scene.shareable) if share else ("copy", False)
        name = ROW_NAME[button]
        draw_row(screen, scene, fonts, rect, button, name, ("none", ""), greyed=shut, icon=icon)
    x, y, _, h = layout.share_note
    note = cached_text(fonts.small, _share_says(scene), LIT if scene.shareable else DIM_TEXT)
    screen.blit(note, (x + 4, y + (h - note.get_height()) // 2))
    pasting = scene.writing is Paste.LEVEL
    text, caret = (scene.field.text, scene.field.caret) if pasting else ("", None)
    draw_field(screen, fonts, layout.level_field, text, caret, "paste", "Paste a level")
    x, y, w, _ = layout.files_rule
    pygame.draw.line(screen, RULE, (x, y), (x + w, y), 2)  # the bar that divides, as the Wheel's


def _draw_wheel(screen: pygame.Surface, scene: MakerScene, fonts: Fonts) -> None:
    """As Tools and Parts draw it (D-068, D-069): a rule, The Wheel's title, which folds; unless
    folded, the focus large at its hub, the Wheel's icons round it, the one Enter uses lit, a
    line under it saying what is focused and its setting, the action being named atop the plane
    (D-314, D-317). The Maker's Wheel never folds: its title has no arrow."""
    layout = scene.layout
    fx, fy, fw, _ = layout.wheel_fold
    pygame.draw.line(screen, RULE, (fx, fy - 3), (fx + fw, fy - 3), 2)  # the bar that divides
    x, y, _, h = layout.wheel_fold
    title = cached_text(fonts.label, WHEEL_TITLE.upper(), DIM_TEXT)
    screen.blit(title, (x, y + (h - title.get_height()) // 2))
    if layout.wheel_view is None:
        return
    centre = centre_in(layout.wheel_view)
    if scene.focus is None:
        pygame.draw.circle(screen, RULE, centre, WHEEL_HEX, 1)
    else:
        pygame.draw.circle(screen, ACTIVE, centre, WHEEL_HEX)
        pygame.draw.circle(screen, LIT, centre, WHEEL_HEX, 2)
        _draw_hub(screen, scene, fonts, centre)
    wheel, radius = scene.wheel(), ICON * WHEEL_HEX
    action = scene.action() if scene.action() in offer(scene.focus) else None
    for slot in wheel:
        lit = slot.what is action
        fill = ACTIVE if lit else HOVER if slot == scene.wheel_hover else BUTTON
        draw_disc(screen, fonts, slot.at, slot.what, fill, LIT if lit else ICON_EDGE, radius)
    lowest = max([centre[1] + WHEEL_HEX] + [slot.at[1] + radius for slot in wheel])
    line = fonts.small.render(says(scene.level, scene.focus), True, DIM_TEXT)  # its setting
    screen.blit(line, line.get_rect(midtop=(round(centre[0]), round(lowest) + LINE_BELOW)))


def _draw_hub(screen: pygame.Surface, scene: MakerScene, fonts: Fonts, centre) -> None:
    """The focus drawn large at the Wheel's hub: a point's cross, the swimmer, a light, an
    obstacle as big as its radius says, within the hub."""
    focus = scene.focus
    if isinstance(focus, Point):
        fonts.icons.draw(screen, "location-crosshairs", centre, 28, TEXT)
    elif focus is Piece.START:
        draw_symbol(screen, BODY, centre, 0.6 * WHEEL_HEX, scene.heading, 3)
    else:
        item = scene.level.items[focus]
        size = {
            ItemKind.LIGHT: 0.45,
            ItemKind.OBSTACLE: 0.25 + 0.13 * item.value,  # 1 to 5 u
            ItemKind.MARK: 0.3 + 0.02 * item.value,  # 1 to 30 u
        }[item.kind]
        _draw_object(screen, fonts, item.kind, centre, size * WHEEL_HEX)


def _draw_wheel_tip(screen: pygame.Surface, scene: MakerScene, fonts: Fonts) -> None:
    """The Wheel's icon under the mouse, named in a tooltip as the bar's are (D-069): the less
    and the more as the focused item's kind says them, the key while key hints are on."""
    slot = scene.tooltip
    if slot not in scene.wheel():
        return
    text = name(scene.level, scene.focus, slot.what)
    text += f" ({slot.key})" if scene.settings.key_hints else ""
    half = fonts.text.size(text)[0] // 2 + 8  # the box's half width
    x = max(round(slot.at[0]), BAR_WIDTH + 4 + half)
    draw_tip(screen, fonts, text, midbottom=(x, round(slot.at[1] - ICON * WHEEL_HEX - 10)))


def _about(scene: MakerScene, what: object) -> tuple[str, tuple[str, ...]]:
    """What the Maker's info boxes say: an object's row, undo and redo, a view's button, a row
    of Start from."""
    if isinstance(what, Piece):
        return NAMES[what], (PIECE_ABOUT[what],)
    if isinstance(what, Start) and what.index is None:
        blank = f"No item, the swimmer at the origin, no goal, {BLANK_TIME:g} s, two of each part."
        return "Blank level", (blank, KEPT)
    if isinstance(what, Start):
        level = scene.starts[what.index][1]
        return level.title, (level.spec, KEPT)
    return ROW_NAME[what], (TIP[what],)


def _draw_status(screen: pygame.Surface, scene: MakerScene, fonts: Fonts) -> None:
    """What a click or a key does now; why something was refused; what a passkey opened."""
    text, colour = scene.hint(), DIM_TEXT
    if scene.message:
        text, colour = scene.message, REFUSED
    elif scene.said:
        text, colour = scene.said, LIT
    draw_status_line(screen, scene, fonts, text, colour)
