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
      and every later stage needs levels.
      - The plane: lights, obstacles and the swimmer's start, placed, moved and turned; flow
        items when stage 3 brings them. Values on a lattice, positions every 0.5 u and powers in
        whole numbers: invariant 4 binds only the player's graph, but a lattice keeps a level's
        text short and its layout legible.
      - The board: zone, stock and locked parts, set with the board editor itself.
      - Objectives from `OBJECTIVES`, with their settings, and the time allowed.
      - A clear check, as in Mario Maker: a level is shared only once its maker has won it; the
        winning board goes with it, as its proof and as the score to beat.
      - Shared as text, with the board's encoder (stage 0); no server.
- [ ] **"Two lights, four obstacles"**, set aside as too hard for level 2 (D-032): 5 winners in
      2,603 random wirings, the fastest a one-eyed circler. Its file is in the history
      (`game/nektoids/levels/data/two-lights.json`, removed after PR #12).
- [ ] **Sharing levels and solutions.**
