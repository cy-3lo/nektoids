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
- [ ] **Colours** (D-501 to D-503). A signal in two channels, (a, v): amber and violet; wires
  and operators neutral, white.
  Each a PR into the stage, each playable:
  - [ ] Channels inside, nothing seen: the state (N, n, 2), the laws on the last axis, every part
    amber; every shipped level's proof plays the same, positions equal tick by tick.
  - [ ] Parts painted amber or violet with a Paint button on the Board, its brush's colour
    switched with nothing picked: eyes, Sources, thrusters, each its own channel; a board's text and a level's word a version up, the old still read;
    undo and redo.
  - [ ] Lights white, amber or violet (D-506): white shines in both channels; in the level's
    format and word, three keys in the Editor, the rays tinted.
  - [ ] Beads in two streams, violet half a spacing behind, never blended; a stream's beads 0.5 hex
    sizes apart at full rate.
  - [ ] Tint, Filter and Swap (D-507), three operators in rounded squares under Paint; Tint and
    Filter painted with the same button.
- [ ] **Levels for memory and colour** (first ones: D-510, chapters 4 Colour and 5 Memory). Memory with no schedule, the light hidden by shadows
  (D-019): round an obstacle, the tank holding the bearing it last read. Colour: go to the violet light
  and flee the amber one; two lights a colour-blind circuit cannot tell apart; a valve built from parts
  (D-501).

## 17. Flows (stage 4, D-600 to D-604)

Built on `stage/4-flows`, branched from `stage/3-memory`, the exploration's decisions brought
over; its prototype stays local, off the public repository.

- [x] **Thrusters on the outer ring** (D-605). Anywhere on the Board, but idle off the rim: faded,
  no push, no flame, said in the run's status line. Turning's start board and the proofs of
  Turning, Latch, Spot the violet and Dragster II moved to it.
- [x] **The swimmer moves by the Stokes solve** (D-606). The prototype's lean solve into
  `sim/flow.py`, vectorised over the bodies, no `@`; the lights' and obstacles' inverse built
  once with the arena and handed on by `moved`; `world.step` takes its velocity and spin. Every
  proof run again: its ticks re-recorded, its time allowed raised where it loses by time; a
  board that no longer wins goes to the physicist.
- [x] **Patience, retuned** (D-607). A full drive wins it in 13.6 s, before the halved one (33 s, D-606);
  its two tests in `test_determinism.py` are marked expected to fail until it is.
- [x] **The flow drawn** (D-608). Tracers as in D-603, a fixed field over the visible plane, switched
  on and off in the run view; visual only, reseeded on restart, seek, pan and zoom. Checked in
  the browser.
- [x] **A pinned swimmer's flow** (D-609). Against an obstacle, the solve still reports and draws the
  velocity the swimmer would have if free (7 u/s), and the tracers show that flow. The contact
  force belongs in the Stokes problem: an unknown force on the swimmer, set so that its
  velocity into the obstacle is zero, one more solve per contact (a 2×2 system in a crevice).
- [ ] **Gaps in the fixed field of tracers.** Move a tracer from a crowded cell to an empty one
  now and then, away from the swimmer, so that the field heals.
- [ ] **Tuning by eye** (first pass: D-610). ℓ, thrust, the rotational radius (0.75 u), the tracers' density, their
  brightness and their tails.
- [x] **Then flow sensing**, a stage of its own: §18 (D-700).

## 18. Flow sensing (stage 5, D-700)

Built on `stage/5-flow-sensing`, branched from `stage/4-flows`; stage 4's open items above are
merged in as they land.

- [x] **Pumps and sources in the solve** (D-700). `Arena` holds them, fixed; their flow at the
  swimmer (V += u, Ω += ω/2) and in `flow_at`, so the tracers show it; the lights' and
  obstacles' reactions to them solved once, at load; the swimmer meets them as it meets a light.
  A tick costs 164 µs natively with two pumps and two sources among five spheres, against 109.
- [ ] **Pumps and sources in the level maker.** The level format's next version, older levels
  with none; placed, turned and signed as a light is set; drawn so they read with the tracers
  off: a pump a disc with an arrow, a source rays out, a sink rays in; shared as text.
- [ ] **The flow sensor.** A sense `flow` in `sim/world.py`, a kind in the table, turned like an
  eye; the board's word at its next version; its icon on the Board and in Diagnostic. It reads
  the absolute flow first; the relative form one switch away (D-700). Its name is the
  physicist's to give.
- [ ] **Levels for flows.** Find the sink; go up a pump's jet; follow a wall by its echo. Camille
  plays them.
