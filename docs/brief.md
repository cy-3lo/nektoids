# Zach-like collective behaviour game — working brief

The player does not steer agents. The player authors the **regulation** —
the wiring from sensors to responses — then presses run and watches a
deterministic physical simulation play out.

---

## 1. Design principles

### The loop (five beats)

1. Player receives a **spec**, not a puzzle: inputs, required outcome, constraints.
2. Player authors a **mechanism** (node graph), not a solution path.
3. Press run. Deterministic simulation plays out and is watched.
4. Failure is **legible** — the player can see why.
5. Success is scored on **several incompatible axes**, so optimisation never terminates.

### Non-negotiables

**No sliders.** Continuous weight-tuning turns the player into a bad gradient
descent. The authored artifact must be discrete and structural: which sensor
feeds which response, which wires cross, discrete gain nodes.

**But not bang-bang either.** The escape: beads carry magnitude as *rate*, not
value, and outputs integrate incoming bead rate. A sensor emitting 8 beads/s vs
2 beads/s is proportional control with no continuous parameter anywhere in the
graph. Bang-bang only appears if the player inserts a **threshold node**, which
then becomes a deliberate choice with a cost rather than the only option
available. Discrete gain via ×2 and ÷2 nodes on top. A leaky-integrator node
gives memory and smoothing later. **Keep thresholds out of the first levels
entirely.**

**Thrust budget, not node budget.** Constant thrust force. Graph complexity
increases body size, size increases drag, drag reduces speed. Complexity becomes
an in-world consequence the player *feels* rather than a counter they read off a
scoreboard. It couples to stealth for free: a bigger agent is a louder stresslet.
This replaces node-count scoring entirely.

**Determinism, fixed seeds.** Same rules, same layout, same outcome. Stochastic
boids make failures unreproducible and the loop collapses.

**Countable win conditions.** Not "look at the pretty flock". Get 40 of 50 agents
past the gap. Split around the obstacle and rejoin. Keep cohesion above threshold
while a predator makes three passes. Herd prey into the pen.

**The generalisation pillar.** One rule set, five seeds / five environments, all
must pass. This is the original contribution: most puzzle games reward hardcoding
a solution to one level. Making generalisation the tested skill is both true to
biology and, as far as I can tell, not something any game does.

**Spatial scarcity in the editor.** LabVIEW is the cautionary tale: infinite
canvas, and every real program becomes unreadable spaghetti. Small fixed grid,
node budget, wire crossings expensive, area as a scored axis. Layout becomes part
of the puzzle instead of a mess the player tolerates.

### Legibility (the thing that decides whether it works)

The swarm is illegible by construction. One agent inside the swarm is not.

- **Click an agent to inspect it.** Highlight its neighbours, show its sensor
  inputs as live beads on the wires, draw its steering vector.
- **Beads on wires.** Density = magnitude, colour = identity, spacing = rate,
  direction = flux. Readable at a glance and physically honest.
- A player must be able to look at a failed run and see *which wire went dark*.
- Precedent for the animated-execution display: Unreal Blueprint's debugger.

---

## 2. Sensors — physical, not abstract

Abstract sensors ("neighbour direction") hand the player information no real
agent has. Physical sensors give ambiguity, and ambiguity is the puzzle.

| Sensor | What it gives | Cost to build |
|---|---|---|
| **Optical opacity** | 1D angular field: something is there, not what or how far | Ray casting — trivial |
| **Chemical** | Diffused *history*, not current state. Trails, alarm, plumes | Coarse grid diffusion — cheap |
| **Optical flow** | Conflates egomotion with others' motion — player must subtract it. Best aha moment | Moderate |
| **Flow sensing** | Direction and sign from field asymmetry | Analytic, see below |

**Build order:** opacity → chemical → optical flow → flow sensing. Each is a new
node in the same editor, so the game grows by addition rather than rewrite.

### Sensor layout as a second authored artifact

How many eyes, what aperture, where on the body, how far apart the two flow
sensors sit. Wider spacing gives better directional discrimination but a bulkier
agent. Two chemical sensors give a gradient; one gives only a level. More sensors
cost more → natural second scoring axis → non-unique solutions.

### Hydrodynamics: singularities, not a solver

No Navier–Stokes. Linear superposition of **stresslets** or **potential dipoles**,
each agent a moving singularity, field evaluated analytically at each sensor
point. Closed form, instant, O(N²) at 100 agents is nothing.

Decay exponent is a **design** decision as much as a physical one:

- 2D stresslet ~ 1/r — honest for a force-free swimmer, but slow decay couples
  everyone to everyone. Hurts legibility, makes failures global.
- 2D source dipole ~ 1/r² — gives a local neighbourhood the player can reason about.
- Want the stresslet anyway? Add a smooth cutoff radius and present it as a
  *sensor property*, not a fudge.

**Three things the stresslet buys that are worth the trouble:**

- **Sign is information.** Pushers and pullers have opposite far fields. A player
  can wire a discriminator that tells predator from prey by field topology alone.
- **Sensing is reciprocal.** You disturb the flow you read. Weaker stresslet =
  quieter but slower. Swimming hard makes you findable. A stealth level where you
  must cross a predator's sensing range without being heard is physically correct
  and, as far as I know, unbuilt.
- **Walls come free via images.** Image singularities behind each wall give
  boundaries their own hydrodynamic signature. Wall-following emerges from flow
  sensing with no separate contact sensor — which is what real swimmers do.

### Visualising the field

Advected tracer particles: a few thousand, seeded uniformly, re-seeded as they
leave, opacity by local speed. Cheap, and *motion is what reads*. Line integral
convolution is prettier if wanted later.

**Caution:** the field is beautiful and you will be tempted to make the game about
looking at it. Keep tracers as a toggleable overlay and make sure the game is
readable with it off. The content is the rules, not the flow.

---

## 3. Weekend jam TODO

Target: three tutorial levels plus one real level, playable in a browser, in
~2 days. Throwaway by design.

### Toolchain: Python → browser

**pygame-ce + pygbag.** Write normal pygame, run `pygbag main.py`, it compiles
CPython to WebAssembly and emits a folder with `index.html`. Zip, upload to
[itch.io](http://itch.io/) as an HTML5 project. People ship Ludum Dare entries this way every round.

Three things to know going in:

- **Load time** ~5–10 s behind a progress bar (the Python runtime is a few MB).
- **Speed:** WASM CPython has no JIT. Keep positions and velocities as **numpy
  arrays** and compute the whole interaction matrix at once — never loop over
  agents. numpy is available under pygbag. This is how the physics should be
  written anyway.
- **Structural quirk:** the main loop must be `async` with
  `await asyncio.sleep(0)` every frame so the browser can breathe. One line, but
  it has to be there from the start.

### Scope lock (decide before writing code, do not revisit)

- [ ] 2D, top-down
- [ ] **One** sensor type: optical opacity, two of them, fixed positions
- [ ] **Two** outputs: left thruster, right thruster
- [ ] Node vocabulary: wires only, plus ×2 and ÷2. **No threshold node.**
- [ ] 3 Braitenberg tutorial levels + 1 real level
- [ ] Fixed seed, fully deterministic
- [ ] pygame-ce, exported via pygbag

### Why Braitenberg for the tutorial

Two sensors, two thrusters, and the only choice is **crossed or uncrossed** —
fear versus aggression. A complete lesson in sensor-motor wiring, with two wires
and no text.

- Level 1: uncrossed → agent flees the light/obstacle
- Level 2: crossed → agent charges it
- Level 3: introduce ÷2 on one side → asymmetry, orbiting

Simulators exist all over the web; none I know of with a bead display. The
visualisation is the original part.

### Day 1 — simulation + editor skeleton

- [ ] Agent integrator, fixed timestep, deterministic, numpy-vectorised
- [ ] Ray-cast opacity sensor, drawn in the agent's own frame
- [ ] Wall collision
- [ ] Node graph data structure: sensors → gain nodes → thrusters
- [ ] Graph evaluation per tick
- [ ] Ugly-but-working editor: place node, drag wire, delete
- [ ] Run / reset button

### Day 2 — legibility, levels, ship it

- [ ] **Beads animating along wires during run** (rate = magnitude)
- [ ] Click-to-inspect an agent: sensor values live, steering vector drawn
- [ ] 3 Braitenberg levels + 1 real level with a countable win condition
- [ ] Body size grows with graph complexity → drag → visibly slower
- [ ] End screen: *"If you liked this and want to support development, reach out"*
      with a contact link
- [ ] `pygbag` build, zip, upload to [itch.io](http://itch.io/)

**Explicitly out of scope for the weekend:** flocking, multiple agents, flow
sensing, chemical fields, optical flow, sensor layout editing, threshold nodes,
the generalisation pillar, sound, art, saving, undo.

**Success criterion:** do 5 strangers finish the real level, and does anyone
email? Nothing else matters at this stage.

---

## 4. Homework

### Play (in this order)

- **Gladiabots** — visual behaviour trees, then watch a match you cannot
  intervene in. Closest shipped thing to this design. Play first.
- **Opus Magnum** — purest form of the loop. GIF export turned solutions into a
  social object.
- **Shenzhen I/O** — signals on wires; teaches a system through a printed manual
  rather than a tutorial.
- **SpaceChem** — the original spec-in/spec-out formulation.
- **Polybridge 2** — for legible failure, nothing else comes close.
- **Baba Is You** — rules as manipulable objects.
- **Factorio** — the circuit network specifically, not the factory.

Zachtronics closed in 2022; fans named the genre "Zach-likes", spanning the
explicitly programming ones (TIS-100, Shenzhen I/O, Exapunks) and the sneakily
programming ones (Opus Magnum). Catalogue on Steam and [zachtronics.com](http://zachtronics.com/).

### Read / watch

- **The Algorithmic Beauty of Plants**, Prusinkiewicz & Lindenmayer —
  free at [algorithmicbotany.org/papers](http://algorithmicbotany.org/papers). Plus his later auxin-transport papers.
- **Bret Victor, "Inventing on Principle"** — [worldofend.com/talks](http://worldofend.com/talks). Immediate
  visible feedback between rule and consequence. 20 min; will shape the interface
  more than any game design writing.
- **Nicky Case, "Explorable Explanations"** — [explorabl.es](http://explorabl.es/) and [ncase.me](http://ncase.me/).
- **Craig Reynolds, boids** — [red3d.com/cwr/boids](http://red3d.com/cwr/boids). Canonical formulation + bibliography.
- **Sebastian Lague** (YouTube) — simulation-as-content, done well.
- **Game Maker's Toolkit** (YouTube) — standing reference on mechanics-first design.
- **Zach Barth's GDC talks** — GDC Vault / YouTube, on building puzzles around a
  system rather than the reverse.

### Tools & venues

- **pygame-ce + pygbag** — the Python-to-browser path. Start here.
- **Godot** — [godotengine.org](http://godotengine.org/). Only if the project outgrows canvas-level 2D;
  GDScript reads Python-adjacent but is a week of learning curve for no gain at
  prototype scale.
- **raylib + Emscripten** (C++) — the alternative if native speed and a desktop
  build ever matter. Tiny API, no engine concepts. Swift is out: browser delivery
  via SwiftWasm is research-grade.
- **Braitenberg, *Vehicles: Experiments in Synthetic Psychology*** — the source
  for the tutorial design.
- **[itch.io](http://itch.io/)** — publishing + the jam ecosystem
- **r/gamedesign**, Godot forums — feedback that isn't from friends
- **GMTK Game Jam** — ran 22–26 July 2026; sign-ups on [itch.io](http://itch.io/) well ahead of the next
- **Ludum Dare** — winding down, six more events committed through 2028
- Smaller [itch.io](http://itch.io/) jams run continuously — better for a first attempt, lower stakes
