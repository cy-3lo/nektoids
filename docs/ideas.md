# Ideas for later

Not in the current stage's scope (`CLAUDE.md`, Scope). Each line says where the idea comes from.
An idea moves to [`todo.md`](todo.md) only with a decision in [`decisions.md`](decisions.md) that
puts it in scope: a stage opens with one (D-105). Until D-028 these were logged in the decision
log as "post-jam".

## The order after the jam (D-105)

The jam build shipped as v1.0 (D-106). Listen still: Camille's views and strangers' runs on
itch.io (brief §3: do five strangers finish the real level?) may reorder what follows. Five
stages, in this order.
Each opens with a decision that sets its scope, as the scope lock did for the jam, and each
brings its own levels.

0. **Foundations**: one table of part kinds, sensors in general, a level format with a version,
   saving and a board as text. Done (D-200 to D-206, #46).
1. **A level maker**, for us and Camille first, then for players. Under way (D-300).
2. **Memory**: tanks, valves, loops in the editor, lights that change in time.
3. **Flows and flow sensing**: streams and vortices as items, a swimmer they carry, a sensor
   that reads them.
4. **Actions other than moving**: a lamp first, and something that reads it.

Collectives, sensor layout, the score's histograms, sound and art come after; their sections
close the file.

## 0. Foundations

Done: D-200 to D-206, built on `stage/0-foundations` and merged into `main` in #46.

## 1. A level maker

In the todo, §11, since D-300: built on `stage/1-level-maker`.

Later, from the board's locked parts (D-319): a level that starts with wires, or with parts
the player may move, as Aggression's prewired eye and thruster; the Maker places locked parts
only, the player wiring them.

## 2. Memory: the graph's vocabulary

- **Tanks**: reservoirs that store signal, the memory (D-015, `.claude/rules/graph.md`). Their
  law (the physicist, 2026-10-04): T dh/dt = in − h, and the tank sends out its level h, with
  T ≈ 4 s. That is the lag of every node (D-017) with τ = 4 s instead of `TAU` = 1/60 s: in
  `graph/laws.py` (D-202), `Relax(Scaled(1.0), tau=4.0)`, one entry in the table of kinds, and
  `test_laws.py` already checks its fill, 0.5 (1 − 1/e) after T, and that T h is what came in
  less what went out. Being linear, a tank forgets over about T. Its level drawn as a fill.
- **Valves** (the physicist's "diode", 2026-10-04): a control b cuts a flow a,
  out = max(0, a − b), and b itself is not changed. Each bead of b stops one bead of a, which
  the beads can show. A diode would add nothing: every wire is one-way already (D-016).
  Difference is |a − b|, the full wave; a valve is the half wave, and the order of its inputs
  matters, so the board must show which one is the control: the control wire ending in a bar,
  ⊣, as repression is drawn in gene networks? With a Source a valve inverts: max(0, 1 − b). It
  is no threshold: its output stays graded. Its law is three lines in `graph/laws.py` (D-202),
  but wires come into a node sorted by the part that feeds them: the control needs ports first.
  - Does b end at the valve, to be forked before it if needed elsewhere (D-016), or pass on
    through it, which makes a part with two outputs?
  - Set aside: a(1 − b), divisive and smoother, but it shuts only when b is full.
- **Loops in the editor**: the dynamics accept them already, with memory as a consequence
  (D-017). With tanks and valves they give a flip-flop: a tank whose output comes back to it
  undiminished, Doubles making up for the fork, holds its level for good; with more gain it
  fills up and stays full; a valve on the loop empties it.
- **Lights that change in time** (2026-10-04): a light item with a schedule, its power a
  function of t, deterministic: a light that flashes once and goes dark, lights that switch on
  in turn. Levels where what the eyes read now is not enough, so memory is needed.
- **A threshold node**, as a deliberate, costed choice; never in the first levels (brief §1).
- **Colours for signals**: beads coloured by identity (brief §1); the palette's colour picker
  is waiting for it (D-025).
- **Signals in three colours** (the physicist, 2026-10-04): colour carried and changed by the
  circuit, not only drawn. A signal becomes three rates, (r, g, b), each in [0, `RATE_MAX`].
  - A bead has one colour, so a wire carries three streams of beads, each at its own rate. A
    wire is never drawn in a blended hue: 0.3 red with 0.7 green read as one hue cannot be read
    (invariant 6).
  - Today's laws act channel by channel, unchanged: split, ×2, ÷2, Sum, Difference, the lag,
    tanks, valves. New operators: a filter that passes one colour or stops one; a shifter that
    turns colours round, r → g → b → r.
  - Colours come from coloured lights, with eyes that send each colour as they receive it, and
    from Sources of a colour. They go to thrusters, which push with all their channels or with
    their own colour only, and to the lamp (stage 4), which shines the colour it is fed, so a
    swimmer can signal.
  - Levels: go to the red light and flee the blue one; two lights a colour-blind circuit cannot
    tell apart.
  - Cost: `y` goes from (N, n) to (N, n, 3); the laws take the channels as a trailing axis
    (D-202), and numpy broadcasts them.
  - Today's levels must play as they do: white light is all three channels, so does a thruster
    sum them or take their mean?
  - The three hues join the one palette (D-047, D-049), not pure RGB: red against green is the
    commonest colour-blind confusion. A bead shape for each colour as well?
  - Colours come in a chapter of their own, never in the first levels.

## 3. Flows, and the other senses (brief §2)

- **Stokes flow round the swimmers.** Each swimmer a moving singularity (a stresslet ~1/r, or a
  source dipole ~1/r² for a local neighbourhood), the field summed analytically at each sensor.
  Pushers and pullers have opposite far fields, so the sign is information; sensing is
  reciprocal (swimming hard makes you findable: a stealth level); walls come with image
  singularities, so wall-following emerges from flow sensing.
- **Flow sensing**, the sense that reads that field: direction and sign from its asymmetry.
- **Background flows as items** (2026-10-04): analytic and superposed, evaluated at the bodies
  and the sensors in one broadcast: a uniform stream, a simple shear, a point vortex with a
  Rankine core, a source and a sink, a disc in a stream (a doublet). They come before the
  swimmers' own flow: one swimmer has nothing else to sense.
- **A swimmer in a flow** (2026-10-04): overdamped as in D-022, by Faxén's laws for a sphere
  (D-045): V = u(x) + F/(6πμR), Ω = ω(x)/2 + T/(8πμR³). Faxén's R²∇²u/6 vanishes in every flow
  above, potential or linear (a Rankine core turns as a solid), so these are exact.
- **A flow sensor** (2026-10-04): a part turned like an eye, reading the flow past it, relative
  to the body, along its facing: max(0, (u(x_s) − V − Ω × r_s)·n), never negative (D-014); two
  facing opposite ways give the sign. It is a sense: a name in the table of kinds, a function
  in `sim/world.py`'s `SENSES` (D-203). Two consequences worth levels:
  - A uniform stream cannot be felt: the body drifts with it. Rheotaxis needs a shear, a wake,
    or a light to hold on to. A body that only drifts in a linear flow reads the strain alone,
    E·r_s, Faxén's spin taking out the vorticity.
  - A swimmer feels its own swimming as a head wind: the egomotion the brief asks the player
    to subtract from optical flow. Whether the sensor reads it is the stage's first decision.
- **Levels for flows** (2026-10-04): reach a light that thrust alone cannot, the stream
  carrying; hold station in a shear; cross a vortex; find the sink.
- **Tracer particles** to show the flow: a toggleable overlay; the game must read without it.
- **Walls as items** in the open plane: segments, with contacts and shadows (D-028).
- **Solid lights**, and swimmers that touch each other (D-022).
- **Chemical fields**: trails, alarm, plumes; diffused history rather than current state, on a
  coarse grid. Two sensors give a gradient, one only a level.
- **Optical flow**: it conflates egomotion with others' motion, and the player must subtract it.

## 4. Actions other than moving

- **A lamp** (the physicist, 2026-10-04): a part whose rate sets the power of a light at its
  mount, read as D-019 reads lights: 1/r, a cosine, shadows; a light that moves, in
  `eye_rates`. Shining all round, or a beam that faces where it is turned? Its swimmer's own
  eyes do not see it at first, the body being transparent to its own parts (D-018); seeing it
  would be a loop through the world. It is an action: a name in the table of kinds, a function
  in `sim/world.py`'s `ACTIONS` (D-203).
- **Something that reads the lamp**: with one swimmer, nothing does yet.
  - Photo-targets, items that count the light they receive: a dose objective, "light the three
    beacons", with shadows in the way.
  - Moths: bodies with a fixed wiring in the level's data, Braitenberg's 2b, that the player
    herds into a ring with the lamp. They are several agents: the sim is written for N
    (`.claude/rules/simulation.md`), but bodies with different graphs are new, and the first
    step to Collectives.
- **Other actions**: loose discs to push (contacts exist, D-022); a pump, a source or a sink in
  stage 3's flow that other bodies feel (the brief's reciprocal sensing).

## Collectives

- **Flocks**: many agents, pairwise (N, N) broadcasts (`.claude/rules/simulation.md` already
  asks for code written for N). Countable goals: 40 of 50 past the gap, split and rejoin round
  an obstacle, keep cohesion while a predator passes (brief §1).
- **Predator and prey**: two populations, herding prey into a pen.
- **How routes divide**: by sense, by collective, or one as the depth of the other (D-028, left
  open).
- **The generalisation pillar**: one rule set, five seeds or environments, all must pass
  (brief §1).

## Sensor layout, a second authored artifact (brief §2)

- **How many eyes, what aperture, where on the body**, each costing size; non-unique solutions.
- **Icons for sensor types** inside the shapes, when there is more than one (D-008, D-012).
- **Levels with more than two eyes or thrusters, on zones wider than 19 cells.** The sandbox
  tries it first: every part without limit, on 37 cells (D-102; the physicist, 2026-10-04).

## Score

- **Histograms per axis**, Zachtronics-style: where you stand among all players on each axis,
  not a ranked list. Needs a server, or distributions shipped with the game.
- **More axes**: area on the board, wire crossings (brief §1: crossings expensive, D-007).
- **Bests kept between sessions**: a board has its text (D-205) and Save/Load copies it (D-206),
  but nothing is kept between sessions. The page's storage (`localStorage`), reached as the
  clipboard is (D-206), could keep the wins of Files.

## Interface

- **Touch**, from Camille's notes (`ebc4abb`; todo §7 until D-104): no hover and no keys. The
  tooltips (D-025) and L, R, Space, Esc and 0 need an on-screen form. One gesture stays one undo
  step (D-027). The Wheel (D-068, D-069) does the rest: a click on a cell shows what can be done
  there, a click on a part arms Wire, a drag moves a part, or draws a wire with Wire chosen
  (D-072).
  - Does a phone's keyboard come up for Chapters' passkey field (D-075)? If not, the field
    needs letters of its own on screen.
  - Paste a board's field is a text field of the page itself (D-206): on a phone it may bring
    the keyboard up, and the passkey field could be made the same way.
  - The canvas is 960 × 640 px: on a phone a 40 px hex is about 16 px wide in portrait and
    24 px in landscape, where a finger wants about 44. Landscape only, larger hexes?
  - Under pygbag, do touches arrive as mouse events or as FINGERDOWN only? Try on a phone
    first.
  - How far must a finger move before a tap becomes a drag? Today a press becomes a drag
    once the pointer leaves the part's cell (D-085): enough for a finger on large hexes?
- **A board that does not fit, shown in red** (the physicist, 2026-10-04): loading a text or a
  win that a level cannot hold puts it on the board anyway, its surplus parts in red, instead of
  refusing with a message (D-092, D-206).
- **Parts as the encyclopedia** (todo §8 until D-104): a row opens into its entry, in the
  drawer; today the entry opens in a box beside it. The rest of the activity bar is built
  (D-053 to D-069).

## Presentation

- **Sound, art.**
- **Sound and Music in Settings**, once there is sound (D-054; todo §8 until D-104).
- **GIF export of a run**: it made Opus Magnum's solutions a social object (brief §4).

## Studio

- **The domains nektoids.com and nektoids.io** (the physicist, 2026-10-04): both unregistered
  that day (`whois`). The itch.io page has made the name public (D-106), and a .com costs about
  €10–15 a year. A .io costs more, and its future has been uncertain since the 2025 UK–Mauritius
  treaty on the Chagos, so the .com first.
- **v1.1 on itch.io** (2026-10-05): `main` has had Save/Load since #46, which v1.0 does not.
  Upload it before stage 1 ends, or wait for the level maker?
