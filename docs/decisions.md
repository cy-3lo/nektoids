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


**D-018 — 2026-09-30 — The board is the body plan: where a part sits on the board is where it sits on the body. Supersedes "moving sensors on the body" (out) in the scope lock of `CLAUDE.md`.**
The board is the body seen from above, forward = E = +x of the body, the board's up its left (+y);
a part's facing (D-009) is where it points. The centre of the zone's cells is the centre of the
body and the zone's outermost cells lie on its rim, so a mount is measured in body radii:
`Network.mount`, (n, 2), and the part sits at R rot(heading) m in the world, R the body radius.
The body is transparent to its own parts: its eyes see through it, and a thruster pushes
whichever way it faces, even into the body. It still casts a shadow on everything else.
A thruster's position is its lever arm, so the layout is part of the mechanism, and the tutorial
reads as Braitenberg's vehicle: the upper-right thruster, pushing E, sits front-left and turns the
body right, like his left wheel.
Consequences: in a free board, placing an eye or a thruster chooses where it sits on the body,
which is sensor layout (brief §2, "a second authored artifact"); tutorial boards lock their parts,
so their positions stay fixed. Moving a part (D-011) moves it on the body. Sensors sit on the left
of the board by habit, so eyes end up at the back of the body and still see ahead, since their
own body is transparent to them. Operators have a mount too; nothing uses it.

**D-019 — 2026-09-30 — Eyes read light: point sources, 1/r, a cosine for where the eye looks, hard shadows cast by discs, no reflection. Replaces the brief's opacity sensor for the jam.**
An eye is a flat detector at its mount (D-018), looking along its facing. It reads
E = sum over lights of P max(0, n·s) / max(r, R_MIN) V, and sends min(`RATE_MAX`, E); s is the unit
vector to the light, r its distance, and V is 0 when the segment to it meets a disc, an obstacle or
another body (a body is transparent to its own eyes, D-018). The 2π of 2D spreading is folded into
P, so a light's power is the distance at which an eye looking straight at it saturates. A light is
a disc as big as a swimmer, R_MIN = 1 u: nearer than that counts as at its rim. It shadows nothing.
Lengths are in u, the base body radius; obstacles are discs of 1 u by default; x right, y up,
angles counter-clockwise. Pixels exist only in the view, which fits the arena to the screen.
Levels choose how many lights and obstacles. An eye reads E = ∫ I cos θ, θ from the normal of its
flat face, which for point sources is the sum above. The player sees the light as rays, as many
from each light as its power and each stopped by the first disc it meets, so their density is
its 1/r and a shadow is where no ray goes; what each eye reads exactly shows as a polar plot of E
against the way it faces.
Braitenberg's vehicles steer by light, and the brief's opacity ray ("something is there, not how
far") gives no gradient to follow. A graded reading does carry distance, which opacity withheld;
the ambiguity the puzzle needs survives: a dim light near and a bright one far read alike, two
lights add, and a reading depends on where the eye looks as much as on where the light is.
Consequences: near a light both eyes saturate and steering fades, which shows (both eyes white).
Point sources give hard shadows, so an eye crossing a shadow's edge jumps; the lag of the nodes
(D-017) smooths it. Cost: one segment–disc test per eye, light and disc, in one numpy broadcast.
Natively, `eye_rates` takes 0.04 ms a tick for the jam and 0.5 ms for 100 swimmers, 4 lights
and 20 obstacles; a light map of 80 × 76 cells takes 0.3 ms. WASM is still to be measured.

**D-020 — 2026-09-30 — An eye looks out of its flat face. Supersedes D-012's "the eye ... looks out of the round one".**
The flat face of the cut disc is the photosensor of D-019: it is drawn towards where the eye
faces, the round side behind. Where an eye looks (its facing, D-009) and what it reads are
unchanged; only the drawing was the wrong way round, sensing through its back. The eye icon still
lies along the flat face, centred in the shape; in the menu the eye looks up.

**D-021 — 2026-09-30 — One key, one meaning, in every view.**
A key the editor uses keeps its meaning everywhere, and the arena view's view keys are the
editor's own (`VIEW_KEYS`: + and − zoom, H takes the hand, C centres); with the hand, the arrows
drag the view the way they point, as the mouse would, in both. So R, which rotates in the editor,
no longer starts a run again: 0 does (t = 0), in the arena and in the developer view (F2).
Letters are matched on the character typed; digits, Space and the arrows on the physical key,
since unshifted 0 types "à" on AZERTY and Safari reports the arrows as keypad keys (PR #3).
A new view or key checks `TOOL_KEYS` and `VIEW_KEYS` first; `test_arena_layout.py` pins the rule
for the arena. F2's W (waveform) still clashes with the editor's Wire, to be moved.

**D-022 — 2026-10-01 — Swimmers are overdamped: the thrust is balanced by the Stokes drag of a sphere of the body's radius. Supersedes D-016's "thrusters integrate is done by the body's momentum".**
A thruster at rate y pushes with y `THRUST` along its facing (D-009), at its mount, R m from the
centre (D-018). The body has no inertia: its velocity and spin balance the thrusters' total force
F and torque T at once, V = F / (6πμR) and Ω = T / (8πμR³). `THRUST = 1` is the unit of force,
and μ is set by `SPEED`: one thruster at `RATE_MAX` pushing a base body through its centre moves it
at 3 u/s. The state is position, heading and radius; velocity is not state, so the simulation
rule's symplectic Euler gives way to explicit Euler on x and θ, and the nodes' lag (D-017) is the
only smoothing.
One tick: the bodies move with the thrust the nodes have, contacts put them back outside the
obstacles and inside the walls, the eyes read the light where the bodies now are, the nodes follow.
After a tick, as after a restart or a drag, the eyes' rates in y are what they read where the body is.
Contacts are hard and frictionless: a body overlapping an obstacle is moved radially out until it
touches it, obstacles in arena order, then its centre is clamped to [R, W − R] × [R, H − R]; three
passes a tick, for crevices. For an overdamped body this cancels the normal velocity and keeps the
tangential one, so it slides. Contacts exert no torque, and walls have no hydrodynamic effect.
Walls come last, so a body never leaves the arena. Lights are not solid; bodies do not touch each
other yet (one swimmer).
A sphere, because a disc in 2D has no Stokes drag (Stokes' paradox). One μ sets one scale and the
sphere sets the other: a thruster with lever ℓ = m × f (body radii) turns its body on a circle of
radius (4/3) R/ℓ, so Ω = (3/4) ℓ V/R. On the tutorial board (ℓ = √3/4), crossed wiring in "One
light" touches the light in 8.7 s and uncrossed turns away and stops in the dark; speeds stay
within 3.6 u/s and turning within 26°/s, 56°/s for one thruster at full rate.
Consequences: V ∝ 1/R and Ω ∝ 1/R², so a body that complexity grows loses its turning first.
Explicit Euler under a constant thrust draws a closed regular polygon, not a spiral. Without
momentum, an eye crossing the edge of a shadow stops the body within a few ticks: it shows, and it
is the eye's doing; smoothing it is a question for TAU.

**D-023 — 2026-10-01 — A run ends when every objective is met or the level's time is up; objectives count visits to lights, and a visit counts once. Supersedes the "Reach a light" bar.**
A swimmer visits a light when their discs touch, centre distance ≤ `LIGHT_RADIUS` + R, checked
after every tick; the run remembers it in `visited`, (N, L), whatever the swimmer does next. An
objective counts from that, so many met out of so many needed: `VisitLights` needs every swimmer
to touch every light, in any order, the one light in "One light" and both in "Two lights". Each
level has a `time_limit` [s]. The arena view stops at the tick the run is won, or after
round(time_limit / dt) ticks, and says which in a banner; visited lights get a ring and the
objective a count, "1 of 2". A level without objectives is never won, only timed out. The end is
derived from the tick and `visited`, never stored, so one frame back takes it back.
The old bar was a live fraction of the way to the nearest light, any light, which fell again when
the swimmer left, and nothing ended a run; the brief asks for countable win conditions (§1).
Consequences: a count jumps from 0 to 1 where the bar filled; at 3.6 u/s a tick moves 0.03 u
against a touch at 2 u, so no visit falls between ticks. Limits: "One light" 20 s (crossed wiring
touches at 8.7 s); "Two lights" 45 s, where a one-eyed circler found by a search of the free board
(5 winners in 2,603 random wirings) visits both in 23.1 s, passing 0.08 u from each centre, deep
enough to survive the ulps of D-004; `test_determinism.py` pins it. Dragging and turning a
swimmer by hand stay a developer's tool and are not scored: the player will not touch a
programmed swimmer.

**D-024 — 2026-10-01 — F4 prints the editor's board as one line of JSON, the start of a save format. Saving for the player stays out of scope.**
`Board.to_dict` gives the zone, what the level handed out, the parts in id order (kind, cell
[q, r], facing by name, locked) and the wires in the order they were drawn, each naming its ends
by their place in that list, with its path. `Board.from_dict` places the parts and draws the
wires again in that order, so the network is the one saved; ids left by deleted parts close up.
F4 works in every view, behind `DEV_VIEW`, and only prints: to the terminal natively, to
pygbag's terminal on the page in the browser, so no file is written (`.claude/rules/web.md`).
A board built in the editor can now be handed over, to a test or to the other contributor,
without transcribing it.
Consequences: a path comes back as saved unless the board was edited with Move or Delete, after
which a wire drawn again may take another route as short; keeping saved paths exactly is for
when saving arrives. The format has no version number yet.

**D-025 — 2026-10-01 — Turning acts on the selected part, from two buttons and L and R; the palette is titled sections, two buttons a row, with room kept for editing and files. Amends D-009's Rotate tool and D-021's arena keys.**
Turn left and Turn right replace Rotate. Pressing either button, or L (left, counter-clockwise)
or R (right), turns the selected eye or thruster by 60° at once and takes that tool; with the
tool, a click turns the part clicked and selects it, and shift-click still turns it the other
way (D-009). The selected part is the last one placed, wired from, moved or turned: a click on a
part with any tool but Delete selects it, its cell is lit like the tool in hand, Escape or a
right click drops it, and deleting it clears it. Operators and locked parts refuse as before.
The palette widens from 72 to 120 px, so the grid's column narrows from 688 to 640 px; the zone
and the hex size are unchanged (D-013). Its sections, each under its title: View (zoom in, zoom
out; hand, centre), Tools (add, wire; move, delete; turn left, turn right), a row each kept free
for Edit (undo, redo, D-027) and File (save, load, post-jam), nothing drawn there yet, and
Colours. Tooltips sit left of the palette.
Turning a part took the Rotate tool, then a click, and a shift-click to go back; with a
selection, the same key or button acts at once, and left and right sit side by side. The room
lets undo and saving arrive without moving every button again.
Consequences, in the arena view (F3), so that a key keeps one meaning (D-021): L and R turn the
swimmer left and right, as Q and E did, and X (x-rays) shows or hides the rays, as L did. Start
again takes Font Awesome's backward-fast (|◀◀, back to t = 0), leaving rotate-left to Turn left.

**D-026 — 2026-10-01 — A wire may be drawn from either end: it is turned round when only that way do the kinds allow it.**
`Board.orient(first, second)` gives the wire's source and target. A wire drawn from a thruster,
or into a sensor, runs the other way, provided that way is allowed: thruster to eye is eye to
thruster, ×2 to eye is eye to ×2. Otherwise it runs the way it was drawn: between two operators,
whose direction only the player knows, even when that way is then refused for a count or a loop;
and thruster to thruster or eye to eye, which no direction allows, are refused as before. The
editor no longer refuses a thruster pressed first; over an empty cell its preview runs into it.
The wire is routed from its source, so one drawn backwards is the same wire, route and all, as
one drawn forwards; routing it the way it was drawn would not be, since D-007's tie-break
follows the direction (from (0, 0) to (2, 1) the route heads E first, the other way SE).
Starting from the wrong end was refused although only one wire could be meant. Turning a wire
round on the board's state, a full Sum or a loop, would make a wire the player did not draw.

**D-027 — 2026-10-01 — Undo and redo in the jam, by whole board states; one step is one gesture. Takes "undo" off the scope lock's Out list in `CLAUDE.md`.**
`Board.snapshot` freezes what the player has built, the parts, the wires as drawn and the stock
left, and `Board.restore` puts it back in place, so the views that hold the board see it. The
editor keeps a `History` of up to 100 states: between gestures, from a press to its release or a
key, it compares the board with the last state kept and, if it changed, keeps it, so a whole Move
drag is one step and a palette click none. Undo and Redo sit in the palette's Edit section, greyed
when there is nothing to take back, and answer Ctrl+Z, Ctrl+Shift+Z and Ctrl+Y (Cmd on a Mac),
matched on the key code; with Ctrl or Cmd no other shortcut acts. A new edit after an undo forgets
what could be redone. Undo drops a wire half drawn, and a selection whose part is gone.
States, not edits: routes depend on the order wires were drawn and never move (D-007), so
replaying edits could route a wire differently, while a state comes back routes and all. A board
is a few dozen frozen parts and wires, so a hundred states cost nothing. Ids are not put back:
the next part placed after an undo still gets a new one.
Consequences: supersedes D-025's order of the palette, which becomes View, Tools, Colours, Edit;
Edit holds Undo and Redo, then Save and Load, greyed until saving exists (still out of scope; F4
prints a board, D-024). The undo and redo icons are Font Awesome's hooked arrows (reply,
share), since its round arrows are the turn tools. The arena view (F3) undoes nothing: it runs
the board as it was when it opened.

**D-028 — 2026-10-01 — The game opens on the first tutorial; a level is data, with its items in an open plane; it is scored on time and number of parts. Supersedes D-022's walls, and D-003's "post-jam" entries in this log.**
The first screen is Tutorial 1's board under a title card that a click dismisses, with a Map
button from the start. The map holds the levels as routes, the sandbox, and later the rest. In
the jam it has one route, light: three Braitenberg tutorials, then the real level. How routes
divide later, by sense or by collective, is left open: the jam has one swimmer and one sense.
A level is plain data, as a board is (D-024): its title and spec, the swimmer's start, the items
placed in the plane (lights and obstacles, others to come), its board (zone, stock, locked
parts), its objectives and its time limit. A level editor, saving and sharing levels will read
and write the same thing. There are no walls: the plane is open, a swimmer that leaves simply
runs out of time, and rays and the light map are drawn as far as the view shows.
Each level is scored on the time to win and the number of parts on the board, two axes that pull
against each other; the session's runs show as points with their Pareto front. Nothing is kept
between sessions: saving stays out.
The brief's success criterion is strangers finishing the real level, and every screen before
the first puzzle loses some; the loop starts with a spec. Levels written in Python could not come
out of a level editor. The walls were a box for trying things, part of no spec.
Consequences: `contact.confine` loses its clamp to the walls; the arenas of D-019 become levels.
What is left to do is in `docs/todo.md`; ideas for after the jam are in `docs/ideas.md`, no
longer logged here as "post-jam".

**D-029 — 2026-10-01 — A light is reached a little short of touching: the centres within 1.2 times the sum of the radii. Amends D-023's "their discs touch".**
`objectives.REACH = 1.2`: a swimmer of radius R reaches a light (radius `LIGHT_RADIUS`) when
their centres are within 1.2 (R + `LIGHT_RADIUS`), 2.4 u for a base body, that is 1.2 diameters.
`touching` is renamed `reaching`. As a body grows with its complexity, the slack stays a fifth
of the touching distance.
Touching exactly was stricter than it looked: a swimmer passing just beside a light, which the
player reads as reaching it, did not count. The win needs no exact trajectory anyway (D-004).
Consequences: the pinned wins come a little earlier, crossed wiring in "One light" at 8.59 s
(8.66 s before), the one-eyed circler in "Two lights" at 22.81 s (23.06 s); the time limits stand.
At 3.6 u/s a tick moves 0.03 u against a reach of 2.4 u, so still no visit falls between ticks.

**D-030 — 2026-10-01 — A level is played in a loop: its board in the editor, Run, the run, Edit back, Next level once won. Each level keeps its board for the session.**
The game opens on the first level's board in the editor, its title and spec over the board. Run,
a wide button at the foot of the menu, or Space (play, as in the arena, D-021), opens the run
view on that level alone. Edit, a button in the player's row, or Esc, goes back to the editor,
the board as it was left. Once the level is won, the banner offers Next level (Enter), when
there is one, and Edit, to do better on time or parts (D-028); when time is up, Edit only. Each
level keeps its board, and its editor with its undo history, until the game closes.
The player's run view touches nothing of the programmed swimmer: no dragging or turning it, and
none of the developer's tools (light map, polar plot, Tab between levels); clicking it to see
its wiring stays. F3 keeps the developer's run view of every level, with all of them.
`editor/router.py` holds which level is open and whether it is edited or run, with no pygame,
and `main.py` turns that into scenes; a scene asks for a change through its `request`.
Consequences: the arena's palette gains Edit; the banner has a fixed size, so its buttons can
be hit-tested headless. The title card, the map and the end screen come next (D-028).

**D-031 — 2026-10-01 — With a turn tool, a click on a part that is not selected only selects it; a click on the selected part turns it. Amends D-025.**
The turn buttons and L and R still turn the selected part at once, the part just placed among
them. A click with the tool used to turn whatever it landed on, so picking out the part to turn
turned it by mistake.

**D-032 — 2026-10-01 — Level 2 is "In the shadow": one light, three obstacles, the swimmer starting in the shadow of one. "Two lights, four obstacles" is set aside.**
The light (power 8) is 15 u ahead of the start, behind an obstacle of radius 1.5 whose shadow
covers both eyes: they read 0, so a Braitenberg wiring alone never moves. A Source gives the
swimmer a drive of its own; with it, crossed wiring slides round the obstacle, sees the light and
reaches it in 3.7 s; uncrossed flees out of sight. The time limit is 15 s, leaving room for
slower solutions. Two lights, where 5 random wirings in 2,603 won, was too hard for a second
level; it waits in `docs/ideas.md`.
The lesson follows the first level's: an eye in the dark sees nothing, and the drive has to come
from somewhere. `test_determinism.py` pins the driven, crossed winner and the stillness without
a drive.

**D-033 — 2026-10-01 — The run view has a timeline instead of one frame back: every tick is recorded, a click or a drag puts the run at any time, a red mark shows where it ended. A step is 0.1 s. Supersedes D-021's `,` (one frame back) and the time in the status line.**
Two rows of five buttons, the view's first (zoom in, zoom out, hand, centre, rays), then the
player's (edit, start again, play, a step, fast), and right under it a bar spanning the level's
time: the part run so far is lighter, the part played brighter, a playhead sits at the time
shown, and once the run is over, won or out of time, a red mark stands across the bar where it
ended. Every tick run is kept (`editor/recording.py`). A click or a drag on the bar puts the run
there, paused: a tick kept comes back at once; ahead of the furthest tick run the run races
there, 40 ticks a frame, and stops on arriving; never past the run's end. The run is
deterministic (invariant 1), so this is the run one would have watched straight through, as a
check showed to the bit. Start again (0) goes back to tick 0 of the same run. A step (`.`),
paused, runs `STEP_FRAMES` = 6 frames, 0.1 s: one frame, 1/60 s, showed no motion. In F3,
moving or turning the swimmer by hand cuts the recording there. The time shows over the
timeline, "3.7 / 15 s", and the status line keeps only the keys. Time left stays among the
objectives (D-023).
One frame back went one frame at a time over the last 20 s; the timeline goes anywhere, and a
level's run is short (15 s, 20 s), so keeping all of it costs little. The rows of buttons were
uneven, and the timeline belongs with the buttons that play the run.

**D-034 — 2026-10-01 — A level is named by its route and its place, "LEVEL 1.2", before its title; every view writes its section titles alike.**
The jam's one route is 1 (light, D-028), so its levels are LEVEL 1.1, LEVEL 1.2 and so on
(`router.level_label`). The editor writes "LEVEL 1.2. In the shadow" and the spec over the board;
the run view writes it over the arena's top left, on a backdrop that reads over the rays and the
light map, and its column falls into three titled parts, CONTROLS (with the time at its right),
OBJECTIVES and INSIDE (the swimmer's wiring), in the style of the editor's palette titles
(`draw.draw_title`: upper case, dimmed). F3's "(2/2)" goes: the number says it. The end banner
moves down to leave the title clear.

**D-035 — 2026-10-01 — Around the levels: a title card over the first, a map of the route and the sandbox, an end after the last. A level opens once the one before it is won.**
The game opens on LEVEL 1.1's board under a veil and a card, "NEKTOIDS, a game by Cy-3LO, Wire
the eyes to the thrusters, then Run", gone at the first click or key (D-028). The map, from the
editor's Map button over Run or Tab, lists the route's levels, each won, open or locked, then the
sandbox apart; a click opens a level, Esc or Back returns to the open one. A level opens once the
one before it is won, this session: nothing is saved. The sandbox, always open, is the old "Two
lights, four obstacles" (D-032) on the free board, with no objective and 120 s. On the route's
last level a win offers "The end" instead of Next level; the end thanks the player and asks
them to leave a comment on the itch.io page (the brief's contact line), and Esc or Map goes to
the map.
`editor/router.py` gains the screens (title, map, edit, run, end) and the session's wins, still
with no pygame; `editor/shell.py` places the map's rows and the buttons, `shell_draw.py` draws.

**D-036 — 2026-10-01 — Each part in the menu has an info disc; clicked, a box beside the menu says what the part does and what may go in and out. "Difference" reads "Diff".**
A small ⓘ sits on each menu row between the name and the count. A click on it opens a box at
that row, to the right of the menu: the part's name, what it does in a few lines, then "In:" and
"Out:", written from the board's own rules (D-014, D-016: a Sum or a Diff takes two wires at
most and sends one; what a part sends is shared among its wires out). The next click or key
closes the box and does nothing else, so a click meant to close it never places or wires a
part. The texts live in `editor/parts.py`, with the names, where a test checks every part has
both. Difference is shown as "Diff", to fit the row; the kind and the levels' data keep
`difference`.

**D-037 — 2026-10-01 — Run and Map move to the palette, under LEVEL, as icon buttons; levels come in chapters, not routes; the eye and rocket icons grow. Amends D-030 and D-035.**
The palette ends with a LEVEL section: Map, then Run, lit, icons only, Tab and Space in their
tooltips as before. The menu's foot is empty again. The map's title reads "CHAPTER 1: LIGHT";
LEVEL 1.2 is the chapter's second level (D-034), and `router.CHAPTER` replaces `ROUTE`. Inside
their shapes, the eye's icon goes from 0.55 to 0.68 of the hex size and the rocket's from 0.5 to
0.62 (`draw.ICON_SCALE`), as large as they go and still clear of the shapes' edges.

**D-038 — 2026-10-01 — Each objective keeps its own latched marks; a new one, Leave the ring, asks the swimmer to get out of a ring round the light. Generalises D-023's `visited`.**
An objective says what counts at a tick, `marks(arena, pos, radius)`, a boolean array (N, K),
and the run ORs each tick's into its own array (`latch`): once marked, always marked. Visit
every light marks the lights reached (D-029); Leave the ring (`radius`, 12 u for Fear) marks a
swimmer once its centre is farther than the radius from every light. The ring is drawn dashed
round the light and lights up once left; the view frames it. The marks go into the recording,
so the timeline restores them (D-033).
Fear could not be "end in the dark": that wins only at the end. A ring to cross is countable,
shows on screen, and is passed or not, with margin: the winner leaves it in about 3 s of 10.

**D-039 — 2026-10-01 — The first level teaches by a tutorial that shows, says and waits; later levels only hint. LEVEL 1.1 is Fear, with no operator.**
A level's data may carry a tutorial: its ghosts, the parts it builds, drawn faintly in their
cells facing the way they should (and outlined over a part that does not face its way yet),
and its steps. A step says a few lines, shows one or more targets (an area, a menu row, a tool,
a Level button, a cell, a part of the run view), which stay lit while the rest is dimmed, and
waits: until a part is placed, faces a way, a tool is taken, a wire is drawn, the run starts, or
the run is won. It moves on as soon as that happens, by mouse or by keyboard, or on Next. Its box
sits beside its targets, clear of them. A step that shows nothing is a hint: nothing is dimmed.
LEVEL 1.1, Fear, has a tutorial of 14 steps: the board, the menu, the palette, then placing two
eyes at the front and turning them to look back (NW, SW), two thrusters at the back corners,
wiring each eye to its own side, Run, and the swimmer fleeing out of the ring (D-038). The level
hands out two eyes and two thrusters only, and the menu shows only the parts a level hands out,
so no operator appears yet. One light (1.2) and In the shadow (1.3) each carry two hints. F1, a
developer's key, goes to the editor from anywhere.
`editor/tutorial.py` reads and follows a tutorial with no pygame, tested by walking Fear's;
`tutorial_draw.py` draws the overlay; `main.py` keeps one per level for the session.

**D-040 — 2026-10-01 — LEVEL 1.2 is Love: stay by the light without touching it, with two Sources, two Sums and two Diffs handed out. Objectives keep any state, not only latched marks; a run can be lost. Generalises D-038.**
Love is Braitenberg's vehicle 3a: each eye inhibits the thruster on its own side, Diff(Source,
eye) = 1 - e, so the swimmer swims to the light, slows as its eyes brighten, and stops where they
saturate. The level: one light of power 8, the swimmer 15 u away facing it, 20 s; two
objectives, Stay by the light (within 6 u of its centre for 5 s in a row) and Don't touch the
light (no swimmer reaches it, D-029); two eyes, two Sources, two Sums, two Diffs, two thrusters;
two hints. The Sums are handed out and not needed: thruster inputs already add. Love with the
eyes turned NE and SE wins at 7.6 s and stops 3.7 u from the light, 1.3 u clear of touching;
with the eyes straight ahead it stops 8.7 u out, outside the ring, and runs out of time (where
it stops is roughly P cos of the eye's angle to the light). Aggression, fear head on and a bare
Source drive touch the light within 5 s. All pinned in `test_determinism.py`. The chapter is now
Fear (1.1), Love (1.2), One light (1.3), In the shadow (1.4).
An objective now keeps what it needs: `start(now)` at t = 0, then `keep(kept, now, dt)` each
tick, from what counts now (`marks`). Visit every light, Leave the ring and Don't touch keep
latched marks, as before; Stay by the light keeps each swimmer's time in its ring, back to 0 when
it leaves, kept once full. `count(kept)` says how many are met, `progress(kept)` fills its bar,
and `lost(kept)` may lose the run: Outcome gains LOST, checked before WON and TIME_UP, so a
touch ends the run at once. The banner says what lost it ("It touched the light at 4.72 s"),
with Edit only, and the objective's row turns red. The ring to stay in is drawn dashed like the
ring to leave, lit once met. What the objectives keep goes into the recording (D-033).

**D-041 — 2026-10-02 — Who does what: the physicist directs and Claude writes the code, in every package; Camille plays the builds and gives his views. Supersedes D-005.**
Camille has no Claude subscription and is not programming; what he brings is a player's view, as
in his notes on the editor (`ebc4abb`, `todo.md` §7). The physicist directs and reviews his own
pull requests with `/pr-prep`; Claude writes, whole features included, after a short plan and a
go. Camille's notes go into `todo.md` or `ideas.md`, in English, with his name on them.
D-005 split the code between two programmers who review each other, and one of them is not
programming: a review that cannot happen only holds the work up.
Consequences: `CLAUDE.md`, the README, `/pr-prep` and the walkthrough change with it. The
walkthrough stays, for when Camille wants to read the code.

**D-042 — 2026-10-02 — A level opened from the map or by Next level comes up under its card: its name, what it asks, its time. Amends D-035.**
The spec was only in the editor's caption, above the board, where a player who has just pressed
Next level starts wiring without reading it (brief §1: the player receives a spec first). The
card is the title card's veil and panel, with LEVEL 1.n, the title, the spec and "You have 20 s.";
any click or key takes it away and does nothing else. A level is opened from a map row or by Next
level, the sandbox included; it is returned to by Back from the map, Edit after a run or F1, and
those show no card. At startup LEVEL 1.1 keeps the title card alone. A line too wide for the card
is shrunk to fit: the sandbox's title is. `router.py` gains `Screen.SPEC`, which `open` and `next`
lead to and `begin` leaves; `shell_draw.py` draws the card.

**D-043 — 2026-10-02 — A light is reached at 1.05 times the sum of the radii, 2.1 u for a base body. Amends D-029.**
At 1.2 (2.4 u), a swimmer that lost Love for touching the light still stood 0.4 u from it, rim
to rim, two fifths of its radius: the banner said it touched what the player saw it miss. At 1.05
the gap is 0.1 u. Visits and touches keep one definition of reaching, so a level that asks to
touch the light (One light) and one that forbids it (Love) agree on what touching is.
Consequences: crossed wiring in One light wins at 8.64 s (8.59 s before), the drive in In the
shadow at 3.76 s (3.70 s); Love's winner rests 1.6 u clear of reaching (1.3 u before). At 3.6 u/s
a tick moves 0.03 u against a reach of 2.1 u: still no visit falls between ticks.

**D-044 — 2026-10-02 — Love's light has power 3.5, not 8: the simplest love wins. Amends D-040.**
At power 8 the eyes saturate about P u out, so a swimmer whose eyes look ahead came to rest 9 u
from the light, outside the 6 u ring, and ran out of time. Only two eyes turned out (NE, SE) won,
each reading half as much: a trick nothing on screen points to, on the first level after the
tutorial. At 3.5 one eye looking ahead, a Diff of a Source and the eye, and one thruster, all on
the axis, rests 4.5 u out and wins at 10.3 s; two such chains rest 4.2 u out and win at 7.6 s.
Both bodies lie wholly inside the dashed ring, 1 u or more clear of touching. Turned out, the eyes
now lose: closing in, the light falls behind their flat faces, the brake fades and the swimmer
touches it. Wiring with no Diff still loses (aggression, fear, a bare drive). Powers 4 and 4.5 also
win, but the swimmer's rim then rests on the ring's dashed line, so it looks half out. All pinned
in `test_determinism.py`.

**D-045 — 2026-10-02 — Complexity is the number of parts, and it is scored, not felt: every body stays a sphere of radius 1 u. Supersedes the scope lock's "body size grows with graph complexity" and brief §1's "thrust budget, not node budget".**
`complexity(board)` counts the parts on the board, the locked ones included, and not the wires.
The score reads it, as one of D-028's two axes (time to win, number of parts); the body does not.
Two reasons. Flow comes later, and Stokesian dynamics is much simpler and faster when every
object is a sphere of the same radius 1. And D-028 already scores the number of parts, so a
body that grew with them would charge for the same parts twice. The cost is now read off the
score rather than felt in the run: that is the trade against the brief. Locked parts count
because every solution of a level pays them alike: they shift every score equally, leave the
Pareto front unchanged, and the count is what the player sees on the board.
Consequences: `BASE_RADIUS` stays the radius of every body; V ∝ 1/R and Ω ∝ 1/R² (D-022) stay in
the model but R never moves; the pinned winners stand. `CLAUDE.md`'s scope lock and the graph
rules change with it. Obstacles keep their own radii for now.

**D-046 — 2026-10-02 — A won run is scored by its time and its parts; the level's wins this session show in the run view's column, in place of the wiring, with their Pareto front.**
`Score(parts, ticks)`: `complexity(board)` (D-045) and the tick the run was won at, exact where
seconds would not be. One score beats another if it is no worse on either axis and not the same;
the front is the scores no other beats. The router keeps each level's scores for the session in
a set: `main.py` records a run on every frame it stands won, and the same board always wins at the
same tick, so a win counts once. Lost runs, runs out of time and the sandbox score nothing.
The banner says "Done in 7.56 s with 8 parts". While the run stands won at its end, the column's
last block, titled Your wins, plots time (0 to the level's time allowed) against parts: the front
bright and joined by a staircase, the other wins dimmed, this run ringed. Scrub back on the
timeline and the wiring returns. Under the banner, where it was first placed, the plot hid the
light and the swimmer resting by it in Love; the levels' items reach most of the arena's height
(Fear's ring 76 to 532 px), so no place over the arena stays clear, and the column always does.

**D-047 — 2026-10-02 — Every colour is named by its job and comes from one palette, built from four numbers in OKLCH; the game takes Forest, violet and sky.**
`editor/palette.py` holds every colour the game draws, and no other module holds one (a test
checks). A palette is ten neutrals (deep, base, surface, raised, line, muted, dim, parts, text,
bright) at the lightness of the greys the game was drawn in, measured in OKLab, so every contrast
stays as it was; all of one tint, `tint_chroma` at the dark end fading to a third at the bright
end. Two accents, of different hues, each in three levels: dark for fills under light icons, mid
for marks on parts, bright for highlights over dark ground. `sense` is the eyes' and the
tutorial's (the tool in hand, the eye's face, a target's outline), `act` the thrusters' and the
swimmer's. The signals keep their hues: red for refusals and lost runs, amber for the developer
view. Below the palette, each colour the drawing code uses is defined from a role, under the
names it had: `BACKGROUND = P.base`, `ACTIVE = P.sense.dark`, `BODY = P.act.bright`. The eye's
flat face and the thruster's back are drawn in their accent's mid level, a band astride the
edge, wherever a part is drawn: the board, the menu, the tutorial's ghosts, the run's column.
`PALETTE = make_palette(tint_hue=150, tint_chroma=0.028, sense_hue=315, act_hue=235)`: green-grey,
violet and sky blue, chosen among ten candidates rendered into the editor, a run and a tutorial
step (the page is in this session's artifacts). Changing those four numbers changes every colour.
Tests pin the conversion, the order of the levels, the accents 45° apart or more, and contrasts
for any tint: text on the background 7 or more, dim text and parts on panels 4.5 or more, the
accents' marks on the board 3 or more (WCAG).

**D-048 — 2026-10-02 — A tutorial can be skipped; while a step leads, only what it asks goes through; its targets are lit by holes in the veil, with no outline; its box keeps clear of the targets, the way between them and the step just done. Amends D-039.**
Skip, beside Next on every step but the last (where Close does the same), ends the level's
tutorial and its ghosts; later levels keep their hints, which block nothing. Going to the map
starts every tutorial again from its first step, finished or skipped, `follow` passing over what
the board already holds. Only a step that waits for Next has a Next; a step that waits for an
action stays until it is done, since a later step needs it (Next past "place an eye" left no eye
to turn). On a step that leads and waits for Next (the introductions, the last), any key or
click moves on, but a click on Skip; a hint takes only its buttons (`tutorial.answer`).
While a step that shows a target is up, `tutorial.allows(step, action)` lets through only the
means to what it waits for: picking that part and placing it on that cell; a turn tool, or L and
R, on that part; that tool; the Wire tool and that wire, either way round (D-026); Run. While it
waits for a win, Run and Edit. A step that waits for Next lets nothing through. The editor asks
before every action that changes the board, the tool in hand or the screen (pick, place, tool,
turn, wire, move, delete, undo, redo, Run, Map, Space and Tab included), the run view before
Edit and Next; a refusal changes nothing, flashes a wrong cell and says "do what the box says,
or press Skip". Zoom, centring, info boxes and folding the menu are not asked; hints let all
through. Before this, a dimmed control still worked: Space mid-step jumped to the run.
Fear's placing steps also light the menu row their part comes from, so what is lit is what is
live; its last step says "Close, then Next level when you are ready."
The veil has holes and no frames: a disc round a cell, a rounded rectangle round an area or a
button. The box keeps clear of the step's targets, of the straight way from each to the next
(the hand's path, 20 px either side) and of the targets and way of the step just done, when the
player did something for it, so it covers neither the drag about to happen nor the part just
placed. It tries beside each target, the last first, then the clear spot of a 16 px grid nearest
the last target. A step that lights a whole area cannot clear it, and the box sits over its
corner as before. Pinned for every step of Fear's tutorial in `test_tutorial.py`.

**D-049 — 2026-10-02 — The palette is Slate and evergreen with a red: accent 1 (teal) marks what the player works with, the swimmer included, accent 2 (red) what goes wrong; no colour outside the palette. Amends D-047.**
`make_palette(tint_hue=273, tint_chroma=0.022, accent1_hue=187, accent2_hue=25, light_hue=85)`.
The fifth number is new: the tint's hue turns from `tint_hue` in the darks to `light_hue` in the
lights, the shorter way round and smoothly, between L = 0.30 and 0.75. That is what Slate and
evergreen does: slate darks, taupe in the middle, warm greys in the lights, which one hue cannot
give. Accent 1, teal, is the faces of eyes and thrusters alike, the tool in hand, Run and the
tutorial's highlight, and the swimmer in the run. Accent 2 was sand; it is red now, and it is
every refusal, lost run, run out of time and developer warning, whose red and amber used to sit
outside the palette (D-047 kept them as fixed signals). `sense` and `act` are renamed `accent1` and `accent2`.
The contrasts stay those of D-047: the lightness steps do not change.

**D-050 — 2026-10-02 — Fear's tutorial explains the run view with the run held still, and ends on the score; a step that explains a panel outlines it and lights its titles; the guided level starts afresh at every visit to the map. Amends D-030 and D-048.**
After Run, the run waits while three steps show Controls (the buttons and the timeline),
Objectives and Inside (the wiring, live), each with Next; a fourth lights Play and the arena and
waits for the win; the last shows Your wins (D-046) and how a win is scored, time and parts,
the line through the wins no other beats. Inside comes before the win because a won run puts
Your wins in its place. A step that leads and waits for Next explains (`Tutorial.explains`): it
holds the run's clock still, and, as dimming suits an action but not a panel, it outlines what
it shows in accent 1 and draws that panel's titles in accent 1 (`tutorial.panels`; the menu's
groups, the palette's sections, Controls, Objectives, Inside or Your wins). A panel's hole and
outline follow its own edges, square, the outline inside them: rounded and grown by a margin,
they ran off the screen at its edges. Cells keep their disc, buttons and rows a rounded hole. The box may lie over
an area 400 px wide or more (the board, the arena), never over a narrower target: it had
covered Play.
Opening the map now resets the guided level, 1.1, whose tutorial leads (`tutorial.guided`): a
fresh board, a fresh undo history, its tutorial at step 1. Restarting the tutorial alone kept the
board, and `follow` passed straight over every step already built, so it never really started
again. The other levels keep their boards for the session (D-030); their hints start again.
Fear's tutorial has 17 steps.

**D-051 — 2026-10-02 — The editor and the run will be rebuilt round an activity bar, drawers and environment tabs. Amends D-016, D-025, D-035, D-037; the work is todo §8.**
The rule: in the Editor the main screen shows the board, as the Diagram view or the Run preview;
in the Run it shows the level; drawers never take it. An activity bar down the left edge, one
icon per drawer; one drawer open at a time, pushing the board aside, folded by its icon or an
arrow on its edge; every drawer's rows alike (icon, name, (i), then a count, a key, a lock or a
tick). At the top, what the player works with: in the editor Parts (puzzle-piece), which is also
the parts' encyclopedia, Tools (screwdriver-wrench), Files (floppy-disk), Sense (stethoscope),
Navigator (compass); in the Run Objectives (list- check), Inside (magnifying-glass), Score
(trophy), Navigator. At the foot, in both: Settings (gear), Chapters (map), then an accented
switch between the environments, Editor and Run, which are also tabs over the content (no
Builder tab until there is a builder): Run (play) in the editor, back (diagram-project) in the
Run. Chapters, not "Map", replaces the full-screen map. Settings holds fast forward's speed, key
hints, tooltips' delay, Fear's tutorial again, and Sound and Music once there is sound; not the
palette. Tools stay in their drawer while the ring round a selected cell (todo §7) brings them
to the hand; Parts and the ring both hand out parts, and complement each other. Sense and Inside
show one circuit, the board as it runs, with no numbers and a level meter by each eye and
thruster in accent 1, the colour of their faces; the two mirror each other: in the editor, Sense
puts the Run preview on the main screen and the level, with the probe, in the drawer; in the
Run, Inside keeps the arena on the main screen and the preview, small, in the drawer. In the
editor it runs where a probe stands, the swimmer put anywhere on the level and turned, nothing
run or scored; two icon buttons over the editor switch views at any time: the Diagram view, a
hex grid, and this Run preview, an operator with two wires in at ±45° and one out, a bead on
each. There, each eye's meter is a handle the player drags to set what the eye reads, to see how
the circuit answers: a test input, kept nowhere and never seen by the run, so the board itself
still holds no continuous parameter (brief: "No sliders"). This amends D-016, whose sensor
sliders were the developer's only. This session's winning boards are kept in memory; Files can
wait, and a board as text is its own PR (todo §9). The run's controls go to a bar under the
arena. Fear's tutorial is rewritten with the bar. Decided from three rounds of mockups drawn
with the game's own palette and renders.

**D-052 — 2026-10-02 — In every circuit view, parts keep their colour; a level meter by each eye and thruster shows its rate, all meters alike, in accent 1. Amends D-017's shading.**
The beads and the meters already show the rates, so shading each part by its rate said it twice.
Wherever the circuit is drawn (the run's Inside, the developer view, and the Sense and Inside
drawers to come), a part keeps its fill, and each eye and thruster has a meter beside it: 1.0 hex
size tall, 10 px wide, its centre 0.86 hex size to the right of the part's, past any part's reach
whichever way it turns, filled from the foot up to its rate in accent 1 (`METER`), the colour of
the part's face. The developer view's thruster bars become these meters, on the eyes too, opposite
its sliders; it keeps its names and numbers.

**D-053 — 2026-10-02 — The editor's frame, step A of D-051: the activity bar with Parts, Tools and Navigator, one drawer at a time, the tabs and the switch. The menu and the palette go.**
The bar is 48 px wide down the left edge: the drawers' icons (Parts, Tools, Navigator) at the
top, the open one lit with an accent bar on its edge; at its foot Chapters, which opens the
full-screen map until it is a drawer, and the accented switch to the Run. A drawer is 248 px
wide; it pushes the board aside, and the view slides with the board's centre, so nothing jumps;
its own icon again, or the arrow on its edge, folds it. Every row is alike: an icon (a part
itself in Parts), the name, an info disc, then a count, the infinity sign, a key or a lock. Parts
holds the groups that fold, Tools the tools, Edit (Undo, Redo shown as Ctrl Y) and File (Save
and Load, locked), Navigator the view's buttons. A row's info disc opens a box beside the drawer:
a part's entry (parts.py), a tool's hint, a button's tip; opening the entry in the drawer itself
is to come. The tabs over the board read Editor and Run, the level's caption after them; the Run
tab runs, like the switch and Space. Parts is open when a level opens. The tutorial now lights
"parts" (the drawer) and "bar" (the activity bar) where it lit the menu and the palette; a tool it
shows is its row, or the Tools icon while that drawer is closed; a step opens the drawer its
targets are in (`tutorial.drawer_for`), once, when it comes up. Fear's first steps say so.
`layout.make_layout(drawer, folded, kinds)` builds it all; `scene.open_drawer` changes it.

**D-054 — 2026-10-02 — Step B of D-051: Chapters and Settings are drawers at the bar's foot. The full-screen map goes; choosing a place in Chapters does what opening the map did. Amends D-035 and D-050.**
Settings (gear) and Chapters (map) sit at the bar's foot, in that order, over the switch to the
Run. Chapters lists the chapter's levels, then the sandbox, in the common rows: the level's
number where the icon goes, its title, an info disc (the title, what the level asks, and the
fastest win this session), then a tick once won or a lock until the level before it is won; the
open place is lit. Tab opens Chapters, or folds it. A click on an open row opens that place under
its card (D-042); a locked row refuses and says why; during a leading tutorial step the rows
refuse like the rest. The full-screen map and its screen go; the end's button reads "Chapters
(Esc)" and comes back to the last level with Chapters open. Choosing a place does what opening
the map did (D-050): the guided level, Fear, starts afresh, the others keep their boards and
their hints start again; the editor left goes back to Parts. Settings, by section: Run, fast
forward's speed (2, 4 or 8 frames' worth of ticks a frame, 4 at first); Display, key hints on or
off (the keys on the rows and in the bar's tooltips) and the tooltips' delay (0.5, 1 or 1.5 s);
Help, the tutorial, which reopens Fear from its first step on a fresh board; Sound, Sound and
Music, locked until there is sound. A click on a row steps to its next choice. The settings last
the session (`editor/settings.py`), shared by every level's editor and the run. The info disc
moves to 156 px into a row, 6 px on from D-053, so that "In the shadow" fits before it; the
sandbox's row reads "Sandbox", its title in its info box.

**D-055 — 2026-10-02 — Two fonts, by their job: FreeSans Bold names things, IBM Plex Mono explains them.**
pygame's own font, FreeSans Bold, rounds each letter's advance to a whole pixel at 15 to 18 px,
so the gaps within a word vary ("le ft", "i ts") and paragraphs read badly. In IBM Plex Mono
every advance is the same, so the gaps are even. Chosen from seven monospaced fonts, then from
three ways to use it, each drawn by the game. FreeSans Bold keeps what names something: titles,
the names of rows and objectives, info boxes' headings and buttons (22 px); section labels,
tabs, keys, the level's title and the tutorial's buttons (18 px); the cards' titles (64 px).
Plex Mono, Medium, takes what explains: the tutorial, info lines, the status lines, counts and
values (15 px); tooltips and the cards' lines (17 px). `Fonts` names the roles: `name` and
`label` in FreeSans, `text` and `small` in Plex Mono, and `big`. The font ships as a file with
its licence (SIL OFL 1.1, 137 KB), opened by path. The wider text moves three things: the
tutorial box is 464 px wide, for 48 characters, with 22 px lines; the cards are 600 px wide; the
Run's key line and the note over its wins are shorter. The developer view's labels crowd its
parts a little more; it is behind DEV_VIEW.

**D-056 — 2026-10-02 — The level's title and what it asks sit on their own line under the tabs, inside the Editor's tab.**
After the tabs, on their line, the caption ran off the screen once its spec was in Plex Mono
(D-055). It now has a strip of its own, 26 px high, under the tabs and over the board: the
level's label and title in FreeSans (18 px), then its spec in Plex Mono (15 px), on one
baseline, a rule under them. The strip has the open tab's colour, so it reads as inside the tab.
The board starts under it (`layout.TOP`). The longest, In the shadow's, takes 620 of the 632 px
it has with a drawer open. The Run gets the same line with its frame (D-051, step C).

**D-057 — 2026-10-02 — Step C of D-051: the run has the editor's frame. Its column on the right goes; its controls go under the arena.**
The run shows the level on the main screen, the arena, inside the frame the editor has. Down the
left edge, the bar: Objectives (list-check), Inside (magnifying-glass), Score (trophy) and
Navigator (compass) at the top; Settings and Chapters at its foot, over the switch back to the
editor (diagram-project; Esc). One drawer at a time: Objectives at the first run, then the one
last open. The tabs, Run lit, with the level's line under them (D-056); the status line at the
foot. Objectives: a row per objective on two lines, its name and info disc, then its bar and so
many of so many, a tick once met, red if it lost the run; then the time left. Inside: the
swimmer's wiring, live. Score: the level's wins this session, this run ringed once won, a note
while there is none. Navigator: zoom in and out, the hand, centre, and the rays (X). Under the
arena, a 48 px strip: start again (0), play or pause (Space), a step (.), fast forward (F), the
timeline, the time. The banner at the arena's top keeps Next level and Edit. Chapters and
Settings work from the run as from the editor: a place picked there, or the tutorial again,
leaves the run. One class holds the frame's logic for both screens (`frame.Frame`, pure, tested
headless); one set of functions draws it (`draw.py`). Fear's run steps light the controls, then
open and outline Objectives, Inside and Score; their box keeps clear of the controls, wide but
low, as it does of any target that is not an area. The developer's arena view (F3) has the same
frame.

**D-058 — 2026-10-02 — Step D of D-051: the Run preview, Sense and its probe, the eyes' meters as handles. Amends D-016.**
Two buttons in the top right corner of the editor's main screen, as big as the switch, show the
Diagram view (three hex cells: the board on its grid, to edit) or the Run preview (an operator,
two wires in at 45 degrees and one out, a bead on each): the board as it would run where a probe
stands, on its body, drawn plain as Inside draws it in the run, beads on the wires and a meter
by each eye and thruster. The probe is the swimmer put anywhere on the level and turned; nothing
moves and nothing is scored; its eyes read the light there and the circuit settles tick by tick
(`probe.Probe`, pure). It starts at the level's start, at rest, and is made again where it stood
when the board changes. Sense (stethoscope), an editor drawer between Tools and Navigator, shows
the level small, its obstacles, lights and rings, and the probe: a press or a drag puts it
anywhere outside the obstacles; the wheel over the map, or L and R while the preview shows,
turns it by 15 degrees. Opening Sense shows the Run preview; taking a tool or a part shows the
board again. In the preview each eye's meter is a handle, its knob as big as a bead, at what the
eye sends: dragged, it holds the eye at that level, the knob lit, and the circuit shows what
follows; moving or turning the probe gives every eye back to the light. A test input, kept
nowhere and never seen by a run: the board still holds no continuous parameter (brief: "No
sliders"); this amends D-016, whose sensor sliders were the developer's only. While a tutorial
step leads, the preview is refused and the board stays on screen.

**D-059 — 2026-10-02 — Step E of D-051: Files keeps this session's winning boards; a click puts one back, and Undo brings back the board left.**
Each win of a level keeps the board that won it, the first one for each score, in memory for
the session (`Router.record`, `Router.wins`); nothing is written anywhere (saving stays out of
scope). Files (floppy-disk), an editor drawer between Tools and Sense, lists the open level's
wins, at most ten: those no other beats first, each with a tick, then the rest, the fastest
first; each row reads its time and its parts, lit while its board is the one on the grid. A
click puts that board back and shows the Diagram view; the board left goes to Undo, as any
change does. While a tutorial step leads, Files refuses. A board as text, to keep or to send,
is its own PR (todo §9).

**D-060 — 2026-10-02 — The run opens paused, and Fear's tutorial opens in it; the Run preview keeps the board's scale and place; the objectives show by the timeline; Navigator has an overview.**
Every run opens paused, so the player opens the drawer they want before Play. Fear's tutorial
starts in the run (a tutorial's data says the screen it starts on): the swimmer in its arena,
then Objectives, then "Click the Editor tab", which only the tab, Esc or the switch get past;
then the editor's steps, then the run's: the controls, Inside, Play, Score. While a step leads,
the run's controls and its timeline go through its gate too, open only while it waits for a
win. Resting the mouse on the other environment's tab shows what the switch says: Run (Space),
Back to the editor (Esc). The Run preview draws the board through the editor's own view, so
switching views moves nothing, and zoom, the hand and centre act on both. At the right of the
timeline, where the time was, so many objectives met of so many, lit once all are, red once one
is lost or the time is up; the time shows in the timeline's tooltip, and stays there for the
sandbox, which has no objective. Under Navigator's rows, an overview: the whole board, its
parts as dots, in the editor; the whole level and the swimmer in the run; a frame round what
the main screen shows, and a press or a drag there centres the view.

**D-061 — 2026-10-02 — Only the tutorial's opening steps, and its last, move on at any key or click; the others that explain wait for Next or Enter. Amends D-048. Ghost parts are a paler grey, with no outline.**
Since Fear's tutorial opens in the run (D-060), steps that only explain also come later, in the
editor and in the run (the board, Parts, the bar, the controls, Inside). There, a click to look
round, an info disc or a drawer, moved the tutorial on unasked. Now the steps before the first
that asks for an action, and the last, move on at any key or click, as D-048 had it for the
first messages; the others move on only by Next or Enter, and other clicks go to the screen,
where the step's gate still refuses what it does not ask for. Fear's step to the editor shows
both ways there, the Editor tab, its name lit, and the switch. A tutorial's ghost part, where a
part goes and which way it faces, is a paler grey shape with no outline. Fear's last step no
longer names Braitenberg.

**D-062 — 2026-10-02 — When a step explains the run's arena, it outlines the whole Run page: the Run tab, the level's line and the arena.**
The arena alone, outlined, put the tutorial's box against the outline's top edge. The step now
outlines the run's page as a folder: the Run tab on top, then the level's line and the arena
under it (`tutorial.Page`). Its header, the tabs and the level's line, counts as a target the
box keeps clear of, so the box lies inside the page, under the level's title, with room round
it.

**D-063 — 2026-10-02 — A step that asks for an action no longer dims the screen: its cells turn to the accent, its rows and buttons are outlined. Amends D-048.**
Dimming everything but the target made the steps that ask for an action (place a part, turn it,
wire two parts, Run, Play) feel constrained. Now the screen keeps its light: each cell such a
step shows is filled in the accent, under its ghost or its part, which stay as they are
(`tutorial.focus_cells`); a row, a tool, a tab or a button it shows is outlined in the accent.
Steps that explain keep the veil and the outline of D-050. The gate is unchanged: only what the
step asks for goes through.

**D-064 — 2026-10-02 — The level's title under the tabs is FreeSans at 22 px, not 18. Amends D-055, D-056.**
At 18 px it looked smaller than the Plex Mono beside it; at 22 px its capitals stand 11 px to
Plex's 10, the same x-height. What the level asks, after it, ends in an ellipsis where it does
not fit: In the shadow's, with a drawer open. The level card and Objectives give it whole.

**D-065 — 2026-10-02 — The run's objectives sit at the foot of every drawer, and the Objectives drawer goes; Navigator keeps only the view's options, the overview and a zoom bar; wires keep one colour. Amends D-052, D-057.**
The objectives were seen only with their own drawer open. Now they sit at the foot of whichever
drawer the run has open, Inside, Score, Navigator, Settings or Chapters, under a rule and their
label, each row as before; with the drawer folded, the timeline's summary shows them (D-060).
The bar's Objectives icon goes, and the run opens on Inside. To make room, Navigator shrinks:
the view's options as rows, so far only the rays, in the run; the overview; under it, the zoom
as a bar between its out and in buttons, pressed or dragged, on a log scale. Hand and centre
leave the drawer: dragging the overview does what the hand did; their keys still work. In every
circuit view, Inside, the Run preview and F2, wires and beads keep one colour whatever they
carry: the beads' spacing and the meters show the rates.

**D-066 — 2026-10-02 — The overview shows half as much again as what matters, the zoom goes no farther out, and the view stays inside it.**
The overview showed the zone or the level just as they are, so the main screen could show more,
and the frame round what it shows then lay outside the overview, unseen. Now the overview shows
an extent: what matters, 1.5 times over each way about its middle, widened to the main screen's
shape. In the editor what matters is the zone, its hexes whole, and the extent is at least what
the main screen shows at the default zoom; in the run it is the lights and their rings, the
obstacles and the swimmer where it is now, so the extent grows as the swimmer leaves, every
frame. The farthest zoom shows the extent exactly, and the zoom bar runs from there to the
nearest; the view is kept inside the extent, whatever moves it (`layout.kept_on_board`,
`arena_view.kept_in`), so the frame is always inside the overview.

**D-067 — 2026-10-02 — Settings drops the tooltips' delay and its titles. Amends D-054.**
Settings is its rows one under the other, with no section titles: fast forward's speed, key
hints, the tutorial again, Sound and Music (locked). The tooltips' delay is no longer set: a
tooltip shows after 1 s. Shorter, Settings leaves room in the run for the objectives under it
(D-065).

**D-068 — 2026-10-02 — The editor's hand: a focused cell and the ring of what can be done there, in Tools; Write and Delete; Swap; the ring turns as a wheel. Written after PR #21, which cites it. Amends D-026, D-051, D-053.**
A click focuses a cell, lit on the board. Tools, first in the bar and open when a level opens,
draws it large, its part at its facing, with the ring round it: round an empty cell, the parts
the level still hands out, each with its number; round a part, turn left, move, wire, swap, turn
right and delete, the wire on top, the turns either side of the gap at the foot, the turns only
for eyes and thrusters, Swap only while another part of its group is left; a part the level
placed offers only Wire. Up to five icons sit beyond the cell's corners; more turn on a wheel,
as cards on a rotary file: the others piled under the ring's two ends, drawn empty, set back
along the circle so their edges show. The keyboard going round turns the wheel just enough for
its choice to be on the ring; so do the mouse wheel over the picture and the mouse resting on a
pile. Clicking a part arms Wire from it: the next part clicked is wired to it, and the focus
goes on to that part; a drag from a part moves it. Only a part clicked wires either way round
(D-026); a part focused otherwise, placed or just wired to, wires on only along the signal, so a
chain goes on, eye to sum to thruster, but from a thruster a click on an eye only focuses the
eye. A wire that cannot be made ends the attempt: nothing stays focused, and the status line
says why. Swap (S) turns the part into another of its group, in its place, its facing kept where
both turn, with every wire it can take; the status line says how many could not follow; one
step for undo (`Board.replace`). Tools' rows above the picture: Write and Delete (E goes from one
to the other, Esc back to Write), then Undo and Redo. In Delete there is no focus and no ring: a
click removes the part under it with its wires, or the wire under it, darkened while the mouse
is on it. The keyboard drives the same focus: the arrows, Enter, the ring's keys, Esc back one
step. Atop the main screen, always, what the next click or Enter does: the action as a ring's
icon, its key beside it, a line under it saying what it is; a click on it opens Tools.

**D-069 — 2026-10-03 — The main view follows the drawer: the Run preview only in Diagnostic, Sense renamed. The ring is the Wheel, at the foot of Tools and of Parts. A key for each drawer, its initial; Delete on Backspace; one key, one meaning within an environment; tooltips after 0.5 s; Run first, and a level opens on its run. Amends D-021, D-058, D-060, D-067, D-068.**
The switch between the Diagram view and the Run preview goes. The main screen shows the board,
except while Diagnostic is open, where it shows the Run preview; Navigator keeps what was shown
before it, so the preview can be zoomed and moved. Sense is called Diagnostic: it is where the
board is tested. While a tutorial step leads, Diagnostic does not open. While the preview shows,
a key that edits the board is refused and the status line says to open Tools or Parts; undo and
redo still work, and the preview follows them; the action atop the main screen hides, and the
status line says what the preview offers, an eye's knob to drag. The ring of D-068, the focused
cell drawn large at its hub, is called the Wheel, in the code too (`wheel.py`, where the rim is
its arc of up to five icons). Tools and Parts both have it at their foot, under a rule and its
title, The Wheel, which folds as Parts' groups do, in both at once; folded, the title sits at
the drawer's foot and the rows above take the room. Parts lists its groups as sensors,
actuators, operators, and the parts' numbers and the Wheel's order follow: with all seven handed
out, the thruster is 3. Parts' list scrolls, by the mouse wheel or a scroll bar, when it does
not fit. The Wheel's icon under the mouse is named in a tooltip, as the bar's are, after the
same rest and as warm: its name, and its key while key hints are on; the keys no longer sit
round the rim, and the Wheel takes the room they leave, its cell 46 px across instead of 40, its
icons with it. The accent names what is chosen: beside the action atop the main screen, the
action, with its key; in the line under the Wheel, its lit icon, the keyboard's choice or the
tool in hand, else what the cell holds, dimmed. On the board, the focused part loses its white
circle: the lit cell says it, and while the keyboard wires, the ghost wire shows where the wire
starts. Over a part the wire cannot reach, its way still shows, dimmed, as over an empty cell,
with the cell outlined in red and the reason in the status line. The line under the action atop
the main screen sits under its disc. Each drawer opens, or folds, by a key, its initial: T
Tools, P Parts, F Files, D Diagnostic, N Navigator in the editor; I Inside, S Score, N Navigator
in the run; the comma Settings in both, with Ctrl or Cmd too (a Mac's browser keeps Cmd+comma
for its own settings); Tab Chapters, as before. Delete takes Backspace and Delete, the keys that
delete everywhere else, and frees D. D-021 becomes one key, one meaning within an environment: a
letter may mean one thing in the editor and another in the run, as F is Files in the editor and
Fast forward in the run, S Swap and Score, since the two never show together. X, the run's rays,
no longer zooms out in the editor. Once a tooltip of the bar shows, the next icon's shows at
once, for 0.3 s after the last one went, as the mouse crosses the gaps between icons. Every
tooltip shows after 0.5 s, not 1 s (amends D-067). The tabs read Run, then Editor, and every
level opens on its run, paused, as Fear's did (D-060): at the start, from Chapters, by Next
level; its card, the title card or the level's, shows over that run, so only the card goes when
it is dismissed; the editor is a tab or Esc away. The tutorial follows in its own PR.

**D-070 — 2026-10-03 — Fear's tutorial follows the Wheel: the eyes from the Wheel, the thrusters from Parts, each wire by two clicks; a step may show a Wheel's icon, or Tools. Amends D-048, D-060.**
After D-069 the tutorial still taught the old panel: its wiring step said to drag from the upper
eye, which now moves the part, and a step refuses moves; its turns pointed at buttons that were
gone. Fear's editor steps are now: the board, and atop it what a click does; Tools, with Write
and Delete, Undo and Redo, and the Wheel at its foot; the bar, each drawer by its initial too;
the first eye, by a click on its cell then the Eye on the Wheel, or 1, turned by Turn left on
the Wheel, or L; the second eye the same way; then Parts, and the two thrusters dragged from it;
each wire by a click on the eye, then on the thruster; Run, by its tab, the switch or Space.
Fear has 20 steps. A step may show a Wheel's icon by its name, {"wheel": "eye"} or {"wheel":
"turn left"}, outlined as a disc, and only while the step's own cell is focused, since the Wheel
round another cell would act there; and the Tools drawer, {"area": "tools"}. A step that shows a
Wheel's icon keeps Tools or Parts open, whichever is, else opens Tools, and unfolds the Wheel if
it is folded. The {"tool": ...} target, which showed nothing since D-068, goes, and so does a
tutorial's start screen: every level opens on its run (D-069). Diagnostic is only named, in the
bar step; teaching it is for later.

**D-071 — 2026-10-03 — Fear's tutorial in 16 steps: nothing dimmed, the swimmer boxed, pages and drawers outlined with their tab or icon; one card for the second eye, one for Parts and both thrusters; in the run, Play first, a pause for Inside, then the win and the score. Amends D-050, D-062, D-070.**
No step dims the screen any more: an explaining step outlines what it shows in the accent and
leaves the rest as it is, as a step that asks for an action already did (D-063). Fear's first
step boxes the swimmer alone, {"run": "swimmer"}, its place read off the run; Objectives is
outlined. The editor's board is explained as its page, {"page": "editor"}: the Editor tab, the
level's line and the board as one shape, as the run's page (D-062). Tools, Parts, Inside and
Score are each outlined with their icon in the bar, {"drawer": "tools"}, as one shape, a step
that asks for an action outlining it too. The bar's step goes. The second eye is placed and
turned on one card, and Parts explained and both thrusters dragged from it on one: a step may
wait for a list of things, met once each is, letting through the means to any. A step that shows
a Wheel's icon keeps its box clear of the whole Wheel. In the run, Play comes first and waits
for 1 s of the run ({"time": 1.0}); then the run pauses for Inside, the beads explained, and
Next lets it go on by itself, an explaining step resuming the run it paused; a step waits for
the win; the last explains the score alone: time and parts, fewer is better, the line of
unbeaten wins. The step on the run's controls goes: Play's own text and the controls' tooltips
name them. An outline round a target at the screen's edge, a tab, the switch, a drawer, keeps 3
px inside it.

**D-072 — 2026-10-03 — With Wire chosen, a drag from a part draws a wire, not a move. Amends D-068.**
With Wire chosen, by W or the Wheel's icon, a drag from a part moved it, as D-068 has any drag do.
Now it draws a wire from that part, its ghost following the mouse, made to the part it is released
on, the focus going on to that part, as a click on the one then on the other would; released on an
empty cell, the attempt ends with the reason; back on its own part, or off the board, nothing. With
Wire only at hand, after a click on a part, a drag still moves it.

**D-073 — 2026-10-03 — The run's overview never shrinks below its start, nor while the main screen's frame touches its border. Amends D-066.**
The run's extent, what Navigator's overview shows and the most the arena may, followed what
matters every frame (D-066), so in Love, as the swimmer came to the light, it shrank and the view,
kept inside it, zoomed in on its own. Now the extent is kept from frame to frame: what matters
now, never less than the extent at the run's start, and never less than it was while the main
screen's frame touches its border, zoomed out or slid to an edge. Away from the border it may
shrink back, as far as its start, once the swimmer has gone far and come back.

**D-074 — 2026-10-03 — LEVEL 1.2 is Aggression, guided: the player builds Braitenberg's 2b from its shadows, wires and all, then tries it in Diagnostic before the run. Love is 1.3. Amends D-039, D-040.**
One light, the level crossed wiring wins, is called Aggression, Braitenberg's vehicle 2b, and
comes second, after Fear, his 2a: the brief's order (§3, level 2: crossed, the swimmer charges
the light). Love is 1.3, In the shadow 1.4. Aggression hands out two eyes and two thrusters
only, the parts Fear taught; its arena, objective and time stand, and so do its pinned results.
Its tutorial leads, so the first two levels are guided (D-039 had only the first) and each
starts afresh from Chapters (D-050). In the run: the swimmer and its objective; to the editor.
In the editor, one card: build what the shadows show. The model is the board crossed wiring wins
with: the eyes at the back looking NE and SE, the thrusters at the front, each eye wired to the
thruster on the other side; the four cells lit, the shadow parts and, new, shadow wires, a
tutorial's ghost_wires drawn faintly along their route until the real wire is made. The card
waits for all of it, placed, turned and wired, and lets through only what builds toward the
model. Then: open Diagnostic, a step that waits for that drawer and lets it open, its icon shown
while it is closed; then what Diagnostic shows, the run held, the swimmer free to drag on the
map. Then Run, Play to the win, and a closing hint: crossed, the wires turn the swimmer toward
the light. Sources stay for Love, where a Diff of a Source and an eye is the point.

**D-075 — 2026-10-03 — Each level's win gives a passkey, a word that opens the next level at once when typed in Chapters. Nothing is stored: not saving. Amends D-035.**
A player who comes back, the session gone, need not win the levels before again. A level's file
holds its passkey, A to Z, at most 10 letters: the word its win gives, which opens the next
level. Fear gives LOVE, Aggression SWORD, Love HEART; In the shadow gives DARK, which opens
nothing until there is a 1.5. The win card names it under the time, "Passkey for LEVEL 1.2:
LOVE", in the accent; a won level's info box in Chapters gives it too, never one not yet won. At
Chapters' foot, under the sandbox, a field: a click on it, or P while Chapters is open (P is not
Parts then), and the player types, A to Z, Backspace, Enter to try, Esc or a click elsewhere to
give up; every key goes to the field meanwhile, in the editor and in the run. A word opens its
level and every level before it, for the session, none of them won, so no score; the status line
says which, in the accent, or that no level has that word. D-035's rule stands otherwise: a
level opens once the one before it is won, or by its word. The words are ours (the todo's
caution about titles). Whether a phone's keyboard comes up for the canvas is left to the touch
work (todo §7).

**D-076 — 2026-10-03 — The body at work, seen: in the run and in Diagnostic the swimmer shows its parts, its thrusters' flames, the light its eyes draw in, where it goes and how it turns. accent2 marks the thrust too; the light is a bulb. Amends D-049; reads the scope lock's "art".**
The run drew the swimmer as a circle round a wedge: what it read, what it pushed and what that
did showed only in Inside's beads, a failure the player could not see on the arena (invariant
6). It now shows the brief's steering vector (§1) and more, chosen on an art sheet drawn in the
game's palette over the game's own runs of Aggression. The parts: each eye's face and each
thruster's back in their teal, 2 px, where the board puts them on the body (D-018), with the
parts' outlines in a dim grey, 1 px, the board's shapes scaled by the body's reach. The flames:
specks of 3 px drifting out of each thruster's back, 3 body radii long at any rate, widening by
10° either side; the rate is their density, 12 at once at RATE_MAX, each speck out in 16 frames.
The light drawn in: the flames run backwards, specks drawn into each eye's face from each light
it sees, along the light's own direction, from 3 body radii out, in 0.5 s; as many as that light
gives the reading, 12 at once at RATE_MAX; over the face's width as the light sees it, its
cosine (D-019); none from a light behind the face or in shadow. Headlight cones out of the faces
were tried and left: they point where the eye looks, not where its light comes from. Flames and
light are of one lightness (OKLab L 0.56), the flames a darker accent2, the light a warm grey,
both dimmer than the swimmer. The specks are drawn from a table seeded once and read by the
run's frame, as the rays are (invariant 1): never read by the model, still while paused, the
same on a replay or a scrub, faster under fast forward. The motion, both in the swimmer's own
accent1, 2 px: a segment from the rim along the velocity, as long as the way gone in 1 s, its
leaving the rim saying its way; an arc 1.6 body radii from the centre, from the heading, as long
as the angle turned in 2 s, at most 300°. Both come from the thrust now (D-022), what the next
tick does, so Diagnostic's probe, which stands still, shows where it would go, and a swimmer
against an obstacle points into it while it slides. Nothing is cleared over the body: the marks
cross it. Diagnostic's map shows all of them at its scale; its main screen, where the body is
the board, none. Navigator's overview stays plain. In the run, Navigator's View shows two more
rows under Rays, each on or off for the session: Motion, M, a gauge, the velocity and the spin;
Streams, W, the wind, the flames and the light drawn in. M and W are Move and Wire in the editor,
which never shows these rows (D-069). A light in the run is a
bulb, 1.6 light radii high, not a sun; the Rays button's bulb now says the same. Amends D-049:
accent2 marks what goes wrong and, darker, the thrust. The scope lock has art out: these marks
are legibility, each shows a quantity of the model, and the scatter of the specks, the nearest
thing to art, is drawing only.

**D-077 — 2026-10-03 — LEVEL 1.4 is Shadows, not In the shadow.**
One word, as the chapter's other titles are: Fear, Aggression, Love. Its file is `shadows.json`;
its passkey, DARK, stands. Earlier entries keep the old name.

**D-078 — 2026-10-03 — Each level's three hints are asked for in turn in Hints, a drawer at the bar's foot in the editor and the run: an idea, the parts, the shadow. Amends D-039, D-051, D-054, D-069.**
Love and Shadows opened with two boxes over the board (D-039), and nothing could be asked for: a
player stuck, or past Skip, had no help. Hints (a life ring; ?, H being the hand's) sits at the
bar's foot above Settings, in both environments. Its rows, in the common style: Hint 1, Hint 2,
Hint 3, each locked until the one before is taken. A click takes one, and its lines stay under
its row, so every hint taken reads at once. Hint 1, the idea, is a line of the level's, a bit
cryptic. Hint 2, the parts, counts the shadow's parts in Parts' order, each name as Parts writes it ("One Eye, one Source,
one Thruster, one Diff."), so the two cannot disagree. Hint 3, the shadow, is one winning board
drawn as a tutorial draws its model (D-074), faint: in a picture under its row, and on the
editor's board; its row is then a switch for both. The wire that follows the mouse while one is
drawn is now as thick as a wire made, 3 px, whether or not it can connect. Each shadow, built on its level's own board, wins it
(`test_hints.py`). The ideas: Fear "Each eye its thruster.", Aggression "Cross the wires.",
Love "The light softens the push.", Shadows "There is no light in the dark."; the shadows are
the boards the tests pinned: Fear's and Aggression's models, D-044's smallest Love, and
Shadows' crossed wiring with a Source on both thrusters. Taken hints last the session, level by
level, and Chapters does not reset them. The score does not show them: it is the player's own,
seen by no one else, and a mark would only tax asking for help. While a tutorial leads, the rows
are locked and the drawer says to skip or finish it; the sandbox has none. Love's and Shadows'
boxes go: only Fear and Aggression have a tutorial. Like the comma and Tab, ? is a drawer's key
that is not its initial (D-069); in the run the comma now matches on the character typed,
since AZERTY's ? is a shifted comma. Settings' "Key hints" keeps its name.

**D-079 — 2026-10-03 — Fear's tutorial is an introduction of six steps that builds nothing, shown once a session; Aggression's goes. Amends D-039, D-048, D-050, D-054, D-071, D-074.**
With every level's hints (D-078), a tutorial that built the board showed again what Hint 3
shows, and took sixteen cards to do it. Fear's tutorial now introduces what the hints do not:
in the run, the swimmer and the light, then Objectives; the tabs, Run playing the level and the
Editor building the swimmer, waiting for the Editor; there, the board as the body, a click on a
cell and its Wheel, a step with no target, its box in the main screen's bottom left; the
activity bar, its drawers each by its initial, and those at its foot; last, the Hints icon
alone, `{"icon": "hints"}`, which opens nothing. Any key or click closes that last step, and a
click there also does what it does, so a click on the icon closes it and opens Hints.
Nothing is placed, turned or wired, and there are no ghosts; the steps on Run, Play, Inside and
Score go, the controls' tooltips naming them. Aggression has no tutorial: it is a level like
Love. The tutorial shows once a session: choosing a place in Chapters no longer starts Fear
afresh, board and tutorial, nor restarts any tutorial (D-050, D-054); every level keeps its
board. Settings' Tutorial plays the introduction again from its first step, on Fear as the
player left it. What a tutorial that builds needs, the waits for a part placed, turned or wired,
the ghosts, the Wheel's icons as targets, stays in `tutorial.py`, used by no level; the tests
walk the tutorials Fear and Aggression had, kept in `tests/data`. `guided` goes with the rule it
served. Nothing teaches placing, turning or wiring now: the action atop the board, the status
line, the Wheel's tooltips, Parts' (i) and Hint 3 carry it, to be watched when Camille plays it
cold.

**D-080 — 2026-10-03 — A tutorial's target is drawn in accent 1, with sparks drifting out of where its outline was; no outline. Amends D-048, D-050, D-063, D-071.**
An outline round a target said where to look, and nothing more; the outlines of the tab, the
switch and an icon crowded the strip they sit in. Now what a step shows is drawn in accent 1 by
what draws it: a drawer's icon, a tab's name, the titles of a panel or a drawer, as D-050 lit
titles; the swimmer and the switch are accent 1 already. The activity bar keeps its colours and
sparks round its two groups of icons, each on its own: the drawers at its top, and at its foot
the drawers there with the switch. `panels`
names them for every step that leads, not only those that explain: an area, a drawer or a part
of the run by its name, a tab as "tab:editor", an icon as "icon:hints"; `main.py` sets them as
the scene's `lit`. Colour alone cannot single a target out, since accent 1 already marks what
the player works with (D-049), so it moves: specks of accent 1 dark drift out of the target's
edge, where its outline was (6 px round a button, a row or the swimmer; a panel's own edges; a
disc round a cell or a Wheel's icon), 14 px out in 24 frames (0.4 s), one alive per 24 px of
edge on average, on the 3 px grid of the thrusters' flames and from the same table of draws,
made once and read by the frame (D-076): still while nothing moves, the same each time. Their
frame is `main.py`'s count of frames drawn, drawing only. Chosen over a glint sweeping across
the target and a colour that breathes, from a preview in the game's own renderer. The box loses
its accent border, now RULE, 1 px, as an info box's; the accent goes to Next or Close, filled in
accent 1 dark as the tool in hand is, since that is what Enter, or on the opening and last steps
any key, does. Skip stays plain.

**D-081 — 2026-10-03 — Every tutorial card that waits for Next closes at any key or click, which does nothing else. Amends D-048, D-060, D-061.**
Only the opening cards and the last closed at any key or click (D-061); the others waited for
Next or Enter, so that a click to look round went to the screen (D-060), and a card with no
target let everything through (D-048). In Fear's introduction that made cards 4 and 5 leak:
Space on the board's card ran the level, a drawer's key on the bar's card opened it. Now a card
that waits for Next takes every key and every click, Skip aside, and moves on; the key or click
does nothing else. A modifier alone, Shift, Ctrl, Cmd, Alt or Caps Lock, closes nothing, so a
player may switch windows. A step that waits for an action is unchanged: the press goes to the
screen. On the last card a click that closes it still reaches the screen (D-079), so a click on
the life ring opens Hints. `Tutorial.opening` goes with the rule it served.

**D-082 — 2026-10-03 — A part's entry shows the part at work: its own small circuit, running under what the entry says, with the run's light and flames.**
A part's (i) in Parts said what the part does in words (D-036); the beads that say it on the
board were seen only once a board ran. Now the entry's box holds, under its lines, a circuit of
the part's own, 420 by 140 px, drawn as Inside draws a board (`draw_circuit`, moved to
`draw.py`), its wires, beads and parts, at one scale for every entry. The inputs on the left,
the part in the middle, a thruster on the right taking what it sends. The inputs are eyes set to
a reading, not lit by a light, so that less than 1 can go in: a Source sends 1, and ×2 of 1 is
still 1. Eyes and thrusters face outwards, the eye's face to the left and the thruster's back to
the right, and the run's marks show what they read and push (D-076): specks of light drawn into
each eye's face from the left, as many as it reads, and flames streaming out of each thruster's
back to the right, as many as its rate, from the same table of draws; no meters. Eye: an eye into
a thruster, three cells apart, its reading rising and falling from 0.2 to 0.9 every 10 s, more
light giving more beads. Source: a Source into a thruster, a steady 1. Double: 0.3 in, 0.6 out.
Halve: 0.8 in, 0.4 out. Sum: 0.3 and 0.4 in, 0.7 out. Diff: 0.7 and 0.3 in, 0.4 out. Thruster:
two eyes, 0.3 and 0.4, into it, added. Only the Eye's reading moves, so that the beads can be
counted. The entry's beads keep their speed once out (`beads.Travelling`): the spacing is the
rate when each left, so a change of rate runs down the wire as a front and no bead goes
backwards, as `Beads` would as the reading climbed; Inside keeps `Beads`. The circuit opens at
its steady rates, run 0.25 s before it shows. For ×2 and ÷2 the beads going out keep time with
those coming in: a bead leaves as one arrives, and ×2 sends another halfway to the next, ÷2 one
for every two. The entry is made when a part's box opens and dropped when it closes; the scene's
update moves it once a frame (`Frame.frame_update`), so drawing changes nothing. Never read by
the model. The entry stays in the box beside the drawer until it moves into the drawer (todo §8).

**D-083 — 2026-10-03 — The Wheel is seen to turn: each step slides its icons in 0.1 s, eased out, and a step taken during a slide goes straight on; resting on a pile clicks every 0.5 s. Amends D-068.**
With more than five icons the Wheel's turn jumped: the five on the rim changed in one frame, and
the player could not see which way it had gone. Now each step, by the keys, the mouse wheel or
the mouse resting on a pile, slides the icons along the rim and the piles in 6 frames (`SLIDE`),
quick at first and slowing as they arrive (`wheel.slid`), then rests. Each icon runs along the
circle between its two places: 60° from corner to corner on the rim, about 7° down a pile. A
step taken during a slide goes straight on, from where the Wheel shows to the new turn, rather
than waiting in a queue: what is drawn is never more than 0.1 s behind, and as the Wheel holds
seven icons at most, a slide covers two steps at most. The turn itself is set at once, as
before; only the drawing, and the clicks on what is drawn, follow the slide. An icon leaving the
rim for a pile goes empty at once and passes under the icon sliding over its place; one coming
off a pile shows its face as it lands. Half way between two corners an icon swings about 3 px
past the Wheel's room, into the drawer's margin, never out of the drawer. Where the Wheel's
icons change (a new focus, Swap, Esc out of Swap) it shows at its start at once, without a
slide. Resting on a pile turns it after 0.25 s, then every 0.5 s (`PILE_FRAMES`, 24 frames
before, now 30).

**D-084 — 2026-10-03 — The arrows go along the Wheel's arc and stop at its ends; "nothing" is only where it opens. Amends D-068.**
The Wheel is an arc, not a circle: a first icon on the left, a last on the right, the gap at
the foot. The keyboard went round it as a circle, from the last icon on to the first, with
"nothing" a stop between them round a part. Now → and ↓ go to the next icon and stop at the
last, ← and ↑ to the one before and stop at the first. Round a part, the Wheel still opens on
"nothing", where Enter closes it; from there → goes to the first icon, ← to the last, and
"nothing" is not met again: Esc closes the Wheel. The Wheel turns with the choice, as before.

**D-085 — 2026-10-03 — A part dragged off the body is deleted when let go there: off the zone's cells, on the drawer or the bar. Amends D-068.**
A drag that moved a part off the zone flashed "outside the zone", and the part waited at the
last cell that worked. Now, off the body, the part still waits there, but darkened with its
wires, as Delete's preview darkens them, the action atop the main screen is Delete, and the
status line says that letting go deletes it. Let go there, on the grid outside the zone, on the
drawer, Parts or another, or on the bar, the part goes with its wires and nothing is focused;
brought back on the body first, the move goes on. The drag and the deletion are one step for
undo, which puts the part back where the drag began. A tutorial step that does not let a part be
deleted leaves nothing darkened, and the part let go off the body stays, the status line saying
why. A press still becomes a drag once the pointer leaves the part's cell; whether that suits a
finger is the touch item's question (todo §7).

**D-086 — 2026-10-03 — A part may go on a cell a wire crosses: placed or moved there, the wires crossing it are routed round it, and stay so. Amends D-007, D-011.**
Dropping a part on a cell a wire used was refused (D-007), and so was moving one there (D-011): a
wire drawn after a part went round it, but a part put after a wire could not go where the wire
ran. Now the wires crossing that cell are routed again round the part, in the order they were
drawn, each by D-007's rule (the shortest free path, then the fewest bends, then the direction
order), round the parts and the wires already there; every other wire stays, and each keeps its
place in the order. If one finds no way round, nothing changes and the status line says so. A
part moved routes again its own wires and those crossing the cell it goes to, together, in the
order they were drawn. A drag, or the keyboard carrying a part, works each step out from the
board as it was when the part was picked up: a wire the part passed over goes back as it moves
on, and only where it is let go are the wires routed round it. If the board is edited otherwise
on the way, a turn while the keyboard carries the part, the move goes on from the board as it
then is, and the turn stays. D-007's "routes never move once
drawn" becomes: a route changes only when a part is put on a cell it crosses, placed or moved
there, or when its own part moves (D-011); it never changes on its own.

**D-087 — 2026-10-03 — The wire being drawn is white until it may connect, then accent1, drawn over every other; every wire on the board is 3 px.**
While a wire was drawn, it was a mid grey until it could connect, then white; beside a shadow
wire, a tutorial's or a hint's, drawn a paler grey, the two looked alike. Now the wire being
drawn is white until it may connect, and accent1, what the player works with, once it may. It
is drawn last, over the shadows and the wires made: building the shadow's own wire, on the same
route, the shadow hid it. Wires had two widths, 3 px and 2 px for the shadows. Now every wire on
the board, made, darkened for Delete, a shadow or being drawn, may connect or not, is 3 px,
whatever the zoom, its arrowheads as before; the hint's small picture of a shadow too. 5 px,
scaling with the zoom, was tried and found too heavy. Inside's circuit and the parts' entries
keep their 2 px wires, sized for their beads.

**D-088 — 2026-10-03 — Hints' rows are all speech bubbles; under the shadow's picture, "Go to Tools or Parts", with their icons. Amends D-078.**
Hints' three rows had three icons: a speech bubble for the idea, a puzzle piece for the parts,
which is Parts' own icon in the bar, and a ghost for the shadow. Each is now a speech bubble: a
hint, whatever it says. The bar's Hints keeps its life ring. Under the shadow's picture, in the
editor and in the run, a line says where to build it: "Go to Tools or Parts", each drawer's
icon before its name, as the bar draws it; in the run, the editor is a tab away. The picture
gives up a line's room to it where room is short, in the run above the objectives, where it
stays at least 140 px across.

**D-089 — 2026-10-03 — The run's Inside is called Diagnostic, with the editor's stethoscope, and opens by D. Amends D-069.**
The run's drawer that shows the swimmer's wiring live, its beads and meters, was Inside, a
magnifying glass, opened by I. The editor's drawer where the board is tested is Diagnostic, a
stethoscope, opened by D (D-069). Both show the board at work, so they now share the name, the
icon and the key: in the run, Diagnostic, the stethoscope, D, its initial; I is free again. As
D-069 allows, the key means the same drawer's place in each environment, never two things in
one. In the code the run's drawer stays `Drawer.INSIDE`, the name the tutorials' data uses; the
earlier decisions and the walkthrough keep calling it Inside.

**D-090 — 2026-10-03 — A drag from the part Wire is lit for draws its wire; a drag from any other part moves it. Amends D-068, D-072, D-085.**
A click on a part, or a part just placed, focuses it and lights Wire in its Wheel: the next part
clicked is wired to it. Yet a drag from it moved it, since only Wire chosen, by W or the Wheel's
icon, made a drag draw a wire (D-072); the Wheel showed one thing and the drag did another. Now a
drag from the part Wire is lit for draws its wire, as Wire chosen does, either way round (D-026),
released on the part to wire to; released on an empty cell it ends the attempt, as D-072 has it,
and off the body it does nothing: the lit part is not deleted by a drag, nor darkened as if.
A drag from any other part still moves that part, and dropped off the body deletes it (D-085);
the lit part moves by M or the Wheel's Move, or by a drag once the focus is elsewhere. Clicks do
not change: a click that cannot wire focuses the cell or the part it falls on, so lighting Wire
costs nothing. The status line says "Click or drag to another part to wire it; M moves it."

**D-091 — 2026-10-03 — A part placed or moved with the mouse wires either way round, as a part clicked; only the part just wired to wires on only forward. Amends D-068.**
D-068 had a part focused without a click on it, placed, moved or just wired to, wire on only
along the signal: a click on a part it could not feed only focused that part. So an eye just
placed was wired to the thruster clicked next, but a thruster just placed, Wire lit for it, was
not wired to the eye clicked next: the eye was only focused. Now a part placed, from Parts or the
Wheel, or moved, by a drag or Move, wires either way round, as a part clicked does (D-026): a
click, or a drag (D-090), on any part their kinds let it be wired to makes the wire. Only the part
the focus goes on to after a wire keeps D-068's rule, so that a chain goes on by clicks (eye, sum,
thruster) and, from a thruster just wired to, a click on the other eye focuses that eye to start
its own wire. A click that cannot wire still focuses what it falls on.

**D-092 — 2026-10-04 — Files lists every level's wins, each level's under its title, a group that folds as Parts' do; a win of another level goes on the open level's board if it fits. Amends D-059.**
Files listed only the open level's wins, so a vehicle won in one level could not be carried into
the next, though the levels build on each other: Aggression is Fear with its wires crossed. Now
it lists this session's wins of every level of the chapter: the open level's first, then the
others in the chapter's order, each under its number and title (`1.2 Aggression`), which folds
and unfolds as Parts' groups do; a level with no win has no group, and the sandbox, which keeps
none, has none. Each level keeps at most ten, as before, and the list scrolls, by the mouse
wheel or its scroll bar, as Parts' does. A click on a win puts
its board on the open level's (`Board.adopt`) when the level hands out its parts, as many as it
has; the stock left is counted again from what the level hands out. Otherwise nothing changes
and the status line says why: "this level hands out no sums". The board left goes to Undo, as
before. A row is lit while its parts and wires are those on the grid, whatever the stock. With
wins listed, the note under them goes into each win's info box.

**D-093 — 2026-10-04 — Save and Load leave Files; saving and a board as text go together to ideas.md, out of the jam. Amends D-027, D-053, D-059; todo §9 goes.**
Save and Load sat greyed at Files' foot since D-027, a promise the jam will not keep, and took
room from the wins listed above them (D-092). They go: Files lists the wins down to its foot.
Saving and a board as text (todo §9: a board packed into a short line of letters or words, with
check symbols) are one piece of work, the same format of D-024 written to a file or to a line;
they leave the todo for `ideas.md`, as one entry, and Save and Load come back with it. The
scope lock's Out line says so. F4 still prints a board (D-024).

**D-094 — 2026-10-04 — The tutorial's cards and the info boxes hold paragraphs, wrapped to the box, ragged right; a part's In and Out are grey. Amends D-036, D-039.**
Their texts were lines broken by hand, so an edit left lines of every length. Now a card's "say"
in a level's file is a list of paragraphs, each starting on a new line, and the card wraps them
to 48 characters of Plex Mono, its width (`Step.lines`); the box's height follows the lines it
makes. An info box wraps each of its paragraphs to 46 characters, the width of a part's circuit
under them (D-082): a part's text is one paragraph (`parts.WHAT`), then In and Out, each its
own, drawn in the dim grey that tells them from what the part does. Full justification was
tried and set aside: in a mono font it opens uneven gaps in a line short of words. The (i) on
every row is 16 px, from 12.

**D-095 — 2026-10-04 — A drawer's icon that a tutorial step shows keeps its colour; its sparks say it. Amends D-080.**
D-080 drew every target of a step in accent 1, with sparks drifting out of its edge. On a small
icon of the bar, as Hints' on Fear's last card, the sparks already single it out, and the accent
on the icon itself was one signal too many. A drawer's icon now keeps its colour, dim, or white
while its drawer is open; its sparks stay. Areas, drawers' titles, the run's parts and the tabs
keep the accent as before.

**D-096 — 2026-10-04 — Every drawer of rows scrolls when its rows do not fit, in the editor and in the run. Amends D-069, D-092.**
Only Parts and Files scrolled, and only in the editor. In the run, where the objectives take the
drawer's foot (D-065), Navigator already ran 16 px under them on a level with two objectives,
and Chapters will with the seven levels of D-097. Now Tools, Navigator, Hints, Settings and
Chapters lay out their rows from the drawer's top and, if they run below its floor, scroll: the
floor is 8 px over the objectives in the run, the drawer's foot in the editor, and the Wheel's
title in Tools, as in Parts. They show within a list area, clipped, with the scroll bar of D-069
while they do not fit; out of it, a row neither shows nor answers a click. The objectives and the
Wheel stay put. The scrolling itself, the wheel, the bar held and dragged, each drawer's own
scroll for the session, moves from the editor's scene into `Frame`, so the run has it too.
Hints' shadow still shrinks to fit, but no smaller than 140 px; past that the drawer scrolls.
Diagnostic, Inside and Score are drawings fitted to their room, not rows, and do not scroll.
Clips now nest (`clipped`), so a picture clipped to its frame inside a scrolled drawer, Navigator's
overview, stays clipped to the drawer as well. Checked in the web build: the wheel scrolls Love's
Navigator in the run.

**D-097 — 2026-10-04 — The chapter is seven levels, one new idea each: Fear, Aggression, Love, Orbit, Shadows, Greed, Patience. LEVEL 1.4 is Orbit, the brief's level 3, won by circling the light twice; a new objective counts the turns. Changes the scope lock's level count in `CLAUDE.md`; Shadows moves to 1.5.**
The brief's third tutorial puts ÷2 on one side for an orbit. In this physics it does not orbit:
crossed with ÷2 on one wire, the swimmer still comes to the light and parks on it, as plain
aggression does. A circuit was searched for by simulation, with boards built through `Board`
and every result checked from seven perturbed starts (±0.1 u, ±0.2 u, ±2°, 1e-9): an orbit needs
one side pushed all the time and the light pushing the other. The orbiter is four parts: an eye
at the back left looking ahead drives the left thruster, a Source the right one; the Source turns
the swimmer left until the light, ahead of the eye's face, straightens it, and it settles on a
circle 5.2 u from a light of power 8. Orbit: that light at (25, 19), the swimmer 10 u from it on
a tangent, (25, 9) heading E; Circle the light twice and Don't touch it, in 30 s; two eyes, a
Source, two Halves, two thrusters handed out. The orbiter wins in 18.4 s; Shadows' board (crossed
plus a Source on both, five parts) in 25.8 s; the brief's ÷2, eyes ahead, crossed, one halved,
with a Source on one side (six parts), in 17.4 s, the fastest. Aggression and a halved drive
touch the light and lose; a bare drive, fear with a drive, a blind circler run out of time.
Its hints: "One side pushes always.", and the orbiter as the shadow. Its word is MOON.
`CircleLight` (kind "circle light", `turns`) keeps for each swimmer and light the angle the light
last saw it at and the angle swept since t = 0, each tick's change taken the short way round,
so going back unwinds it; kept once full. It counts whole turns, at most `turns`, "1 of 2"; its
row has the rotate icon and says "Go round the light twice, either way." A swimmer circling
beside the light, not round it, counts nothing.
The chapter, from the same search, each level adding one idea to the last and its model board
growing by at most two parts (4, 4, 4, 4, 5, 6, 6): Orbit after Love, the four Braitenberg
levels first; then Shadows (a drive, D-032); Greed, 1.6, two lights where plain aggression parks
on the bright one and Shadows' drive overshoots, won by a Double on each crossed wire; Patience,
1.7, the real level, three lights and two obstacles from a start in the dark, won by halving the
drive. Their layouts and pins come with them (D-098). The existing words stay with their levels.

**D-098 — 2026-10-04 — LEVEL 1.6 is Greed, two lights won by doubling the eyes; LEVEL 1.7 is Patience, the real level, three lights and two obstacles won by halving the drive. Only the first five levels have hints. Amends D-078; todo §2 is done.**
Both come from D-097's search, each checked from seven perturbed starts. Greed: a bright light
(power 6) 10 u ahead of the start, (18, 19), and a dim one (power 3) off to the side, (13, 10.5);
no obstacle; touch both in 20 s. Plain aggression reaches the bright light and stays on it,
where both eyes read full; Shadows' drive carries the swimmer past the dim one. A Double on each
crossed wire, six parts, touches both in 9.8 s: steering twice as hard, it leaves the bright light
and turns back for the dim one. A halved drive and the orbiter do not win; doubled eyes with a
drive, halved or not, win from some starts only. Its word is GOLD.
Patience, the real level: three lights of power 4 in a loop, (23, 18.5), (21, 8.5), (14.5, 18), the
last just behind the obstacle the swimmer starts behind, as in Shadows, (12, 19) r 1.5, start
(8, 18.4) heading E; a second obstacle, (18.5, 11) r 1.5, between the second light and the third;
touch all three in 20 s. From the start no eye sees a light, so nothing without a drive moves
(Shadows' lesson); with Shadows' full drive, doubled eyes or not, the swimmer flies past the
lights. Halving the drive, a Source through a Halve on both thrusters with crossed eyes, six parts,
touches all three in 10.9 s; doubling the eyes too, eight parts, in 10.3 s: the level's Pareto
front. Its word is SNAIL and opens nothing yet.
Hints: Greed and Patience have none; the drawer says "No hints here.", as it now says in the
sandbox. A player who reaches them has the drive, the gain and the asymmetry from the five before,
and the real level is the one the brief's success criterion asks strangers to finish on their
own. `test_hints.py` checks that the first five have hints and the rest none;
`test_determinism.py` pins both winners and the ways to fail.

**D-099 — 2026-10-04 — Under WASM `eye_rates` takes 0.07 ms a tick for the jam, about twice its native time; the names show no clash so far; the click lost after a key in headless Chrome no longer happens. Todo §6.**
Measured in headless Chrome on the physicist's Mac, from a throwaway copy of the game whose
`main.py` times the calls at startup (pygbag's CPython 3.12, numpy 2.0.2), against the same file
run natively (CPython 3.11, numpy 2.4): `eye_rates` for the jam, one swimmer and two eyes in
Shadows, 0.067 ms (0.036 natively); for 100 swimmers, 4 lights and 20 obstacles, D-019's case,
0.92 ms (0.50); the light map, 80 × 76 cells, 0.62 ms (0.32); a whole `world.step` in Patience,
0.25 ms (0.13). WASM is about 1.9 times slower, and the two ticks of a frame cost 0.5 ms of its
16.7 ms: the physics leaves the frame to the drawing.
The names (D-006): TMview finds no trade mark whose name contains NEKTOIDS, or even NEKTO; for
CY-3LO its loose search returns 403 marks that share fragments (CYCLO 3, C3 CYCLONIC), none close.
A web search finds only our own repository for either. itch.io's search sits behind a bot check
that a script cannot pass, so it stays in the todo, to do by hand; none of this is legal
clearance.
The lost click (todo §6, seen 2026-10-02 on Fear's first drag step, which D-079 removed): in
headless Chrome, two Enter presses then one click on Skip close the tutorial, and a drawer's key
then one click on Chapters opens it; typed passkeys followed by a click on a row work too.
Clicks seemed lost once more while this was checked, because the script measured the canvas
before pygbag resized it (640 × 640 while loading, 1280 × 853 once started); measured after the
start, every click lands. The item goes.

**D-100 — 2026-10-04 — The names stand: itch.io returns nothing for nektoid* or Cy-3LO. Completes D-099's search for D-006; todo §6 is done.**
Searched by hand by the physicist, itch.io's search being closed to scripts. With TMview and the
web search of D-099, nothing found clashes with Nektoids or Cy-3LO. A search is not legal
clearance; nothing here needs more for a free jam build.

**D-101 — 2026-10-04 — The run opens at 16 px/u, the swimmer's radius on screen, centred on what matters; the overview shows it 1.5 times over and at least a zoom click past the opening. Amends D-066.**
The run opened on `frame()`, the points round their mean with 3 u to spare, then kept inside the
overview, 1.5 times what matters. On Greed and Patience the frame was larger than the overview,
so they opened at the farthest zoom, the zoom bar at its end: Greed at 32 px/u, twice as close
as Fear's 16, with no room to zoom out. Fear and Orbit opened well, at 15.8 and 16.1 px/u. Now
every level opens at 16 px/u, the swimmer 32 px across, centred on the middle of what matters,
or farther out if what matters would not show whole, which no level needs. The overview, and
the farthest zoom, is what matters 1.5 times over, as before, and at least what the opening
shows, one zoom click (1.25) out: every level's farthest is now 12.8 px/u. Fear's overview is
what it was, within 2 %; Orbit's shows 1.2 times more. A first try, the run opening on twice
what matters and the overview 2.5 times, made Fear's swimmer 20 px across and left Greed at
24 px/u. Centre keeps `frame()`, round the swimmer and the lights; the editor is unchanged.

**D-102 — 2026-10-04 — The sandbox hands out every part without limit, on a zone one ring wider: 37 cells. The scope lock's two eyes and two thrusters are the levels'. The editor opens a zone too tall for its default size smaller.**
The sandbox has no objective and scores nothing (D-046), so nothing in it needs the levels'
counts; it is where to try what the levels do not ask. Its stock is null, unlimited, for every
part, eyes, thrusters and the Source included, and its zone is `hex_disc(3)`, 37 cells instead
of 19. The levels keep theirs; more eyes in a level stays in `ideas.md`. The body is still a
sphere of radius 1 u (D-045): the zone's outermost cells lie on its rim (D-018), so the old
rim's cells sit at about two thirds of the radius, and placing is finer. The code was already
written for any number of eyes and thrusters: four of each, crossed, run at 0.43 ms a frame
natively. At the default 40 px a hex, the zone's top row lay under the action atop the board;
the editor now opens a zone at the largest size, 40 px at most, that keeps its hexes clear of
that action and of the board's sides (`layout.opening_view`): the sandbox at 34 px, every level
at 40 as before.

**D-103 — 2026-10-04 — Aggression comes with one eye wired to its own side's thruster; its tutorial opens in the editor, Parts open, and two cards take the player to Diagnostic to try it. Amends D-069, D-070 and D-079.**
Nothing taught Diagnostic since D-079 took Aggression's tutorial away (D-070 had left it for
later). Aggression's board now starts with two of its parts on the cells of its hint's shadow,
unlocked: the eye at the back left looking NE, wired to the thruster at the front left, facing
E. Uncrossed, it is half of Fear's swimmer, and turns from a light on its left; the level asks
the player to cross it. Parts shows one eye and one thruster left. A tutorial may name the
editor's drawer it starts in, `starts_in`: while its first card is still to come, the level's
card gives way to the editor with that drawer open, not to the run. D-069 stands for every
other level; D-070 had dropped a tutorial's start screen. Aggression's starts in Parts. Its
first card names the board and lights the stethoscope, waiting for Diagnostic; the second
lights nothing, its box at the foot of the main screen: the main screen shows the board, the
map the swimmer and the light, to drag and turn to see what it does. Then Close, and the
player tries it with no card in the way, the drawer's own note under the map. The tutorial builds
nothing, so D-079's objection, a tutorial repeating Hint 3, does not apply. A card's box keeps
clear of the parts on the editor's board, as it does of its targets (D-048). A hint's shadow is
built on `Level.blank_board()`, the level's zone and stock with none of its parts, so its
picture is what it was. Hints stay locked until the tutorial ends or is skipped (D-078).

**D-104 — 2026-10-04 — Touch and the activity bar's last two items leave the todo for ideas.md; the todo keeps only the shipping. Amends D-051; todo §7 and §8 go.**
The jam ships without them. Touch (§7, from Camille's notes) has to be tried on a phone before
anything can be decided, and none of its questions has an answer yet. Of the activity bar (§8,
D-051), the bar, its drawers and its environments are built (D-053 to D-069); what is left is
Sound and Music in Settings, which wait for sound, and Parts as the encyclopedia opening in the
drawer, which is polish. Each goes to `ideas.md` as one entry, its questions kept, saying where it
came from. The todo keeps §5, the shipping. Camille's views on the jam build go to the todo if
they must be fixed before it is uploaded, to `ideas.md` otherwise.

**D-105 — 2026-10-04 — After the jam, in stages: foundations, a level maker, memory, flows, actions other than moving. Each opens with a decision that sets its scope in place of the scope lock, once the jam build is out.**
The physicist named four directions for after the jam: flows and flow sensing, a level maker,
actions other than moving (light emission), memory (tanks, switches, diodes). `ideas.md` now
opens with them in order, each idea filed under its stage. Foundations come first, since every
stage adds parts or levels: one table of part kinds, sensors in general, a level format with a
version, saving and a board as text. The level maker next: Camille can make levels without
programming (D-041), and every later stage needs levels. Memory then, which changes only
`graph/`: tanks, T dh/dt = in − h with T ≈ 4 s, the lag of D-017 with its own τ; valves,
max(0, a − b), the physicist's "diode", since a wire is one-way already (D-016); loops in the
editor; lights that change in time, for levels the present reading cannot win. Flows fourth, the
largest change to `sim/`, whose levels want tanks: analytic streams and vortices as items, a
sphere carried by Faxén's laws, a sensor of the flow relative to the body. Actions last: with
one swimmer a lamp needs something that reads it, photo-targets or bodies with a fixed wiring,
the step to Collectives.
Shipping and its feedback come before all of it and may reorder it. Until the jam build is out,
the scope lock in `CLAUDE.md` and the `scope-check` skill stand as they are; then the first
stage's decision replaces the lock with that stage's scope.

**D-106 — 2026-10-04 — The jam build ships as v1.0: a GitHub release on `main` with its web build, and an itch.io page, cy-3lo.itch.io/nektoids. Applies D-105.**
Camille's review left nothing to fix before the upload. `DEV_VIEW` is off, so F1 to F4 do nothing;
`main` at the merge of #43 is tagged v1.0, and the release carries `web.zip`, the HTML5 build
uploaded to itch.io. The physicist checked the itch.io page in Chrome and in Safari, where the keys,
the fonts and the canvas had never been tried. The todo's §5 goes. As D-105 has it, the jam's scope
lock now gives way to stage 0's (D-200): `stage/0-foundations` comes to `main` in one PR.

**D-200 — 2026-10-04 — Stage 0, Foundations, is built on `stage/0-foundations`, and its scope replaces the jam's scope lock there. Its decisions are numbered from D-200. Applies D-105.**
The jam build ships from `main`, with what Camille's review finds to fix, so Foundations is
built beside it. Each item is a `feat/…` branch whose PR goes into the stage, and the stage goes
into `main` in one PR once the build is uploaded; until then the lock stands on `main`, as D-105
asks. In: the game as the jam shipped it, and the five items of `ideas.md` §0, which move to the
todo's §10 in the order they will be built: the objectives in one list, a level format with a
version, one table of part kinds, sensors in general, saving and a board as text. Out: all else
in `ideas.md`; nothing new for the player but Save and Load, no new part, sense, item, level or
objective. `CLAUDE.md`'s scope section says so, and `/scope-check` reads it. Decisions taken on
`main` meanwhile keep D-106 on and the stage's start at D-200, so no number is taken twice; a
stage built beside another takes the next hundred.

**D-201 — 2026-10-04 — A level file carries its format's version, 1; the loader refuses a file without it, of another version, or with a key it does not know.**
A file from another game, or a key mistyped by hand, was read as far as it went: an unknown key
was dropped, and a mistyped objective setting stopped the load with a TypeError. `Level.to_dict`
now writes `"version": 1` first. `from_dict` refuses another version, and any key it does not
know in the level, its start, an item or an objective, with a ValueError that names it. A change
to any part of the format, the board, hints and tutorial included, raises the version, and
`from_dict` then upgrades the older version instead of refusing it. The keys inside the board,
hints and tutorial are not checked yet; saved boards get a version of their own with saving
(todo §10).

**D-202 — 2026-10-04 — One table of part kinds, `SPEC` in `graph/kinds.py`; each kind's dynamics is a law, a state equation and an output (`graph/laws.py`). Amends D-017.**
A kind's facts were spread over a dozen tables and if-chains in `graph/` and `editor/`, and a
kind left out of `GAIN` was taken for a sensor and held at 0. Each kind is now one entry:
category, letter, name, info text, law, facing, wire limits; `tests/test_kinds.py` checks every
entry whole, and the old tables are views of it. A kind's dynamics is no longer a gain and input
signs, which spell only g·|Σ ±x|, but a law: a state equation dy/dt = f(x, y), x the rates on
its wires in, and an output o = g(y), which its wires carry, shared. The output depends on the
state alone, so a tick reads every output, then steps every state, and a loop needs no solve.
Each law owns its explicit step, so its arithmetic is fixed, and says the longest tick it is
stable for. Every jam part relaxes, τ dy/dt = F(x) − y, o = y, with D-017's τ and F a scaled sum
or |a − b|: the run is bit-identical. A tank, T dh/dt = in − h, is the same law with τ = 4 s; a
part whose output is not its state, a bucket with a hole, takes a law of its own; a part with
two states is a decision. Wires come into a node sorted by the part that feeds them, so a valve's
control needs ports first (stage 2). A tick costs about 1.8 times what it did, a few numpy calls
per law; laws of one type can step together if a later stage needs it. Where a sensor's rate
comes from and what an actuator does to the world stay outside the law: the todo's item on
senses and actions.

**D-203 — 2026-10-04 — A sensor's rate comes from its kind's sense, an actuator's effect from its kind's action, each named in the table of kinds and mapped to its function in `sim/world.py`.**
`world.step` read the eyes and pushed with the thrusters by name, and the Sources' rate was set in
`dynamics.given_rates`: a sensor kind wired in nowhere would have read 0, an actuator would have
done nothing, with no error. The table now names an Eye's sense, light, a Source's, steady, and a
Thruster's action, push; `SENSES` and `ACTIONS` in `world.py` map each name to its function, with
the signatures `eye_rates` and `thrust` already had. A tick takes every sensor's reading by its
sense (`readings`) and sums every actuator's action (`push`; one action alone is not added to a
zero), so the run is bit-identical, and the drawn motion (`marks.motion`) is the same sum. A test
checks that every sensor has a sense and every actuator an action the simulation knows. Flow
sensing (stage 3) is then a sense, a lamp (stage 4) an action. The editor's views that read the
eyes alone, the arena's eye columns after a drag and its polar plot, Diagnostic's probe, the
schematic, the encyclopedia's demos and the intake specks, stay so until a second sense needs
them. `dynamics.step` keeps taking the eyes and sources, for those views and the tests, around
`step_given`, which takes every sensor's rate.

**D-204 — 2026-10-04 — A saved board comes back with every wire on its saved path, checked against the board's rules; a wire saved without one is routed. Amends D-024.**
`Board.from_dict` drew every wire again, so a wire left on a detour, after a Move, a Delete or a
part put on a wire, came back on another route, and a board loaded was not the board saved. D-024
left exact paths for when saving arrives; saving is stage 0's last item. `Board.connect` takes a
path now: the wire is checked by the rules as before (ends, kinds, loops, counts), and its path
must join its ends a step at a time, through free cells of the zone, by edges no other wire takes.
`from_dict` lays each wire on its path in the order they were drawn, and refuses data no board
could hold, naming why. A wire saved without a path, which no file has, is routed as before. The
board as text (D-205) needs it too: a path the router would not take is written step by step.

**D-205 — 2026-10-04 — A board as text holds only the decisions the rules leave open, as one integer in a mixed radix, written in base 59 with four check characters per block; it names no level, and its version is hidden in the checks.**
A board is a diagram on a body: its zone, a disc; its parts in id order, each a cell, a kind and
a facing if it turns; its wires in drawing order, each its ends and its path. No level: loading a
text into one is `Board.adopt` (D-092), which says what the level does not hand out, as for a win
of another level. Replayed on a bare body, each decision is a digit whose base is the number of
choices the rules allow there, so a forced choice costs nothing; a path costs one binary digit
when it is the router's, drawn after the wires before it, and its steps otherwise. The id order
is kept, since a Thruster sums its wires in its nodes' order and the run must be bit-identical.
A kind is one of 32 codes, `Kind`'s order, which only grows at its end: a text written today
holds once tanks and valves exist. A zone is one of 16 codes, discs of radius 0 to 7 and room for
other shapes. The integer is written in base 59, the alphanumerics without I, l and O, which are
read as 1, 1 and 0; no symbol, since symbols break a double-click and chat apps read * and _ as
Markdown. It goes in blocks of 53 characters, each followed by four check characters of a
Reed-Solomon code over the integers mod 59, a field since 59 is prime. The format's version is a
hidden first symbol of every block, never written: a text of another version fails its checks.
With distance 5, one wrong character is put right and two are refused, never read as another
board. Fear's model board is `2Svbskor23U3aec`, 15 characters; Patience's, 26; F4's JSON for
them, about 500 and 1,000. A change to the format, to a part's rules or to the router raises the
version. Save and Load in Files, and the clipboard, come next.

**D-206 — 2026-10-04 — Save/Load at Files' foot: Copy a board puts its text on the clipboard, and Paste a board, a field, takes a text and puts its board on the level. On the web the clipboard goes through the page. Amends D-093 and `.claude/rules/web.md`.**
Copy a board, a row, puts the board's text (D-205) on the clipboard and in the status line, to
copy by hand where the clipboard is out of reach. Under it, Paste a board is a field drawn as the
passkey's (D-075): a click opens it, Cmd/Ctrl+V pastes, a board's characters may be typed, Enter loads, Esc
or a click elsewhere gives up. The text's board goes on the level by `Board.adopt`, as a win of
another level does (D-092), the level's locked parts being the text's parts on their cells;
otherwise the status line says why ("this level hands out no doubles"), and a mistyped
character put right is said. Undo takes a load back (D-027). On the web, pygame has no clipboard
(pygbag ships no `pygame.scrap`), and Safari 26.6 sends no copy or paste event to a page where
nothing is selected and refuses `navigator.clipboard.readText`. So a few lines of JavaScript, put
in once at startup, write with `navigator.clipboard.writeText` on Copy's click, and give Paste a
text field of the page's own, invisible. It is focused once the click is over, or Safari takes
the focus back, and its keys are stopped before the game's listeners, which would cancel Cmd+V;
the editor reads it once a frame. Tried in Chrome and in Safari 26.6, 2026-10-04; Firefox and
phones are not. Natively, `pygame.scrap`. Only `editor/clipboard.py` talks to the page.

**D-300 — 2026-10-04 — Stage 1, a level maker, opens: built on `stage/1-level-maker`, its scope replaces stage 0's, and its decisions are numbered from D-300. Applies D-105.**
Stage 0 is on `main` (#46), and the jam build is out as v1.0 (D-106). Stage 1 is built as stage
0 was (D-200): each item a `feat/…` branch whose PR goes into the stage, and the stage into
`main` in one PR, so that `main` can still ship a v1.x meanwhile. Unlike stage 0's, this opening
goes on `main` itself, which is no longer the jam build, so the plan shows there. In: the game as
it is on `main`, and the items of `ideas.md` §1, which move to the todo's §11 as they were
written: a level editor, for us and Camille first (D-041), then for players, which places the
plane's lights, obstacles and start on a lattice, sets the board's zone, stock and locked parts,
the objectives and the time allowed, and shares a level as text only once its maker has won it;
"Two lights, four obstacles" brought back; sharing levels and solutions, with no server. Out:
all else in `ideas.md`; no new part, sense or item. Each item is planned when it starts, and its
own decisions, a level's text first among them, are taken then, as the board's was (D-205).

**D-301 — 2026-10-05 — The level maker is the Maker, a third tab on the sandbox alone: the sandbox's level is the one made, and the Editor and the Run try it. Its drawers: Objects, Goals, Brief, Files, Navigator. Values sit on a lattice the plane shows as a grid; sliders and typed numbers set them; Save copies the level's JSON.**
The physicist asked for a tab of its own, with drawers for the objects, the objectives with
sliders and their values, the level's text and a save, and for the Editor and the Run to go on
working on the level being made, as Mario Maker plays a course from where it is built. The
sandbox is already a level with no goal and every part handed out (D-102), so it becomes the
place where a level is made rather than a second place beside it: its tabs are Run, Editor,
Maker; a level of the chapter keeps two. The Maker's drawers are Objects (O): the lights, the
obstacles and the swimmer's start; Goals (G): the objectives with their settings, and the time
allowed; Brief (B): the title and the spec; Files (F): Copy level, Paste a level, and a level to
start from; Navigator (N): the run's, with the overview, the zoom and the rays. Space and the
switch run the level. Values sit on the todo's lattice: positions every 0.5 u, powers whole,
headings every 15°; each setting declares its range and step. The plane shows that lattice, a
dot every 0.5 u and a line every 5 u with its coordinate at the edge, in the Maker only; the
dots go to whole u, then away, as the view zooms out, before they crowd. Sliders and typed
numbers are the maker's, not the player's graph: invariant 4 binds only the graph. Save copies
the level's JSON as `to_json` writes it, the shipped files' layout, to the clipboard, which
D-206 already reaches in Chrome and Safari; no file is written, so `web.md` stands. The level
made lasts the session, as wins do; nothing is stored (D-075). Ranges proposed, to be settled
when Goals is built: a light's power 1 to 16; an obstacle's radius 0.5 to 5 by 0.5; a ring's
radius 2 to 30 by 0.5; seconds 1 to 60; turns 1 to 10; the time allowed 5 to 300 s by 5. The
first step, the tab itself, shows the plane over its grid, read only; each drawer comes with its
own pull request into `stage/1-level-maker`.

**D-302 — 2026-10-05 — The Maker's Objects is a copy of Parts: the objects as rows, undo and redo, the Wheel at its foot round what is focused on the plane. A click focuses, a drag moves; the Wheel offers a light and an obstacle on an empty point, less, move, delete and more on an item, the turns and Move on the swimmer. Applies D-301; amends D-068 for the Maker.**
The physicist asked for Objects to work as Parts does in the editor, the Wheel offering what may
be placed and what may be done, and asked whether moving or editing should come first. Both
come by gesture, as on the board (D-090): a click on an object focuses it, and its Wheel shows
what can be done to it; a drag moves it, on the lattice, one step for undo. A click on the open
plane focuses its nearest lattice point, and the Wheel offers a light (1) and an obstacle (2)
there, as an empty cell offers the parts; a drag there moves the view. Round a light, Dimmer,
Move, Delete, Brighter; round an obstacle, Smaller, Move, Delete, Bigger: the less and the more
either side of the gap, where a part's turns sit, on < and >, since + and - zoom. Round the
swimmer, Turn left, Move, Turn right (L, R): it is never placed nor deleted. Move in hand, a
click on the plane or an arrow, 0.5 u, moves the focus. The mouse wheel on an object makes it
more or less, or turns the swimmer. Objects' rows are Light, Obstacle and Swimmer, each with how
many are on the plane: a click on Light or Obstacle puts it in hand for the next click on the
plane, a drag puts it where it is let go; Swimmer focuses it. Under them, Undo and Redo (Ctrl+Z,
Ctrl+Y), over whole levels. A new light has power 4, a new obstacle radius 1 u. A change the
level cannot hold is refused, its reason in the status line: a light touching an obstacle, the
arena's own refusal, or the swimmer starting inside one. A value off the lattice in a shipped
level stays until it is changed: the sandbox's heading of 20°, turned, becomes 30°. Each change
is a new `Level` (`levels/making.py`), handed to the router, the editor's caption and Run
preview, and the next run.

**D-303 — 2026-10-05 — F1, F2 and F3 are the tabs, Run, Editor and the Maker, in every environment, as a click on the tab. Space and Esc stay; the developer's F1 to F4 move to F5 to F8. Amends D-069; applies D-301.**
With three tabs, Space (to the run) and Esc (from the run to the editor) no longer reach every
tab, and Esc in the Maker puts down what is in hand. The physicist asked for one switch between
the three: each tab has its key, in the tabs' order, the same everywhere, and its tooltip says
it. F3 on a level of the chapter, which has no Maker, says the Maker is Free play's, in
Chapters. A tutorial's step that holds a tab holds its key too. Space and Esc keep what they did,
so the tutorials' words hold. The developer's keys, behind `DEV_VIEW`, move four on: F5 the
editor, F6 the circuit view, F7 the arena view, F8 the board's JSON. In the browser, F1 is help
and F3 is find: the page stops both, in `clipboard.py`'s script, and the game still gets them;
tried in headless Chrome. On a Mac's own keyboard F1 to F3 work the screen and the windows
unless fn is held, or the function keys are set as standard ones in the system's settings.

**D-304 — 2026-10-05 — Tab goes round the tabs, Shift+Tab back; Esc opens Chapters once it has nothing left to back out of. The hints show Tab for the tabs; F1 to F3 work and are not shown. Amends D-069, D-303.**
The physicist found F1 to F3 awkward, a Mac's keyboard wanting fn for them, and asked for Tab to
go round the tabs and Esc to open the levels. Tab now goes to the next tab, Run, Editor, then the
Maker on the sandbox, round to the first, Shift+Tab to the one before; on a level, Tab goes from
the run to the editor and back. Esc keeps what it backs out of, in the editor the hand, Swap,
Delete, a part in hand or a wire under way, the Wheel opened by keys, the focus, and in the Maker
what is in hand, Move, the focus; with nothing left it opens Chapters, or folds it, as Esc opens a
game's menu. A right click backs out only. In the run, where Esc took the player to the editor,
it opens Chapters at once, and Tab takes the player to the editor; the end banner's Edit says
Tab. The tabs' tooltips, the switch's and Chapters' name Tab, Shift+Tab and Esc; F1, F2 and F3
still go to Run, Editor and the Maker, unnamed, for whoever knows them. Space still runs from
the editor and the Maker, and plays in the run. The developer's arena (F7) keeps Tab for its
levels and Esc for the editor.

**D-305 — 2026-10-05 — Brief, the Maker's third drawer, holds the level's title and its spec, each in a field of text that a click opens with what the level says; Enter or a click elsewhere keeps what is typed, Esc gives it up. Every field of text is one `TextField`, with a caret. Applies D-301; amends D-206.**
The plan's Brief: the level's words, as Objects is its plane. Its two fields sit under their
labels, the title a row high, the spec six lines high and wrapped, enough for its longest. A
field opens once the click on it is over, as Paste a board does for Safari (D-206), holding the
level's title or spec with the caret after it; the arrows, Home and End move the caret natively,
and on the web the page's own field moves it and says where it is, so the bar drawn is where the
next character goes. Enter or a click anywhere else keeps the text, its spaces squeezed, one
step for undo; Esc leaves the level as it was. A title or a spec with nothing in it is refused,
"a level needs a title", "say what the level asks"; a title is at most 40 characters, a spec
120. The caption over the main screen, Chapters' row, the level's card and the next run follow.
Paste a board's field is the same class, taking only a board's characters (D-206), and it, the
passkey's and the title's are drawn by one function, `draw_field`: the caret is now a bar in the
accent, and a board's text shows its spaces. In the page's field Tab no longer takes the focus
away. The run's status line drops F for fast forward, which its button's tooltip names, so that
Tab and Esc fit (D-304).

**D-306 — 2026-10-05 — Marks, a third kind of item: a zone on the plane, a circle the swimmer neither sees nor touches, which only the objectives read. Placed, moved, sized and deleted in Objects; drawn as a grey empty circle with a cross on its centre, in every view. The level format is version 2; version 1 is read as it is. Widens D-300's "no new item" for marks alone.**
The physicist's grammar for objectives (reach, leave, stay, circle; all, one, none; lights,
obstacles, marks) needs zones to aim at, and Fear's and Love's rings are zones already, round
their one light. A mark is `{"kind": "mark", "at": [x, y], "radius": r}`, radius 0.5 to 30 u
by 0.5, 3 u when placed. `Level.arena` holds the lights and the obstacles only, as before, so the
simulation and every shipped run are what they were; `Level.marks` holds the zones. In Objects
a mark is a row and an empty point's third offer (3), its Wheel Smaller, Move, Delete, Bigger,
as an obstacle's. A mark is grabbed by its rim or its centre, within 6 px: a click inside a zone
finds the point there, so a light may still be put inside one; a light or an obstacle over a
mark is found first. Marks are drawn under the lights and the obstacles, in the Maker, the run,
Diagnostic's map and the overviews, and the run and the Maker frame them whole. Adding a kind of
item changes the format (D-201): files are version 2, and version 1, which has no marks, is
upgraded as it is; a newer version is refused. Every shipped file is rewritten, its version
line alone changing. `CLAUDE.md`'s scope now says so. Until the next decision makes objectives
sentences, no objective reads a mark. Objects' Undo and Redo lose their section title, so its
four rows and theirs fit over the Wheel.

**D-307 — 2026-10-05 — An objective is a sentence: reach, leave, stay or circle; all, one or none; lights, obstacles or marks; with a stay's seconds or a circle's turns. "None" makes it a ban, lost the moment it happens. Version 1's five objectives are five sentences and run as they did, to the tick and the bit. The level format is version 3; version 2's rings become marks on its lights. Amends D-038, D-040, D-097; applies D-306.**
The physicist proposed objectives that can be "programmed": avoid, reach or approach all, one or
none of the lights, marks or obstacles. With marks as zones (D-306), "approach" is to reach a
mark round the thing, and "avoid" is to reach none, so four verbs carry it: reach (touch a light
or an obstacle, at 1.05 times touching distance, D-043; come into a mark, the swimmer's centre
inside its circle), leave (get out of a mark), stay (be inside a mark for so many seconds in a
row) and circle (go round a target so many turns, the angle swept the short way round, D-097).
"All" is every target of the kind, "one" any of them, "none" a ban. Leave and stay take marks
alone; stay and circle take no "none". "Leave all marks" means out of every mark at the same
tick, "stay in one mark" inside any of them, the clock back to 0 only when out of all, as the
rings were. Version 1's objectives are reach all lights, reach no light, leave all marks (Fear's
ring, a 12 u mark on its light), stay in one mark for 5 s (Love's, 6 u) and circle one light
twice; the same comparisons on the same numbers, so every shipped run is bit-identical. A test
recorded eighteen runs before the change, each level's winners and losers, their outcome, last
tick, and each objective's count and progress to the last digit, and pins them. Every
objective of the kind of every target must find one in its level, or the level is refused, and
the Maker keeps the last one. Names stay as players read them, but "Stay by the light", whose
ring is now any mark, reads "Stay in a ring"; a mark is "a ring" to the player. The rings, once
drawn dashed round the lights, are the marks: a grey circle, lit once the goal on them is met.
Files are version 3, `{"verb", "count", "target"}` and the setting; version 2's objectives are
upgraded, their rings appended as marks on every light, and a level whose rings would mix with
its marks, or with rings of another size, is refused. The goals' sliders (D-306's Goals) follow
in their own pull request.

**D-308 — 2026-10-05 — Goals, the Maker's second drawer: the time allowed, a slider, then at most two goals, each a sentence chosen in three rows of buttons, verb, how many, target, every option shown; a word chosen moves the others as little as makes sense, a word that would aim at nothing is dimmed. A stay's seconds or a circle's turns is a slider whose value may be typed. Applies D-301, D-307.**
The todo's Goals, the plan's choice: rows of buttons rather than words that cycle or lists that
drop down, so that every option shows and none hides behind a click (invariant 6). At the top,
the time allowed, 5 to 300 s by 5. Under it, each goal under its name, as the run will say it,
with a bin at the right to take it out; then Reach, Leave, Stay, Circle; All, One, None; Lights,
Obstacles, Marks, as Objects names them; the words chosen lit; under them a slider for the
setting its verb takes, seconds 1 to 60, turns 1 to 10. Add a goal shows while there are fewer
than two, which the run's drawers fit and no shipped level exceeds; the goal added is the first
sentence, in the order of the words, whose target the level has and which it does not ask yet,
reach every light on most levels. A word chosen wins and the others follow
(`objectives.reworded`): Leave or Stay takes the target to marks, Stay or Circle takes "none" to
one; "none" or a light or an obstacle that the verb cannot take puts the verb back to Reach,
which takes any; a setting stays with its verb. A word whose sentence would aim at something the
level has none of, Marks or Leave or Stay on a level without a mark, is dimmed, and a click on it
says "the level has no mark: place one in Objects". A sentence another goal asks, whatever its
setting, is refused. A drag on a slider is one step for undo, as an object's; the mouse wheel
there scrolls the drawer (D-096), not the value, which a click on its box types instead, as
Brief's fields are typed (D-305). Goals that cannot both be met, reach every light and touch
none, are not refused here: the clear check will find no winner. Three pull requests: the
changes (`making.py`), the drawer, the typed value.

**D-309 — 2026-10-05 — A goal's name says "the light", "the ring", only where the level has one; where it has more, it says "a light", "every ring", "the rings". Its name, its info text and the run's last line read the level. Amends D-307.**
D-307 kept version 1's names as players read them, "Don't touch the light", "Leave the ring",
"Circle the light", true on the levels they came from, each with one light or one ring; on a level
made with two lights they say what is not so. The physicist asked for the wording to be right.
Those three names now hold where the level has one target of the kind, and the sentence's own
words where it has more: "Touch no light", "Leave every ring", "Circle a light"; "the rings"
becomes "the ring" where there is one, in "Keep out of", "Stay inside" and their info texts, and
"It touched the light" becomes "It touched a light" where there are more. `Goal.name`, `about`
and `broken` take the level. Every shipped level reads as it did, word for word.

**D-310 — 2026-10-05 — Save, in the Maker's Files (F): Copy level puts its JSON on the clipboard, as `to_json` writes the shipped files; Paste a level, a field, takes a level's text. A level pasted, or started from, brings its title, spec, plane, start, goals and time, not its board, tutorial, passkey or hints. Start from offers a blank plane and every shipped level. Applies D-301, D-206.**
The todo's Save, the plan the physicist agreed to. Files is the Maker's fourth drawer, between
Brief and Navigator, as D-301 listed it. Under Save/Load, Copy level puts the level's text on the
clipboard through D-206's path, which Chrome and Safari reach; the text, 35 lines for the
sandbox's, is too long for the status line, which says that it was copied and how long it is.
Under it, Paste a level is a field as Paste a board is: a click opens it, Cmd/Ctrl+V pastes, Enter
takes the text, Esc gives up. Whatever no level could hold is refused, its reason in the status
line: not JSON, no version or a newer one, a key it does not know (D-201), a light on an
obstacle, a start inside one, a title with nothing in it. What it takes, the plane and the words,
is one step for undo, and the view goes to it. The board stays the one being made: the Maker
sets no board yet, which is the todo's next item, and a board it could neither show nor change
would be a failure the player cannot see (invariant 6). A made level has no tutorial, passkey or
hints. Copy level and Paste a level give the same level back. Start from, under them, offers a
blank plane, no item, the swimmer at the origin, no goal, 30 s, titled "New level", and the
shipped levels, the seven of the chapter and "Two lights, four obstacles", open or not: the Maker
is for us and Camille first. It follows in its own pull request.

**D-311 — 2026-10-05 — The Maker's values are whole numbers: positions on whole u, an obstacle's radius 1 to 5 u and a mark's 1 to 30 u by 1. Its grid is a dot every 1 u, 2 px square, and a line every 5 u, with no coordinate at the edges. The time allowed is 5 to 120 s. Amends D-301, D-302, D-306, D-308.**
The physicist, reviewing the Maker: no rulers, the grid is enough; dots every 1 u and bigger,
2 px, so that all quantities are integers; the time allowed at most 120 s. Positions snap to
whole u, and the arrows with Move in hand step 1 u; radii step by 1 u from 1. A light's power,
the headings every 15°, the time by 5 s, a stay's seconds and a circle's turns were whole
already. The dots go where they would come closer than 8 px, the lines every 5 u stay. A shipped
value off the lattice, the sandbox's lights at 27.5 u, Patience's obstacles of 1.5 u, stays as it
is until the Maker changes it (D-302).

**D-312 — 2026-10-05 — Circle leaves the objectives: a sentence is three words from three, reach, leave or stay; all, one or none; lights, obstacles or marks. Orbit asks to enter four rings round its light, 5 u out, and touch no light, in 20 s. Amends D-097, D-307, D-308.**
The physicist, reviewing the Maker: remove circle, and make Orbit avoid the light and reach marks
placed round it, so that every objective is three words, each chosen from three. Of the 27
sentences, 14 say something a run can count, as before: leave and stay take marks alone, and
stay takes no "none"; the Maker's choosers dim the rest (D-308). Going round is reaching the
marks round the target: it needs no counting of its own, and the turns' slider goes with it.
Orbit keeps its light at (25, 19) and its start at (25, 9) heading east; four marks of 2 u sit
5 u from the light, east, north, west and south, on the circle its hint's board settles on
(5.2 u, measured). Enter every ring and Don't touch the light: the orbiter wins in 9.1 s, the
brief's ÷2 in 8.7 s, the crossed board touches the light, a bare drive and fear go nowhere, the
hint's shadow wins; one lap is enough, so the time allowed is 20 s rather than 30. Its spec
reads "Go round the light through its four rings, without touching it." The pinned runs record
Orbit's three again. A level that still asks to circle, a version 3 file with "circle" or a
version 2 one with "circle light", is refused, saying so; only Orbit asked it. The run no
longer frames a circle round a circled light: Orbit's rings frame themselves.

**D-313 — 2026-10-05 — A level's file writes every whole number as an integer, and its board's zone as its size, 1, 7, 19 or 37 cells, a hexagon round the centre: version 4. Every shipped position is on whole units. Amends D-201, D-306, D-307.**
The physicist, reading a level copied from the Maker: the board's zone, a list of 37 cells, should
be just its size, and every position an integer, the shipped levels' too. A zone that is a
hexagon of r rings round (0, 0), 3r(r + 1) + 1 cells, is written as that number, as a board's
text already gives its zone by its rings (D-205); a zone of any other shape keeps its cells,
which no level has. A whole number is written without its ".0": [25, 19], 20 s. Version 3's
zones are upgraded to their size; the files are version 4, each rewritten. Positions off whole
units moved to the nearest, halves to the even one: Greed's dim light to (13, 10), Shadows' and
Patience's starts to y = 18, Patience's lights to (23, 18) and (21, 8), its obstacle to
(18, 11), the sandbox's lights to (28, 24) and (8, 8) and an obstacle to (14, 28); Patience's
third light goes to (15, 18) rather than (14, 18), which would touch its obstacle. Every level's
winners still win and its losers still lose, the hints' shadows too; the pinned runs record
Shadows', Greed's and Patience's winners again, a few ticks apart. Love's light of power 3.5 and
the obstacles of radius 1.5 in Patience and Shadows are settings, not positions: they stay. The
Maker's Parts drawer will set the zone's size (the todo's "The board").

**D-314 — 2026-10-05 — The Maker's Wheel works as the Editor's: atop the plane, what the next click or Enter does; a click on an object puts Move in hand; an object placed starts at the least, 1, with More lit; the arrows go round the Wheel and Enter uses the icon lit, Move carrying the object with the arrows until Enter or Esc. Amends D-302.**
The physicist, reviewing the Maker: the Wheel should behave as in the Editor, an icon at the top
middle showing the current action, Move the default on an object clicked, + on one first placed,
the arrows turning the Wheel's choice and Enter choosing or applying it; and a new object at the
least, 1. Atop the plane, as atop the board (D-068), the action shows as a lit disc with its name
and key beside it and a line under it: the object in hand, Move in hand, the Wheel's lit icon;
with none, the object focused, plain. A click on an object focuses it with Move lit, in hand
once the click is over: the next click on the open plane moves it there, a click on another
object focuses that one, a drag moves it as before. A light, an obstacle or a mark placed is
power 1 or radius 1 u, the least, and focused with More lit, so Enter, again and again, makes it
more. With something focused, → and ↓ light the next icon, ← and ↑ the one before, stopping at
the ends (D-084); on a point nothing is lit until they do, as the Editor's empty cell. Enter on
the lit icon: less, more and the turns at once; Move in hand, the arrows then carrying the
object 1 u at a time, a step for undo each, until Enter or Esc puts it down, as the physicist
chose; Delete. With nothing focused the arrows move the view, as before. The keys of the icons,
M, L, R, < and >, Delete, 1 to 3, still act at once, and light their icon. A click on the action
opens Objects, as the Editor's opens Tools. Esc puts down what is in hand, then lets go of the
focus, then opens Chapters (D-304). The physicist found the item's Wheel off, More at the lower
right and the top empty: its four icons now sit side by side over the top, no corner left empty
between them, Less, Move, More at the top, Delete, and the arrows go round in that order; the
Editor's Wheel keeps its own. A mark's icon is a + in a circle, as the plane draws it.

**D-315 — 2026-10-05 — Parts, in the Maker: the board's size, 7, 19 or 37 cells, and how many of each part it hands out, none to 9 or unlimited, each with − and +. The Editor's board takes it at once, its parts kept, or the change is refused while the board has more of a part or lies outside. Paste and Start from bring the zone and the parts handed out; a blank plane hands out 2 of each. Applies D-313; amends D-310.**
The physicist, reviewing the Maker: the number of each part allowed was missing, a Parts drawer
with − and + round it; the board's size chosen there, from 7 cells to the sandbox's 37, a
single cell holding nothing that could swim; every part from 0 to 9 or unlimited, as free as
the sandbox; 2 of each by default; the parts grouped and folding as the Editor's Parts. Parts is
the Maker's second drawer (P), under Objects: under Board, Cells, the zone's size, a hexagon of
1 to 3 rings; then Sensors, Actuators and Operators, titles that fold their rows as the
Editor's (D-069), each part's count between − and +, the infinity sign when unlimited, the
buttons greyed at the ends. Each step is a change of the level, one for
undo, and the Editor's board, the same one the run takes, is handed out anew at once
(`Board.rehand`), its parts and wires kept: if it has more of a part than the level would hand
out, or a part or a wire off the smaller zone, the change is refused, "this level hands out two
eyes; the board has three: take it off in the Editor first", as the physicist chose; nothing on
the board changes behind the player's back (invariant 6). Undo in the Maker and Paste and Start
from are refused alike. The Editor's Parts then lists what is handed out, and its undo starts
afresh, its steps having been taken on a board handing out other parts; a board put back by
undo counts its stock left from what the level hands out now. A level copied takes its zone
and its parts handed out with it, so Paste and Start from bring them, which D-310 left out;
the board's own parts, a tutorial's locked ones, are not brought. A blank plane hands out 2 of
each part on the zone it had. The sandbox itself still hands out every part without limit
(D-102). Locked parts, the rest of the todo's "The board", come later.

**D-316 — 2026-10-05 — Every Wheel sets its icons side by side over the top, no corner left empty between them, the Editor's as the Maker's: an odd number centred on the top corner, an even one a corner to its left. Amends D-068, D-314.**
The physicist found a gap at the top of the Editor's Wheel round a Source, whose four actions,
Move, Wire, Swap and Delete, sat two each side of the top corner, as the rule for an even number
of icons put them. D-314 had set the Maker's side by side and left the Editor's; one rule now
serves both: n icons take n corners in a row, from the left, as near the middle as they can, so
two take the upper left and the top, four the four left of the lower right, and an odd number
stays centred on the top. A Source's Wheel reads Move, Wire, Swap at the top, Delete; an empty
cell offering two parts, Fear's, sets them at the upper left and the top. The lowest corner, the
gap where piles end, stays clear. The tutorials, which name icons rather than places, play as
they did.

**D-317 — 2026-10-05 — The Maker reviewed again: a click on the plane opens Objects, whose Wheel never folds; the line under the Wheel says the setting; Move goes when another object or anything off the plane is clicked, leaving nothing lit; the Maker opens on a blank plane. Love's light is power 4 and its ring 7 u, Patience's and Shadows' obstacles 2 u: every setting shipped is whole. Amends D-314, D-315, D-313.**
The physicist, reviewing the Maker. A click on the plane, a point or an object, opens Objects if
another drawer is open, so its Wheel shows; a drag of the view does not. The Maker's Wheel never
folds, its title without the Editor's arrow. The line under it says what is focused and its
setting again, "A light, power 3", the action being named atop the plane. Move in hand goes, and
nothing is lit, the Wheel's empty tool, when another object is clicked, which is focused, or
anything off the plane is; a second click on that object puts Move in hand, as the first did.
Esc puts nothing lit, then lets go of the focus. The key beside the action atop the plane is the
action's, not the object's. The Maker, the first time it opens, makes a blank plane with two of
each part, Free play's level one undo away; if the Editor's board holds more than two of a part,
the blank plane keeps Free play's parts, and the status line says so. The physicist asked for
whole settings too, 4 and 2: Love's light goes from 3.5 to power 4 and Patience's and Shadows'
obstacles from 1.5 u to 2 u. Every level's winners still win and its losers lose; but Love's
winner on the axis rests 5 u from its brighter light, its rim on the 6 u ring, so the ring is
7 u, the body inside it again. The pinned runs record Love's, Shadows' and Patience's again.

**D-318 — 2026-10-05 — Brief is called Text (T). The line under the action atop the plane is short: "Enter: brighter". A setting is said without its unit: "radius 2". A light's power and an obstacle's or a mark's radius are whole, 1 to 8; Fear's ring goes from 12 u to 8 u, its light to power 4 and its start to 3 u from it. Each ring of a goal to enter every one lights as it is entered. Amends D-305, D-311, D-314, D-307.**
The physicist, reviewing the Maker. Brief becomes Text, its key T, which only the Editor's Tools
used; the code still calls the title and the spec the level's brief. The lines under the action
atop the plane, which said too much, are now: "Click the plane: place it", "Enter: place it
here", "Click or arrows: move. Enter: done", "Enter: remove it", "Enter: turn 15° left",
"Enter: dimmer", and so on; with nothing lit, the object and its setting, "An obstacle, radius
2", no unit said. Every item's setting is a whole number from 1 to 8: the shipped lights are 3
to 8, the obstacles 1 or 2, the marks 2 to 12. Fear's ring of 12 u, the one setting above 8, is
8 u; with it alone the fleeing swimmer was out in 1.3 s rather than 3.2, so, as the physicist
suggested, its light is dimmer, power 4, and its start nearer, 3 u from it: out in 3.18 s, its
losers still held in for the 10 s. Its tutorial is left as it is, for later work. In the run, the
rings of a goal to enter every one now light one by one as the swimmer first comes into each,
as the lights to reach already get a white circle each; other goals on the marks light them all
once met, as before, and a ban lights none (`objectives.lit_marks`).

**D-319 — 2026-10-06 — The board's locked parts: Lock, a third mode of the sandbox's Tools (K), makes the part clicked the level's, fixed where it is and using no stock, or frees it again, using one. The level places what the Editor's board has locked: Copy level writes it, Paste and Start from bring it. Locked parts only: no starting wire, no free starting part. Amends D-310, D-315.**
The todo's last part of the board, as the physicist chose it: locked parts set with the board
editor itself, in Tools, the same gesture as Delete, rather than a seventh icon on a part's Wheel.
On the sandbox Tools offers Lock under Write and Delete: while it is on, a click on a part, or
Enter on the focus, locks it, the part drawn as the level's are, and a click on a locked part
frees it; freeing one of a kind the level hands out no more of is refused, "give one more in
Parts". A locked part keeps its cell and its facing (D-009) and uses no stock, so locking one
gives its stock back. The level follows the board: once a frame the Maker takes the parts the
board has locked into its level, no wire with them, a step for its undo, which frees them again;
the Editor's undo covers the locking itself. Copy level writes them; Paste a level and Start
from bring a level's locked parts onto the Editor's board, keeping those already there, freeing
those it does not place, putting down the new ones, refused if the board has something on one
of their cells, "take it off first", or would hold more than the level hands out. A blank plane
places none. A level's free parts and wires, Aggression's prewired eye and thruster, are not
brought, and a level made places none: that is in ideas.md for later. The Editor's undo starts
afresh only when the zone or the parts handed out change, not when a part is locked.

**D-320 — 2026-10-06 — Share level, in the Maker's Files: once the level, as it stands, has been won in the Run, it is copied with its proof, the winning board's text and its score; pasted, the proof is run again, a second of it a frame, and the level is cleared if it wins, its score the one to beat, else a draft. The proof's board stays hidden. Applies D-205, D-310; the todo's clear check and sharing as text.**
The physicist's plan, as Mario Maker clears a course by its maker. A run of the made level won
in Free play gives the Maker a proof: the board that won, as its text (D-205), the tick it won at
and its parts; a better score replaces it. The proof holds while the level stays as it was won;
any change in the Maker voids it. Files has Share level under Copy level, greyed until then, and
a line under it: "Won in 9.11 s, 4 parts", or "Win it in the Run, as it stands", or "Give it a
goal, then win it"; a click without a proof says so. Share level copies the level's JSON with
`"proof": {"board", "ticks", "parts"}`; Copy level stays a draft, with none. The key joins
version 4, which has not reached `main`, so no version is added; a proof's unknown key is
refused (D-201). Paste a level takes the level as before, then, if it has a proof, puts the
proof's board on a fresh board of the level, refused if it does not fit, and runs it headless
(`levels/proof.Replay`), 120 ticks a frame: the worst run, 120 s, takes some 2 s natively and
more in a browser, which must never hold a frame. Won, the level is cleared, "Cleared: won in
9.11 s with 4 parts, the score to beat", and its proof kept, its tick its own run's and its parts
counted on the board, not taken on trust; otherwise it stays a draft and says so. What is
checked is the outcome: across platforms a run may differ in its last bit (D-004). The proof's
board never goes on the Editor's board, so a player solves the level alone; the score to beat
shows in Files only, the run's Score drawer later.

**D-321 — 2026-10-06 — Share level sits under Copy level and Paste a level, its line "Win it in Run first" until the level is won. Tools ends with Erase all. Parts is the Editor's first drawer and the one it opens on; the run opens on Diagnostic when a place is chosen; the Maker on Objects. Amends D-320, D-068, D-069.**
The physicist, trying Share level and the Editor. In the Maker's Files, Share level now comes
after Copy level and the field to paste a level into, its line under it saying "Win it in Run
first" until the level as it stands is won, and the score once it is; a click before says the
same. The Editor's Tools ends with Erase all, under Undo and Redo: every wire and every part
but the level's own off the board, their stock back, one step for undo, greyed with nothing to
erase; a tutorial's step that stops a board put back stops it too. The Editor's bar starts with
Parts, then Tools, and an editor opens on Parts, the level's or a place chosen in Chapters, where
it opened on Tools; the run opens on Diagnostic when a place is chosen, as it did the first time,
then keeps the drawer the player leaves it on from one run to the next; the Maker opens on
Objects, as it did. The tutorials, which open their own drawers, play as they did.

**D-322 — 2026-10-06 — The Maker's Files: Save/Load stays at the top; under a rule, the levels to start from are a list of their own that scrolls, Blank level, then Chapter 1: light and Free play under titles that fold, as Chapters lists them. Amends D-310.**
The physicist asked for Start from to be organised in chapters, a horizontal line, a Blank level
button, the chapter's title, which folds, and a button for each level, a sub-drawer of its own
with a scroll bar when needed. Save/Load, its title, Copy level, Paste a level, Share level and
its line, no longer scroll; the rule under them divides, as the Wheel's does; under it Blank
level, once Blank plane, then Chapter 1: light's seven levels under their numbers and Free play's
Sandbox, each title folding its rows as Parts' and Files' do (D-069), the list scrolling in its
own area, its scroll bar at the drawer's edge (D-096). The rows above the list are drawn apart
from it, so that its clip never hides them, which is what hides the title of the Editor's Files
(the todo's §12).

**D-323 — 2026-10-06 — A drawer's rows over the Wheel scroll only if the rows themselves do not fit: the gaps under the last row are not counted. Applies D-096.**
The sandbox's Tools, with Lock and Erase all, showed a scroll bar for 8 px: its last row ended at
364 px, the Wheel's area began at 368, but the gap under the last row and the section's gap after
it counted as content. They no longer do, for Tools and the Maker's Objects alike: nothing moves on
screen, the Wheel keeps its height, which a Wheel's piled icons need, and a drawer whose rows do
not fit scrolls as before, to its last row.

**D-324 — 2026-10-06 — "Two lights, four obstacles" comes back as the chapter's last level, 1.8, titled Two lights: reach both lights in 45 s, two eyes, a Source, the operators and two thrusters on 19 cells; its passkey GEMINI. No slider in Objects. Applies D-300; amends D-032.**
The physicist: no slider in Objects, its item struck from the todo; and the old level two, set
aside as too hard (D-032), at the end of the chapter for now, until the chapters he has in mind.
Its plane is the sandbox's, on whole units since D-313: lights of power 8 and 4 at (28, 24) and
(8, 8), four obstacles of 1 u, the start at (15, 19) heading 20°; its board as it was, 19 cells,
two eyes, one Source, the operators without limit, two thrusters; 45 s to touch both lights, in
any order. Its plane having moved half a unit since D-032, a search ran again: of 1,728
one-eyed circlers, an eye anywhere on the board looking any way, wired to either thruster, a
Source on the other, a Halve or a Double on either wire or none, 27 win; the fastest, 5 parts,
an eye at the back left looking ahead through a Double to the left thruster, the Source on the
right, in 24.6 s, which a test pins; plain aggression and Greed's and Patience's models touch
one light only. Like Greed and Patience it has no hints yet. Every level gives a passkey,
named for it: GEMINI, the twins. Its title is Two lights: the old one ran under the info disc
and the lock of its row in Chapters; Free play keeps the plane under the old title.

**D-325 — 2026-10-06 — The game in five chapters: 0 Tutorials, six levels each teaching one thing; 1 Braitenberg, Fear, Aggression, Love, Orbit; 2 Obstacles, new levels then Shadows; 3 Many lights, Greed, Patience, Two lights; 4 Made by users. In Chapters each chapter's title folds, all but the one being played. Amends D-097, D-300, D-324.**
The physicist's plan (the todo's §13), settled with him the same day. Chapter 0 teaches the
board and the parts, one thing a level: 0.1 Wiring, a Source and a thruster locked on the board,
the player drawing the wire between them, the swimmer going straight; 0.2 Turning, a part turned;
0.3 Eyes, the first eye; 0.4 Half, the Halve and the Double; 0.5 Plus, the Sum and the Diff; 0.6
Diagnostic, the drawer, which Aggression's tutorial teaches now (D-103). The Source comes first:
it moves the swimmer with no light to read. Every part Love and Orbit hand out is then known
before them. Chapter 1 keeps Braitenberg's vehicles, one idea a level (D-097): each eye its own
side, crossed, inhibition, one side always pushed. Chapter 2 opens with new levels, made in the
Maker, on obstacles, then Shadows. Chapter 3 goes from Greed's two lights to Patience's three
among obstacles, then Two lights, two among four obstacles, the hardest last (D-324). Chapter 4,
Made by users, the physicist's title, holds the levels made in the Maker or pasted, this session
(D-075). Free play keeps the sandbox
and the Maker.
Each chapter's first level is open from the start, the physicist's choice: a player may begin
any chapter. Inside a chapter a level opens once the one before it is won, or by its passkey
(D-035, D-075), so a chapter's last level gives no word, the next level being open already. Next
level still goes on through the chapters in order, and the end comes after the last chapter's
last level. A level is named by its chapter, LEVEL 2.1. In Chapters each chapter's title folds, as Files' groups do (D-069,
D-322): the chapter being played is open, the others folded; a chapter with no level yet is not
listed. D-300's scope, and `CLAUDE.md`'s, names the levels by chapter; still no new part, sense or
item. The rest of §13 is planned, and its decisions taken, item by item: several chapters in the
game, a level made in the Maker shipped as one of the game's, tutorials, chapter 0's levels,
chapter 2's, Made by users.

**D-326 — 2026-10-06 — Several chapters in the game: each chapter's level files in a folder of its own, a level named by its chapter, LEVEL 2.1; in Chapters, in every tab, each chapter under a title that folds, every chapter folded but the one being played until the player opens one; the Maker's Start from by chapter. Applies D-325.**
`levels/arenas.py` declares the chapters, `CHAPTERS`, each with its number, title, folder and
levels; the route is still one list, `arenas()`, in the same order, so every level's index,
board, wins and passkey are what they were, and `locate` gives a level's chapter and its place
there. The eight files moved as they were, byte for byte, into `1-braitenberg/`,
`2-obstacles/` and `3-many-lights/`; the sandbox's stays. Fear to Orbit are 1.1 to 1.4, Shadows
2.1, Greed, Patience and Two lights 3.1 to 3.3; 1.1, 2.1 and 3.1 are open from the start, and
Orbit's, Shadows' and Two lights' words, MOON, DARK and GEMINI, are kept in their files but no
longer given. Chapters 0 and 4 have no level yet and are not listed. The router keeps which chapters are folded, for the
session, so the run, the Editor and the Maker show the same: at first all but chapter 1. A
level whose chapter is folded, opened from Chapters or by Next level, folds every other chapter
instead, so the open level's row always shows; a level in a chapter that shows keeps the
player's folds, as the sandbox does; a passkey shows the chapter of the level it opens. Free
play and the passkey field stay under the chapters, scrolling with them (D-096). The Maker's
Start from lists Blank level, then a group per chapter, then Free play (D-322), folding as the
Maker's own groups do.

**D-327 — 2026-10-06 — The strip of tabs is a shade lighter than the open tab, the shut tabs on it, and the accent over the open tab is 3 px, as thick as the one along the open drawer's icon. Amends D-056.**
The physicist: the accent line over the open tab was thinner than the nav bar's, and the shut
tabs and the rest of the strip, where more tabs would go, should be a shade lighter than the open
tab's black. The strip was the bar's colour, `P.deep`, darker than the open tab's, `P.base`; it is
now `P.surface`, the drawers' colour, one step above it. `LIT_EDGE`, 3 px, is both accents.

**D-328 — 2026-10-06 — A level made in the Maker ships from Share level: its text and its proof in a file of its chapter's folder, its passkey, hints and tutorial written there by hand. Every shipped level carries its proof, which a test runs again; a hint's shadow goes over the level's locked parts; a tutorial refuses a key it does not know. Applies D-320, D-325; the todo's §13.**
The path, from the Maker to the game: win the level in the Run, Share level, save its text as
`data/<chapter>/<name>.json`, name it in its chapter in `levels/arenas.py`, write in the file
what the Maker does not set, then `PYTHONPATH=game python -m nektoids.levels.level FILE` writes
it as the game does, which the tests ask, byte for byte (D-313). The physicist: the proof stays
in the file, and a test runs it again, as a pasted level's is (D-320). Every shipped level now
carries one, so every level's file shows a board that wins it: Fear, Aggression, Love, Orbit and
Shadows their hint's shadow, Greed, Patience and Two lights the models their tests win with
(D-098, D-324), each run on its level from its start, its tick and parts the proof's. The test
checks the win and the parts, not the tick, which may differ in its last bit on another
platform (D-004). A level may place locked parts (D-319) and hand out none: `blank_board`, what a
hint's shadow is built on, keeps the locked parts, and drops the free ones and the wires as
before (D-103), so a shadow over 0.1's locked Source and thruster no longer asks for parts the
level does not hand out. A tutorial's data and its steps refuse a key they do not know, as a
level's do (D-201): a misspelt "untill" was skipped silently, and the step never waited. Every
shipped level's tutorial is tested, not only Fear's: Aggression's had not been.

**D-329 — 2026-10-06 — A level's hints are its idea, written in its file, and its proof: Hint 2 counts the parts the proof's board adds, Hint 3 shows that board over the parts the level places. Only chapters 0 and 1 have hints: Shadows' go. Amends D-078, D-103.**
The physicist: Hint 3 is taken from the proof, as Hint 2 is, and there are no hints after
chapter 1. A hint's shadow was written by hand, cell by cell, each wire from a cell to a cell,
and a test checked it won; a Maker level now comes with the board that won it (D-328), so a
level's `hints` holds its idea alone, refusing any other key, and `Hints.of(level)` puts the
proof's board on the level's blank board, the locked parts under it the level's own: the parts
it adds are the shadow's ghosts, in the editor and in Hint 2's count, its wires the ghost wires.
A shadow that adds no part, as 0.1's will, says "No part to add: only wires." The five shadows
became the proofs of D-328, so every hint reads as it did: Fear's, Aggression's, Love's and
Orbit's ideas stay; Shadows', "No light in the dark.", goes with its hints, chapter 2 having
none, as Greed, Patience and Two lights never had. Its proof stays, as every level's.

**D-330 — 2026-10-06 — Score shows a level's proof as a dark grey cross, the score to beat, under the player's wins; its board stays hidden. Applies D-328; amends D-046.**
The physicist: the player does not see the proof's board, but sees it in Score, as a darkish grey
cross. `to_beat(level)` is the proof's score, its parts and tick; Score plots it in `P.muted`,
two strokes 2 px wide, under the wins, so a win on it covers it, and its axes take it in. Two
lines head the plot, "Time against parts." and "The cross: one to beat."; with no win yet, the
plot shows the cross alone. Every shipped level has a proof (D-328), so every level shows one.
A level pasted with its proof in Free play keeps it in the Maker, not in its level: its cross
stays in `ideas.md`.

**D-331 — 2026-10-06 — A level has an author, written in the Maker's Text, the field opening on "@", and signed in its card's bottom right corner, in a darker grey. Every shipped level is "@Cy-3LO". A pasted level keeps its author; one started from another has none. The level format is version 5; version 4 is read as it is. Amends D-305, D-310.**
The physicist: the Maker and the level format had no author. Text's third field, Author, under
Title and Spec, a row high, opens on what the level says, or on "@" if it has none; what is
typed is kept as it is, spaces squeezed, 24 characters at most, and nothing, or the "@" alone,
leaves the level unsigned. The card a level opens under shows it in `GREYED`, small, in its
bottom right corner, as a signature, the lines above it where they were. The studio signs every
shipped level, the sandbox's too, as `CLAUDE.md` writes it, "@Cy-3LO", not "Cy_3LO". Paste a
level brings the author with the rest, someone's level staying theirs; Start from and a blank
plane leave it unsigned, a level started from another being its maker's to sign. Adding a key
changes the format (D-201): files are version 5, written "author" after "spec", and version 4,
which has none, is read unsigned.

**D-332 — 2026-10-06 — Dragster, the physicist's level made in the Maker, ships as chapter 4's first, LEVEL 4.1, signed "@Cy-3LO": reach a mark 15 u ahead in 4 s with Sources and thrusters from the stock. Its proof is two drives on the body's axis, 2.52 s. Applies D-325, D-328, D-331.**
The physicist made it in the Maker and put it in chapter 4, the levels made by players, signed
by the studio. "Go as fast as possible.": the swimmer at (-15, 0) heading 0, a mark of 8 u at
(8, 0), its centre to reach it in 4 s; a 7-cell board handing out three Sources and three
thrusters. One Source on one thruster, 3 u/s, runs out of time; two, each on a thruster on the
body's axis, back and front, win in 2.52 s, its proof; three would be faster, for more parts.
It is the route's last level, after Two lights, so it gives no passkey and has no hints
(D-329). Its file is `4-made-by-users/dragster.json`.

**D-333 — 2026-10-06 — In the run, a drawer's title scrolled under the objectives is the list's, clipped with its rows: the layout says which titles are the foot's. Applies D-065, D-096.**
In the run's Chapters, with every chapter open or the passkey field below the room, a title of
the list scrolled down under the objectives was drawn over OBJECTIVES, unclipped: the drawing
took any title whose corner lay in the objectives' area for theirs. The layout now keeps the
foot's titles apart, `foot_titles`, and only those are drawn over the objectives; the others are
the list's, clipped with it. The todo's §12 had it since D-326.

**D-334 — 2026-10-06 — Tutorials stay written by hand in their level's file. Chapter 0's first two lead the player through what they teach, a ghost where the part goes or how it faces and a card that waits until it is done; from 0.3 on, cards explain and the player builds. Settings' Tutorial replays the open level's tutorial, greyed on a level with none. Fear's introduction moves to 0.1, Aggression's Diagnostic cards to 0.6, once those levels are made. Amends D-039, D-054, D-079.**
The physicist chose the way chapter 0 teaches: lead in 0.1 Wiring and 0.2 Turning, explain after.
A tutorial is hand-written in its level's JSON, which the Maker does not set and the tests check
(D-328); what one that builds needs, the ghosts and the waits for a part placed, turned or wired,
has stayed since D-079 took it from Fear, and 0.1 and 0.2 use it again. From 0.3 on a card shows
the new part or drawer and says what it does, waiting for Next or for a drawer opened, and the
player builds with no ghost; the hints wait until the tutorial ends or is skipped (D-078).
Settings' Tutorial, which started Fear's again whatever the level, replays the open level's from
its first step, under its card, its board as the player left it; on a level with none, the
sandbox among them, its row is greyed and a click says "this level has no tutorial". Fear's six
cards, the swimmer, the objectives, the tabs, the board, the bar and Hints, are the game's
introduction, and Aggression's two lead to Diagnostic (D-103): they stay where they are until 0.1
and 0.6 are made, so the game always opens with one, and move then.

**D-335 — 2026-10-06 — Chapter 0, Tutorials: 0.1 Wiring, 0.2 Turning, 0.3 Eyes, 0.4 Half, 0.5 Minus, 0.6 Diagnostic, each on a 7-cell board, each won by its proof and lost by the board that misses its lesson; every one open from the start, none giving a passkey. Fear's introduction opens 0.1; Aggression's Diagnostic cards are 0.6's. Applies D-325, D-334; amends D-075, D-079, D-103.**
Designed with the physicist, each checked by simulation (`tests/test_chapter0.py`):
- 0.1 Wiring: a Source and a thruster locked on the axis, nothing handed out; Fear's five cards,
  then one that leads the wire, Run, Play, and Hints last. Into a ring 16 u ahead in 10 s: 4.35 s.
- 0.2 Turning: redesigned by D-336, a thruster's turn making the swimmer turn round an obstacle.
- 0.3 Eyes: an eye and a thruster to place and wire, a light of power 4 12 u ahead: 5.38 s; an
  eye looking back never moves. Cards explain the eye, from 0.3 on (D-334).
- 0.4 Half: stay 3 s in a ring of 3 u; a Source on the thruster crosses it in 2 s, halved it
  stays, 9.03 s. The Double is handed out too: no wire carries more than a Source sends, so on
  a Source's wire it adds nothing, which its card says.
- 0.5 Minus, once Plus: the Diff alone, the Sum left to Love, the physicist's choice. Stay 3 s in
  the ring of 8 u round a light 16 u ahead, without touching it: |Source - eye| slows to nothing
  as the eye fills, 7.42 s; an eye alone or a Source alone touch the light.
- 0.6 Diagnostic: an eye wired to a thruster comes with the eye looking back, so the swimmer
  never moves; Aggression's two cards, moved, take the player to Diagnostic to find why; turned
  forward, the eye reaches the light, 5.38 s.
Each is the studio's, "@Cy-3LO", hinted (D-329) with an idea of its own. The physicist: every
tutorial is open always, so a player may take them in any order, or none; a chapter says so,
`Chapter.all_open`, and its levels give no passkey, having nothing to open. Chapter 1 keeps its
hints, and chapters 2 and after have none, as D-329 has it. The game now opens on 0.1. Fear and Aggression lose their tutorials, Aggression keeping its
prewired half swimmer (D-103); Settings' Tutorial is greyed on them (D-334).

**D-336 — 2026-10-06 — A tutorial's highlight is accent1 alone, the sparks gone: a panel's titles, a tab's name, a cell, and now a drawer's icon in the bar, drawn in it. 0.1's cards edited by the physicist. 0.2 Turning: a thruster off the axis, pointing through the centre, turned to push ahead, takes the swimmer round an obstacle into the ring behind it. Amends D-080, D-095, D-335.**
The physicist reviewed chapter 0 in `docs/tutorials.md`, a table of every card, generated from
the level files: what is open, the text, what is lit, what moves it on. No highlight with sparks:
accent1 is enough, or an icon. The sparks (D-080) go, their code with them; what a step shows is
still drawn in accent1 by what draws it (`tutorial.panels`), and the bar's icons now are too:
every one for a step that shows the bar, the Hints icon for one that shows it (D-095 had left
them to the sparks). 0.1: the swimmer, already in accent1, needs no highlight; Objectives' title
alone is lit; "Click the Editor tab or button, or press Tab."; the board's card goes; the bar's
icons are lit; the wire's card lights its two cells, "Click the Source, then the Thruster to wire
them."; the Run and Play cards light nothing, and so hold nothing back (D-048); the last lights
the Hints icon: "You won! You reached the objectives. If you are stuck, try clicking Hints."
0.2 was redesigned on 37 cells, a thruster turned off the centre; D-338 redesigned it again.

**D-337 — 2026-10-06 — A tutorial's highlight pulses, accent1 bright to medium and back every 1.2 s, smoothly, in place of the sparks. A game's word in a card's text, marked "**Editor**", is drawn in accent1. Amends D-063, D-094, D-336.**
The physicist chose among animated trials, a hard blink and a smooth pulse, on text (the
Objectives title, the Editor tab) and on icons (the bar, the Hints icon): the pulse. What a step
lights, a tab's name, a drawer's title, a section's, a bar's icon or a cell, is drawn in
`palette.pulse(frame)`, a cosine between `P.accent1.mid` and `P.accent1.bright` over
`PULSE_FRAMES`, 72 frames; `main.py` counts the frames, drawing only, and hands the colour to the
scenes, `Frame.lit_ink`. A cell fills with half of it over the zone's colour (`FOCUS_TINT`), in
place of `FOCUS_CELL`. And in a card, the game's words, the tabs, the drawers, the parts, the
Wheel's actions, the keys, are set apart, as the physicist asked: marked "**Editor**" in the
level's file, as markdown writes bold, which `docs/tutorials.md` shows so, they are drawn in
accent1, steady. A step wraps by what shows, its marks taking no room, and a marked phrase that
runs on to the next line stays marked there. The six tutorials' words are marked, to be edited.

**D-338 — 2026-10-06 — Every tutorial opens on the Run, its introduction ending "Press the Editor button or tab, or press Tab." 0.2 Turning, on 19 cells: the thruster behind the Source, as in 0.1, is moved to the swimmer's right, and turns it round an obstacle into the ring behind. A card may wait for a part moved. The switch, Play, a row of Parts and a Wheel's icon pulse when a card shows them. 0.1's cards as the physicist edited them. Amends D-334, D-335, D-336, D-337.**
The physicist edited 0.1 in `docs/tutorials.md`: "swimmer" marked; "Click the Editor tab or
button, or press Tab."; the Run card lighting the Run tab; "Press Play, or Space to play the
simulation.", lighting Play. A highlight with no accent drawing of its own showed nothing once
the sparks went: the switch at the bar's foot, the run's Play, a row of Parts and a Wheel's icon
now pulse too (`tutorial.panels` names them "level:edit", "play", "menu:eye", "wheel:move").
Every tutorial opens on the Run, as 0.1 does, and its introduction ends on the Editor, lighting
its tab and button and waiting for it; 0.3 to 0.6 opened in the Editor, Parts open, and now say
their goal first: no tutorial names `starts_in`. 0.2: 37 cells were too many, 7 or 19 enough; its
first card, on the Run, says the goal, reaching the ring by turning round the obstacle; the next
leads the thruster's move, from behind the Source, where 0.1 has it, to the swimmer's right. On 19
cells a thruster one row off the axis, pushing ahead, circles on 3.08 u: an obstacle of 1 u at
(0, 3), a ring of 1 u at (0, 6), entered after some 160 degrees, in 2.92 s; behind the Source the
swimmer goes straight and misses, and on the left it circles the other way. A card may wait for
`moved`, a part of that kind on that cell, as `placed` does, letting through the Move tool and a
drag, and nothing else; `placed` still lets no move through.

**D-339 — 2026-10-06 — The physicist's review, round two: 0.1's Run card lights the Run button too; 0.3 shows the wiring's shadow; 0.5's second card lights the Diff alone. The run opens on Diagnostic, always. A stay's goal says its seconds, "Stay 3 s in the ring". The Editor's Diagnostic has no handles on its eyes' meters, and a part clicked there opens Tools on it. Chapters' numbers are in their names' font. Fear's plane turned a quarter, the swimmer facing right. Amends D-058, D-307, D-321, D-338.**
Tutorials: in 0.1 the card that sends the player to the Run lights its button with its tab; 0.3
ghosts its model, an eye ahead looking forward wired to a thruster behind, while its cards
explain; 0.5's card on the Diff lights its row of Parts, not the drawer's title. The run kept the
drawer it last had open, from one run to the next; it opens on Diagnostic every time now, as it
did when a place was chosen (D-321). A stay's name said where, not how long: "Stay 3 s in the
ring", "the" where the level has one, "every ring" for all. The Editor's Diagnostic let the
player drag an eye's meter to set what it reads (D-058), a slider in all but name: it goes, the
meters staying meters, and a click on a part in the Run preview opens Tools, the board in place
of the preview, with that part's Wheel. In Chapters, and in the Maker's Start from, a level's
number was in Plex Mono, its name in FreeSans Bold, each centred on its own: the number is in the
name's font now, on one line with it. Fear's plane turns 90 degrees clockwise about the start, so
that the swimmer faces right, as in every other level: the start at (17, 19) heading 0, the light
and its ring at (17, 16), still on its right; every run ends as it did, to the tick.

**D-340 — 2026-10-06 — A run won opens Score. Score's plot is boxed, its time axis ticked in round seconds, at most six ticks, their numbers apart from its label, "time (s)", turned upright. Amends D-046, D-339.**
The physicist: when the level is won, the run should show Score, the win just scored; and the
plot should be a square box, as wide as the drawer lets it, its label near the drawer's edge, its time axis ticked more than at its two ends, the numbers in seconds,
apart from the axis's label, written along it. The run, reaching its win, opens Score (not in the
developer's view); it opened on Diagnostic, and stays so until then (D-339). The plot is a box,
RULE's colour; the time axis is ticked every 1, 2, 5, 10, 15, 20, 30 or 60 s, the first of them
giving at most six ticks from 0 to the time allowed (`arena_layout.time_ticks`): 10 s every 2,
20 s every 5, 45 s every 10, 120 s every 30. A tick is a short line inward from both sides of
the box; its number, in seconds, sits left of the box; "time (s)", turned a quarter, stands left
of the numbers. The parts' axis is as it was. The box and its ticks are a shade lighter than a
rule, `PLOT_FRAME`, and its numbers and its axes' names lighter than dimmed text, `PLOT_TEXT`.

**D-341 — 2026-10-06 — Free play is Build your level, its row Open Maker, which opens the Maker on Objects, no card, under a card of its own, once a session, lighting the Maker's tab. The sandbox's caption says YOUR LEVEL. The Author field's "@" stands outside it, fixed. The todo's §13 is done. Amends D-035, D-301, D-322, D-331.**
The physicist closed §13: chapter 2's new levels and chapter 4's are made with the Maker as they
come. Its door in Chapters is renamed: the section once Free play is Build your level, its row,
once Sandbox, Open Maker, its info "Build your own level in the Maker: its objects, its goals,
its parts. Try it, then share it." Chosen, it opens the Maker on Objects, with no level card
(`Router.open`), and the shipped sandbox's file holds the Maker's introduction, a tutorial of
one card, which `main.py` runs on the Maker's screen too: it lights the Maker's tab, pulsing, and
says what the Maker is for; any key or click closes it, and it shows once a session, Settings'
Tutorial bringing it back (D-334). The caption's label, once SANDBOX, is YOUR LEVEL; F3 off the
sandbox says "the Maker opens from Chapters: Open Maker"; the Maker's Start from lists the old
plane under Sandbox, by its title, Two lights, four obstacles. The code keeps the word sandbox.
The Author field in Text: its "@" stands outside the field, before it, so that it cannot be
deleted; the field holds the name after it, and what is typed is signed "@" and the name; an
empty name leaves the level unsigned (D-331). The level file still writes "@Cy-3LO".

**D-342 — 2026-10-06 — The Maker's Start from opens with every chapter folded, and no longer lists the sandbox's plane, Two lights, four obstacles. The light's rays are a shade lighter. Amends D-310, D-322, D-341.**
The physicist: in the Maker's Files the chapters should be folded, and the sandbox's plane go.
Start from lists Blank level, then each chapter under its title, folded at first (the Maker's
own folds, which a click on a title changes, D-322); the old plane, once Free play's (D-035,
D-341), is gone from it, its file still the sandbox's, where the Maker's introduction lives. And
the rays a light sends, in the run, Diagnostic's map and the Maker's plane, are a shade lighter:
`RAY`, three quarters of the way from the bar's black to a rule's grey, was under half.

**D-343 — 2026-10-06 — The end says where to reach the studio: "leave a comment on the itch.io page or at contact@nektoids.com." Amends D-035.**
The physicist's: the domain registered on 2026-10-06 has its address. The end screen's second
line, which named the itch.io page alone, names both; it fits on one line of the end screen.

**D-344 — 2026-10-06 — Fear's proof is the physicist's board, 3C4tsBWoGsoQcW4i, four parts, won in 2.03 s: Score's cross and Hints 2 and 3 show it. Amends D-328.**
The physicist found it, and holds it optimal: two eyes at the back corners, each looking across
the body, back and out to the other side, wired to the thruster on the side it looks to, the
thrusters at the back corners as before. It wins Fear in 244 ticks, 2.03 s, where the old
shadow's board, eyes at the front looking back, took 3.18 s, with as many parts. Fear's idea,
"Each eye its thruster.", still holds: each eye drives the thruster on the side it sees.

**D-345 — 2026-10-06 — The streams thin out from 3 to 5 body radii, and are never shorter than 32 px on screen, on average: Diagnostic's map and a run zoomed out draw them longer. Amends D-076.**
The physicist's (todo §12): in Diagnostic's map the flames and the light drawn in should reach
farther, and at full rate they ended abruptly at 3 body radii. Chosen on a trial drawn by the
game's own code, the run of Aggression and the maps of Fear, Love and Dragster, fades and floors
side by side. Each speck now ends at its own distance, drawn evenly between 3 and 5 body radii:
a stream is as dense as before over its first 3 body radii, then thins out to none by 5, 4 on
average. The specks keep their speed, 3 body radii in 16 frames out of a thruster and in 0.5 s
into an eye, and their density, 12 at once in the first 3 body radii at RATE_MAX, 16 in all on
average: their number is still the rate. A stream is drawn longer where it would be shorter than
32 px on screen, on average. A body radius is 5 to 14 px in Diagnostic's map, so the maps of
Wiring, Minus, Love, Two lights and Dragster draw longer streams, and so does a run zoomed out
past 8 px/u; the run at its opening zoom, 16 px/u, is as it was. The info boxes' streams thin
out too, their farthest speck where it was, so that the boxes do not move. A probe near the
map's edge has its streams cut by the map's frame.

**D-346 — 2026-10-06 — Share level, once it has copied, opens its box on how to share the level: "Copied: your level and its proof. To share it with the community, paste it into a comment on the itch.io page, cy-3lo.itch.io/nektoids, or send it to contact@nektoids.com." Amends D-320.**
The physicist's: a level copied with its proof said only so on the status line, and nothing of
where to take it. The box is Share level's info box, beside its row, as the info disc opens it;
the next click or key closes it, and only that, as any info box. The info disc still tells what
Share level does. No server: the community is the itch.io page's comments and the studio's
address (D-343).

**D-347 — 2026-10-06 — The time allowed, in the Maker's Goals, is 1 to 120 s, by 1 s. Amends D-311.**
The physicist's: a level as short as Dragster's 4 s, or Dragster II's 1 s, could not be made in
the Maker, whose slider went from 5 to 120 s by 5. The slider now steps by a second; its value
may still be typed.

**D-348 — 2026-10-06 — Dragster II, the physicist's, ships as LEVEL 4.2, signed "@Cy-3LO": reach Dragster's mark in 1 s, from a stock of nine Sources and nine thrusters on 19 cells. Chapter 4's levels, made by users, are all open and give no passkey. Applies D-325, D-332, D-347.**
"Go even faster.": Dragster's plane, the swimmer at (-15, 0) heading 0 and a mark of 8 u at
(8, 0), with a board of 19 cells handing out nine of each. Its proof is the physicist's, nine
Sources each on a thruster, 18 parts, won in 69 ticks, 0.575 s. Levels made by users come in no
order, so chapter 4 is open from the start, as the tutorials are (D-335), and none of its levels
gives a word; it has no hints (D-329). Its file is `4-made-by-users/dragster-ii.json`.

**D-349 — 2026-10-06 — A level whose goals are won or lost where its swimmer starts is not judged: its run plays out its time, the Maker's status line says so and Share level refuses it. A level of bans alone is won when its time is up, none broken. Amends D-040, D-307, D-320.**
The physicist found it in the Maker: Dragster II's goal turned to "Leave every ring", its
swimmer starting out of the ring, and the run was over at once, "Done in 0.00 s", again after
every rewind; to him it looked frozen, a failure he could not read (invariant 6). Goals are
counted from where the swimmer starts, so a goal met there wins at the first tick: leave every
ring or a ring from outside them, reach a ring from inside it; a ban broken there loses, "Stay
inside the ring" from outside it. Such a level is now not judged: no banner at its start, Play
runs it, and it ends when its time is up, the banner adding "Not judged: won where it starts".
In the Maker the status line says "Won (or Lost) where the swimmer starts: move the start or
change a goal." while it holds, and Share level refuses the level, whose run cannot be won. A
ban was met while unbroken, so a level asking bans alone was won at once wherever it started;
such a level is now won by keeping its bans until its time is up: "Reach none of the lights"
alone is to keep off the light for the time allowed. No shipped level is decided at its start,
a test says so, and none asks bans alone.

**D-350 — 2026-10-07 — A lit button filled in the accent, the switch at the bar's foot, pulses its fill: accent1's dark halfway to its medium and back, in step with the other targets' ink; its icon stays white. Amends D-337, D-338.**
The physicist's, watching a new player: the Editor button's icon pulsed, where the colour that
draws the eye is the button's own. Its fill now pulses and its icon keeps the text's white. The
fill stops halfway to the medium: there the icon is 3.3:1 over it, above the 3:1 a graphic
needs, where on the medium itself it would be 2.0:1. Play, a grey button, keeps its pulsing
icon; tabs, bar icons and rows keep their pulsing ink, having no fill in the accent.

**D-351 — 2026-10-07 — A tutorial closed on its last card leaves its shadow on the board, for the session; skipped, it takes it away. Amends D-334, D-339.**
The physicist's, watching a new player: in 0.3 the shadow of the model, an eye ahead looking
forward wired to a thruster behind, went with the last card, 3 / 3, just when the player was to
build it. The tutorial now lends its ghosts once closed, after a tutorial still running and a
hint's shadow shown, until Settings' Tutorial starts it again. Skip still ends it with its
ghosts: the player asked for none. 0.1's and 0.2's ghosts are built over before their last card.

**D-352 — 2026-10-07 — 0.6 Diagnostic's eye comes looking back and to the right, SW, a turn left off straight back. Amends D-335.**
The physicist's, watching a new player: with the eye looking straight back, away from the light
dead ahead, the probe in Diagnostic had to turn more than 90° before the eye read anything.
Turned 60°, the light is still 120° off its axis at the start, so the swimmer still never moves;
but three presses of L, or the wheel, 45° in all, and the eye reads, its beads running to the
thruster; dragged beside the light, above it, it reads more. The proof, its eye turned forward,
is unchanged.

**D-353 — 2026-10-07 — Two hints, on every level of chapters 0 to 3: Hint 1, the parts one way to win adds; Hint 2, its shadow, those parts where they go and the way they face, without their wires. The idea is gone, and with it a level's `hints`. Chapter 4's levels, made by users, have none. Amends D-078, D-098, D-329.**
The physicist's, watching a new player: the idea, a bit cryptic, did not help, and the shadow's
wires gave the whole answer away. The parts and where they sit, turned as they should be, leave
the wiring to the player. Both hints come from the level's proof, so every level that ships with
one may have them: chapters 0 to 3; chapter 4's, made by users, keep none, by its `hints` flag.
The ideas leave the level files, which take no `hints` key now; no file but the game's had one
(D-310), so the format keeps its version 5. A tutorial's own shadow keeps its wires. Patience's
parts take three lines, the most; the shadow's picture keeps its 140 px above the objectives.

**D-354 — 2026-10-07 — Chapter 1's swimmers come with a thruster locked on each side, at (1, -2) and (-1, 2), straight above and below the centre on the board, both pushing forward, and no thruster to place; Aggression's board holds nothing else. New proofs for Aggression, Love and Orbit. Amends D-097, D-103, D-325, D-344.**
The physicist's, watching a new player: with thrusters of his own to place, a player found
better ways than Braitenberg's, a swimmer going sideways like a crab. Braitenberg's vehicles
have their motors on their two sides; so have chapter 1's now, locked, the eyes and what wires
them the player's. Aggression no longer comes half built: its free eye, thruster and wire, half
of Fear's swimmer (D-103), go. The proofs, the scores to beat and the hints' shadows, are
boards as Braitenberg drew them on those thrusters, picked from a search over the eyes' cells
and facings: Fear's, the physicist's, already had them (2.03 s). Aggression: the eyes at the
front corners, (2, -2) and (0, 2), looking ahead, crossed, 4.57 s, four parts, the fastest.
Love, Braitenberg's 3a: the same eyes, each taken from its own Source in a Diff driving its own
side, 7.28 s, eight parts; eyes turned in win sooner, 6.69 s, left for the player to find; a Source wired to two Diffs splits its beads between them, so one Source will not do,
but one eye on the axis with a Source, both split over two Diffs, wins too, as the one
thruster on the axis did, at the same tick. Orbit, the orbiter of D-097: the eye at the back
left looking ahead on the left thruster, a Source on the right, 6.53 s, four parts. Tests that
built on Fear's and Aggression's boards as they were, the old tutorials of `tests/data` and the
board's text pinned on Fear's model, keep those boards as fixtures.

**D-355 — 2026-10-07 — A passkey opens levels of its own chapter only: the level after the one whose win gives it, and those before it in that chapter; the other chapters stay as they are. Once every level is won, the last win gives VEHICLES, the word for every level, which opens them all. Amends D-075, D-325, D-326.**
The physicist's: passkeys go chapter by chapter. Each chapter's first level is open, and the
others open one after another, as won or by the word the level before gives. A word opened every
level before it on the whole route: GOLD, Greed's, opened chapter 1's too; it now opens only
Greed and Patience. MOON, DARK and GEMINI, each a chapter's last, were never given (D-326) and now
would open nothing: they leave their files. A player who has won every level in a session gets
one word to keep for them all, after Braitenberg's book, Vehicles: on the win card that
completes the set, "Passkey for every level: VEHICLES", and in each won level's info box in
Chapters. Typed, it opens every level of every chapter, none of them won.

**D-356 — 2026-10-07 — The Editor is the Board, the tab where the player wires the control board; the Maker is the Editor, the level editor. The tabs read Run, Board and, on Build your level, Editor; the code follows. Amends D-301, D-303, D-341.**
The physicist's: "Editor" fits the tool that makes levels, and the tab where the swimmer is wired
shows its board. The tabs, their tips, the switch's tip, the banner's button ("Board (Tab)"),
the status lines, the refusals, the Chapters row Open Editor and every tutorial card say so:
"Press the **Board** button or tab". F1, F2 and F3 are Run, Board and Editor. The code's names
follow, in two steps so that "editor" never means both: the Board's are `Env.BOARD`,
`Screen.BOARD`, `LevelButton.BOARD`, `ArenaButton.BOARD`, `BoardScene`, `board_scene()` in
`main.py`, `Router.open_board()`, a tutorial's `tab:board`, `level:board` and
`{"screen": "board"}`; the Editor's, `Env.EDITOR`, `Screen.EDITOR`, `EditorScene` in
`level_editor.py` and `level_editor_draw.py`, `editor()` in `main.py`, `Router.open_editor()`
and `tab:editor`. The package `nektoids/editor/`, the whole interface,
keeps its name, and `levels/making.py`, about making a level, its own. Decisions before this one
keep the names they were written with.

**D-357 — 2026-10-07 — Love's and Orbit's proofs are the physicist's: Love's, 18ZTtJNDZkXYA2nBggbmTZb7b, eight parts, 7.28 s; Orbit's, J1uA9PSzoTci9G, four parts, 9.43 s, the eye at the front looking ahead and to the left on the left thruster, a Source on the right. Orbit's four rings, of 2 u, move onto its circle, 9 u round the light, on the diagonals, at (±6, ±6) from it. Amends D-312, D-354.**
The physicist's boards, as Fear's (D-344): Score's cross and the hints show them. Love's is the
3a of D-354 laid out more tidily, won at the same tick. On the locked thrusters Orbit's orbiter
goes round 9 u out, where the rings, 5 u out, never were: it passed 4 u from their centres. The
physicist asked for larger rings; on the same centres they would have needed 5 u, reaching the
light and each other, the start on the lower ring's edge, counted in. On the diagonals, 8.5 u
out, 2 u rings keep their size, none holds the start, and they lie on the circle: the orbiter
wins in 9.43 s, and a tight orbit like the old one, inside them, no longer does. The orbiter with
a Halve on each wire goes round the same circle at half the speed and wins too, in 18.9 s.

**D-400 — 2026-10-07 — Stage 2, the Board, opens beside stage 1: built on `stage/2-board`, its scope the todo's §15, a Board built with fewer moves, and its decisions numbered from D-400. D-105's memory, flows and actions each move one stage down. Amends D-105.**
The physicist's: the new Board of the todo's §15, hex buttons round a board of one fixed size and
no Navigator, is a stage of its own; stage 1's list does not hold it (D-300). Stage 1 stays open
for Camille's review of v1.1, his levels and the banner, and stage 2 is built beside it, as stage
0 was built (D-200): each item a `feat/…` branch whose PR goes into the stage, and a stage built
beside another takes the next hundred. Whether it ships with v1.1 or after is decided on how it
goes and on Camille's response to v1.1; until then this opening stays on the stage's branch, not
on `main`. In: the Board's layout, its buttons and its gestures, and chapter 0's cards rewritten
for them. Out: all that stage 1 leaves out; no new part, sense or item; the model, the levels and
their format stay as they are. Its design is chosen from mockups drawn with the game's own code,
as D-051's was. Memory is now stage 3, flows stage 4 and actions stage 5; decisions before this
one keep the numbers they were written with.

**D-401 — 2026-10-07 — The Board's look: one hex size, 38 px, on every level; no zoom, no pan, nothing atop the board; buttons in the cells round it, at the same places on every level, as large as the cells and touching, drawn as keys with a 3 px bevel and a drop shadow. Tools, the Navigator and the Wheel leave the Board; Parts stays, for the counts and the info discs; Erase all goes to Files. Amends D-013, D-060, D-068, D-069, D-102, D-321.**
Decided from seven rounds of mockups drawn with the game's own code (todo §15), as D-051 was,
the renders kept outside the repository. At 38 px the 37 cells with a row of buttons above and
below are 532 px tall, in the 554 px a drawer leaves (11 to spare), and 36 px clear at each side.
The places, the board's centre at (0, 0), r down: at N, Select (1, -4), Move (2, -4) and Lock
(3, -4), Lock on the board reached from the Editor only, its place empty elsewhere (D-319); at
S, Undo, Redo and Delete, from (-3, 4) to (-1, 4); at W, Turn left (-3, -2) and Turn right
(-2, -2) side by side, Wire (-3, -1) under them; at E, Eye (4, -3), Source (4, -2) and Thruster
(4, -1), then Double (2, 2) and Halve (3, 2) side by side over Sum (1, 3) and Difference (2, 3).
A kind the level does not hand out leaves its place empty. A button's bevel is lit from the top
left, from the dim grey to the deepest, its shadow 2 px right and 3 px down. Chosen, it is
pressed in: accent 1's dark, the bright on its far sides, no shadow. Lit, it applies to what is
picked: its bevel in accent 1, its key on a light tag inside its top corner. Greyed, it cannot
act now: its bevel dimmed, its icon greyed, an eye's face or a thruster's back in accent 1's
dark. A tool's icon is three quarters of the hex; a part is drawn 2 px smaller than on a cell, as
the button's darker ground makes it look larger. A part's count, what is left, shows on a dark
tag inside the bottom corner for 1.5 s after one is placed; Parts lists them all, each with its
info disc, and no longer holds the Wheel. Picked empty cells carry no number. The outside of the
zone keeps its grid. Negative buttons, a gap between buttons, keys and counts beside the
buttons, and a line of seven at N were tried and set aside.

**D-402 — 2026-10-07 — The Board's gestures: one button chosen at a time, Select when none; with something picked a button acts on it at once, else on each click and along a drag; right clicks wire, the chain going on; the mouse wheel turns, up to the right. Amends D-068, D-090, D-304.**
A Part stays chosen while one of its kind is left, then Select is. Keys choose as clicks do:
Esc, M, Del, K, L, R, W, 1 to 7, Ctrl+Z and Ctrl+Y; Esc first drops what is picked, then
chooses Select, then opens Chapters (D-304). Select: a click on an empty cell picks it, one
after another; a click on a part picks parts instead, the first click saying which; a click on a
picked one drops it, a click off the zone drops them all. A drag from an empty cell picks the
empty cells it crosses; a drag from a picked part moves them all; a drag from another part
moves it, as today (D-090). A group moved onto a taken cell is refused whole, the cells in the
way flashing. With something picked, a lit button acts on it at once, in the order picked, and
Select stays chosen with the pick kept: a Part fills the empty cells, the last left empty if the
parts run out, or swaps a picked part for one of its group (D-068's Swap); Turn turns each part,
again at each press; Delete deletes them; Wire chains them; Move is chosen, and the next click
puts the first part picked there, the others keeping their places round it. With nothing picked,
the chosen button acts on each click on a cell that allows it, and along a drag on each one
crossed: a Part places one per empty cell, Delete and Turn act once on each part, Wire chains the
parts in the order crossed, Move carries the part pressed; a Part on a taken cell is refused.
Greyed is what cannot act now: on what is picked, if anything is, else on the board. Right
clicks wire: A then B makes A→B, and the chain goes on from B; Esc, a left click or a right click
off a part ends it; a right drag chains the parts it crosses. On the Board a right click no
longer backs out (D-304). The mouse wheel over a part, or over a picked part with the rest of the
pick, turns it 60° a notch, up to the right; a trackpad's small scrolls add up to a notch, with a
short pause after each turn. One gesture is one undo step (D-027), a run of turns on one part
one gesture. Diagnostic's Run preview hides the buttons. The Editor keeps its Wheel (D-314);
touch keeps Wire and Turn on buttons, having no right click nor wheel.

**D-403 — 2026-10-07 — Picking, as built: a second click on a part picks it too, so two parts clicked are no longer wired; the parts a fill places are picked; a click of the other kind starts a pick of its own; with one part picked, Wire is held to wire from it; a press on the held button puts it down. Amends D-026, D-091, D-402.**
The physicist's answers, and what building D-402 asked. With Select held, a click on an empty
cell picks it and a click on a part picks parts, one after another; a click of the other kind
drops the pick for one of its own kind; a click on a picked one drops it, one off the zone drops
all. Wiring is now a button's: two parts picked and Wire, which chains them in the order picked;
one part picked and Wire, held to wire from it; or Wire held, a part clicked, then the next, the
chain going on from the last; an empty cell ends it. The clicks that wired two parts (D-026) and
the rule that a chain wires on only forward (D-091) go. A part's button on picked cells fills
them in order and picks the parts it placed, so L or Wire act on them at once; on picked parts it
swaps those that may become one. Turn and Delete leave the level's parts out; Lock makes all the
level's, or frees all; Move is refused with one of the level's picked, and refused whole, the
first cell in the way flashing, if a cell the group would land on is taken or off the zone. With
something picked, a button that cannot act on it but may on the board is held, the pick dropped;
a press on the held button holds Select again. With nothing picked, Move held lifts a part
clicked and puts it on the empty cell clicked next. Esc backs out of a wire's chain or a part
lifted, then the pick, then the held button, then opens Chapters (D-304). The keyboard has a
cursor: the arrows move it, Enter clicks there. Wiring's and Turning's cards say so.

**D-404 — 2026-10-07 — Drags and right clicks, as built: a held button acts along a drag on each cell it enters; with Select, a drag from an empty cell picks the empty cells it crosses and one from a picked part moves the pick, let go off the body it goes; right clicks wire whatever is held, and a left click ends their chain and acts. Amends D-072, D-085, D-090, D-304, D-402.**
A press acts as a click does; then each cell the drag enters, once: a part's button places one
on each empty cell while one is left, then Select is held; Delete, Turn and Lock act on each part
crossed; Wire chains the parts crossed in that order, the empty cells between leaving the chain
as it is. With Select, a drag from an empty cell picks the empty cells it crosses, the parts it
crosses left out; one from a part not picked moves it alone, as before (D-090), but Wire held no
longer draws one wire by a drag (D-072): it chains. A drag from a picked part moves the whole
pick, worked out from the board as it was picked up (D-086); a step refused leaves it where it
last could go, the cell in the way flashing; let go off the body, every picked part goes, with
its wires, darkened while it is off (D-085), the physicist's: one Undo brings them back. Right
clicks wire whatever button is held, which stays held: a part right-clicked starts the chain, the
next is wired to it and the chain goes on from there; a right drag chains the parts it crosses;
a right click off a part, Esc, or a left click ends the chain, the left click acting too, the
physicist's. On the Board a right click no longer backs out (D-304). A drag, or a right drag, is
one step for undo (D-027).

**D-405 — 2026-10-07 — The mouse wheel, as built: over a part it turns it 60° a notch, up to the right; over a picked part, every picked part that turns; a trackpad's small scrolls add up to a notch, then rest 0.15 s; turns on the same parts, less than 0.5 s apart, are one step for undo. Applies D-402.**
A wheel's notch is a turn at once; a trackpad's scrolls, fractions of a notch, add up, and the
one that makes a notch turns the part, then the scrolls are let go for 9 frames, so that a flick
of two fingers turns it once (`notches.py`). Up is the wheel's own: with natural scrolling the
system's flip is undone, so that up turns to the right on a mouse and on a trackpad alike. The
level's parts and the operators do not turn, and say so. A run of turns on the same parts is one
step for undo, kept once the wheel has rested 30 frames, or at once when the mouse leaves the part
or anything else is done. Over an empty cell or off the board the wheel does what it did. The
probe in Diagnostic keeps its own way, up counter-clockwise (D-058).

**D-406 — 2026-10-07 — The Board after the physicist's first review: a click picks one thing, Shift or Cmd adds; a drag picks, places or wires along a path it can go back on; no Move button, the Board at 40 px; Esc is Chapters' key only; Lock on every Board, the player's own; the grid in 2 px over the buttons' shadows; stage 2 goes to `main`. Amends D-304, D-319, D-400, D-401, D-402, D-403, D-404.**
The look, from three more rounds of mockups: the cells' sides are 2 px anti-aliased strokes, the
zone's a lighter grey than the pattern round it, drawn over the buttons' shadows and under the
buttons, wires and parts; a button is drawn 2 px inside its cell, clear of the line; the
swimmer's symbol is 5 px wide, a shade darker, under the grid. Tried and dropped: an edge round
the zone in an accent (Benjamin's, in accent2, which is the refusals' colour), a gap between the
board and its buttons, and rounded corners where three cells meet. Each button has a tooltip: its
name, its key, and for a part how many are left; Select's key is S. Move goes: a drag moves a part
or the pick, and Shift with an arrow moves the picked parts a cell. Select, Lock and Delete sit at
N, Undo and Redo at SW across from Sum and Difference, and the Board grows to 40 px, the view
centring the largest zone and its buttons together. Select is in hand whenever the Board's tab
opens.

Picking: a click picks the one cell or part clicked, a click on the only thing picked drops it,
and Shift or Cmd adds one to the pick or drops it. A drag picks along its path: going back onto a
cell of the path cuts the path back to it, however far; a drag of empty cells that meets a part
picks parts from there. From a part, the drag's first step decides: into a part not picked it
picks parts, the empty cells passed over; else it moves the part, or the pick. Placing: a part's
button acts when let go, and dragged onto the board places one, as a row of Parts does; with a
part held, a drag places one in each empty cell, going back taking them away, and a drag from a
part moves it, after which Select is in hand again, as after wiring by right clicks. Wiring: a
chain is a path, and going back to one of its parts undoes the wires made after it; wiring over a
wire takes it away; a wire refused ends the chain; a drag's chain, left or right, ends when let
go; a right click off a part ends the chain and drops the pick. Ctrl+click is a right click, for
trackpads without one, and every right click's work has another way: Wire or W, and the clicks.
Delete, clicked on a part's rim, takes the short wire to its neighbour there.

Esc opens and folds Chapters, and only that, on the Board; the captions point to S and the clicks
instead. Lock is on every Board and is the player's: a part locked stays put, as it is, not moved,
turned, swapped or deleted, its wires free to come and go; ringed in the accent, where the level's
ring is light; Erase all spares it; saved boards keep it, the board's text does not, as it keeps
no lock. On the sandbox, Shift+Lock makes a part the level's, as Lock did (D-319). Stage 2 goes
to `main` now, the physicist's, before Camille's review of v1.1 (D-400 left it open).

**D-407 — 2026-10-08 — Diagnostic on the Board keeps the board editable: the main screen stays the board with its buttons; the drawer runs it at its top, as Run's Diagnostic does, and shows the level's map at its foot. The Run preview goes. Amends D-058, D-060, D-069, D-339.**
The physicist's: with the board always on the main screen, a change shows at once in the drawer,
and nothing is refused for being in a preview. The drawer's top, "The board at work", draws the
board fitted with its body, plain, beads on the wires and a meter by each eye and thruster, as
Run's Diagnostic draws it (D-089); its foot, "The level", is the map as before, 216 px square,
the probe dragged on it. Over the map, L, R and the mouse wheel turn the probe; anywhere else
they turn the parts, the physicist's. The probe is made again whenever the board changes, where
it stood. A part clicked on the preview to edit it (D-339) goes with the preview. The status line
says how to use the map while the mouse is on it. Diagnostic's last card in chapter 0 says what
the drawer shows.

**D-408 — 2026-10-08 — Tutorial cards keep clear of what the player needs: on the Board, of the buttons round the board, Undo and Redo given up last; in the run, of the controls, the drawer and the swimmer. Chapter 0 lights a part's button with its row, and its shadows are darker. Amends D-048, D-103, D-337.**
From the physicist's review of chapter 0 against the new Board (D-406). A card's place keeps
clear of its targets, the hand's way between them, the work just done and the parts (D-048,
D-103), and now of the buttons; where no place is clear, it gives up the ways, then Undo and
Redo, which a step needs least, then the buttons, then the work just done, never its targets.
With the Parts drawer open, a card of 464 px finds no room clear of every button in a board area
of 664 px: three of chapter 0's cards lie over Undo and Redo. A card with no target looks for a
clear place from the board's foot up. In the run, a card keeps off the controls, the drawer
and the swimmer, over the arena between the swimmer and the timeline. Eyes, Half and Minus light
the part's button round the board and its row in Parts; Eyes says how: the buttons dragged onto
their ghosts, then W and the two parts. The tutorials' shadows, parts and wires, are the line's
grey, a shade darker, not to be taken for a wire. Settings' Tutorial row is named Redo
tutorial, which is what it does (D-334): from the first step, on the board as it stands. Minus
hands out a Sum too, the physicist's, so that Sum and Difference sit side by side, to choose.

**D-409 — 2026-10-08 — Diagnostic's board is titled "Active board", in the run and on the Board; on the Board, a note under the map says it can be dragged. Amends D-089, D-407.**
The physicist's. The run's Diagnostic called its board "The swimmer's wiring", the Board's "The
board at work": both are now "Active board". Under the Board's map, a note: "You can drag the
swimmer anywhere; the wheel, or L and R, turn it." Its room is taken from the active board, now
248 px high, the map moved up over the note.

**D-410 — 2026-10-08 — The Editor's keys: square keys fixed on the screen, floating over the plane at its edges, tools at its left, objects at its right, in place of the Wheel and the action atop the plane; a click picks, Shift adds, a drag draws a rectangle that picks or moves the pick, a held object is laid along a drag, the Hand pans, the wheel sizes or zooms; the swimmer can be cut and placed again; Erase all takes the goals too. Amends D-301, D-302, D-307, D-314, D-316, D-317.**
The physicist's, from four rounds of mockups and a review: the Board's buttons sit round a fixed
board, the Editor's plane pans and zooms, so its keys are squares fixed on the screen, 36 px so
that their icons are the bar's size, 20 px inside the plane's edges, clear of the drawer's
handle, with nothing under them but the plane. At the left, two columns: Select and Hand; Bigger
and Smaller, carets up and down; Zoom in and out; Undo and Redo; Copy and Paste; Cut, which takes
the place of Delete, and Erase all. At the right: the Swimmer, drawn as its symbol, key 0, then
Light, Obstacle and Mark, 1 to 3; Objects' rows in that order. Each looks as the Board's buttons
do (D-401): chosen, lit, greyed; each has its tooltip, its name and key. The Wheel, the action
atop the plane and the undo rows of Objects go.
With Select, a click picks the object clicked, Shift or Cmd adds one, the open plane drops the
pick; a drag from the open plane draws a rectangle, a + at its first corner and at the mouse,
which picks the objects whose centres lie inside it; a drag from an object moves it, or the pick
it is in, on the lattice, one step for undo. The Hand pans; a right drag pans whatever is held.
An object's key held, each click on the plane places one; a drag lays them along its way, each
touching the last, going back taking them away, as the Board's parts (D-404), and lets go with
Select in hand; dragged onto the plane from its key or its row, one lands there. A level has one
swimmer: its key is greyed while it is on the plane; Cut takes it off, the run refused until its
key, or 0, places it again; Undo puts it back. Bigger, Smaller, Cut and Copy act on the items
picked; Paste puts copies where the mouse is, else 2 u beside, and picks them; what is copied
lasts the session, for any level. Erase all asks "Are you sure you want to erase all the
objects?", Cancel the default, Enter, Esc or a click elsewhere cancelling; it takes every item
and every goal, which would aim at nothing, the swimmer and the time allowed staying. A value
shows a moment under an object placed or set, as the Board's count (D-401). The mouse wheel over
an item sizes it, the pick if it is picked, over the swimmer turns it, over the open plane zooms
there; notches as the Board's (D-405). Keys: S, H, 0 to 3, < and >, + and -, Del cuts, Ctrl+C,
Ctrl+V, Ctrl+X; the arrows move the pick 1 u, else the view; Esc opens Chapters (D-406). The swimmer is
drawn with lines 0.15 of its radius on screen, 2 px at least, in the run, the Editor, their maps
and on its key, the physicist's. A click with an object's key held stays a click though the
mouse moves a little: only a drag that lays a second object lets the key go. A right click, not
a drag, puts the key down and drops the pick, Select in hand. An object's key, its first gesture
says how it is used: a drag lays a row; a click places one, and then each click places one, a
drag putting the key down to move the object under it, or pick with a rectangle, as Select.

**D-411 — 2026-10-08 — In the run, a drag moves the view, left or right, and the mouse wheel zooms about the mouse, as in the Editor (D-410). Amends D-065, D-066.**
The physicist's. A left press on the arena that moves 4 px or more moves the view; one let go
where it was is a click, which inspects, as before; the developer's drag still moves the swimmer.
A right drag moves the view whatever the press would do. The wheel over the arena zooms about the
mouse, a trackpad's small scrolls adding up to a notch (D-405); in the developer view it still
turns the swimmer. The Hand and Navigator's zoom stay.

**D-412 — 2026-10-08 — In the Editor's Parts, a − or + held keeps stepping: after 1 s, three steps a second, the whole ladder, ∞ included; the hold is one step for undo. Amends D-315.**
The physicist's, from the todo's §11. A press steps once, as before; held 60 frames over the same
button, it steps again every 20 frames until it is let go, the mouse leaves the button, the end of
its row is reached or a step is refused, the status line saying why (D-315). Both numbers are
constants in `editor/hold.py`, to be tuned by trying. Undo takes the whole hold back, as a run of
the wheel's notches (D-405).

**D-413 — 2026-10-08 — A level is shared as a few lines of text: its title, author and description, then the level as one word, then, once won, the winning board's text. Copy level and Share level write them, Paste a level reads them; JSON leaves the Editor, and shipped files stay JSON. Amends D-310, D-320, D-328, D-331.**
The physicist's, from the todo's §11: a short text to paste into a comment or an email,
`Title:`, `Author:`, `Description:`, `Level:` and `Board:`, each on its line. The level's word
holds only the level as played: the start, the items, the zone, what the board hands out, the
parts it places, locked, the time and the goals; no title, spec or author, which are the lines
above it, and no board but its locked parts. It is built as a board's text (D-205): each
decision a digit whose base is the number of choices, a position one digit within 32 u of the
origin and more beyond, a heading a whole degree, the locked parts the board's own digits; the
integer is written in base 59 with the board's checks, moved to `graph/spelling.py`, under a
hidden version symbol of its own, 31, so a board's text pasted as a level is refused, "that is a
board's text: paste it on the Board", and a level's word on the Board likewise. Every shipped
level's word is 18 to 35 characters; Dragster's whole text, 115, against 374 of compact JSON.
Paste a level finds the lines by their labels, in any order, what comes before the first or
after a word left out, as an email's greeting and signature; a line break pasted into any field
is now a space, so the lines run together in a field of one line and are still read. A word
alone is a level untitled. The proof's tick and parts are not written: a pasted proof is run
again and counted (D-320). Copy level writes no `Board:` line; Share level does. A pasted
level keeps its author, as D-331 said and the Editor did not. To ship a level (D-328), its text
saved to a file goes through `PYTHONPATH=game python -m nektoids.levels.levelword TEXT FILE`,
which runs its proof again and writes the level's file as the game writes it; passkey and
tutorial are still written there by hand.

**D-414 — 2026-10-08 — The README is written for visitors: the game, how to play it and how to build it, the `docs/` folder, credits. `docs/ideas.md` is no longer committed: it stays on the developers' disks, ignored by git. Amends D-028.**
The physicist's, the todo's §14. The README says what the game is, plays it in a browser on
itch.io or natively from `requirements.txt` (the game is not an installable package), builds it,
and lists `docs/`; it names no contributor but Cy-3LO, and says nothing of how the work is shared.
`ideas.md` held thoughts for later, not for strangers: it is taken out of the repository, its
history left as it is, and CLAUDE.md no longer counts it among the files strangers read. The
banner, the todo's other item, comes later.

**D-415 — 2026-10-08 — Diagnostic's circuit, the Board's and Run's, shows each eye's light and each thruster's flame behind it, faint and short, in place of the level meters. Amends D-052, D-089.**
The physicist's: a meter, a bar of the faces' accent beside a part, was hard to read and taken
for the part's accented face. Behind the wires and the parts, the specks the run draws (D-076)
now come into each eye's face and out of each thruster's back, as many as the rates, the way the
part faces: at most 1.4 hex sizes from the face, against 1.8 in a part's entry (D-082), in the
run's colours taken 30% towards the panel's, the variant he chose of three. The entry's specks
and Diagnostic's are drawn by one module, `editor/streams.py`, any facing; the entry's are the
same as before, speck for speck. The developer view keeps its meters beside its numbers.

**D-416 — 2026-10-08 — A wire carrying RATE_MAX shows 10 beads a second, not 4, at the same speed: beads 0.35 hex sizes apart at full rate, not 0.875.**
The physicist's, comparing 4, 6, 8 and 12 a second on the banner's board: on the short wires of
a board, one or two cells, a low rate often showed one bead or none. The speed stays 3.5 hex
sizes a second, so the beads move as before, closer together; the rate still reads as their
spacing. Every circuit takes it: Diagnostic, the Board's and Run's, the parts' entries, where ×2
and ÷2 still send their beads in time with those coming in, and the developer view.

**D-417 — 2026-10-08 — The banners: the title, the studio and the README's phrase, the swimmer at the run's scale, its velocity and spin shown, and its board at work at the same moment, drawn by the game's own code; one atop the README and as GitHub's social preview, two for itch.io. Closes the todo's §14.**
The physicist's, from mockups rendered by the game. One board, two eyes ahead and two thrusters
at the tail, wired without crossing, a Double on the left, a Source less the right eye on the
right, runs 1 s towards a light that is never seen: its rays fade out before it. The swimmer is
drawn as the run draws it at its opening scale, 16 px a unit; beside it, its board on its body,
its beads (D-416) and its streams in the run's colours, neither brighter nor dimmed as
Diagnostic's (D-415), three frames of specks so that they read on a still. GitHub's is 1280 by
640, nothing within 40 px of its edges, as GitHub's template asks; itch.io's cover 630 by 500
and its page banner 960 by 300. `docs/banner/make_banners.py` draws all three again when the
game's look changes; the README shows GitHub's under its title, the phrase in its alt text.

**D-500 — 2026-10-08 — Stage 3, memory, is decided: tanks, loops on the board, and lights that change in time, with their levels; valves stay in the ideas. Built on `stage/3-memory`, branched from `main` once stages 1 and 2 are there (#125); its decisions take the five hundreds. Applies D-105, D-400.**
The physicist's, from the ideas' §3, the stage D-400 put next. A tank is a part whose level h
lags what comes in, T dh/dt = in − h, T about 4 s, and which sends out its level: the lag every
node has (D-017), slower, one entry in the table of kinds and its law in `graph/laws.py`
(D-202), its level drawn as a fill. Loops: a wire may come back round to a part before it; the
dynamics take loops already (D-017), the Board refuses them, and with a tank a loop holds a
level. A light may follow a schedule, its power a function of time, set in the Editor and
deterministic (invariant 1): a flash that goes dark, lights that switch on in turn, so that what
the eyes read now is not enough. Valves, out = max(0, a − b), need ports first and stay in the
ideas, as do the threshold node and colours. The todo's §16 lists the work; each item is planned,
and its decisions taken, when it starts.

**D-418 — 2026-10-08 — A field of text repeats a key held and selects: Shift with the arrows, Home and End, Ctrl or Cmd+A, a drag in the open field; what is typed or pasted replaces the selection, Backspace and Delete take it out, Ctrl or Cmd+C and X copy and cut it. Amends D-206, D-305.**
The physicist's, before v1.1: deleting a word took a key press a letter, and nothing could be
selected. Natively a key held repeats after 0.4 s, every 35 ms, while a field is open and only
then, so the game's own keys still act once a press. A field holds an anchor beside its caret;
the selection between them is drawn behind the text in the accent's dark. A click in the open
field puts the caret on the place nearest it, found as the field draws its text: IBM Plex Mono's
characters are all one width, measured once at startup. On the web the page's field already
repeats and selects with the keys; the game now reads the selection's other end from it too, and
a click or drag in the game's field selects in the page's. Every field takes it: the Editor's
title, spec, author and typed values, Paste a level and Paste a board.

**D-419 — 2026-10-08 — Build your level is captioned by its level's title alone, or YOUR LEVEL while it has none, in the Run, the Board and the Editor; a blank level starts with no title, its field showing "Title", dimmed. Amends D-310, D-341.**
The physicist's, before v1.1: "YOUR LEVEL. New level" said the same thing twice. A level made
in the Editor may have no title; the chapters' levels keep "LEVEL 1.2. Fear" (D-034). A level
shared with no title is read back with none (D-413), and so captioned YOUR LEVEL where it is
pasted.

**D-420 — 2026-10-08 — Every heading within a drawer is drawn alike: in capitals, 20 px, larger than the 18 px they had, smaller than the drawer's own title, now 24 px in a font of its own, in a grey between that title and the rows; a chapter's reads "1. BRAITENBERG". Amends D-069, D-326.**
The physicist's, of four drawn for the chapters, then toned down and extended to every heading:
"CHAPTER 1: BRAITENBERG" was in the small capitals of a section title, dimmed, as small as Parts'
group titles; in the rows' white it stood out too much, and no heading may be larger than its
drawer's title. Section titles ("SAVE/LOAD", "OBJECTIVES", "ACTIVE BOARD"), titles that fold
(Parts' groups, the chapters) and the Text drawer's fields' titles are drawn by one function,
`draw_heading`, lit in the accent as before while a tutorial step explains them. The chapter's
number before a dot sits over its levels' "1.1", "1.2"; "Ch." added nothing under a drawer
titled Chapters.

**D-421 — 2026-10-08 — A row's info disc sits 50 px from the row's right end, just before its count, lock, infinity sign or tick, in one column in every drawer; a switch reads "on" in white and "off" in grey, with no tick. Amends D-051, D-054.**
The physicist's: the disc stood 156 px from the row's left, far from the lock or the infinity
sign at the right end, a gap of some 26 px. Measured from the right it sits close to them, and
long names get more room. "Key hints ✓ on" was the widest status and ran into the disc; the
switches, Key hints in Settings and the shadow in Hints, now say "on" or "off" alone, the word's
colour telling which, as Fast forward says "4x". A click on the disc falls where it is drawn.

**D-422 — 2026-10-08 — The bar between a drawer's parts is drawn two shades lighter, in the secondary text's grey, and the Board's Diagnostic has one between its active board and its level. Amends D-065, D-407.**
The physicist's: the bar over the run's objectives, and the one in the Editor's Files between
Save/Load and the levels to start from, were in the rules' grey, barely seen on the panel. Rules
that outline a box or a column keep their grey; a bar that divides a drawer is `DIVIDER`. Under
the Editor's Files' bar, 12 px before the levels to start from, not 6.

**D-423 — 2026-10-08 — No semicolon in what the game shows: a period or a colon in its place, in info boxes, status lines, notes, refusals and tutorial cards.**
The physicist's. Fourteen went: "…but the level's own. Undo brings them back.", "Click or drag
to pick cells or parts. Shift adds.", "this level hands out one eye. The board has two", the
cards of 0.1 Wiring and 0.6 Diagnostic, and the rest of their kind. Comments and the docs keep
theirs.

**D-424 — 2026-10-08 — Lights are solid, discs of 1 u that a swimmer slides round as it does an obstacle; each obstacle is a sphere in the same fluid as the swimmers, held at its rest by a spring, and gives a little when pushed: SPRING_GIVE, 0.30 u, under a head-on push of two thrusters at full rate. Amends D-019, D-022; the stage's scope takes them in.**
The physicist's, from the ideas logged with D-406. Lights stay fixed: a light that moved would
change what the eyes read. An obstacle and a swimmer touching share an overlap as their Stokes
drags say, ζ = 6πμR each, neither having inertia; the spring pulls the obstacle back,
ζ du/dt = -k u, k = 2 THRUST / SPRING_GIVE, by an Euler step as the swimmers move, so that under
a steady push it settles exactly at k u = F, whatever its size, a larger sphere only slower, and
let go it comes back without ringing. Its displacement is the run's state, shared by every
swimmer as one world: the plane it is in (`Arena.moved`) is what `world.step` takes and gives,
what the run records and puts back, what the eyes' shadows and the goals' "reach an obstacle"
read, and what is drawn. A light counts as reached at 1.05 times the touching distance (D-043),
so a swimmer that runs into one has reached it, and "Don't touch the light" is lost as before.
Every shipped level's proof still wins; the tests' model boards win too, Greed's 0.7 s sooner,
round a light it went through, Patience's 0.1 and 0.3 s sooner, Shadows' 7 ticks sooner. No
level is changed until the physicist has seen it on screen. First 0.15 u, doubled after a look.
