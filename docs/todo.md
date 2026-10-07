# To do

The jam build shipped as v1.0 (D-106), and stage 0, Foundations, is built (D-200 to D-206). What
is left goes here, in the order it unblocks the rest; the PR that does an item removes it, and
what was done is in git and in [`decisions.md`](decisions.md). Sections keep their numbers,
which the decision log cites. Ideas for later go in [`ideas.md`](ideas.md). §11 is stage 1, a
level maker, built on `stage/1-level-maker` and merged into `main` in one PR (D-300); §13, the
chapters, levels and tutorials made with it, done (D-325 to D-341); §14, the repository's face;
§15 is stage 2, the Board, built beside stage 1 on `stage/2-board` (D-400).

## 11. A level maker (stage 1, D-300)

For us and Camille first, then for players (D-105). Each item is planned, and its decisions
taken, when it starts.

- [x] **A level editor**, Super Mario Maker-like: levels are data already (D-028). It comes
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
    level or a shipped level, a list of its own under a rule, its chapter folding (D-310, D-322,
    #64, #65).
  - [x] Erase all, in the Editor's Tools; Parts the Editor's first drawer, the run opening on
    Diagnostic (D-321).
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

- [x] **"Two lights, four obstacles"**, set aside as too hard for level 2 (D-032), back as the
  chapter's last level, 1.8: 27 of 1,728 one-eyed circlers win it, the fastest in 24.6 s
  (D-324).
- [x] **Sharing levels and solutions.** Solutions as a board's text (D-205, D-206); levels as
  their JSON (D-310), shared with their proof (D-320).

## 12. Checks and fixes on `main` (done, D-345)

Done: Files' title drawn again; Copy and Paste a board in Firefox, and the Maker's typed values
and Paste a level in Safari, checked by the physicist; the streams thin out from 3 to 5 body
radii and are never shorter than 32 px on screen (D-345).

## 13. Chapters, levels and tutorials, made with the Maker (done, D-325 to D-341)

Done: five chapters, 0 Tutorials to 4 Made by users (D-325, D-326); a Maker level shipped with
its proof, its hints from it (D-328, D-329); chapter 0's six tutorials, reviewed in
[`tutorials.md`](tutorials.md) (D-334 to D-339); Dragster (D-332); Build your level, Open Maker,
in Chapters (D-341). What is left is made with the Maker as it comes, under Build your level:
chapter 2's new levels, obstacles before Shadows, and chapter 4's, Made by users.

## 14. The repository's face

- [ ] **A new banner for GitHub**, the physicist's: a new catch phrase and an image, at the top of
  the README and as the repository's social preview (1280 × 640 px). The image could be the game
  itself, a swimmer and its streams round a light, rendered by the game's own drawing (no new
  art: the stage's scope leaves art out). The phrase to find: the README's line today, "You
  don't steer the agents. You wire their sensors to their thrusters, press run, and watch.",
  and its "collective behaviour", come from the jam's brief, when the game was to have many
  swimmers; it has one.

## 15. The Board, built with fewer moves (stage 2, D-400)

The physicist's: players build their control boards with less back and forth of the mouse and the
keyboard, from buttons round a board of one size. Its look and places are D-401, decided from
seven rounds of mockups; its gestures are D-402. Each item below is a `feat/…` branch into
`stage/2-board`, planned when it starts.

- [ ] **Drags and right clicks** (D-402): each button along a drag, a picked group moved, right
  clicks wiring with the chain going on.
- [ ] **The mouse wheel** (D-402): 60° a notch, up to the right, a trackpad's scrolls added up.
- [ ] **Chapter 0's cards**, rewritten for the buttons: today they point at the drawers, the bar
  and the Wheel ("Move on the Wheel").
