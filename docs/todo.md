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
      first after the foundations (D-105): Camille can make levels without programming (D-041),
      and every later stage needs levels. It is the Maker, a third tab on the sandbox (D-301).
      Done, on `stage/1-level-maker`:
      - [x] The Maker's tab: the plane at large over a grid of 0.5 u, Navigator (D-301, #50).
      - [x] Objects, as Parts with its Wheel: lights, obstacles, marks and the swimmer's start,
        placed, dragged, sized, turned, deleted; undo and redo (D-302, D-306, #51, #55).
      - [x] The tabs: F1 to F3, Tab and Shift+Tab; Esc backs out, then opens Chapters (D-303,
        D-304, #52, #53).
      - [x] Brief: the level's title and spec, in fields of text with a caret (D-305, #54).
      - [x] Marks, zones only the objectives read (D-306, #55); objectives as sentences: reach,
        leave, stay or circle all, one or none of the lights, obstacles or marks; level format
        version 3, every shipped run as it was (D-307, #56, #57).
      - [x] Goals: the time allowed, and at most two goals, each a sentence chosen in three rows
        of buttons, the words that would aim at nothing dimmed; sliders for the time and a
        stay's seconds, their values typed too (D-308, #59, #60, #61; circle gone, D-312).
      - [x] Save, in the Maker's Files: Copy level, its JSON; Paste a level; Start from a blank
        plane or a shipped level; each taking all but the board (D-310, #64, #65).
      To do, in this order:
      - [ ] The board: zone, stock and locked parts, set with the board editor itself. Done:
        the zone's size and the parts handed out, in the Maker's Parts (D-315); to come, the
        locked parts.
      - [ ] Share level, after the board, the physicist's plan (2026-10-05): Copy level stays a
        draft, for us, with no proof; Share level is offered once the level, as it stands, has
        been won, and copies its text with its proof, the winning board's text (D-205) and its
        score, the one to beat. Paste a level replays the proof, the runs being deterministic,
        and marks the level cleared if it wins, else pastes it as a draft, unproven. The check
        is the outcome, not the tick: a run may differ in its last bit across platforms (D-004).
        Shared as text, as a board is (D-206); no server.
      - [ ] Perhaps: a slider in Objects for the focused item's power or radius, beside < and >.
- [ ] **"Two lights, four obstacles"**, set aside as too hard for level 2 (D-032): 5 winners in
      2,603 random wirings, the fastest a one-eyed circler. Its plane lives on as the sandbox's,
      under that title (`levels/data/sandbox.json`); its file as a level is in the history
      (`game/nektoids/levels/data/two-lights.json`, removed after PR #12).
- [ ] **Sharing levels and solutions.** Solutions can be shared already, as a board's text
      (D-205, D-206); a level needs a text of its own, the stage's first decision.
- [ ] **A first level, before Fear** (the physicist's): its parts already on the board, one eye
      and one thruster, and the player just has to connect them; the goal is to go straight
      (Drags). D-300's scope names the levels, so it takes a decision when it starts.

## 12. Checks and fixes on `main`

- [ ] Files' title, "Wins this session", is not drawn: it lies above the wins' list, and the
      drawer's rows are clipped to that list (`editor/draw.py`, `draw_drawer`). Seen 2026-10-04.
- [ ] Copy a board and Paste a board in Firefox; only Chrome and Safari 26.6 were tried (D-206).
