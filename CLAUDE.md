# Nektoids

A game by Cy-3LO (always written exactly so; `cy-3lo` in handles and URLs).

A Zachtronics-style puzzle game about collective behaviour. The player never
steers agents: they wire sensors to thrusters in a small node graph, press run,
and watch a deterministic 2D simulation play out.

- Design brief: `docs/brief.md` — read sections 1 and 3 before proposing any feature.
- Decision log: `docs/decisions.md` — append-only; check it before re-opening a question.

## Who works here

Two contributors, father and son, building this together to learn and to have fun.

- The physicist (professor of mechanical engineering) owns `game/nektoids/sim/`.
- The CS student (first year, Télécom Paris) owns `game/nektoids/graph/` and `game/nektoids/editor/`.
- Each reviews the other's pull requests.
- `CLAUDE.local.md` (not committed) says who is at the keyboard. If it is missing, ask once.

This is a learning project. The humans write the interesting parts.

- Explain before writing. For anything non-trivial, propose a short plan and wait for a go.
- Prefer small diffs a human can read in five minutes over large complete ones.
- When the student is at the keyboard, do not write whole features in `graph/` or `editor/`:
  scaffold, name the concept, point to where it goes, then review what he writes.
- Tests, tooling, CI and boilerplate may be written in full.
- The humans may write in French: answer in the language of the prompt.
  Code, comments, commit messages and docs stay in English.

## Scope lock (weekend jam)

Changing this list requires an entry in `docs/decisions.md`.

In: 2D top-down; one agent; two optical opacity sensors at fixed positions; two outputs
(left and right thruster); eyes and thrusters point where the player turns them, in 60° steps
(D-009); nodes are wires, ×2, ÷2, sum and difference, plus a source (D-014); three
Braitenberg tutorial levels plus one real level with a countable win condition; fixed seed,
fully deterministic; body size grows with graph complexity, which raises drag.

Out: flocking and multiple agents, flow sensing, chemical fields, optical flow, moving sensors
on the body, threshold nodes, the generalisation pillar (multi-seed validation), sound, art,
saving, undo.

If a request touches something out of scope, say so plainly and offer the smallest in-scope
version. `/scope-check` does this formally.

## Layout

```
game/                    everything pygbag bundles; keep it lean
  main.py                entry point; async loop (pygbag requirement)
  nektoids/sim/          physics: state arrays, integrator, sensors (numpy, no pygame)
  nektoids/graph/        node graph: data structure, evaluation, bead rates (no pygame)
  nektoids/editor/       pygame UI: grid, node placement, wires, beads, inspector
  nektoids/levels/       level definitions: layout, seed, win condition
tests/                   pytest; never import pygame here
docs/                    brief, decisions
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
4. No continuous parameter in the graph. Magnitude is bead rate; gain only via ×2 and ÷2.
5. Web-safe. Python 3.11 compatible, pygame-ce only, no threads, no blocking I/O.
6. Legibility beats features. A failure the player cannot see on screen is a bug.

## Git

- `main` is protected. Work on `feat/…`, `fix/…`, `chore/…` branches; one idea per PR.
- Run `/pr-prep` before opening a PR; it fills `.github/pull_request_template.md`.
- Never push, force-push, rebase or rewrite history unless asked in this session.
- Record design decisions (scope, physics model, API shape) in `docs/decisions.md`.
