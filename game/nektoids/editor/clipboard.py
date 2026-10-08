"""The clipboard and Load's field: through the page on the web, through pygame natively (D-206).

On the web pygame has no clipboard (pygbag ships no `pygame.scrap`), and a canvas is never
pasted into: Safari sends no copy or paste event when nothing on the page is selected, and
refuses `navigator.clipboard.readText`. So the page does it, with a few lines of JavaScript put
in once at startup (`install`): Save writes the text with `navigator.clipboard.writeText` on a
click; Load focuses a text field of the page's own, invisible, once the click is over, which
Cmd/Ctrl+V pastes into and whose keys never reach the game; the Board reads it once a frame.
Natively, `pygame.scrap` does both, and the Board hands the field pygame's keys. The page's
own F1 and F3, help and find, are stopped: they are the Run's and the Editor's tabs (D-303).
"""

from __future__ import annotations

import json
import sys

WEB = sys.platform == "emscripten"

PAGE = r"""
window.addEventListener('keydown', function (e) {
  if (e.key === 'F1' || e.key === 'F3') { e.preventDefault(); }  // the tabs', not help, find
});
window.nkCopy = function (text) {
  if (navigator.clipboard) { navigator.clipboard.writeText(text).catch(function () {}); }
};
window.nkField = (function () {
  var field = null, ended = '';
  function make() {
    field = document.createElement('textarea');
    ['autocapitalize', 'autocorrect', 'autocomplete'].forEach(function (name) {
      field.setAttribute(name, 'off'); });
    field.setAttribute('spellcheck', 'false');
    // Writing aids and password managers attach to any field that gets focus; one of them
    // failed in Safari on this one. These are the marks they read as "leave it alone".
    [['data-gramm', 'false'], ['data-gramm_editor', 'false'], ['data-enable-grammarly', 'false'],
     ['data-lt-active', 'false'], ['data-1p-ignore', 'true'], ['data-lpignore', 'true'],
     ['data-bwignore', 'true'], ['data-form-type', 'other']].forEach(function (pair) {
      field.setAttribute(pair[0], pair[1]); });
    field.style.cssText = 'position:fixed;left:0;top:0;width:2px;height:2px;opacity:0;'
      + 'border:0;padding:0;';
    ['keydown', 'keyup', 'keypress'].forEach(function (name) {
      field.addEventListener(name, function (e) { e.stopPropagation(); }); });
    field.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); ended = 'enter'; }
      else if (e.key === 'Escape') { e.preventDefault(); ended = 'escape'; }
      else if (e.key === 'Tab') { e.preventDefault(); }  // the focus stays in the field
    });
    document.body.appendChild(field);
  }
  return {
    open: function (text, longest) {
      if (!field) { make(); }
      field.value = text; field.maxLength = longest; ended = '';
      setTimeout(function () {  // after the click, or Safari takes the focus back
        field.focus(); field.selectionStart = field.selectionEnd = field.value.length; }, 60);
    },
    close: function () { if (field) { field.blur(); } },
    text: function () { return field ? field.value : ''; },
    caret: function () {  // the end the selection grows from, as the keys move it (D-418)
      if (!field) { return 0; }
      return field.selectionDirection === 'backward' ? field.selectionStart : field.selectionEnd;
    },
    anchor: function () {
      if (!field) { return 0; }
      return field.selectionDirection === 'backward' ? field.selectionEnd : field.selectionStart;
    },
    select: function (caret, anchor) {  // a click in the game's field: the page's follows
      setTimeout(function () {
        if (!field) { return; }
        field.focus();
        field.setSelectionRange(Math.min(caret, anchor), Math.max(caret, anchor),
          caret < anchor ? 'backward' : 'forward');
      }, 60);
    },
    ended: function () { var was = ended; ended = ''; return was; }
  };
})();
"""


def _page(code: str):
    import platform  # pygbag's: the page's window

    return platform.window.eval(code)


def install() -> None:
    """Once, at startup: the page's side of it (web.md: no loading during the loop)."""
    if WEB:
        _page(PAGE)


def copy(text: str) -> None:
    """Put `text` on the clipboard, if the browser lets it; the status line shows it anyway."""
    if WEB:
        _page(f"nkCopy({json.dumps(text)})")
        return
    import pygame

    try:
        pygame.scrap.put_text(text)
    except (NotImplementedError, pygame.error):
        pass


def paste() -> str:
    """Natively: what the clipboard holds as text, or nothing. On the web the page pastes."""
    if WEB:
        return ""
    import pygame

    try:
        return pygame.scrap.get_text() or ""
    except (NotImplementedError, pygame.error):
        return ""


def open_field(text: str, longest: int) -> None:
    """On the web, the page's field takes the keys, once the click is over, holding `text`, the
    caret after it, and no more than `longest` characters."""
    if WEB:
        _page(f"nkField.open({json.dumps(text)}, {int(longest)})")


def close_field() -> None:
    if WEB:
        _page("nkField.close()")


def field() -> tuple[str, int, int, str | None]:
    """On the web: what the page's field holds, where its caret is and the selection's other end
    (D-418), and "enter" or "escape" if it was ended since the last call, else None."""
    if not WEB:
        return "", 0, 0, None
    ended = str(_page("nkField.ended()"))
    caret, anchor = int(_page("nkField.caret()")), int(_page("nkField.anchor()"))
    return str(_page("nkField.text()")), caret, anchor, ended or None


def select_field(caret: int, anchor: int) -> None:
    """On the web, the page's field selects from `anchor` to `caret`, and takes the keys."""
    if WEB:
        _page(f"nkField.select({int(caret)}, {int(anchor)})")
