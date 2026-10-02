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
An activity bar down the left edge, one icon per drawer; one drawer open at a time, pushing the
board aside, folded by its icon or an arrow on its edge; every drawer's rows alike (icon, name,
(i), then a count, a key, a lock or a tick). At the top, what the player works with: in the
editor Parts (puzzle-piece), which is also the parts' encyclopedia, Tools (screwdriver-wrench),
Files (floppy-disk), Sense (stethoscope), Navigator (compass); in the Run Objectives
(list-check), Inside (magnifying-glass), Score (trophy), Navigator. At the foot, in both:
Settings (gear), Chapters (map), then an accented switch between the environments, Editor and
Run, which are also tabs over the content (no Builder tab until there is a builder): Run (play)
in the editor, back (diagram-project) in the Run. Chapters, not "Map", replaces the full-screen
map. Settings holds fast forward's speed, key hints, tooltips' delay, Fear's tutorial again, and
Sound and Music once there is sound; not the palette. Tools stay in their drawer while the ring
round a selected cell (todo §7) brings them to the hand; Parts and the ring both hand out parts,
and complement each other. Sense and Inside show one circuit, the board as it runs, with no
numbers and a level meter by each eye and thruster in accent 1, the colour of their faces; a
swap button exchanges the drawer and the main screen. In the editor it runs where a probe
stands, the swimmer put anywhere on the level and turned, nothing run or scored; two icon
buttons over the editor switch views at any time: the Diagram view, a hex grid, and this Run
preview, beads through a diamond. There, each eye's meter is a handle the player drags to set what
the eye reads, to see how the circuit answers: a test input, kept nowhere and never seen by the
run, so the board itself still holds no continuous parameter (brief: "No sliders"). This amends
D-016, whose sensor sliders were the developer's only. This session's winning boards are kept in memory; Files can
wait, and a board as text is its own PR (todo §9). The run's controls go to a bar under the
arena. Fear's tutorial is rewritten with the bar. Decided from three rounds of mockups drawn with
the game's own palette and renders.

**D-052 — 2026-10-02 — In every circuit view, parts keep their colour; a level meter by each eye and thruster shows its rate, all meters alike, in accent 1. Amends D-017's shading.**
The beads and the meters already show the rates, so shading each part by its rate said it twice.
Wherever the circuit is drawn (the run's Inside, the developer view, and the Sense and Inside
drawers to come), a part keeps its fill, and each eye and thruster has a meter beside it: 1.0 hex
size tall, 10 px wide, its centre 0.86 hex size to the right of the part's, past any part's reach
whichever way it turns, filled from the foot up to its rate in accent 1 (`METER`), the colour of
the part's face. The developer view's thruster bars become these meters, on the eyes too, opposite
its sliders; it keeps its names and numbers.
