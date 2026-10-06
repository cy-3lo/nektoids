# To do

The jam build shipped as v1.0 (D-106), and stage 0, Foundations, is built (D-200 to D-206). What
is left goes here, in the order it unblocks the rest; the PR that does an item removes it, and
what was done is in git and in [`decisions.md`](decisions.md). Sections keep their numbers,
which the decision log cites. Ideas for later go in [`ideas.md`](ideas.md). §11 is stage 1, a
level maker, built on `stage/1-level-maker` and merged into `main` in one PR (D-300).

## 11. A level maker (stage 1, D-300)

For us and Camille first, then for players (D-105). Each item is planned, and its decisions
taken, when it starts.

- [ ] **A level editor**, Super Mario Maker-like: levels are data already (D-028). It comes
  first after the foundations (D-105): Camille can make levels without programming (D-041), and
  every later stage needs levels. It is the Maker, a third tab on the sandbox (D-301).
  Done, on `stage/1-level-maker`:
  - [x] The Maker's tab: the plane at large over its grid, a dot every 1 u and a line every
    5 u, no rulers; Navigator (D-301, D-311, #50).
  - [x] Objects, as Parts with its Wheel: lights, obstacles, marks and the swimmer's start,
    placed, dragged, sized, turned, deleted; undo and redo (D-302, D-306, #51, #55). The Wheel
    works as the Editor's: the action atop the plane, Move on an object clicked, More on one
    placed, the arrows and Enter, its icons side by side; a click on the plane opens it
    (D-314, D-316, D-317).
  - [x] The tabs: F1 to F3, Tab and Shift+Tab; Esc backs out, then opens Chapters (D-303,
    D-304, #52, #53).
  - [x] Text, once Brief: the level's title and spec, in fields with a caret (D-305, D-318,
    #54).
  - [x] Marks, zones only the objectives read (D-306, #55); objectives as sentences: reach,
    leave or stay all, one or none of the lights, obstacles or marks (D-307, #56, #57); circle
    gone, Orbit asking to enter four rings round its light (D-312); the rings lit one by one
    as they are entered (D-318).
  - [x] Goals: the time allowed, and at most two goals, each a sentence chosen in three rows of
    buttons, the words that would aim at nothing dimmed; sliders for the time and a stay's
    seconds, their values typed too (D-308, #59, #60, #61).
  - [x] Save, in the Maker's Files: Copy level, its JSON; Paste a level; Start from a blank
    plane or a shipped level (D-310, #64, #65).
  - [x] Whole numbers: positions on whole units, settings from 1 to 8, the shipped levels too;
    level files version 4, the zone written as its size (D-311, D-313, D-317, D-318).
  - [x] Parts, in the Maker: the board's size, 7, 19 or 37 cells, and each part handed out,
    none to 9 or unlimited, grouped and folding as the Editor's; the Editor's board takes it
    at once or the change is refused; Paste and Start from bring it (D-315).
  - [x] The Maker opens on a blank plane, two of each part (D-317).
  - [x] The board's locked parts: Lock, a mode of the sandbox's Tools (K), makes a part the
    level's, fixed and using no stock, or frees it; the level places what is locked, Copy level
    writes it, Paste and Start from bring it (D-319).
  - [x] Share level: once won as it stands, the level copied with its proof, the winning board's
    text and its score; pasted, the proof run again, the level cleared if it wins, its score the
    one to beat, else a draft (D-320).

  To do, in this order:
  - [ ] Perhaps: a slider in Objects for the focused item's power or radius, beside < and >.
- [ ] **"Two lights, four obstacles"**, set aside as too hard for level 2 (D-032): 5 winners in
  2,603 random wirings, the fastest a one-eyed circler. Its plane lives on as the sandbox's,
  under that title (`levels/data/sandbox.json`); its file as a level is in the history
  (`game/nektoids/levels/data/two-lights.json`, removed after PR #12).
- [x] **Sharing levels and solutions.** Solutions as a board's text (D-205, D-206); levels as
  their JSON (D-310), shared with their proof (D-320).
- [ ] **A first level, before Fear** (the physicist's): its parts already on the board, one eye
  and one thruster, and the player just has to connect them; the goal is to go straight
  (Drags). D-300's scope names the levels, so it takes a decision when it starts.

## 12. Checks and fixes on `main`

- [ ] Files' title, "Wins this session", is not drawn: it lies above the wins' list, and the
  drawer's rows are clipped to that list (`editor/draw.py`, `draw_drawer`). Seen 2026-10-04.
- [ ] Copy a board and Paste a board in Firefox; only Chrome and Safari 26.6 were tried (D-206).
- [ ] The Maker in Safari: a slider's typed value, Paste a level (D-308, D-310); only Chrome was
  tried.
