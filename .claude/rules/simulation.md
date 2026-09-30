---
paths:
  - "game/nektoids/sim/**"
  - "tests/test_determinism.py"
---
# Simulation rules

- State is numpy: `(N, 2)` float64 for position and velocity, `(N,)` for heading. The jam has
  one agent, but write for N so flocking later is an addition, not a rewrite.
- Pairwise interactions use full `(N, N)` matrices built by broadcasting. N ≈ 100 makes O(N²)
  cheap. No Python loop over agents.
- `step(world, controls, dt)` advances one fixed step. Say in the docstring whether it mutates.
  No hidden module-level state.
- Integrator: semi-implicit (symplectic) Euler at fixed `dt` unless a decision says otherwise.
- State units in docstrings (u, s, u/s), u being the base body radius (D-019); pixels exist only
  in the view. Named constants at module top, no magic numbers.
- Determinism holds per platform, not across platforms: numpy SIMD paths and libm transcendental
  functions can differ in the last ulp between native CPython and WASM, and trajectories diverge.
  Hence win conditions must be robust (counts, thresholds with margin), never "exact trajectory".
- Every physics change keeps `tests/test_determinism.py` green and adds a behavioural test
  (e.g. symmetric sensor input gives a straight line; a free agent decelerates under drag).
- Sensors are physical. An eye reads light (D-019): point sources, 1/r, a cosine for where it
  looks, hard shadows cast by discs (obstacles and other bodies), no reflection, capped at
  `RATE_MAX`. It tells how much light, not what or where. A body is transparent to its own
  parts (D-018).
