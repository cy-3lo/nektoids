# To do

The jam build shipped as v1.0 (D-106). Stage 0, Foundations (D-200 to D-206), stage 1, a level
maker (D-300 on), and stage 2, the Board (D-400 on), are built; stage 3, memory, is decided
(D-500). What is left goes here, in the
order it unblocks the rest; the PR that does an item removes it, and what was done is in git and
in [`decisions.md`](decisions.md). Sections keep their numbers, which the decision log cites.
Ideas for later are kept apart, off the repository (D-414).

## 11. A level maker (stage 1, done, D-300 to D-357, D-412, D-413)

Done: the Editor, a tab of Build your level (D-301, D-356), where a level is made: its lights,
obstacles and marks, the swimmer's start, its goals and time, its text, the parts its board
hands out and those it places, locked (D-302 to D-322); whole numbers everywhere (D-311,
D-313); − and + that keep stepping when held (D-412); Share level, the level won with its proof
(D-320), written as a few lines, the level one word, the board that won it another (D-413);
"Two lights" back as 1.8 (D-324).

## 12. Checks and fixes on `main` (done, D-345)

Done: Files' title drawn again; Copy and Paste a board in Firefox, and the Maker's typed values
and Paste a level in Safari, checked by the physicist; the streams thin out from 3 to 5 body
radii and are never shorter than 32 px on screen (D-345).

## 13. Chapters, levels and tutorials, made with the Maker (done, D-325 to D-341)

Done: five chapters, 0 Tutorials to 4 Made by users (D-325, D-326); a Maker level shipped with
its proof, its hints from it (D-328, D-329); chapter 0's six tutorials, reviewed in
[`tutorials.md`](tutorials.md) (D-334 to D-339); Dragster (D-332); Build your level, Open Maker,
in Chapters (D-341). What is left is made with the Editor as it comes, under Build your level:
chapter 2's new levels, obstacles before Shadows, and chapter 4's, Made by users.

## 14. The repository's face

- [ ] **Put the banners up** (D-417): `docs/banner/github.png` as the repository's social
  preview (Settings, General); `itch-cover.png` and `itch-banner.png` on the itch.io page.

## 15. The Board, built with fewer moves (stage 2, done, D-400 to D-417)

Done: buttons round a board of one size, its look and gestures decided from ten rounds of
mockups (D-401 to D-406); Diagnostic in the drawer, the board kept editable, its streams in
place of meters, its beads denser (D-407, D-409, D-415, D-416); chapter 0's cards read again
(D-408); the Editor's keys in place of its Wheel (D-410); the run's drag and wheel (D-411).

## 16. Memory and colour (stage 3, D-500, D-501)

Built on `stage/3-memory`, branched from `main` once #125 is merged. Each item is planned, and
its decisions taken, when it starts.

- [ ] **Tanks.** A part whose level h lags what comes in, T dh/dt = in − h, T about 4 s, and
  sends out h: `Relax(Scaled(1.0), tau=4.0)` in `graph/laws.py`, already checked by
  `test_laws.py`; a row in the table of kinds, its icon, its level drawn as a fill; its entry
  in the info box; how it counts in the score (D-045).
- [x] **Loops on the board** (D-428, brought onto `main` before v1.1). A wire may come back
  round to a part before it, as the dynamics always allowed (D-017). A tank on a loop that
  holds its level, Doubles making up for the fork, comes with the tanks.
- [ ] **Colours** (D-501, D-502). A signal in two channels, (w, r): white and red, each its own.
  Each a PR into the stage, each playable:
  - [ ] Channels inside, nothing seen: the state (N, n, 2), the laws on the last axis, every part
    white; every shipped level's proof plays the same, positions equal tick by tick.
  - [ ] Parts painted white or red with a Paint button on the Board: eyes, Sources, thrusters,
    each its own channel; a board's text and a level's word a version up, the old still read;
    undo and redo.
  - [ ] Lights coloured, white or red, in the level's format and the Editor.
  - [ ] Beads in two streams, red half a spacing behind, never blended; a stream's beads 0.5 hex
    sizes apart at full rate.
  - [ ] Paint, Filter and Swap, three operators; Paint and Filter painted with the same button.
- [ ] **Levels for memory and colour.** Memory with no schedule, the light hidden by shadows
  (D-019): round an obstacle, the tank holding the bearing it last read. Colour: go to the red light
  and flee the white one; two lights a colour-blind circuit cannot tell apart; a valve built from parts
  (D-501).
