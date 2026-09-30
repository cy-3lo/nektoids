---
paths:
  - "game/nektoids/graph/**"
---
# Node graph rules

- The graph is the player's artifact: discrete and structural only.
- Jam vocabulary: Eye and Source (sensors: emit only), Wire, Double (×2), Halve (÷2),
  Sum (a + b) and Difference (|a − b|), each with two inputs and one output, Thruster (sink).
  Rates are never negative (D-014).
  No Threshold node. No slider, no numeric field the player can type into.
- Magnitude travels as bead *rate*. Thrusters integrate incoming rate over a tick.
  Keep the numeric rate (the model) separate from the drawn beads (the editor's view of it).
- Evaluation is deterministic: topological order, ties broken by node id (D-016). The editor
  rejects cycles for now; the evaluator accepts them and raises `AlgebraicLoopError` unless the
  loop is contractive (memory and the leaky integrator come after the jam).
- Complexity cost is one function, `complexity(graph) -> int`, which the simulation turns into
  body radius. Do not add a separate node-count score.
- Dataclasses, and numpy for evaluation (D-016); no pygame import. Everything here is testable
  headless.
