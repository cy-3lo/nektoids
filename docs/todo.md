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

- [ ] **Save and Load**, the last of saving (was todo §9; D-093). Saved paths are kept exactly
      (D-204), and a board has its text (D-205, `graph/boardtext.py`). Save and Load come back
      as rows at the foot of Files, under this session's wins (D-092); until D-093 they sat
      there greyed (D-027). Loading a text puts its board on the open level by `Board.adopt`, or
      says why not.
      - Copy and paste between the canvas and the page: does pygbag reach the clipboard? Try it
        on the web build first; else the text shows in a box to select, and a field takes it.
      - A level's locked parts: the text's parts on their cells are the level's own.
