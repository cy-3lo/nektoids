# Decisions

Append-only. One entry per decision that constrains future work. A later entry may supersede an
earlier one; say so explicitly.

Format: **ID — date — decision.** Why. Consequence.

---

**D-001 — 2026-09-29 — Toolchain: pygame-ce + pygbag, published on itch.io as HTML5.**
Python for both contributors; browser delivery without a rewrite.
WASM CPython has no JIT, so physics is numpy-vectorised, and the main loop is async.

**D-002 — 2026-09-29 — Everything pygbag bundles lives under `game/`; tests and docs stay outside.**
pygbag packages the whole app folder; tests, docs and CI config have no business in the web build.
pytest finds the code through `pythonpath = ["game"]`.

**D-003 — 2026-09-29 — Weekend scope lock as written in `CLAUDE.md`.**
Ship three tutorial levels and one real level in two days.
Out-of-scope ideas are logged here as "post-jam", not implemented.

**D-004 — 2026-09-29 — Determinism is guaranteed per platform, not across native and WASM.**
numpy SIMD paths and libm functions can differ in the last ulp; the dynamics amplify it.
Win conditions are robust counts with margin, never an exact trajectory.

**D-005 — 2026-09-29 — Ownership: the physicist owns `sim/`, the CS student owns `graph/` and `editor/`.**
Each works where he learns most from the other's review.
Every PR is reviewed by the non-owner.

**D-006 — 2026-09-29 — Names: the studio is Cy-3LO, the game is Nektoids.**
Nekton (organisms that swim rather than drift) + the -oids of boids and asteroids; the studio is
C. Eloy in leetspeak. Both came back clear on GitHub, Steam, the App Store and the domain
registries; itch.io search, Google and TMview (classes 9 and 41) to be checked by hand.
Canonical spellings: "Cy-3LO" and "Nektoids"; `cy-3lo` and `nektoids` in handles and URLs.
The studio logo must not reference C-3PO visually.

**D-007 — 2026-09-29 — Editor: small hex board, auto-routed wires, straight crossings only.**
Pointy-top hexes; the level sets the board size and either pre-places the sensors and thrusters
(locked, tutorial and first levels) or hands them out as palette stock. A wire joins two components
by the shortest free path, then the fewest bends, then the fixed direction order E, NE, NW, W, SW,
SE. A cell holds one component, or one wire that bends there, or up to three straight wires on
distinct axes. Dropping a component on a cell a wire uses is refused.
Every crossing reads unambiguously on screen (invariant 6), and layout stays part of the puzzle.
Routes depend on build order and never move once drawn, so the board on screen is the layout. If
crossings are to be expensive (brief §1), the cost goes into `complexity()`.

**D-008 — 2026-09-29 — Sensors and thrusters are oriented; rotating them is post-jam.**
Orientation is physical: where an eye looks, which way a thruster pushes. The editor draws it in
the agent's frame with forward = E (the sim's +x): half-disc eyes, square thrusters with a nose.
For the jam it is fixed per kind (left eye NE, right eye SE, thrusters E) and there is no rotate
tool, because choosing it is sensor layout editing, which the scope lock excludes.
Post-jam: a rotate tool in 60° steps, and one bundled icon font (open licence, small, loaded at
startup, checked under pygbag) to mark sensor and actuator types (light, flow, ...) inside the shapes.

**D-009 — 2026-09-30 — Supersedes D-008's rotation clause: the player turns eyes and thrusters.**
Where an eye looks and which way a thruster pushes are part of the mechanism the player authors.
A Rotate tool in the toolbar turns a placed eye or thruster by 60° (click: clockwise, shift-click:
back). New parts take their kind's default direction. Converters have no direction; locked parts
placed by a level keep theirs. The scope lock in `CLAUDE.md` now has sensor directions in and
moving sensors on the body out.
The sim reads each eye's and thruster's direction from the board, never from a constant.

**D-010 — 2026-09-30 — Supersedes D-007's crossing rule: wires share a cell unless they share an edge.**
A wire crosses a free cell through two of its six edges. Any number of wires may cross or turn in
the same cell provided no edge is used twice, so a cell holds at most three. Turns are drawn as
circular arcs tangent to the wire at the edge midpoints: radius s/2 about the shared corner for a
sharp 120° turn, 1.5 s for a gentle 60° one (s the hex size). Routing order is unchanged: shortest,
then fewest bends, then direction order.
Denser layouts than straight-only crossings. Wires still meet only at components, so a crossing
never reads as a junction.

**D-011 — 2026-09-30 — Amends D-007: moving a component routes its own wires again.**
The Move tool drags a placed component cell by cell. At each step its wires are routed again, in
the order they were drawn; other wires never move. A cell another wire crosses, a taken cell, or
one from which its wires find no path is refused, and the component waits at the last cell that
worked. Locked parts don't move.
Rearranging a layout no longer means deleting and rewiring; routes still never change by themselves.

**D-012 — 2026-09-30 — Supersedes D-008's icon-font clause: Font Awesome Free 6.7.2 Solid, in the jam.**
One icon font, bundled unmodified with its licence (SIL OFL 1.1, 416 KB) in
`game/nektoids/assets/fontawesome/` and opened once at startup. Eye for sensors, double chevrons
up and down for ×2 and ÷2, rocket for thrusters. The eye and the rocket turn with their part: the
rocket points where the thruster pushes, the eye lies along the half-disc's flat side and looks
out of the round one; the chevrons stay upright. The toolbar, the fold marks and ∞ use the
same font. Chosen over Material Icons, Phosphor, Tabler, Lucide and Bootstrap for legibility at
20 px (solid glyphs, no thin strokes); Remix Icon is out, its 2026 licence is not open.
Not subset: under OFL a subset is a modified font and could not keep the reserved name. Rendering
under pygbag is still to be checked.

**D-013 — 2026-09-30 — Supersedes the "no zoom" editor rule: zoom and pan move the view, never the zone.**
Zoom in and out (hex size 20 to 80 px, ×1.25 per click, about the centre of the grid) and a pan
tool sit in the palette, apart from the Move tool that moves components. They change only how the
grid is seen: each level's zone stays small and fixed, so spatial scarcity (brief §1) still holds.
`.claude/rules/web.md` is updated to match.
A player can scroll the zone out of sight; the board, routing and scoring never depend on the view.

**D-014 — 2026-09-30 — Extends the scope lock's node vocabulary: Source, Sum and Difference.**
Source: a sensor that senses nothing and emits a signal of its own; it has no direction. Sum (+)
and Difference (−): at most two inputs and one output; with a single input they pass it through.
Difference is |a − b|, so the order of its inputs does not matter. Signals (bead rates) are never
negative. Supersedes "nodes are wires, ×2 and ÷2 only" in the scope lock of `CLAUDE.md` and the
jam vocabulary in `.claude/rules/graph.md`. Still no threshold node and no continuous parameter.
What a source emits, and how every node turns input rates into output rates, is for the graph
evaluation work; the editor only enforces the input and output counts.

**D-015 — 2026-09-30 — The middle category is called Operators, not Converters.**
It will also hold tanks (reservoirs that store signal: the memory), which convert nothing; each
of its parts operates on the signal: ×2, ÷2, sum, difference, and later store. "Gates" was set
aside because it suggests logic and thresholds, which the brief keeps out of the early levels.
Tanks themselves stay post-jam (`.claude/rules/graph.md`).

**D-016 — 2026-09-30 — How the graph is evaluated: instantaneous rates, split fan-out.**
Resolves the open questions of D-014 and `docs/walkthrough.md` §5. Every node has an output rate
y in [0, `RATE_MAX`] and no dynamics: operators, sensors and actuators are instantaneous. A rate
is a fraction of what a wire can carry, so `RATE_MAX = 1`.
A node with k outgoing wires sends y/k on each (split: beads are conserved at a fork). Incoming
rates add; Double is ×2, Halve is ÷2, Sum is a + b, Difference is |a − b|; every output is capped
at `RATE_MAX`. A Source emits `SOURCE_RATE = 1`, an Eye its sensor rate; the developer view
starts its eyes at 0.5. The beads it draws are only a view: 8 a second on a wire at rate 1. A
Thruster's y is the rate handed to the sim; "thrusters integrate" is done by the body's momentum,
so the graph holds no integrator state.
Loops: the editor still refuses them. The evaluator accepts any directed graph. Without lag a loop
of operators is an algebraic loop, y_u = F(y_u; y_k) with F piecewise affine, sensors known. A DAG
is solved in one pass, a loop by iteration when the loop gain rho(|W|) < 1 (unique solution),
otherwise it raises `AlgebraicLoopError`: a loop needs a state. When tanks arrive they are the only
states; the graph is cut at them and the rest must be acyclic or contractive.
Amends invariant 4 of `CLAUDE.md`: "gain only via ×2 and ÷2" is dropped, since split gives 1/k and
sensors are not powers of two anyway. The player still sets no continuous parameter.
Consequences: with a Source and a Difference a player can build |x − c|, a threshold-like function;
it costs nodes, so it is paid through `complexity()`. The developer view has sensor sliders, behind
`DEV_VIEW` only; the player's graph has none (brief: "No sliders").

**D-017 — 2026-09-30 — Every node lags: tau dy/dt = F(y) - y, tau = 1/60 s. Supersedes D-016's instantaneous rates.**
F is D-016's rule (split fan-out, gain, |a − b|, cap at `RATE_MAX`); the rate of a node now relaxes
towards F instead of equalling it. One global `TAU = 1/60 s`. Eyes and sources are given, not
lagged: a sensor's rate in a tick drives that tick. The controller has state: `y` of shape
(N, n) lives with the agent, starts at rest (all 0) and goes into the hash of the run. One explicit
Euler step of the sim's dt is y + (dt/tau)(F(y) − y); `step` refuses dt/tau outside (0, 1], which
keeps every rate in [0, `RATE_MAX`] for every graph. Use dt = tau/2 (the sim's 1/120 s): at
dt = tau the step is y ← F(y) and loops that settle in continuous time flicker at every tick.
Supersedes D-016's `evaluate`, `AlgebraicLoopError` and "a loop needs a state": a loop is feedback
that the state remembers. It may settle, hold a value, latch (two stages inhibiting each other keep
the winner) or oscillate (three inverting stages of gain 4). `contraction_factor`, rho(|W|) < 1,
stays as a diagnostic: the loop then settles to one value from any start. The editor still
refuses loops; allowing them gives memory without tanks (D-015), so that is a scope decision.
Consequences: a path of d operators reaches 95% of a step in 5, 11 and 18 ticks for d = 1, 3 and
6 (42, 92 and 150 ms at dt = 1/120 s); tau sets both the reaction time and the speed of loop
dynamics. Developer view: each wire shows its flux now, along its whole length, with one phase
per wire (`phase += flux dt`, mod 1) so that nothing jumps. The default style puts beads
`speed / flux` apart; when a low flux changes fast this whips the far beads (49 to 581 times the
steady step in one tick, for a flux swinging between 1/16 and 1 of the full rate in 2 s to 0.1 s),
so a `belt` style (fixed spacing, speed proportional to flux) is one
key away. Beads and intensity are shades of grey.

