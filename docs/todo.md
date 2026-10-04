# To do

What is left before the jam build ships, in the order it unblocks the rest. The PR that does an
item removes it; what was done is in git and in [`decisions.md`](decisions.md). Sections keep
their numbers, which the decision log cites. Ideas for after the jam go in [`ideas.md`](ideas.md).
§10 is stage 0, Foundations, built on `stage/0-foundations` and merged into `main` once the
jam build is uploaded (D-200).

## 5. Ship

- [ ] `DEV_VIEW = False` for the build that is uploaded.
- [ ] `pygbag --build --archive game`, upload to itch.io.
- [ ] Check in Chrome and in Safari. Safari has never been checked: the keys (Cmd+Y opens its
      History window), the fonts, the canvas.

## 10. Foundations (stage 0, D-200)

What every later stage needs; none of it shows to the player but Save and Load. In the order
they are built.

- [ ] **One table of part kinds** (from a map of the code, 2026-10-04). A kind is spread today
      over `Kind` and its side dicts in `graph/board.py`, `GAIN` in `graph/network.py`, `NAME`
      and `WHAT` in `editor/parts.py`, and `editor/icons.py`, `layout.py` (`MENU_GROUPS`),
      `wheel.py`, `draw.py`, `marks.py` and `entry.py`. A kind left out of `GAIN` is taken for a
      sensor and held at 0 (`graph/dynamics.py`, `step`), with no error. Every stage after this
      adds parts: with one table, checked by a test, a new part is one entry.
- [ ] **Sensors in general**: `sim/world.py`'s `step` hands the graph the eyes' rates only; flow
      sensing (stage 3) is a second sense.
- [ ] **Saving and loading, and a board as text**, one piece of work (was todo §9; D-093). Save
      and Load come back with it, as rows at the foot of Files, under this session's wins
      (D-092); until D-093 they sat there greyed (D-027). The format of D-024, with a version
      number, keeping wire paths exactly; a board as a short line of ASCII to copy, paste, keep
      in a text file and open again: that board packed into bits and spelled out. Its language
      is a decision first. `Board.from_dict` never reads a saved path today: it draws every
      wire again (`graph/board.py`).
      - Letters (base 32, like a licence key) or words from a list (2048 words, 11 bits each)?
      - Length, roughly: six parts and six wires with their paths kept exactly come to under 200
        bits, about 35 letters or 17 words; less if the paths are drawn again in wire order,
        which gives the same routes unless Move or Delete was used (D-024).
      - A check against typing mistakes, Shannon-like: redundant check symbols, so a mistyped
        line is refused (or even corrected) rather than loading another board. A version mark.
      - Copy and paste between the canvas and the page: does pygbag reach the clipboard? Wait
        and see on the web build.
      - The same mechanism as the level passkeys (D-075): a word that brings a state back.
