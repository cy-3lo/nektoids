# Walkthrough: `graph/` and `editor/`

For Camille, for when you want to read the code behind what you play (D-041). This page is the
map: read it with the code open beside it. It takes about half an hour, and nothing here needs
Claude.

Read the sections in order: run the editor, see what it does, follow the code in the order it
runs, then check yourself with the questions in section 3. Section 4 lists what is weak or
untested, which is where your review matters most.

## 0. Run it first

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
python game/main.py
```

In the window, try:
- drag an Eye, a Sum and a Thruster from the left menu onto the lighter cells;
- wire them with the Wire tool (drag from one part to another);
- turn a part: it is selected once placed (or click it with Move), then L turns it left and R
  right, as do the two turn buttons;
- drag a part with Move and watch its wires follow;
- hover with Delete to see what would go;
- undo and redo with the Edit buttons or Ctrl+Z, Ctrl+Shift+Z (Cmd on a Mac).

Hover a button on the right for a second to see its shortcut key.

Press F2 for the developer view (section 6): the board as a running circuit, with its equations. Tab steps through eleven example boards, and F2 brings you back.

## 1. What it does

The editor lets the player place components (sensors, operators, actuators) on a small hex
board and join them with directed wires, which route themselves around everything already there.
The result is the agent's controller: a small graph that the simulation will later evaluate at
every step.

## 2. The code, in the order it runs

### 2.1 One frame: [`game/main.py`](../game/main.py)

At startup, `main.py` builds four objects:
- the fonts (`Fonts.load()`, which also reads the icon font once);
- a board (`free_board()`);
- the screen layout (`make_layout()`);
- the `EditorScene` that ties them together.

Then comes an `async` loop, which pygbag needs so the browser gets control back every frame.
Each frame it:
1. passes every pygame event to `scene.handle_event`;
2. calls `scene.update()` (timers);
3. calls `draw(screen, scene, fonts)`;
4. flips the display;
5. waits for the next tick and yields with `await asyncio.sleep(0)`.

That split is the architecture. **The scene changes state, drawing only reads it**, and the
board changes only through its own methods.

### 2.2 Hex coordinates: [`graph/hexgrid.py`](../game/nektoids/graph/hexgrid.py)

- **Cells** are axial coordinates `(q, r)` on pointy-top hexes, with screen y pointing down.
- **Directions** are indices 0 to 5 in the order E, NE, NW, W, SW, SE. So `opposite(d) = (d + 3) % 6` and the three axes are `d % 3`. The module docstring draws them.
- **Pixels:** `to_pixel` and `from_pixel` convert between cells and pixels. `from_pixel` uses cube rounding, the standard way to snap a point to the nearest hex.
- **Board shapes:** `hex_disc(r)` gives the 3r(r+1)+1 cells within r steps. `offset_rect` gives a rectangle, which the tests use.
- **Keyboard:** `vertical_step` is what the up and down arrows use. Hexes have no N or S direction, so it zigzags NW/NE to keep a straight column on screen.

Everything here is a pure function, tested in `tests/test_hexgrid.py`.

### 2.3 The board: [`graph/board.py`](../game/nektoids/graph/board.py)

This is the player's artifact, and it has no pygame in it (`tests/test_architecture.py` enforces
that).

**Data:**
- **`Kind`** is the vocabulary: Eye, Source, Double, Halve, Sum, Difference, Thruster. Each kind knows:
  - its `category` (sensor, operator or actuator);
  - whether it `emits` and `receives`;
  - its `default_facing` (eyes and thrusters point somewhere, the others don't);
  - its input and output limits (Sum and Difference: two in, one out).
- **`Node`** (id, kind, cell, locked, facing) and **`Wire`** (source id, target id, path) are frozen dataclasses. A wire's `path` runs from the source cell to the target cell, both included.
- **`Board`** holds:
  - `cells`, the level's zone;
  - `nodes`, a dict by id; ids increase and are never reused, so dict order equals id order;
  - `wires`, in the order they were drawn;
  - the stock (`remaining`, `total`).

**Invariants.** Every method keeps these true:
1. a node sits on a cell of the zone, and no other node or wire uses that cell;
2. no wire passes through a component's cell;
3. no cell edge is used by two wires, which is the crossing rule (D-010);
4. the wires contain no cycle.

**Operations:**
- `place`, `remove_node`, `move_node`, `rotate`, `connect` and `remove_wire`.
- Anything the player can get wrong returns `Refused(reason)` instead of raising, so the editor can show the reason on screen.
- `preview` does every check `connect` does without changing anything: same component, output/input kinds, duplicate, loop (`_reaches` is a DFS), the input/output limits, then routing. The editor uses it for the ghost route.
- `move_node` is all-or-nothing. It lifts the node's own wires, moves the node, and routes them again one by one. If any finds no path, it restores the node and the wires exactly as they were.

**The crossing rule** is two small functions:
- `crossings(path)` lists, for each free cell a wire crosses, the edge it comes in by and the edge it leaves by.
- `can_pass(edges_used, into, out)` says whether a new wire may enter a cell heading `into` and leave heading `out`: no U-turn, and both edges still free.

**Routing** (`route`) is Dijkstra's algorithm over states `(cell, heading)`, not just cells. Whether you may cross a cell depends on where you come in and where you go out, so the heading is part of the state.
- **Cost:** the tuple `(steps, bends)`, compared lexicographically. Shortest first, then straightest.
- **Heap entries:** `(steps, bends, counter, cell, heading, path)`. The counter increases with every push and neighbours are tried in the fixed direction order. So when two routes cost the same, the one pushed first wins, and the result never depends on hashing or dict order. That's invariant 1 of the project, determinism.
- **Stopping:** the goal is accepted when it is popped, not when it is pushed, so the cheapest way in wins.

### 2.4 Levels: [`levels/sandbox.py`](../game/nektoids/levels/sandbox.py)

This file holds two starting boards on the 19-cell zone `hex_disc(2)`:
- `free_board()` gives the player the parts in stock.
- `tutorial_board()` pre-places locked eyes and thrusters. The placements are listed in a tuple rather than a dict, because the order sets the node ids.

### 2.5 Screen and view: [`editor/layout.py`](../game/nektoids/editor/layout.py)

The screen has three columns: the menu on the left, the grid in the centre, the palette on the
right, in titled sections of two buttons a row: View, Tools, Colours, then Edit, with undo,
redo and, greyed until saving exists, save and load (D-025, D-027). This
module has no pygame either (tested in `tests/test_layout.py`).
- **`Layout`** is frozen. It holds the fixed rectangles, and `make_layout(folded)` builds it again when a menu group folds.
- **`View`** is how the grid is seen: the hex size and where cell (0, 0) sits on screen. `zoom` (which keeps the point under the zoom fixed) and `pan` return a new `View`. They never touch the board (D-013).
- **Hit-testing** answers "what is under this pixel": `cell_at`, `menu_item_at`, `tool_at`, `view_button_at`, `group_at`, `palette_target_at`.
- **`visible_cells`** lists every hex that shows in the grid area.
- **`_section`** lays out one palette section: its title, its buttons two a row, and where the
  next starts. `palette_titles` are drawn; `palette_room` is kept free.
- **`TOOL_KEYS` and `VIEW_KEYS`** are the shortcut letters; `TURNS` says which way each turn tool
  goes, in hex directions (counter-clockwise is +1).

### 2.6 Input and interactive state: [`editor/scene.py`](../game/nektoids/editor/scene.py)

`EditorScene` owns everything that changes while the player works:
- the current `tool` and the `view`;
- what is being carried: `picked` and `dragging` for Add, `source`, `pressed` and `fresh` for Wire, `moving` for Move, `panning_from` for the hand, `cursor` and `carrying` for the keyboard;
- what is under the mouse: `pointed` (any grid cell) and `hover` (only zone cells);
- `selected`, the part the turn buttons and keys act on (D-025);
- the last refusal (`message`, `flash_cell`).

It calls only the board's public methods.

**Following one event:**
- `handle_event` dispatches. Mouse motion and button presses first set `cursor = None`: the mouse takes over from the keyboard.
- `_track(pos)` runs on every mouse move:
  - it pans if the hand is dragging;
  - it updates the tooltip timer and recomputes `pointed` and `hover`;
  - it refreshes the ghost route when the hovered cell changes;
  - when the pointed cell changes during a Move, it takes one step of the move.
- `_press(pos)` checks in priority order: a palette tool, a view button, a menu title (fold), a menu item (pick up a part), and only then the grid, where it acts according to the tool.
- `_release(pos)` ends drags: the Add drop, the Move, the pan, and the Wire decision.

**The Wire tool** is the subtlest part:
- A press only records `pressed`.
- The release decides (`_end_wiring`):
  - releasing on the node you pressed is a click: it picks the source, connects the chosen source to that node, or drops the source on a second click (`fresh` tells the two apart);
  - releasing anywhere else is a drag, from the pressed node to the one under the mouse.
- Either way, `_connect` asks `board.orient` which end is the source (D-026): a wire drawn from a
  thruster or into a sensor is turned round; between two operators it runs as drawn.
- `_wire_start` says where the ghost route is drawn from, and `_update_ghost` computes it:
  - `board.route` over an empty cell, drawn dim, into the part if it is a thruster;
  - `board.preview` over the other end, oriented, drawn bright if it may connect.

**Info boxes (D-036):** `info_at` comes before `menu_item_at` in `_press`, so a click on a row's
disc opens its box instead of picking the part up; while a box is open, `handle_event` spends the
next click or key on closing it. The texts are in [`editor/parts.py`](../game/nektoids/editor/parts.py).

**Turning (D-025):** `_choose(tool)` is where a tool's button and its key meet. A turn tool turns
the selected part at once (`_turn`), then turns whatever part is clicked. L and R also turn the
swimmer in the arena view: one key, one meaning (D-021).

**Undo (D-027):** [`editor/history.py`](../game/nektoids/editor/history.py) keeps whole board
states (`Board.snapshot`), not edits. At the end of `handle_event`, unless a Move is under way,
`_keep` compares the board with the last state kept and records the old one if it changed: one
step per gesture, whatever the tool. `_edit` puts a state back with `Board.restore`, in place,
because `main.py` and the arena view hold the same board.

**Delete:** `_delete_target(cell, pos)` is the single hit test. A click on a component's shape takes the component. Otherwise the wire drawn nearest the click is taken, which is the only way to reach a wire between two neighbouring parts, since it crosses no free cell. `doomed()` asks the same function, so the darkened preview is exactly what a click would remove.

**Keyboard:** the cursor is a virtual mouse.
- The arrows move `cursor` and call `_track` at its pixel.
- Enter calls `_press` then `_release` there. In the Move tool, one Enter grabs and the next drops.
- Digits pick a menu part by physical key, so they work unshifted on AZERTY.
- Letters go to `_shortcut`.

Because the cursor goes through the same code as the mouse, no tool has keyboard-only logic.

### 2.7 Drawing: [`editor/geometry.py`](../game/nektoids/editor/geometry.py), [`icons.py`](../game/nektoids/editor/icons.py), [`draw.py`](../game/nektoids/editor/draw.py)

- **`geometry.py`** (no pygame) says where a wire is drawn. It enters and leaves each cell through the midpoint of an edge, perpendicular to that edge.
  - Straight through, the wire is a segment.
  - Turning, it is the circular arc tangent to both edge normals: radius s/2 about the shared corner for a sharp 120° turn, 1.5 s for a gentle 60° one. `turn_centre` finds that centre as the point where the two edge lines meet.
  - Because the direction is the same on both sides of every edge, the drawn wire is smooth.
  - `wire_arrows` puts one arrow per crossed cell. `nearest_wire` is the hit test the Delete tool uses.
- **`icons.py`** opens the Font Awesome file at startup (D-012), once per size on a fixed ladder (by path: under pygbag, pygame-ce can't open a font from bytes in memory), and caches every glyph by size, colour and angle. The eye and the rocket turn with their part (`POINTS_TO`); the other icons stay upright.
- **`draw.py`** draws in this order:
  1. the menu and the palette;
  2. the grid, clipped to its area: the hexes (darker outside the zone), the ghost, the wires, the parts, the keyboard cursor;
  3. the status line, the separators, the tooltip, and finally the part being dragged.

  It only reads. The two scene methods it calls, `doomed()` and `_wire_start()`, are queries.

### 2.8 Tests

| File | Guards |
|---|---|
| `tests/test_hexgrid.py` | directions match the screen, pixel round trips, discs, vertical steps |
| `tests/test_board.py` | placement and stock, wire validity, the edge rule (a stress layout with its own checker), one pinned route, moves that fail leave everything unchanged |
| `tests/test_geometry.py` | arc radii and tangency, arrows, wire hit-testing |
| `tests/test_layout.py` | three columns, hit-testing, folding, zoom and pan, shortcut keys |
| `tests/test_assets.py` | the icon and text fonts ship with their licences, and are small |
| `tests/test_architecture.py` | no pygame in `sim/` or `graph/` |
| `tests/test_network.py` | the board compiled to arrays: numbering, input order, impossible wires, topological order, loops |
| `tests/test_dynamics.py` | the lag step by step, bounds for every graph, determinism, rates against an independent evaluator, loops that settle, hold, latch or oscillate |
| `tests/test_analysis.py`, `tests/test_equations.py` | the loop report and the equation text |
| `tests/test_beads.py`, `tests/test_devdrive.py` | the bead phase and its two styles, the clock, sliders, waveforms, fitting the view |
| `tests/test_scenarios.py` | the eleven example boards build, and behave as their titles say |

## 3. Questions to answer after reading

1. **Why is the router's state `(cell, heading)` and not just `cell`?** Find a case where two routes reach the same cell and only one of them may continue straight on. And what decides between two routes with the same steps and bends? (Look at the heap entries in `Board.route`.)
2. **Who may change the board?** List every call to `place`, `remove_node`, `move_node`, `rotate`, `connect` and `remove_wire`, and check that they all come from `EditorScene`. Then check that nothing in `draw.py` changes state.
3. **Trace the Wire tool by hand.** First case: press on A, move to B, release on B. Second case: click A, then click B. Which lines of `_wire` and `_end_wiring` run in each case, and what do `pressed` and `fresh` hold at each step?

## 4. Weak or untested

- **`scene.py`, `draw.py` and `icons.py` have no automated tests.** The rule is that tests never import pygame. They were checked by scripted headless runs, which are not in the repo. A good first change: pull the Wire press/release rules out into a small pure class (inputs: pressed node, released node, current source; output: the action) and unit-test it.
- **The final guard in `Board.route`** (`_uses_each_edge_once`) is never reached by any test.
- **Open bug: the arrow keys do nothing in the web build** (`pygbag game`), though they work natively. The suspected cause: the arrows scroll the page, the browser then sends a mouse move, and `handle_event` treats it as "the mouse takes over", clearing the cursor.
- **`draw.py` calls `scene._wire_start()`,** a private method, from outside the class. It should become public.
- **Refusal reasons are English strings,** and the tests compare them. Rewording a message breaks tests.
- **`node_at`, `wires_in` and `_edges_used` scan everything each time.** That's fine for 19 cells; it will need an index for large zones.
- **Routes depend on the order wires were drawn** (D-007). `test_detour_is_shortest_then_straightest` pins one route, so a change in routing shows up as a failing test instead of silently changing players' layouts.
- **Delete in a cell crossed by wires takes the nearest wire even when the click is far from it.** This lets the keyboard cursor, which sits at the cell centre, delete wires that turn. It may surprise a mouse user.

## 5. Where to go next

- **The graph's dynamics** are written (D-017, section 6) and are yours to review. What is left is
  the hook into the simulation: `thrust_rates` gives one rate per thruster, `Node.facing` says
  where it pushes, and the state `y` of shape (N, n) has to live with the agents.
- **`complexity()`**, one integer per graph that the simulation will turn into body size
  (`.claude/rules/graph.md`).
- **The web arrow-key bug** above.

## 6. The graph as dynamics, and the developer view (D-017)

This part is where `graph/` and `editor/` meet the simulation. Read D-016 and D-017 in [`decisions.md`](decisions.md) first; D-017 replaces part of
D-016.

### 6.1 What it computes

Every node has one number, its rate `y`, between 0 and `RATE_MAX = 1`: a fraction of what a wire
can carry. The rate of a node relaxes towards what its inputs ask for, like a first-order filter
with time constant `TAU = 1/60 s`:

    TAU dy/dt = F(y) - y

- a wire carries its source's rate divided by the number of wires leaving that node (a fork
  splits, so beads are conserved);
- `F` adds what arrives, applies the gain (Double ×2, Halve ÷2, Sum ×1, Difference |a − b|,
  Thruster ×1) and caps the result at `RATE_MAX`;
- eyes and sources are given, not computed. A Source emits `SOURCE_RATE = 1`.

The simulation advances this with one explicit Euler step per tick: `y + (dt / TAU) (F(y) - y)`.
That makes the controller a piece of state, like a position: `y` of shape (N, n) must be kept
from tick to tick, and it goes into the hash of the run.

### 6.2 The code

- [`graph/network.py`](../game/nektoids/graph/network.py): `Network` is the board flattened into
  numpy arrays, with no screen positions and no wire paths. `from_board` compiles a real board,
  `from_edges` builds one from kinds and pairs, so tests can make graphs the board refuses.
  `topological_order` is Kahn's algorithm, ties by index, like a build system ordering its
  dependencies; it is only used now to tell whether a graph has a loop.
  `mount` says where each node sits on the body (D-018): the board is the body seen from above,
  forward = E, the board's up the body's left, the zone's outermost cells on the rim. So a
  thruster's cell is its lever arm. `body_mounts` computes it.
- [`graph/dynamics.py`](../game/nektoids/graph/dynamics.py): `step(net, y, eyes, dt)` returns the
  rates one tick later. Each node gathers its inputs slot by slot, in a fixed order, instead of
  with a matrix product: a BLAS row computed in a batch can differ in the last bits from the same
  row computed alone, and invariant 1 forbids that. `step` refuses `dt > TAU`, because then the
  new rate would overshoot its target and could leave `[0, RATE_MAX]`.
- [`graph/analysis.py`](../game/nektoids/graph/analysis.py) and
  [`graph/equations.py`](../game/nektoids/graph/equations.py) are developer tools: the loop report
  and the equations as text. The game never calls them.
- [`editor/schematic.py`](../game/nektoids/editor/schematic.py) (state and input),
  [`schematic_draw.py`](../game/nektoids/editor/schematic_draw.py),
  [`devdrive.py`](../game/nektoids/editor/devdrive.py) (clock, sliders, waveforms, pure),
  [`beads.py`](../game/nektoids/editor/beads.py) (pure) and
  [`levels/scenarios.py`](../game/nektoids/levels/scenarios.py) make the F2 view.

### 6.3 Loops

The editor still refuses loops; the dynamics do not. A loop is feedback that the state remembers,
so it always has a trajectory from rest. What it does depends on its gain:

- below 1 (`contraction_factor`, in `network.py`), it settles to one value whatever its start;
- at 1 it can hold a value: the board "Loop of gain 1" keeps what an eye pulse left in it;
- above, it can latch or oscillate: the board "Toggle" keeps whichever stage won, and a ring of
  three inverting stages of gain 4 oscillates.

That is memory without a tank (D-015), which is why loops are a scope decision (D-017) and why the
editor still says "would close a loop".

### 6.4 The beads

The beads are a picture of the flux now, not a second model. Each wire has one number of memory, a
phase: `phase += flux dt`, modulo 1. A bead leaves the source each time it wraps, and bead k sits
at `(phase + k) * speed / flux`, so the spacing shows the rate along the whole wire at once and
nothing jumps. The catch: when a low flux changes fast, the far beads move 49 to 581 times their
steady step in one tick (`test_beads.py` measures it). Press B in the view for the belt style,
with a fixed spacing and a speed proportional to the flux, which does not do that.

### 6.5 Questions to answer after reading

1. **Why does `Network` sort each node's input slots by source index?** Which test fails if it
   does not? (Look in `test_dynamics.py` for the drawing order.)
2. **Why must `dt` not exceed `TAU`?** Work one step of a node whose target is 0.2 and whose rate
   is 0.9, with `dt / TAU = 1.5`.
3. **Why does `dt = TAU` make loops flicker?** What does a step do to a node when `dt / TAU` is 1?
   (See the last test in `test_dynamics.py`.)
4. **What does the player see when three wires leave one eye?** Is that what a player would
   expect? (The board "A fork splits the rate".)

### 6.6 Weak or untested

- **`schematic.py` and `schematic_draw.py` have no automated tests,** for the same reason as the
  editor. Everything pure in them (clock, sliders, beads, fitting) is tested.
- **`TAU` is a game parameter, not only a number:** it sets the reaction time of every path and
  the speed of every loop. At 1/60 s a ring oscillates at about 11 Hz, too fast for beads to show.
- **The sliders exist only in the developer view** (`DEV_VIEW` in `main.py`); the player's
  graph has none.

## 7. The arena view: your board in a lit arena (D-018, D-019)

F3 opens it. Read D-018 (the board is the body plan) and D-019 (eyes read light) first.

### 7.1 What it shows

Left, the arena: the light as rays, the obstacles, the lights and the swimmer, a circle (its
body) round a wedge whose tip is where it heads. Swimmers, lights and obstacles are all unit
discs. Each light sends as many rays as its power, each stopped by the first obstacle or swimmer
it meets, so their density falls as 1/r, like the light, and a shadow is where no ray goes; the
fans turn slowly, at random but the same at every run; X hides them or shows them again. I, a
developer's key, shows the light as a smoothed map instead. Nothing else is drawn in the arena.

Round the arena, since D-057, the editor's frame (section 15): the bar with Objectives, Inside,
Score and Navigator, the tabs with the level's line under them, and under the arena the
controls (start again, play or pause, a step of 0.1 s, fast forward) and the timeline (D-033).
Every button has a key, which its tooltip names; a key means the same here as in the editor
(zoom, hand and centre are the editor's own keys, and with the hand the arrows drag the view, in
both). Objectives counts each objective, with a bar (section 9); Inside shows the selected
swimmer's wiring on its body, plain: beads on the wires, a meter by each eye and thruster, no
numbers (F2 has those). Since D-022 it swims (section 8); paused, drag
the swimmer, turn it with the wheel or L and R, and watch which eye lights up and which thruster
fires.

What an eye reads (D-019): E = sum over lights of P max(0, n·s) / r, capped at 1, where n is
where the eye looks (out of its flat face, D-020) and s points at the light, and only the lights
no disc hides count. The map is what an eye looking straight at each light would read, summed
over lights. P shows, over the arena, a developer's polar plot of E(phi), what an eye would read
turned to each direction phi, one curve per eye, with a tick where it actually looks. Each light
makes a circle through the centre, pointing at it.

### 7.2 The code

- [`sim/arena.py`](../game/nektoids/sim/arena.py) and [`sim/optics.py`](../game/nektoids/sim/optics.py)
  (your father's): the arena, and the light. `visible` is the shadow test, one segment against
  one disc for every eye, light and disc, done in one numpy broadcast; `eye_rates` is what the
  game will call every tick.
- [`editor/circuit.py`](../game/nektoids/editor/circuit.py): what F2 and the panel share, taken out
  of `SchematicScene`: the network, where its parts and wires sit in a screen area, the beads.
  `schematic_draw.draw_circuit` draws one, `plain` for the panel. The F2 view is pixel for pixel
  what it was.
- [`editor/arena_layout.py`](../game/nektoids/editor/arena_layout.py), pure, like `layout.py`: where
  the run's own things sit in its frame, the controls, the timeline, the banner, and
  `control_at` and `timeline_at` for the mouse.
- [`editor/arena_view.py`](../game/nektoids/editor/arena_view.py), pure: from u (y up) to pixels
  (y down) and back, `zoom_view` and `frame` for the view buttons, `Rays` and `ray_ends` for the
  rays, the grid of the light map, `smooth` and `tone` for its greys, `polar_scale`, and
  `body_at` for the mouse.
- [`editor/arena.py`](../game/nektoids/editor/arena.py) (state and input) and
  [`arena_draw.py`](../game/nektoids/editor/arena_draw.py) (drawing), like `schematic.py` and
  `schematic_draw.py`. The map is computed only while it shows; the shadows of the obstacles
  once per arena (`still_light`), the swimmer's own again when it moves.
- [`levels/level.py`](../game/nektoids/levels/level.py): a level as data (D-028), its lights and
  obstacles as items, each a kind, a point and one setting, as a part is a kind, a cell and a
  facing; the levels themselves are JSON files in `levels/data/`, loaded by
  [`levels/arenas.py`](../game/nektoids/levels/arenas.py) in the order of `ORDER`. And
  [`levels/objectives.py`](../game/nektoids/levels/objectives.py): what a level asks, counted,
  and when a run is over (section 9).

### 7.3 Questions to answer after reading

1. **Why does `visible` skip the eye's own body?** What would the tutorial's eyes read if it did
   not? (D-018; `test_a_body_never_shadows_its_own_eyes`.)
2. **Why is the light map computed on a grid of 4-pixel cells and then smoothed and scaled,
   rather than pixel by pixel?** Count the segment–disc tests for each.
3. **Why does `light_map` with `still` give the same bits as without?** What would break that?

### 7.4 Weak or untested

- **`arena.py` and `arena_draw.py` have no automated tests,** like the other scenes; their pure
  parts do. A headless script drove every key and mouse action once before the PR.
- **The map is smoothed, the eyes are not:** a shadow's edge on screen is soft over about half a
  body radius, while an eye crossing it jumps. The polar plot is exact.

## 8. The swimmer swims: thrust against Stokes drag (D-022)

Read D-022 first. Wire the tutorial eyes to the thrusters crossed, open F3 and press Space: the
swimmer curves to the light and touches it after about 9 s. Uncrossed, it turns its back to the
light and stops in the dark.

### 8.1 What it computes

Each thruster pushes the body; the water pushes back in proportion to the speed, and at this
scale the two balance at once. So the velocity is a function of the thrust, not something that
builds up: there is no inertia, and a swimmer whose thrusters stop stops. Obstacles are hard and
slippery: a swimmer that runs into one slides round it. Since D-028 there are no walls: the plane
is open, and a swimmer that leaves the view swims on until its time is up; an arrow at the
edge of the view points to it (`arena_view.edge_marker`), so it never vanishes unseen.

The arrays, for N swimmers with k thrusters each:

| Name | Shape | Unit | What |
|---|---|---|---|
| `pos` | (N, 2) | u | centre of each body (u = base body radius) |
| `heading` | (N,) | rad | where it points, counter-clockwise from +x |
| `radius` | (N,) | u | body radius, 1 until `complexity()` exists |
| `y` | (N, n) | rate | the nodes' rates (D-017): the controller's state |
| `force` | (N, 2) | f | total push, in the body's frame; one thruster at rate 1 gives 1 f |
| `torque` | (N,) | f u | total turning push; positive turns left |
| `vel`, `spin` | (N, 2), (N,) | u/s, rad/s | how fast it moves (body frame) and turns |

The equations: F = Σ y_k f_k and T = R Σ y_k (m_k × f_k), with f_k the unit vector a thruster
pushes along, m_k where it sits in body radii (D-018), and m × f = m_x f_y − m_y f_x the 2D cross
product. Then the drag of a sphere in a viscous fluid (Stokes' law): V = F / (6πμR) and
Ω = T / (8πμR³). The intuition: viscous drag grows with speed like a damper, a bigger body is
dragged more, and much more when it spins (R³). μ is chosen so that one thruster moves a base
body at 3 u/s (`SPEED`).

The scheme is explicit Euler on position and heading: x += dt V and θ += dt Ω, with V turned by
the heading at the start of the tick. Velocity is not state, so symplectic Euler, which keeps a
position and a velocity in step, has nothing to do here. Under a constant thrust the path is a
regular polygon, which closes, so the swimmer circles without spiralling outwards.

If `dt` doubled to 1/60 s, the swimmer would be fine: at 6 u/s it moves 0.1 u a tick, and a
contact only misses an obstacle when a tick carries it about 2 u. The nodes are the limit: at
dt = TAU each tick sets y to F(y) and loops flicker (D-017); above TAU, `graph.dynamics.step`
raises.

### 8.2 The code, in the order it runs

1. [`editor/arena.py` `_tick`](../game/nektoids/editor/arena.py#L229): one call to `world.step`,
   then the eyes for the drawing are read from the state, then the beads move.
2. [`sim/world.py` `step`](../game/nektoids/sim/world.py#L37), a pure function that returns new
   arrays: move (`motion`), touch (`contact.confine`), see (`optics.eye_rates`), think
   (`graph.dynamics.step`). The order is chosen so that after a tick, y's eye columns are what the
   eyes read where the body now is, the same thing `_moved` ensures after a drag.
3. [`sim/motion.py` `thrust`](../game/nektoids/sim/motion.py#L32): a Python loop over the thrusters
   (two), with numpy across the swimmers. Thrusters are added one by one, never with `@`, so a row
   does not depend on the batch (invariant 1, as in `optics.add_lights` and `dynamics.targets`).
   Then [`stokes`](../game/nektoids/sim/motion.py#L55) and
   [`advance`](../game/nektoids/sim/motion.py#L66).
4. [`sim/contact.py` `confine`](../game/nektoids/sim/contact.py#L24): each obstacle in turn moves an
   overlapping body radially out to touching; three passes, for a crevice between two obstacles.
   A body centred exactly on an obstacle (only by dragging) leaves along +x.
5. Back in `arena.py`: `update` redraws the light map once per frame while it shows (the
   swimmer's shadow moves), and `_drag` uses `confine` too, so a dragged swimmer cannot be dropped
   into an obstacle.

Tests: [`test_motion.py`](../tests/test_motion.py) checks the physics on its own (the sphere's
4/3, which way the tutorial's thrusters turn, a straight line, a circle that does not spiral),
[`test_contact.py`](../tests/test_contact.py) checks sliding round obstacles, into a crevice
between two, and that nothing stops a body in the open, and [`test_determinism.py`](../tests/test_determinism.py) now runs the real tick: 50
swimmers give the same hash twice, and Braitenberg's fear and aggression behave.

### 8.3 Questions to answer after reading

1. **Why does `world.step` move the bodies first and read the eyes after?** What would the panel
   and the polar plot show after a tick if the order were reversed?
2. **Why does the swimmer stop the moment its eyes go dark?** What would change, in the code and
   on screen, if the body had mass?
3. **`confine` loops over obstacles in Python but handles the swimmers as a numpy axis.** Which
   count grows when flocking arrives, and why is that the right way round?

### 8.4 Weak or untested

- **Lights are not solid:** a charging swimmer ends up on top of the light.
- **Swimmers do not touch each other:** with N > 1 they pass through one another.
- **In a crevice narrower than a body,** the swimmer overlaps the obstacle by up to one tick's
  travel (under 0.02 u, less than a pixel).
- **No momentum:** an eye crossing the hard edge of a shadow stops the swimmer within a few ticks,
  since TAU = 1/60 s barely smooths it. Look for it in "Shadows", where the swimmer starts
  behind the obstacle at (19, 19).
- **`arena.py`'s tick has no automated test,** like the rest of the scene; `world.step` has. A
  headless script ran both arenas for 10 s and 20 s before the PR.

## 9. A run ends; F4 prints your board (D-023, D-024)

Read D-023 and D-024 first. In F3, wire the tutorial eyes crossed and press Space: after 8.7 s the
swimmer reaches the light, the run stops and a banner says "Done in 8.59 s". Uncrossed, it runs
out of time at 20 s. In the editor, F4 prints your board as one line of JSON in the terminal (in the browser, in
pygbag's terminal on the page).

### 9.1 What it computes

A run remembers which lights each swimmer has reached: `visited`, a boolean array of shape
(N, L), OR-ed with "reaching now" after every tick, so a visit counts once whatever comes next.
A light is reached a little before the two discs touch: when the centres are within `REACH`
= 1.2 times the sum of the radii, 2.4 u for a base body (D-029).
An objective turns that into a count, `(met, needed)`. `outcome` is a pure function of the level,
`visited` and the tick: won when every objective is met, time up at the level's limit, otherwise
`None`. Because the end is derived, never stored, going back along the timeline simply
un-ends the run.

### 9.2 The code

- [`levels/objectives.py`](../game/nektoids/levels/objectives.py): `reaching` (one numpy
  broadcast, swimmers by lights), `VisitLights.count`, `outcome`. `Objective` is a `Protocol`:
  anything with a `kind`, a `name` and a `count` is one, and `OBJECTIVES` finds its class from
  the `kind` a level's JSON names.
- [`levels/level.py`](../game/nektoids/levels/level.py): `Level.time_limit`, in each level's
  JSON file.
- [`editor/arena.py`](../game/nektoids/editor/arena.py): `visited` lives with the run and in
  `Snapshot`; `update` checks `outcome` after each tick and stops the clock at the tick the run
  ended, since `Clock.frame` hands out a whole frame's ticks at once. Play and Step do nothing
  once it is over; 0 starts again.
- [`editor/arena_draw.py`](../game/nektoids/editor/arena_draw.py): the ring round a visited
  light, "1 of 2", the banner, the time over the timeline, and the time left as a last row whose bar runs
  down to zero, red once the time is up (`_draw_row` draws every row).
- [`graph/board.py`](../game/nektoids/graph/board.py) `to_dict` and `from_dict`, and the F4
  branch in [`main.py`](../game/main.py). Wires refer to parts by their place in the list, not
  by id, since ids have gaps after a delete.
- Tests: [`test_objectives.py`](../tests/test_objectives.py), the round trip in
  [`test_board.py`](../tests/test_board.py), and in
  [`test_determinism.py`](../tests/test_determinism.py) a board that wins "Shadows": the
  crossed wiring with a Source on both thrusters, so the level is known to be winnable.

### 9.3 Questions to answer after reading

1. **Why is `outcome` computed and not stored as a flag on the scene?** What would the timeline
   need to do if it were a flag?
2. **`from_dict` draws the wires again instead of reading their paths.** When does that give a
   different picture from the one saved, and why does it never give a different network?
3. **Why does `update` set `clock.tick` back when a run ends inside a frame?**

### 9.4 Weak or untested

- **The scene's stop-at-the-end has no automated test,** like the rest of `arena.py`; `outcome`
  has, and a headless script drove both arenas to their ends before the PR.
- **The JSON has no version number,** and `from_dict` does not keep saved paths exactly.

## 10. Playing a level: edit, run, next (D-030)

Read D-030 first. `python game/main.py` now opens on level 1's board: build, press Space, watch,
Esc to change the board, and after a win Enter for the next level.

### 10.1 The code

- [`editor/router.py`](../game/nektoids/editor/router.py), pure: `Router` holds the open level
  (`index`), whether it is edited or run (`screen`), and each level's board, made from the
  level's data the first time (`Level.new_board`). `next` refuses to go past the last level.
- [`main.py`](../game/main.py) turns the router into scenes: one `EditorScene` per level, kept
  in `editors` (so undo history stays with its level), and a fresh `ArenaScene` for each run,
  with `developer=False`.
- Scenes never call `main.py`; they set `request` ("run" in the editor; "edit" or "next" in
  the run view), and the loop reads and clears it once a frame. That keeps the scenes free of
  any knowledge of each other.
- [`editor/arena.py`](../game/nektoids/editor/arena.py): `developer` switches the player's run
  view (one level, nothing touches the swimmer) from F3's; `banner_buttons` says what the end
  banner offers. Its buttons' rects come from `arena_layout.banner_rects`, pure, so tests can
  click them.

- [`editor/recording.py`](../game/nektoids/editor/recording.py), pure: every tick of the run, kept
  as it was (D-033). The run is deterministic, so the timeline restores a tick kept and, ahead of
  the furthest one run, `ArenaScene.seek` races there (`SEEK_TICKS` a frame); moving the swimmer
  by hand, in F3, cuts the recording where it happened. `_restore` copies what it puts back,
  because the next ticks change those arrays in place.

### 10.2 Questions to answer after reading

1. **Why does each level get its own `EditorScene` instead of one editor whose board changes?**
   What would undo do across levels otherwise?
2. **Why is `request` a field read by the loop, not a callback the scene calls?**
3. **What does F3 run, and why is it still useful once the player's run view exists?**

### 10.3 Weak or untested

- **`main.py`'s loop has no automated test.** A scratch script drove it through edit, run, a
  win, next level, run and Esc before the PR; `Router` itself is tested.

## 11. Around the levels: title card, Chapters, end (D-035, D-054)

Read D-035 and D-054 first. The game opens under a title card; Chapters (Tab, or its icon at
the bar's foot) lists the levels and the sandbox in a drawer. A level opened from it or by Next
level comes up under its own card, which says what it asks (D-042).

- [`editor/router.py`](../game/nektoids/editor/router.py) holds the screen (`Screen`: title,
  spec, edit, run, end), the open place (a level of the route, or `sandbox_index`) and the
  levels won this session; `unlocked` says which places the player may open, `rows` what
  Chapters shows of each.
- [`editor/shell.py`](../game/nektoids/editor/shell.py), pure: where the card and the end's
  button sit; [`shell_draw.py`](../game/nektoids/editor/shell_draw.py) draws the cards and the
  end from the router, changing nothing.
- [`main.py`](../game/main.py): `shell_event` hands the cards and the end their events;
  `choose_place` opens a place picked in Chapters; a run that is won marks its level won, which
  opens the next one in Chapters.

Questions: why does a won run mark its level won every frame it stays won, rather than once? What
would a player see in Chapters if the mark were only set when Next level is pressed?

## 12. Tutorials and hints (D-038, D-039, D-048, D-050)

Read D-038, D-039 and D-048 first. `python game/main.py` now opens on Fear, whose tutorial
introduces the objective, the tabs, the bar and Hints, once a session (D-079); only what each
step asks works, and Skip ends it. Until D-079 it walked the player through placing, turning and
wiring; the machinery for that stays, used by no level, and the tests walk the old tutorials,
kept in [`tests/data`](../tests/data).

- [`editor/tutorial.py`](../game/nektoids/editor/tutorial.py), pure: `Tutorial.from_dict` reads
  a level's `tutorial` (its `ghosts` and `steps`); `follow(Context)` moves past every step whose
  wait is over (`met`); `next` and `skip` are the box's buttons, `answer` what a key or click
  does to the tutorial, `restart` from the first step again.
  `allows(step, Action)` says what a leading step lets through; `explains` whether it holds the
  run and outlines its `panels`.
  `target_spots` finds what a step
  shows on the screen now open; `box_rect` a spot clear of the targets, the way between them
  (`_crosses`) and the step `before`.
- [`editor/tutorial_draw.py`](../game/nektoids/editor/tutorial_draw.py) draws the sparks out of
  each target (`tutorial.sparks`, D-080) and the box; the targets themselves are drawn in the
  accent by what draws them, from `panels`, set as the scene's `lit`; the ghosts by `draw.py`,
  from `EditorScene.ghosts`, which `main.py` sets every frame, with `gate`, which the editor
  and the run ask before each action that changes something (`_allowed`, `_ask`).
- [`levels/objectives.py`](../game/nektoids/levels/objectives.py): objectives now keep their
  own marks, which is what lets Leave the ring sit beside Visit every light (section 13 makes
  that any state).
- Tests: [`test_tutorial.py`](../tests/test_tutorial.py) walks Fear's tutorial as a player
  would; [`test_determinism.py`](../tests/test_determinism.py) pins Fear's winner and its two
  failures, crossed and with the eyes looking forward.

Questions: why does `follow` loop, rather than move one step? (Place an eye already turned.) Why
does the tutorial live in `main.py` rather than in the editor's scene? Why does the editor ask
the tutorial before acting, rather than `main.py` dropping the events a step does not want?
(Drop a dragged eye on the wrong cell.)

## 13. Love, and a run that can be lost (D-040)

Read D-040 first. LEVEL 1.2 is Love: the swimmer must come to the light and stay by it without
touching it, which needs a Diff on each side, Diff(Source, eye) = 1 - e.

- [`levels/objectives.py`](../game/nektoids/levels/objectives.py): an objective keeps whatever
  it needs, `start` then `keep` each tick (the module's `begin` and `follow` do it for a whole
  level). `Latched` is what most keep: their marks, ORed. `StayNear` keeps a timer per swimmer;
  `KeepOff` loses the run (`lost`), and `outcome` checks that first.
- [`editor/arena.py`](../game/nektoids/editor/arena.py): `kept` replaces `marked`, in the run
  and in each `Snapshot`; `counts()` returns a `Count` per objective, with its bar and whether
  it lost; `lost_by` says which one did, for the banner.
- [`levels/data/love.json`](../game/nektoids/levels/data/love.json): the level, written by
  `to_json`.
- Tests: [`test_objectives.py`](../tests/test_objectives.py) for the timer and the touch;
  [`test_determinism.py`](../tests/test_determinism.py) pins love's two winners (two eyes
  looking ahead, and one eye, one Diff and one thruster on the axis, D-044) and the ways to
  lose: the eyes turned out, or no Diff.

Questions: why does `StayNear.keep` freeze the timer once full rather than let it run on? Why
is LOST checked before WON in `outcome`? (Make a level with Visit every light and Don't touch.)

## 14. The score: time against parts (D-045, D-046)

Read D-045 and D-046 first. Win a level, then win it again with another board: Score, a
drawer of the run (D-057), shows your wins as points, time against parts, and the front of
those no other beats.

- [`graph/board.py`](../game/nektoids/graph/board.py): `complexity(board)`, the number of
  parts. Nothing in `sim/` reads it: every body is a sphere of radius 1 u.
- [`levels/score.py`](../game/nektoids/levels/score.py), pure: `Score(parts, ticks)` and
  `front`, the scores no other beats.
- [`editor/router.py`](../game/nektoids/editor/router.py): `record` keeps each level's
  scores for the session, in a set; `scores` gives the open level's.
- [`main.py`](../game/main.py) records a run while it stands won and hands the level's scores
  to the run; [`arena_draw.py`](../game/nektoids/editor/arena_draw.py) `_draw_wins` draws
  them in Score.
- Tests: [`test_score.py`](../tests/test_score.py) for `beats` and `front`;
  [`test_router.py`](../tests/test_router.py) for a score kept once, per level.

Questions: `main.py` records the score on every frame the run stands won; why is that one
point and not hundreds? Why are scores kept in ticks rather than seconds?

## 15. The editor's frame: the activity bar and its drawers (D-051, D-053)

Read D-051 and D-053 first, and look at the mockups. `python game/main.py`: the bar on the left,
Parts open; click Tools, then its icon again, or the arrow on the drawer's edge.

- [`editor/layout.py`](../game/nektoids/editor/layout.py), pure: `make_layout(drawer, folded,
  kinds)` places the bar's icons, the open drawer's rows (`_Rows`), the tabs and the board;
  `moved_view` slides the view when the board moves; the `*_at` functions say what is under a
  pixel.
- [`editor/scene.py`](../game/nektoids/editor/scene.py): `open_drawer`, and `_press`, which asks
  the fold handle, the bar, the tabs and the info discs before the rows and the board.
- [`editor/draw.py`](../game/nektoids/editor/draw.py): `_draw_bar`, `_draw_drawer` and
  `_draw_row`, the one row style every drawer uses; `_draw_tabs`, with the level's line under
  the tabs (D-056); `Fonts`, the fonts by their job (D-055).
- [`editor/tutorial.py`](../game/nektoids/editor/tutorial.py): `drawer_for`, the drawer a step
  opens.
- [`editor/entry.py`](../game/nektoids/editor/entry.py), pure: a part's entry at work (D-082),
  its own small circuit (`DEMOS`), its light and flames (`light`, `flames`), run by
  `Frame.frame_update` while its box is open and drawn by `draw_info` with `draw_circuit`, as
  Inside draws a board; its beads are `beads.Travelling`. Open a part's (i) in Parts.
- [`editor/wheel.py`](../game/nektoids/editor/wheel.py), pure: the Wheel at the foot of Tools
  and Parts (D-068, D-069). `offer` is what a cell offers; `slots` places the icons at a turn,
  a fraction while the Wheel slides from one turn to the next, eased by `slid` (D-083). The
  scene keeps the turn an integer and starts each slide in `_turn_wheel`. Open the sandbox,
  click an empty cell, and turn its seven parts with the mouse wheel.

Questions: why is an info disc asked before its row, in `_press`? What would the player see if
`open_drawer` did not slide the view? Why do ×2's beads leave in step with those coming in
(`Entry._keep_time`), when no other wire's beads keep time with another's? Why does
`_turn_wheel` start a slide from the turn shown, not from the turn before?

Settings and Chapters (D-054) sit at the bar's foot. Open Settings and click Fast forward, then
Chapters (Tab) and a locked level.

- [`editor/settings.py`](../game/nektoids/editor/settings.py), pure: the session's `Settings`,
  each one stepping through its choices.
- [`editor/layout.py`](../game/nektoids/editor/layout.py): `FOOT`, and `_Rows.settings` and
  `_Rows.chapters`; `chapter_row_at`, `setting_row_at`.
- [`editor/scene.py`](../game/nektoids/editor/scene.py): `_choose_place` and `_set`, which leave
  `chosen` or `request` for `main.py`; `_relayout` keeps the parts and the chapter when the
  drawer changes.

Questions: why does the scene leave the chosen place for `main.py` rather than open it itself?
Why is a row's best time in its info box rather than on the row?

The run has the same frame (D-057). Run a level, open Inside, then Tab, then Esc.

- [`editor/frame.py`](../game/nektoids/editor/frame.py), pure: `Frame`, what both screens
  inherit: the bar, one drawer at a time, the tabs and the switch, info discs, Chapters and
  Settings, tooltips, and the scrolling of a drawer whose rows do not fit (`frame_wheel`, the
  scroll bar, D-096). Each screen gives `_relayout` and `_slid`. Tested headless in
  [`test_frame.py`](../tests/test_frame.py).
- [`editor/layout.py`](../game/nektoids/editor/layout.py): `make_layout(env=Env.RUN)`, the run's
  drawers (`DRAWERS`), its switch (`SWITCH_TO`), `Goal` rows, the controls strip.
- [`editor/arena.py`](../game/nektoids/editor/arena.py): `ArenaScene(Frame)`, `_press`, which
  asks the frame first; [`arena_draw.py`](../game/nektoids/editor/arena_draw.py): `_draw_rows`
  and `_draw_controls`.
- [`main.py`](../game/main.py): `on_screen()`, the scene the tutorial's box and drawers follow;
  `run_drawer`, kept from one run to the next.

Questions: what does `_slid` do in the editor, and in the run? Why is the controls strip not an
"area" for the tutorial's box (`tutorial.is_area`)?

The Run preview and Diagnostic, called Sense until D-069 (D-058). Open Diagnostic: the main
screen runs your board where the probe stands; drag the probe on the map, then drag an eye's
knob.

- [`editor/probe.py`](../game/nektoids/editor/probe.py), pure: `Probe`, the board as it would
  run at a pose, its eyes reading the light once (nothing moves), `hold` for an eye's knob;
  `level_view`, the level seen whole in Diagnostic's map. Tested in
  [`test_probe.py`](../tests/test_probe.py).
- [`editor/scene.py`](../game/nektoids/editor/scene.py): `main` (a `MainView`, which
  `layout.main_view_for` reads off the drawer, D-069), `open_drawer` (Diagnostic shows the
  preview), `_editing`, `_probe_now`, `_hold`.
- [`editor/preview_draw.py`](../game/nektoids/editor/preview_draw.py): the preview and its
  knobs; [`draw.py`](../game/nektoids/editor/draw.py): `_draw_diagnostic`.

Questions: why does the probe read the light once, and not every tick? What would a held eye
do to a run, and why can it not?

Files (D-059): win a level twice with two boards, then open Files and click the other win.

- [`editor/router.py`](../game/nektoids/editor/router.py): `record` keeps the board with its
  score; `wins` lists them, the unbeaten first (`Won`). Tested in
  [`test_router.py`](../tests/test_router.py).
- [`editor/scene.py`](../game/nektoids/editor/scene.py): `set_wins`, `_put_back`, which only
  restores the board: `_keep`, after the click, puts the board left into the history.

Question: why does `_put_back` not call `history.record` itself?

The run opens paused, and Fear's tutorial opens in it (D-060).

- [`editor/tutorial.py`](../game/nektoids/editor/tutorial.py): `Tutorial.start`, the screen a
  tutorial opens on; `{"tab": "editor"}`, a target; `allows` lets the way to the screen a step
  waits for through, and "play" while it waits for a win.
- [`main.py`](../game/main.py): `begun`, a card gone this frame, which opens Fear's run.
- [`editor/layout.py`](../game/nektoids/editor/layout.py): `overview_view`, `shown_frame`,
  `centred_on`, Navigator's overview; [`probe.py`](../game/nektoids/editor/probe.py): `see`,
  the preview through the editor's view.

Question: why must the run's controls ask the tutorial's gate, now that Fear starts in the run?

The objectives at the foot of every run drawer, and Navigator's zoom bar (D-065):
[`layout.py`](../game/nektoids/editor/layout.py)'s `goal_area` and `zoom_bar`, `level_of` and
`value_at`, the zoom on a log scale; `arena_draw._draw_rows` draws the objectives under any
drawer.

## 16. Hints, asked for in turn (D-078)

Read D-078 first. Open Love, press ?, and take Hint 1, the idea, Hint 2, the parts, then Hint
3, the shadow; go to the Editor, where the shadow lies on the board too, and click Hint 3 to
hide it.

- [`editor/hints.py`](../game/nektoids/editor/hints.py), pure: `Hints.from_dict` reads a level's
  `hints`, its idea and its shadow (ghosts, as a tutorial writes them); `says` the lines under a
  row; `parts_line` counts the shadow's parts; `build` makes the shadow for real on a board;
  `Taken`, what the player has taken; `HintView`, what the drawer shows.
- [`editor/layout.py`](../game/nektoids/editor/layout.py): `Drawer.HINTS` in `FOOT`,
  `_Rows.hints`, `HintRow`, `hint_row_at`; the picture's square shrinks to clear the run's
  objectives.
- [`editor/frame.py`](../game/nektoids/editor/frame.py): `set_hints`, `_take_hint`, which leaves
  `asked_hint` for `main.py`; [`draw.py`](../game/nektoids/editor/draw.py): `_draw_hints` and
  `_draw_shadow`.
- [`main.py`](../game/main.py): `hints()`, the open level's, its shadow built once; the ghosts
  are the tutorial's while it leads, else the shadow's while shown.
- Tests: [`test_hints.py`](../tests/test_hints.py), where each level's shadow wins its level.

Questions: why is the Parts hint counted from the shadow rather than written in the level's
file? Why is the shadow built once per level, and not every frame?

Background: [`brief.md`](brief.md) sections 1 and 3 explain the design, and [`decisions.md`](decisions.md)
explains every rule above (D-007 to D-014 cover the editor).
