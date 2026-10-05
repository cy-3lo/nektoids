# Nektoids

A game by Cy-3LO (always written exactly so; `cy-3lo` in handles and URLs).

A Zachtronics-style puzzle game about collective behaviour. The player never
steers agents: they wire sensors to thrusters in a small node graph, press run,
and watch a deterministic 2D simulation play out.

- Design brief: `docs/brief.md` — read sections 1 and 3 before proposing any feature.
- Decision log: `docs/decisions.md` — append-only; check it before re-opening a question.
- What is left to do: `docs/todo.md`; ideas for later: `docs/ideas.md` (D-028).

## Who works here

Two contributors, father and son, building this together to learn and to have fun (D-041).

- The physicist (professor of mechanical engineering) directs and reviews the code in every
  package; he reviews his own pull requests with `/pr-prep`.
- The CS student, Camille (first year, Télécom Paris), does not program here: he plays the
  builds and gives his views. His notes go into `docs/todo.md` or `docs/ideas.md`, in English,
  with his name on them.
- `CLAUDE.local.md` (not committed) says who is at the keyboard. If it is missing, ask once.

Claude writes the code, whole features included, in any package.

- Explain before writing. For anything non-trivial, propose a short plan and wait for a go.
- Prefer small diffs a human can read in five minutes over large complete ones.
- The humans may write in French: answer in the language of the prompt.
  Code, comments, commit messages and docs stay in English.

## Scope: stage 1, a level maker (D-300)

After the jam come five stages (D-105). Each opens with a decision that sets its scope here, as
the scope lock did for the jam. Changing this list requires an entry in `docs/decisions.md`.

In: the game as it is on `main`. 2D top-down; one agent; two eyes that read light (1/r,
shadows, D-019); two outputs (left and right thruster), in the levels: the sandbox hands out any
number (D-102); the board is the body plan: eyes and thrusters sit where they are placed
(D-018, fixed by tutorial boards) and point where the player turns them, in 60° steps (D-009);
nodes are wires, ×2, ÷2, sum and difference, plus a source (D-014); four Braitenberg levels
(Fear, Aggression, Love, Orbit), then Shadows, Greed and one real level, Patience, each with a
countable win condition (D-097); fixed seed, fully deterministic;
complexity, the number of parts, is scored and every body stays a sphere of radius 1 u (D-045);
undo and redo in the editor (D-027). Stage 0's foundations (D-200 to D-206): one table of part
kinds and their laws, senses and actions, a level format with a version, saved boards with
their paths, a board as text, Save/Load in Files.
And stage 1, the todo's §11: a level maker, for us and Camille first (D-041), then for players:
the plane's lights, obstacles, marks (zones only the objectives read, D-306) and start, the
board's zone, stock and locked parts, objectives and the time allowed, a clear check, levels
and solutions shared as text, no server.

Out: no new part or sense, and no new item but marks (D-306). The later stages, memory, flows, actions other than moving, and
all after them (`docs/ideas.md`): flocking and multiple agents, flow sensing, chemical fields,
optical flow, parts that move on the body during a run, threshold nodes, the generalisation
pillar (multi-seed validation), sound, art.

If a request touches something out of scope, say so plainly and offer the smallest in-scope
version, and log the idea in `docs/ideas.md`. `/scope-check` does this formally.

## Layout

```
game/                    everything pygbag bundles; keep it lean
  main.py                entry point; async loop (pygbag requirement)
  nektoids/sim/          physics: state arrays, integrator, sensors (numpy, no pygame)
  nektoids/graph/        node graph: data structure, evaluation, bead rates (no pygame)
  nektoids/editor/       pygame UI: grid, node placement, wires, beads, inspector
  nektoids/levels/       levels as data (JSON in levels/data/, D-028): items, board, objectives
tests/                   pytest; never import pygame here
docs/                    brief, decisions, todo, ideas, walkthrough
```

Path-specific rules live in `.claude/rules/` and load when the matching files are touched.

## Commands

```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python game/main.py               # run natively
python -m pytest -q               # tests, including determinism
ruff format . && ruff check .     # a hook formats edited .py files automatically
pygbag game                       # web build + local server on http://localhost:8000
pygbag --build --archive game     # game/build/web.zip, ready for itch.io
```

## Invariants — breaking one makes the change wrong

1. Determinism. Same level and same graph give a bit-identical run on a given platform.
   No wall-clock time in the simulation, no unseeded randomness, no set/dict iteration order
   in anything that affects state. Randomness only via `np.random.default_rng(seed)` at setup.
2. Simulation is independent of rendering. Fixed `dt`; the frame loop calls `step()` a fixed
   number of times per frame.
3. Vectorised physics. Agent state lives in numpy arrays; no Python loop over agents in `sim/`.
4. No continuous parameter the player can set in the graph. Magnitude is bead rate (D-016).
5. Web-safe. Python 3.11 compatible, pygame-ce only, no threads, no blocking I/O.
6. Legibility beats features. A failure the player cannot see on screen is a bug.

## Git

- `main` is protected. Work on `feat/…`, `fix/…`, `chore/…` branches; one idea per PR.
- Run `/pr-prep` before opening a PR; it fills `.github/pull_request_template.md`.
- After the jam, a stage is built on `stage/<n>-<name>` (D-200): each item a `feat/…` branch
  whose PR goes into the stage, the stage into `main` in one PR. Merge `main` into a stage;
  never rebase it. A stage's decisions take their own hundred (stage 0: D-200, stage 1: D-300).
- Never push, force-push, rebase or rewrite history unless asked in this session.
- Record design decisions (scope, physics model, API shape) in `docs/decisions.md`.
