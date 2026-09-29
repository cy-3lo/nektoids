---
paths:
  - "game/nektoids/graph/**"
---
# Node graph rules

- The graph is the player's artifact: discrete and structural only.
- Jam vocabulary: Sensor (source), Wire, Double (×2), Halve (÷2), Thruster (sink).
  No Threshold node. No slider, no numeric field the player can type into.
- Magnitude travels as bead *rate*. Thrusters integrate incoming rate over a tick.
  Keep the numeric rate (the model) separate from the drawn beads (the editor's view of it).
- Evaluation is deterministic: topological order, ties broken by node id. Reject cycles for now
  (memory and the leaky integrator come after the jam).
- Complexity cost is one function, `complexity(graph) -> int`, which the simulation turns into
  body radius. Do not add a separate node-count score.
- Pure Python and dataclasses; no pygame import. Everything here is testable headless.
