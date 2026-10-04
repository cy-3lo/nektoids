# Ideas for after the jam

Not in the jam's scope (`CLAUDE.md`, scope lock). Each line says where the idea comes from. An
idea moves to [`todo.md`](todo.md) only with a decision in [`decisions.md`](decisions.md) that
puts it in scope. Until D-028 these were logged in the decision log as "post-jam".

## Physics and senses: new routes on the map (brief §2)

- **Stokes flow round the swimmers.** Each swimmer a moving singularity (a stresslet ~1/r, or a
  source dipole ~1/r² for a local neighbourhood), the field summed analytically at each sensor.
  Pushers and pullers have opposite far fields, so the sign is information; sensing is
  reciprocal (swimming hard makes you findable: a stealth level); walls come with image
  singularities, so wall-following emerges from flow sensing.
- **Flow sensing**, the sense that reads that field: direction and sign from its asymmetry.
- **Chemical fields**: trails, alarm, plumes; diffused history rather than current state, on a
  coarse grid. Two sensors give a gradient, one only a level.
- **Optical flow**: it conflates egomotion with others' motion, and the player must subtract it.
- **Tracer particles** to show the flow: a toggleable overlay; the game must read without it.
- **Walls as items** in the open plane: segments, with contacts and shadows (D-028).
- **Solid lights**, and swimmers that touch each other (D-022).

## Collectives

- **Flocks**: many agents, pairwise (N, N) broadcasts (`.claude/rules/simulation.md` already
  asks for code written for N). Countable goals: 40 of 50 past the gap, split and rejoin round
  an obstacle, keep cohesion while a predator passes (brief §1).
- **Predator and prey**: two populations, herding prey into a pen.
- **How routes divide**: by sense, by collective, or one as the depth of the other (D-028, left
  open).
- **The generalisation pillar**: one rule set, five seeds or environments, all must pass
  (brief §1).

## The graph's vocabulary

- **Tanks**: reservoirs that store signal, the memory (D-015, `.claude/rules/graph.md`).
- **A threshold node**, as a deliberate, costed choice; never in the first levels (brief §1).
- **Loops in the editor**: the dynamics accept them already, with memory as a consequence
  (D-017).
- **Colours for signals**: beads coloured by identity (brief §1); the palette's colour picker
  is waiting for it (D-025).

## Sensor layout, a second authored artifact (brief §2)

- **How many eyes, what aperture, where on the body**, each costing size; non-unique solutions.
- **Icons for sensor types** inside the shapes, when there is more than one (D-008, D-012).
- **Levels with more than two eyes or thrusters, on zones wider than 19 cells.** The sandbox
  tries it first: every part without limit, on 37 cells (D-102; the physicist, 2026-10-04).

## Editor and levels

- **Saving and loading, and a board as text**, one piece of work (was todo §9; D-093). Save
  and Load come back with it, as rows at the foot of Files, under this session's wins (D-092);
  until D-093 they sat there greyed (D-027). The format of D-024, with a version number, keeping
  wire paths exactly; a board as a short line of ASCII to copy, paste, keep in a text file and
  open again: that board packed into bits and spelled out. Its language is a decision first.
  - Letters (base 32, like a licence key) or words from a list (2048 words, 11 bits each)?
  - Length, roughly: six parts and six wires with their paths kept exactly come to under 200
    bits, about 35 letters or 17 words; less if the paths are drawn again in wire order, which
    gives the same routes unless Move or Delete was used (D-024).
  - A check against typing mistakes, Shannon-like: redundant check symbols, so a mistyped line
    is refused (or even corrected) rather than loading another board. A version mark.
  - Copy and paste between the canvas and the page: does pygbag reach the clipboard? Wait and
    see on the web build.
  - The same mechanism as the level passkeys (D-075): a word that brings a state back.
- **A level editor**, Super Mario Maker-like: levels are data already (D-028).
- **"Two lights, four obstacles"**, set aside as too hard for level 2 (D-032): 5 winners in
  2,603 random wirings, the fastest a one-eyed circler. Its file is in the history
  (`game/nektoids/levels/data/two-lights.json`, removed after PR #12).
- **Sharing levels and solutions.**

## Score

- **Histograms per axis**, Zachtronics-style: where you stand among all players on each axis,
  not a ranked list. Needs a server, or distributions shipped with the game.
- **More axes**: area on the board, wire crossings (brief §1: crossings expensive, D-007).
- **Bests kept between sessions** (needs saving).

## Interface

- **Touch**, from Camille's notes (`ebc4abb`; todo §7 until D-104): no hover and no keys. The
  tooltips (D-025) and L, R, Space, Esc and 0 need an on-screen form. One gesture stays one undo
  step (D-027). The Wheel (D-068, D-069) does the rest: a click on a cell shows what can be done
  there, a click on a part arms Wire, a drag moves a part, or draws a wire with Wire chosen
  (D-072).
  - Does a phone's keyboard come up for Chapters' passkey field (D-075)? If not, the field
    needs letters of its own on screen.
  - The canvas is 960 × 640 px: on a phone a 40 px hex is about 16 px wide in portrait and
    24 px in landscape, where a finger wants about 44. Landscape only, larger hexes?
  - Under pygbag, do touches arrive as mouse events or as FINGERDOWN only? Try on a phone
    first.
  - How far must a finger move before a tap becomes a drag? Today a press becomes a drag
    once the pointer leaves the part's cell (D-085): enough for a finger on large hexes?
- **Parts as the encyclopedia** (todo §8 until D-104): a row opens into its entry, in the
  drawer; today the entry opens in a box beside it. The rest of the activity bar is built
  (D-053 to D-069).

## Presentation

- **Sound, art.**
- **Sound and Music in Settings**, once there is sound (D-054; todo §8 until D-104).
- **GIF export of a run**: it made Opus Magnum's solutions a social object (brief §4).

## Studio

- **The domains nektoids.com and nektoids.io** (the physicist, 2026-10-04): both unregistered
  that day (`whois`). The itch.io page makes the name public, and a .com costs about €10–15 a
  year. A .io costs more, and its future has been uncertain since the 2025 UK–Mauritius treaty
  on the Chagos, so the .com first.
