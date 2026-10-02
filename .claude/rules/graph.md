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
- Dynamics (D-017): every node obeys tau dy/dt = F(y) - y with one global tau; one explicit Euler
  step per fixed sim tick, dt/tau in (0, 1]. The state `y` (N, n) belongs to the agent and goes
  into the hash. Inputs are gathered in a fixed order, never with `@`. The editor rejects cycles
  for now; the dynamics accept them (a loop is feedback that the state remembers).
- Complexity is one function, `complexity(board) -> int`: the number of parts, locked ones
  included, wires free. The score reads it (D-028); it never changes the body, which stays a
  sphere of radius 1 u (D-045). Do not add a second count.
- Dataclasses, and numpy for the dynamics (D-017); no pygame import. Everything here is testable
  headless.
