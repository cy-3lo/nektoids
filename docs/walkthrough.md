# Walkthrough: `graph/` and `editor/`

For Camille. Under D-005 you own these two packages, but their first version was written before
you joined. This page is the map: read it with the code open beside it. It takes about half an
hour, and nothing here needs Claude.

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
- turn a part with Rotate;
- drag a part with Move and watch its wires follow;
- hover with Delete to see what would go.

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
right. This module has no pygame either (tested in `tests/test_layout.py`).
- **`Layout`** is frozen. It holds the fixed rectangles, and `make_layout(folded)` builds it again when a menu group folds.
- **`View`** is how the grid is seen: the hex size and where cell (0, 0) sits on screen. `zoom` (which keeps the point under the zoom fixed) and `pan` return a new `View`. They never touch the board (D-013).
- **Hit-testing** answers "what is under this pixel": `cell_at`, `menu_item_at`, `tool_at`, `view_button_at`, `group_at`, `palette_target_at`.
- **`visible_cells`** lists every hex that shows in the grid area.
- **`TOOL_KEYS` and `VIEW_KEYS`** are the shortcut letters.

### 2.6 Input and interactive state: [`editor/scene.py`](../game/nektoids/editor/scene.py)

`EditorScene` owns everything that changes while the player works:
- the current `tool` and the `view`;
- what is being carried: `picked` and `dragging` for Add, `source`, `pressed` and `fresh` for Wire, `moving` for Move, `panning_from` for the hand, `cursor` and `carrying` for the keyboard;
- what is under the mouse: `pointed` (any grid cell) and `hover` (only zone cells);
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
- `_wire_start` says where the ghost route starts, and `_update_ghost` computes it:
  - `board.route` over an empty cell, drawn dim;
  - `board.preview` over a target, drawn bright if it may connect.

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
| `tests/test_assets.py` | the icon font ships with its licence, under 500 KB |
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

Your father wrote this part, and you review it (D-005): it is where your two packages meet the
simulation. Read D-016 and D-017 in [`decisions.md`](decisions.md) first; D-017 replaces part of
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
  numpy arrays, with no positions and no wire paths. `from_board` compiles a real board,
  `from_edges` builds one from kinds and pairs, so tests can make graphs the board refuses.
  `topological_order` is Kahn's algorithm, ties by index, like a build system ordering its
  dependencies; it is only used now to tell whether a graph has a loop.
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

Background: [`brief.md`](brief.md) sections 1 and 3 explain the design, and [`decisions.md`](decisions.md)
explains every rule above (D-007 to D-014 cover the editor).
